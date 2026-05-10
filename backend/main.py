"""
FastAPI Backend for Local-First Personal AI Data Vault
All data stays on your machine. No cloud required.
"""
import os
import uuid
import shutil
import json
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

from parser import parse_document
from rag import (
    ingest_chunks, delete_document, chat_stream,
    chat_with_sources, get_vault_stats, check_ollama_status
)

# ── App Setup ──────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Personal AI Data Vault API",
    description="Local-first RAG system — your data never leaves your machine.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Local only — this is fine for a local app
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Storage Paths ──────────────────────────────────────────────────────────────
UPLOAD_DIR = Path(__file__).parent / "uploads"
METADATA_FILE = Path(__file__).parent / "documents.json"
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
UPLOAD_DIR.mkdir(exist_ok=True)

# Serve frontend static files
if FRONTEND_DIR.exists():
    app.mount("/app", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


# ── Document Metadata Store ────────────────────────────────────────────────────
def load_metadata() -> dict:
    if METADATA_FILE.exists():
        with open(METADATA_FILE, "r") as f:
            return json.load(f)
    return {}


def save_metadata(data: dict):
    with open(METADATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ── Models ─────────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    query: str
    llm_model: str = "llama3"
    embed_model: str = "nomic-embed-text"
    n_results: int = 5
    source_filter: Optional[str] = None
    stream: bool = True


class OllamaConfig(BaseModel):
    llm_model: str = "llama3"
    embed_model: str = "nomic-embed-text"


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "Personal AI Data Vault is running. Your data stays local."}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ollama/status")
def ollama_status():
    """Check if Ollama is running and which models are available."""
    return check_ollama_status()


# ── Document Upload & Ingest ───────────────────────────────────────────────────

@app.post("/documents/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    llm_model: str = "llama3",
    embed_model: str = "nomic-embed-text"
):
    """Upload and ingest a document into the vault."""
    allowed_extensions = {".pdf", ".docx", ".txt", ".md", ".markdown", ".html", ".htm"}
    ext = Path(file.filename).suffix.lower()
    
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {allowed_extensions}"
        )
    
    doc_id = str(uuid.uuid4())
    safe_filename = f"{doc_id}{ext}"
    file_path = UPLOAD_DIR / safe_filename
    
    # Save file
    try:
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")
    
    # Parse and ingest
    try:
        chunks = parse_document(str(file_path), file.filename)
        chunk_count = ingest_chunks(chunks, doc_id=file.filename, embed_model=embed_model)
    except Exception as e:
        # Clean up the saved file on error
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Failed to process document: {e}")
    
    # Save metadata
    metadata = load_metadata()
    metadata[doc_id] = {
        "id": doc_id,
        "filename": file.filename,
        "stored_path": str(file_path),
        "ext": ext,
        "size": len(content),
        "chunk_count": chunk_count,
        "embed_model": embed_model
    }
    save_metadata(metadata)
    
    return {
        "success": True,
        "doc_id": doc_id,
        "filename": file.filename,
        "chunk_count": chunk_count,
        "message": f"Successfully indexed {chunk_count} chunks from '{file.filename}'"
    }


@app.get("/documents")
def list_documents():
    """List all documents in the vault."""
    metadata = load_metadata()
    return {
        "documents": list(metadata.values()),
        "total": len(metadata)
    }


@app.delete("/documents/{doc_id}")
def remove_document(doc_id: str):
    """Remove a document and all its embeddings from the vault."""
    metadata = load_metadata()
    
    if doc_id not in metadata:
        raise HTTPException(status_code=404, detail="Document not found.")
    
    doc_meta = metadata[doc_id]
    filename = doc_meta["filename"]
    
    # Delete from vector store
    deleted_chunks = delete_document(filename)
    
    # Delete stored file
    stored_path = Path(doc_meta.get("stored_path", ""))
    if stored_path.exists():
        stored_path.unlink()
    
    # Remove from metadata
    del metadata[doc_id]
    save_metadata(metadata)
    
    return {
        "success": True,
        "message": f"Removed '{filename}' and {deleted_chunks} chunks from the vault."
    }


# ── Chat / Query ───────────────────────────────────────────────────────────────

@app.post("/chat")
def chat(request: ChatRequest):
    """
    Query your vault. Returns a streaming response if stream=True,
    or a full JSON response with sources if stream=False.
    """
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    
    if request.stream:
        def token_generator():
            try:
                for token in chat_stream(
                    query=request.query,
                    llm_model=request.llm_model,
                    embed_model=request.embed_model,
                    n_results=request.n_results,
                    source_filter=request.source_filter
                ):
                    yield token
            except Exception as e:
                yield f"\n\n[Error: {str(e)}]"
        
        return StreamingResponse(token_generator(), media_type="text/plain")
    else:
        try:
            result = chat_with_sources(
                query=request.query,
                llm_model=request.llm_model,
                embed_model=request.embed_model,
                n_results=request.n_results,
                source_filter=request.source_filter
            )
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


# ── Stats ──────────────────────────────────────────────────────────────────────

@app.get("/vault/stats")
def vault_stats():
    """Get stats about the vault: total chunks, documents, etc."""
    stats = get_vault_stats()
    metadata = load_metadata()
    stats["documents_metadata"] = list(metadata.values())
    return stats


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
