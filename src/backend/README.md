## Backend Service (DeepSeek Agent + RAG + MCP)

This backend powers the NiceGUI frontend in the parent `Client_Server/` workspace. It exposes a FastAPI service that combines:

- DeepSeek chat completions with auto tool-calling.
- A Retrieval-Augmented-Generation (RAG) pipeline over `source_documents/` (per-file enable switches, FAISS indexes, MiniLM embeddings).
- A Model Context Protocol (MCP) aggregator that fans out to child tools (system info, MySQL, Bilibili search, pandas/matplotlib utilities, etc.).

The backend also manages uploads, knowledge-base manifests, API key storage, and a safety-checked Agent loop that the frontend can toggle per conversation.

---

## Features

- **REST API surface** for chat, file uploads, KB management, settings, and tool routing.
- **Auto Agent selection**: `/agent/ask` routes obvious intents to specific tools (system info, disk usage, B 站搜索) and otherwise reuses the same `ai_agent` loop that powers `/agent/run`.
- **MCP bridge**: `backend/client.py` streams DeepSeek responses and transparently calls `mcp_service/service.py`, which in turn delegates to the scripts under `mcp_service/tools/`.
- **RAG enable/disable per file**: `_kb_manifest.json` tracks which uploads are indexed, their FAISS store IDs, and timestamps.
- **Configuration persistence** via `mcp_settings.json` (API keys, MySQL DSN) plus runtime overrides through dedicated endpoints.

---

## Project Structure (backend portion)

```
backend/
├── backend_main.py        # FastAPI app entrypoint
├── client.py              # DeepSeek streaming agent + tool orchestration
├── rag_system.py          # RAG engine (MiniLM + FAISS)
├── tool_specs.py          # Shared tool schema injected into DeepSeek
├── models/                # SentenceTransformer model files
└── ...
mcp_service/
├── service.py             # MCP aggregator
└── tools/                 # Child MCP servers (system_info, mysql, bilibili, ...)
source_documents/          # User uploaded KB files (per-file switches)
faiss_store/               # Persisted FAISS indexes per KB file
temp_uploads/              # Transient chat attachments
mcp_settings.json          # Persisted API keys + MCP server configs
```

---

## Prerequisites

- Python 3.10+ (project currently developed on CPython 3.11/3.12).
- Git, pip, and (optional) uvicorn CLI.
- For MCP tools: MySQL instance (if you plan to use `mysql_tool`), internet access for Bilibili API, and a DeepSeek API key.

Recommended local setup:

```bash
cd Client_Server
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

> ❗ Do **not** commit `.venv/`. Dependencies are tracked via `requirements.txt`.

---

## Configuration

Environment variables (or entries in `mcp_settings.json`) control runtime behavior:

| Variable | Purpose |
| --- | --- |
| `DEEPSEEK_API_KEY` | Required for calling DeepSeek chat/completions. Set before launching backend. |
| `DEEPSEEK_BASE_URL` | Optional, defaults to `https://api.deepseek.com`. |
| `AGENT_API_KEY` | Optional. If set, `/agent/ask` and `/agent/run` require matching `X-API-Key` header. |
| `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE` | Used by `mysql_tool`. Can be persisted via `/settings` or set transiently via `/set_mysql_env`. |
| `BACKEND_URL` | Frontend-only; tells NiceGUI which backend URL to hit. |

`mcp_settings.json` stores the same information on disk so restarts keep your settings. Use `/settings`, `/set_mysql_env`, and `/set_deepseek_env` to manage these without editing JSON manually.

Directory expectations (auto-created if missing):

- `source_documents/` – KB uploads. `_kb_manifest.json` lives here.
- `faiss_store/` – FAISS indexes per file (subdirectories hashed by store_id).
- `temp_uploads/` – transient chat attachments.
- `models/all-MiniLM-L6-v2/` – embedding model files for RAG.

---

## Running the Backend

Activate your venv and start uvicorn from the repository root:

```bash
cd Client_Server
uvicorn backend.backend_main:app --host 0.0.0.0 --port 8001 --reload
```

Key startup log messages:

- `[INFO] 初始化 RAG 引擎…` / `[INFO] RAG 引擎就绪！` when FAISS + embeddings load.
- `[WARN] DEEPSEEK_API_KEY 未设置…` if you forgot to export the key.

