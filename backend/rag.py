"""
RAG (Retrieval-Augmented Generation) Pipeline
Uses ChromaDB for vector storage and Ollama for embeddings + LLM
"""
import os
import uuid
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional, Generator
import ollama
import httpx


# ── Vector DB ──────────────────────────────────────────────────────────────────
CHROMA_DIR = os.path.join(os.path.dirname(__file__), ".chroma_db")
COLLECTION_NAME = "personal_vault"

_chroma_client: Optional[chromadb.ClientAPI] = None
_collection = None


def get_chroma_collection():
    """Return (or lazily create) the ChromaDB collection."""
    global _chroma_client, _collection
    if _collection is None:
        _chroma_client = chromadb.PersistentClient(
            path=CHROMA_DIR,
            settings=Settings(anonymized_telemetry=False)
        )
        _collection = _chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
    return _collection


# ── Embeddings ─────────────────────────────────────────────────────────────────
def embed_texts(texts: List[str], model: str = "nomic-embed-text") -> List[List[float]]:
    """
    Generate embeddings via Ollama.
    Falls back to a simple hash-based placeholder if Ollama is unavailable.
    """
    embeddings = []
    for text in texts:
        try:
            response = ollama.embeddings(model=model, prompt=text)
            embeddings.append(response["embedding"])
        except Exception as e:
            raise RuntimeError(
                f"Ollama embedding failed for model '{model}'. "
                f"Make sure Ollama is running and the model is pulled. Error: {e}"
            )
    return embeddings


# ── Ingest ─────────────────────────────────────────────────────────────────────
def ingest_chunks(
    chunks: List[Dict[str, Any]],
    doc_id: str,
    embed_model: str = "nomic-embed-text"
) -> int:
    """
    Embed and store document chunks in ChromaDB.
    Returns the number of chunks stored.
    """
    if not chunks:
        return 0
    
    collection = get_chroma_collection()
    
    texts = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]
    ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
    
    embeddings = embed_texts(texts, model=embed_model)
    
    collection.add(
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids
    )
    
    return len(chunks)


def delete_document(doc_id: str) -> int:
    """Delete all chunks for a given document ID from ChromaDB."""
    collection = get_chroma_collection()
    results = collection.get(where={"source": doc_id})
    if results and results["ids"]:
        collection.delete(ids=results["ids"])
        return len(results["ids"])
    return 0


# ── Retrieve ───────────────────────────────────────────────────────────────────
def retrieve_context(
    query: str,
    n_results: int = 5,
    embed_model: str = "nomic-embed-text",
    source_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Retrieve the top-N most relevant chunks for a query.
    Optionally filter by document source filename.
    """
    collection = get_chroma_collection()
    
    if collection.count() == 0:
        return []
    
    query_embedding = embed_texts([query], model=embed_model)[0]
    
    where_filter = None
    if source_filter:
        where_filter = {"source": source_filter}
    
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(n_results, collection.count()),
        where=where_filter,
        include=["documents", "metadatas", "distances"]
    )
    
    context_chunks = []
    for i, doc in enumerate(results["documents"][0]):
        context_chunks.append({
            "text": doc,
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i]
        })
    
    return context_chunks


# ── Generate ───────────────────────────────────────────────────────────────────
def build_prompt(query: str, context_chunks: List[Dict[str, Any]]) -> str:
    """Build a RAG prompt from retrieved context."""
    if not context_chunks:
        context_str = "No relevant documents were found in your vault."
    else:
        context_parts = []
        for i, chunk in enumerate(context_chunks, start=1):
            source = chunk["metadata"].get("source", "Unknown")
            page = chunk["metadata"].get("page", "?")
            context_parts.append(
                f"[Source {i}: {source}, Page {page}]\n{chunk['text']}"
            )
        context_str = "\n\n---\n\n".join(context_parts)
    
    return f"""You are a helpful personal AI assistant. You have access to the user's private documents stored locally in their Personal Data Vault. Use the provided context to answer the user's question accurately and helpfully.

If the answer is not found in the context, say so clearly and honestly. Do NOT make up information.
Always cite the source document name when referencing specific information.

CONTEXT FROM YOUR VAULT:
{context_str}

USER QUESTION:
{query}

ANSWER:"""


def chat_stream(
    query: str,
    llm_model: str = "llama3",
    embed_model: str = "nomic-embed-text",
    n_results: int = 5,
    source_filter: Optional[str] = None
) -> Generator[str, None, None]:
    """
    Full RAG pipeline: retrieve → build prompt → stream LLM response.
    Yields text tokens as they arrive.
    """
    # 1. Retrieve context
    context_chunks = retrieve_context(
        query, n_results=n_results,
        embed_model=embed_model,
        source_filter=source_filter
    )
    
    # 2. Build prompt
    prompt = build_prompt(query, context_chunks)
    
    # 3. Stream from Ollama
    stream = ollama.chat(
        model=llm_model,
        messages=[{"role": "user", "content": prompt}],
        stream=True
    )
    
    for chunk in stream:
        token = chunk["message"]["content"]
        if token:
            yield token


def chat_with_sources(
    query: str,
    llm_model: str = "llama3",
    embed_model: str = "nomic-embed-text",
    n_results: int = 5,
    source_filter: Optional[str] = None
) -> Dict[str, Any]:
    """
    Non-streaming RAG: returns full response + source metadata.
    """
    context_chunks = retrieve_context(
        query, n_results=n_results,
        embed_model=embed_model,
        source_filter=source_filter
    )
    
    prompt = build_prompt(query, context_chunks)
    
    response = ollama.chat(
        model=llm_model,
        messages=[{"role": "user", "content": prompt}],
        stream=False
    )
    
    answer = response["message"]["content"]
    sources = list({c["metadata"].get("source") for c in context_chunks})
    
    return {
        "answer": answer,
        "sources": sources,
        "context_chunks": context_chunks
    }


# ── Stats ──────────────────────────────────────────────────────────────────────
def get_vault_stats() -> Dict[str, Any]:
    """Return basic stats about the vector store."""
    collection = get_chroma_collection()
    count = collection.count()
    
    sources = set()
    if count > 0:
        all_meta = collection.get(include=["metadatas"])
        for m in all_meta["metadatas"]:
            if m and "source" in m:
                sources.add(m["source"])
    
    return {
        "total_chunks": count,
        "total_documents": len(sources),
        "documents": list(sources)
    }


def check_ollama_status(host: str = "http://localhost:11434") -> Dict[str, Any]:
    """Check if Ollama is running and list available models."""
    try:
        response = httpx.get(f"{host}/api/tags", timeout=3.0)
        if response.status_code == 200:
            data = response.json()
            models = [m["name"] for m in data.get("models", [])]
            return {"running": True, "models": models}
        return {"running": False, "models": []}
    except Exception:
        return {"running": False, "models": []}
