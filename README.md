# StrategyShifu

An HR & Staffing knowledge graph application. Upload any documents — CSV, Excel, PDF, Word, or plain text — and StrategyShifu automatically extracts entities and relationships, builds a queryable knowledge graph, and lets you ask natural language questions against your data.

## Architecture

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, React 18, Tailwind CSS |
| Backend | FastAPI (Python 3.11) |
| Graph database | Neo4j 5 Community |
| Vector database | ChromaDB |
| LLM & Embeddings | Google Gemini 1.5 Flash + text-embedding-004 |
| Ingestion | Regex NER pipeline (entity extraction, chunking, dual-store write) |

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) — runs Neo4j and ChromaDB
- Python 3.11+
- Node.js 18+
- A [Google Gemini API key](https://aistudio.google.com/app/apikey)

## Setup

### 1. Start the data services

```bash
docker compose up -d
```

Verify both containers are healthy before proceeding:

```bash
docker compose ps
```

### 2. Configure the backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

pip install -r requirements.txt

cp .env.example .env
```

Open `backend/.env` and fill in your values:

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=strategyshifu123

CHROMA_HOST=localhost
CHROMA_PORT=8001

GEMINI_API_KEY=your_key_here
```

### 3. Start the backend

```bash
uvicorn main:app --reload --port 8000
```

The API is available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### 4. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

## Usage

1. **Upload** — Go to the Upload page and drag in any supported file. The pipeline extracts text, generates embeddings, writes chunks to ChromaDB, and writes entities and relationships to Neo4j.
2. **Graph** — Navigate to the Knowledge Graph page to explore the entities and relationships extracted from your documents.
3. **Assistant** — Ask natural language questions. The AI retrieves relevant context from both ChromaDB (semantic search) and Neo4j (graph traversal), then generates a grounded answer via Gemini.

## Supported file types

| Format | Extension |
|--------|-----------|
| PDF | `.pdf` |
| Word | `.docx` |
| Excel | `.xlsx`, `.xls` |
| CSV | `.csv` |
| Plain text / Markdown | `.txt`, `.md` |

## API reference

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Service health check |
| `POST` | `/api/upload` | Upload and ingest a document |
| `GET` | `/api/uploads` | List all ingested documents |
| `DELETE` | `/api/uploads/{id}` | Delete a document and its graph/vector data |
| `GET` | `/api/graph/nodes` | All entity nodes |
| `GET` | `/api/graph/edges` | All relationship edges |
| `GET` | `/api/graph/subgraph/{docId}` | Subgraph for a specific document |
| `POST` | `/api/query` | Natural language query with dual retrieval |

## Environment variables

### `backend/.env`

| Variable | Description |
|----------|-------------|
| `NEO4J_URI` | Bolt URI for Neo4j (default: `bolt://localhost:7687`) |
| `NEO4J_USER` | Neo4j username |
| `NEO4J_PASSWORD` | Neo4j password |
| `CHROMA_HOST` | ChromaDB host (default: `localhost`) |
| `CHROMA_PORT` | ChromaDB port (default: `8001`) |
| `CHROMA_COLLECTION` | Collection name (default: `strategyshifu`) |
| `GEMINI_API_KEY` | Google Gemini API key — required for LLM answers and embeddings |
| `UPLOAD_DIR` | Directory for uploaded files (default: `./uploads`) |
| `MAX_UPLOAD_SIZE_MB` | Maximum upload size in MB (default: `50`) |
| `LOG_LEVEL` | Logging level (default: `INFO`) |
| `CORS_ORIGINS` | Allowed CORS origins (default: `http://localhost:3000`) |

### `frontend/.env.local`

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Backend URL (default: `http://localhost:8000`) |
