# AI Data Vault

A local-first AI-powered data vault and retrieval system built using FastAPI, Ollama, and local LLMs. The application enables users to upload, process, index, and query documents using Retrieval-Augmented Generation (RAG) pipelines entirely on local infrastructure.

---

## Features

* Local AI inference using Ollama
* Retrieval-Augmented Generation (RAG)
* Document ingestion and indexing
* Semantic search using embeddings
* FastAPI backend with REST endpoints
* Browser-based frontend interface
* Local vector embeddings with `nomic-embed-text`
* Privacy-focused architecture (no cloud dependency)
* Real-time querying of uploaded knowledge base

---

## Tech Stack

| Layer            | Technology               |
| ---------------- | ------------------------ |
| Backend          | Python, FastAPI          |
| AI Runtime       | Ollama                   |
| LLM              | Llama 3                  |
| Embeddings       | nomic-embed-text         |
| API Server       | Uvicorn                  |
| Vector Retrieval | Local embedding pipeline |
| Environment      | Python 3.11              |

---

## System Architecture

```text
                ┌──────────────────────┐
                │      Frontend UI     │
                └──────────┬───────────┘
                           │
                           ▼
                ┌──────────────────────┐
                │    FastAPI Backend   │
                └──────────┬───────────┘
                           │
        ┌──────────────────┴──────────────────┐
        ▼                                     ▼
┌──────────────────┐              ┌──────────────────┐
│  Embedding Model │              │     LLM Model    │
│ nomic-embed-text │              │      llama3      │
└─────────┬────────┘              └─────────┬────────┘
          │                                  │
          ▼                                  ▼
    ┌───────────┐                    ┌──────────────┐
    │ Vector DB │◄──────────────────►│ RAG Pipeline │
    └───────────┘                    └──────────────┘
```

---

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/ai-data-vault.git
cd ai-data-vault
```

---

### 2. Create Virtual Environment

```bash
py -3.11 -m venv .venv
```

Activate environment:

#### Windows PowerShell

```powershell
.\.venv\Scripts\Activate.ps1
```

---

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 4. Install Ollama

Download Ollama:

[https://ollama.com/download](https://ollama.com/download)

---

### 5. Pull Required Models

```bash
ollama pull llama3
ollama pull nomic-embed-text
```

---

## Running the Project

Navigate to backend:

```bash
cd backend
```

Start the server:

```bash
uvicorn main:app --reload
```

Application URLs:

```text
Backend API:
http://localhost:8000

Frontend App:
http://localhost:8000/app
```

---

## API Endpoints

| Endpoint | Method | Description               |
| -------- | ------ | ------------------------- |
| `/`      | GET    | Health check              |
| `/app`   | GET    | Frontend interface        |
| `/docs`  | GET    | Swagger API documentation |

---

## Example Workflow

1. Upload documents into the system
2. Documents are chunked and embedded
3. Embeddings are stored locally
4. User asks a question
5. Relevant chunks are retrieved
6. LLM generates contextual answer

---

## Project Structure

```text
ai-data-vault/
│
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   ├── .venv/
│   └── ...
│
├── frontend/
│   └── ...
│
├── README.md
└── .gitignore
```

---

## Why This Project Matters

This project demonstrates practical implementation of:

* Retrieval-Augmented Generation (RAG)
* Local LLM deployment
* Semantic vector search
* FastAPI backend engineering
* AI application architecture
* Privacy-preserving AI systems
* Production-oriented AI workflows

---

## Future Improvements

* Multi-user authentication
* Persistent vector database integration
* Docker deployment
* Streaming LLM responses
* Hybrid search (BM25 + vector)
* PDF/image OCR pipeline
* Cloud deployment support
* Chat history memory

---

## Deployment Ideas

This project can later be deployed using:

* Render
* Railway
* Hugging Face Spaces
* Docker + VPS
* AWS EC2
* Azure App Services
* Google Cloud Run

---

## License

MIT License

---

## Author

Developed by Rihen Moradia

GitHub: (https://github.com/mattperrymatt45-pixel)
