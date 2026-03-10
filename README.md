# MCP RAG Server

A Model Context Protocol (MCP) server that exposes a RAG (Retrieval-Augmented Generation) pipeline over HTTP, with OAuth 2.1 authentication. Clients such as VS Code can connect to it, ingest PDF documents, and query them using natural language.

## Overview

```
┌─────────────────────┐        OAuth 2.1           ┌──────────────────┐
│   MCP Client        │ ◄──── token flow ────────► │  Scalekit        │
│  (e.g. VS Code)     │                            │  (auth server)   │
└────────┬────────────┘                            └──────────────────┘
         │  Bearer token
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI App                              │
│                                                                 │
│  /.well-known/oauth-protected-resource  (public, RFC 9728)      │
│                                                                 │
│  AuthMiddleware  ──► validates JWT (issuer + audience + scope)  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                  FastMCP (MCP tools)                     │   │
│  │                                                          │   │
│  │  ingest_data_dir ──► LlamaParse ──► ChromaDB (write)     │   │
│  │  query_documents ──► ChromaDB similarity search          │   │
│  │  get_db_status   ──► ChromaDB collection count           │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────┐
│  ChromaDB           │  (persisted locally in ./chromadb/)
│  Collection: rag_mcp│
└─────────────────────┘
```

### How it works

1. **Discovery** — When a client connects, the server's `/.well-known/oauth-protected-resource` endpoint returns metadata pointing to the Scalekit authorization server (RFC 9728).
2. **Authentication** — The client obtains a Bearer token from Scalekit via OAuth 2.1 and sends it with every request.
3. **Token validation** — `AuthMiddleware` validates the JWT on every request (except `/.well-known/`), checking issuer, audience, and — for `tools/call` requests — the required scopes (`mcp:rag:ingest`, `mcp:rag:search:read`).
4. **Ingestion** — The `ingest_data_dir` tool reads all PDFs from `./data/`, parses them with LlamaParse, and stores the text chunks in ChromaDB. Already-ingested files are skipped.
5. **Querying** — The `query_documents` tool runs a semantic similarity search against ChromaDB and returns ranked results with source file and similarity score.

## Tech Stack

### Server & API
| Component | Library | Purpose |
|---|---|---|
| MCP framework | [FastMCP](https://github.com/jlowin/fastmcp) `>=3.1.0` | Exposes Python functions as MCP tools over HTTP |
| Web framework | [FastAPI](https://fastapi.tiangolo.com/) `>=0.135.1` | HTTP routing, middleware, well-known endpoints |
| ASGI server | [Uvicorn](https://www.uvicorn.org/) | Runs the FastAPI + MCP app |

### Authentication
| Component | Library | Purpose |
|---|---|---|
| OAuth 2.1 / token validation | [Scalekit SDK](https://scalekit.com/) `>=2.5.0` | Bearer token issuance and JWT validation |
| Auth middleware | Custom `AuthMiddleware` (Starlette) | Validates tokens on every request, bypasses `/.well-known/` |
| Resource metadata | RFC 9728 `/.well-known/oauth-protected-resource` | Enables VS Code MCP client to auto-discover the auth server |

### RAG Pipeline
| Component | Library | Purpose |
|---|---|---|
| PDF parsing | [LlamaParse](https://github.com/run-llama/llama_cloud) (`llama-cloud-services >=0.6.94`) | Cloud-based PDF parsing with high fidelity |
| Document loading | [LlamaIndex](https://www.llamaindex.ai/) `llama-index-core >=0.12`, `llama-index-readers-file` | `SimpleDirectoryReader` for loading and chunking documents |
| Vector database | [ChromaDB](https://www.trychroma.com/) `>=1.5.4` | Persistent local vector store for document embeddings |

### Configuration
| Component | Library | Purpose |
|---|---|---|
| Environment config | [python-decouple](https://github.com/HBNetwork/python-decouple) `>=3.8` | Reads settings from `.env` file |

### Requirements
- Python `>=3.13`
- [uv](https://github.com/astral-sh/uv) (recommended package manager)

## Environment Variables

Copy `.env.example` to `.env` and fill in the values:

```env
LLAMA_CLOUD_API_KEY=          # LlamaParse API key
SCALEKIT_ENVIRONMENT_URL=     # e.g. https://<your-org>.scalekit.dev
SCALEKIT_CLIENT_ID=           # Scalekit client ID
SCALEKIT_CLIENT_SECRET=       # Scalekit client secret
SCALEKIT_RESOURCE_METADATA_URL=  # e.g. http://localhost:10000/.well-known/oauth-protected-resource/mcp
SCALEKIT_AUDIENCE_NAME=       # e.g. http://localhost:10000/mcp/
METADATA_JSON_RESPONSE=       # JSON string for the well-known metadata response
PORT=10000                    # Server port (default: 10000)
```

## Running the Server

```bash
# Install dependencies
uv sync

# Start the server
uv run main
```

The server starts on `http://localhost:10000` by default (configurable via `PORT`).

## Project Structure

```
mcp-rag-server/
├── main.py              # FastAPI app setup, mounts MCP server and auth middleware
├── auth.py              # Scalekit JWT validation middleware + well-known endpoint
├── config.py            # Typed settings loaded from .env via python-decouple
├── rag_mcp_server.py    # MCP tool definitions (ingest, query, status)
├── data/                # Drop PDF files here to be ingested
├── chromadb/            # Persistent ChromaDB vector store (auto-created)
├── .env                 # Local environment variables (not committed)
└── .env.example         # Template for required environment variables
```

## MCP Tools

| Tool | Parameters | Description |
|---|---|---|
| `ingest_data_dir` | — | Parses and ingests all PDFs from `./data/` into ChromaDB. Skips files already present in the collection. |
| `query_documents` | `query` (str), `n_results` (int, default 2) | Semantic similarity search over ingested documents. Returns ranked results with content, source file, and similarity score. |
| `get_db_status` | — | Returns the number of document chunks currently stored in the vector database. |

### Scopes

Tool calls require the Bearer token to carry the following OAuth scopes:

| Scope | Purpose |
|---|---|
| `mcp:rag:ingest` | Required to call `ingest_data_dir` |
| `mcp:rag:search:read` | Required to call `query_documents` |

## Connecting from VS Code

Add the following to your `mcp.json`:

```json
{
  "servers": {
    "rag-mcp-server": {
      "type": "http",
      "url": "http://localhost:10000/mcp/"
    }
  }
}
```

VS Code will automatically discover the auth server via the `/.well-known/oauth-protected-resource` endpoint and prompt you to authenticate.

## Notes

- The ChromaDB collection name is `rag_mcp` (set in `config.py`).
- Duplicate ingestion is prevented by tracking ingested file names in the collection metadata.
- The `METADATA_JSON_RESPONSE` env var must be a single-line JSON string with no surrounding quotes.
- `SCALEKIT_AUDIENCE_NAME` must exactly match the `aud` claim in the JWT issued by Scalekit (including trailing slash if present).