The NiceGUI frontend expects the backend on `http://127.0.0.1:8001` (adjust `BACKEND_URL` if you change ports).

---

## Core Endpoints

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/chat` | Streamed RAG conversation (non-Agent mode). |
| `POST` | `/agent/ask` | Single-shot Agent request. Performs API-key validation, keyword routing, and full DeepSeek auto-tool loop when needed. |
| `POST` | `/agent/run` | Full CLI-style agent loop reused by `/agent/ask` fallback. |
| `POST` | `/mcp/call` | Directly call a named MCP tool (primarily for debugging). |
| `POST` | `/upload` | Upload temporary chat attachments. |
| `POST` | `/upload_kb` | Upload knowledge-base files (PDF, TXT, DOCX, XLSX, CSV, JSON). |
| `GET` | `/files` | List KB files with enabled/indexed flags. |
| `POST` | `/files/{filename}/toggle` | Enable/disable a KB file (triggers FAISS index ops). |
| `GET`/`POST` | `/settings` | Persist DeepSeek + MySQL settings to disk. |
| `POST` | `/set_mysql_env`, `/set_deepseek_env` | Apply settings to the running process without touching disk. |

The FastAPI app also exposes `/docs` (Swagger UI) and `/redoc` for interactive exploration.

---

## Agent & Tool Flow

1. Frontend calls `/agent/ask` with a prompt (optional `server`/`tool`).
2. Backend enforces API keys + rate limits, then:
	- If `server/tool` specified → call `_call_mcp_tool()` directly.
	- Else if keywords match (`cpu`, `磁盘`, `b站`, etc.) → deterministic MCP tool call.
	- Else → `_run_agent_loop()` imports `backend.client.ai_agent`, injects shared tool schemas from `tool_specs.py`, and lets DeepSeek decide which tools to call.
3. `backend/client.py` streams assistant output and uses `fastmcp.Client` to call `mcp_service/service.py`.
4. The MCP aggregator spawns the requested child tool script, relays payload `{args, meta, prompt}`, and normalizes responses back to the agent.

To add a new tool:

1. Create a script in `mcp_service/tools/` with `@mcp.tool()` functions (see existing modules for patterns).
2. Register it in `CHILD_SERVERS` inside `mcp_service/service.py`.
3. Add its schema to `backend/tool_specs.py` so DeepSeek knows the function signature.
4. (Optional) extend `ROUTER_RULES` in `backend_main.py` if you want keyword routing.

---

## Frontend Integration

The NiceGUI app (`Client_Server/main.py`) uses `BackendClient` (`api.py`) to call the backend. Ensure `BACKEND_URL` matches the FastAPI host/port, then start the frontend (e.g., `python main.py`) after the backend is running.

Agent mode in the UI simply toggles whether `send_message()` calls `/chat` or `/agent/ask`. All KB management, MCP selection dialogs, and settings forms route to the endpoints listed above.

---

## Troubleshooting

- **DeepSeek key missing**: Set `DEEPSEEK_API_KEY` or POST `/settings` with `{"deepseek_api_key": "..."}`. Otherwise `/agent/*` will raise 401/500 during LLM calls.
- **MySQL tool returns empty rows**: Verify `MYSQL_*` envs (or `/settings` payload) match your DB and the query is `SELECT` based. Logs are appended to `mcp_service/mcp_service_error.log` when child tools fail.
- **Bilibili tool errors**: Requires outbound HTTPS. Inspect `agent_router_error.log` for payloads; the tool now depends on `httpx`.
- **FAISS index mismatch**: Delete the relevant folder under `faiss_store/` plus the entry in `_kb_manifest.json`, then re-upload the KB file.

Logs: runtime errors are appended to `agent_run_error.log`, `agent_auto_route_error.log`, `agent_router_error.log`, and `mcp_call_error.log`. Since they may contain absolute paths, avoid committing them to Git.

---

## Contribution Guidelines

- Follow the existing pattern of deriving paths via `Path(__file__).resolve()` to avoid hard-coding developer-specific locations.
- Keep secrets out of Git—use environment variables or `.env` files listed in `.gitignore`.
- Run `python -m py_compile backend/backend_main.py backend/client.py` (or `ruff`, `pytest`, etc. if available) before pushing.
- Update `requirements.txt` whenever MCP tool dependencies change.

Happy hacking! If you add new endpoints or tools, document them here so the rest of the team can discover them quickly.
