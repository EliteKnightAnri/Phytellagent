import json
import os
import uvicorn
import shutil
from uuid import uuid4
from typing import List, Optional, Dict
from openai import AsyncOpenAI
from fastapi import FastAPI, File, UploadFile, Request, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from fastapi.responses import FileResponse
from datetime import datetime
import hashlib
from docx import Document
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from pydantic import BaseModel
from fastmcp import Client as MCPClient
import traceback
import datetime as _dt
from typing import Dict
from pydantic import BaseModel as PydanticBaseModel
import importlib
from pathlib import Path as _Path

try:
    from .tool_specs import get_tool_schemas
except ImportError:  # pragma: no cover - fallback when running as script
    from tool_specs import get_tool_schemas  # type: ignore

# === 导入知识图谱模块 ===
try:
    from knowledge_graph.tool import kg_query_tool
except Exception as e:
    print(f"[WARN] KG 模块不可用: {e}")
    kg_query_tool = None


# === 导入 RAG 模块（更稳健的加载：支持多种运行上下文） ===
RAGSearch = None
try:
    # 优先尝试按文件路径动态加载，保证在任意工作目录下都能找到同目录下的 rag_system.py
    rag_path = Path(__file__).resolve().parent / "rag_system.py"
    if rag_path.exists():
        import importlib.util
        spec = importlib.util.spec_from_file_location("rag_system_local", str(rag_path))
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            RAGSearch = getattr(mod, "RAGSearch", None)
    # 回退：尝试常规导入路径（兼容不同的包/模块布局）
    if RAGSearch is None:
        try:
            from Client_Server.backend.rag_system import RAGSearch as _R
            RAGSearch = _R
        except Exception:
            try:
                from rag_system import RAGSearch as _R2
                RAGSearch = _R2
            except Exception:
                print("[WARN] 未找到 rag_system.py，RAG 功能将无法使用。")
                RAGSearch = None
except Exception as _e:
    print(f"[WARN] 加载 rag_system 失败: {_e}")
    RAGSearch = None


BASE_DIR = Path(__file__).resolve().parent  # .../Client_Server/backend
ROOT_DIR = BASE_DIR.parent                # .../Client_Server

ALLOWED_KB_EXTS = {'.pdf', '.txt', '.md', '.docx', '.csv', '.xlsx', '.json'}
# 检查知识库上传文件的扩展名是否在白名单内
def _kb_ext_ok(filename: str) -> bool:
    _, ext = os.path.splitext(filename or "")
    return ext.lower() in ALLOWED_KB_EXTS


app = FastAPI(title="DeepSeek Agent Backend (RAG Integrated)", version="2.0")

# === 配置 DeepSeek API 客户端（从环境读取，避免把密钥硬编码在代码中） ===
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
if not DEEPSEEK_API_KEY:
    print("[WARN] DEEPSEEK_API_KEY 未设置（DeepSeek 大模型调用将失败）")

client = AsyncOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL
)

rag_engine = None

# === 知识库 & 清单（用于“按文件开关启用/禁用”）===
KB_DIR = str((ROOT_DIR / "source_documents").resolve())
os.makedirs(KB_DIR, exist_ok=True)

# 用 JSON 记录每个知识库文件的状态（启用/禁用、是否已索引、store_id、更新时间等）
MANIFEST_PATH = os.path.join(KB_DIR, "_kb_manifest.json")
MANIFEST_FILENAME = "_kb_manifest.json"
FAISS_DIR = str((ROOT_DIR / "faiss_store").resolve())
EMBED_MODEL_PATH = str((ROOT_DIR / "models" / "all-MiniLM-L6-v2").resolve())
TEMP_DIR = str((ROOT_DIR / "temp_uploads").resolve())
os.makedirs(TEMP_DIR, exist_ok=True)

# 全局设置文件（保存 API Key 等运行时配置）
SETTINGS_PATH = str((ROOT_DIR / "mcp_settings.json").resolve())


def _ensure_mysql_env(payload: dict) -> dict:
    """Ensure mcpServers.mysql.env exists; seed defaults when missing."""
    mcp_servers = payload.setdefault("mcpServers", {})
    mysql_cfg = mcp_servers.setdefault("mysql", {})
    mysql_cfg.setdefault("command", "uv")
    mysql_cfg.setdefault("args", [
        "--directory",
        "mcp_service/tools",
        "run",
        "mysql_tool.py",
    ])
    return mysql_cfg.setdefault("env", {})


def _load_settings() -> dict:
    if not os.path.exists(SETTINGS_PATH):
        return {}
    try:
        with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _save_settings(data: dict) -> None:
    try:
        with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _make_store_id(filename: str) -> str:
    """为知识库文件生成稳定的索引存储 ID（用于索引目录名/标识符）"""
    return hashlib.sha1(filename.encode("utf-8")).hexdigest()[:16]

def _load_manifest() -> dict:
    """从磁盘加载知识库清单；不存在或损坏时返回空结构，保证服务可用"""
    if not os.path.exists(MANIFEST_PATH):
        return {"files": {}}
    try:
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "files" not in data or not isinstance(data["files"], dict):
            return {"files": {}}
        return data
    except Exception:
        return {"files": {}}

def _save_manifest(data: dict) -> None:
    """将清单写回磁盘（持久化 enabled/indexed/store_id 等状态）"""
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _ensure_manifest_entry(data: dict, filename: str) -> dict:
    """确保某个知识库文件在清单里有记录；若无则创建默认条目并返回该条目"""
    files = data.setdefault("files", {})
    if filename not in files:
        files[filename] = {
            "enabled": False,
            "indexed": False,
            "store_id": _make_store_id(filename),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
    return files[filename]

def _sync_manifest_with_disk() -> dict:
    """将 manifest 与磁盘 KB_DIR 对齐：补齐新增文件、清理已删除文件"""
    data = _load_manifest()
     # 1) 扫描磁盘：有文件就确保 manifest 里有条目
    if os.path.exists(KB_DIR):
        for f in os.listdir(KB_DIR):
            if f.startswith("."):
                continue
            _ensure_manifest_entry(data, f)

    # 2) 计算磁盘上的“有效文件集合”（排除隐藏文件和 manifest 自己）
    disk_set = set(
        x for x in os.listdir(KB_DIR)
        if (not x.startswith(".")) and x != MANIFEST_FILENAME
    ) if os.path.exists(KB_DIR) else set()

    # 3) 清理 manifest 中但磁盘已不存在的条目
    to_del = [k for k in data.get("files", {}).keys() if k not in disk_set]
    for k in to_del:
        data["files"].pop(k, None)

    _save_manifest(data)
    return data

def _bootstrap_rag_enabled_files() -> None:
    """服务启动时：根据 manifest 恢复 enabled 的知识库文件到 RAG 引擎（构建/加载索引）"""
    if not rag_engine:
        return
    data = _sync_manifest_with_disk()
    for filename, info in data.get("files", {}).items():
        if not info.get("enabled"):
            continue
        file_path = os.path.join(KB_DIR, filename)
        ok, msg = rag_engine.enable_file(filename=filename, file_path=file_path, store_id=info["store_id"])
        if ok:
            info["indexed"] = True
        else:
            # 启用失败就自动关闭，避免“显示启用但实际不可用”的状态
            info["enabled"] = False
            info["indexed"] = False
            print(f"[WARN] 启用 {filename} 失败: {msg}")
        info["updated_at"] = datetime.now().isoformat(timespec="seconds")
    _save_manifest(data)

# === 初始化 RAG 引擎（按文件开关模式）===
try:
    if RAGSearch:
        print("[INFO] 初始化 RAG 引擎（按文件开关模式）...")
        rag_engine = RAGSearch(persist_dir=FAISS_DIR, embedding_model=EMBED_MODEL_PATH)
        _bootstrap_rag_enabled_files()
        print("[INFO] RAG 引擎就绪！")
    else:
        print("[WARN] 未找到 rag_system 模块，RAG 模式将不可用。")
except Exception as e:
    print(f"[ERROR] RAG 引擎初始化失败: {e}")


class FrontendChatRequest(BaseModel):
    prompt: str=""  # 用户输入的对话内容
    file_id: Optional[str] = None
    mode: Optional[str] = "general"  # "general" 或 "course_graph"
    selected_tools: Optional[List[str]] = []
    file_ids: Optional[List[str]] = None #多文件
    history: Optional[List[dict]] = []


class MCPCallRequest(BaseModel):
    server: str
    tool: str
    args: Optional[dict] = {}
    meta: Optional[dict] = {}


class AgentAskRequest(BaseModel):
    prompt: str
    # 可选地直接指定要调用的子服务与工具（优先使用）
    server: Optional[str] = None
    tool: Optional[str] = None
    args: Optional[dict] = {}
    meta: Optional[dict] = {}


# 简单内存速率限制（每个 API Key 最多 N 次 / 窗口）
_AGENT_RATE: Dict[str, Dict[str, float]] = {}
_RATE_LIMIT_COUNT = 30
_RATE_LIMIT_WINDOW = 60.0  # seconds


ROUTER_RULES = [
    {
        "keywords": ["cpu", "核数", "核心", "系统信息", "服务器信息", "硬件", "配置", "memory", "内存"],
        "tool": "get_system_info",
    },
    {
        "keywords": ["磁盘", "硬盘", "disk", "空间", "容量"],
        "tool": "disk_usage",
    },
    {
        "keywords": ["b站", "哔哩", "哔哩哔哩", "视频", "bilibili", "搜视频", "查视频"],
        "tool": "search_videos",
    },
]


def _build_payload(args: Optional[dict], meta: Optional[dict], prompt: Optional[str] = None) -> Dict[str, Dict]:
    """构建调用 MCP 工具的 payload，包含 args 和 meta 两部分。"""
    payload_args = (args or {}).copy()
    payload_meta = (meta or {}).copy()
    if prompt:
        payload_meta.setdefault("prompt", prompt)
    return {"args": payload_args, "meta": payload_meta}


def _match_router(prompt_text: str):
    normalized = (prompt_text or "").lower()
    for rule in ROUTER_RULES:
        for keyword in rule["keywords"]:
            if keyword.lower() in normalized:
                return rule
    return None


async def _call_mcp_tool(tool: str, prompt: str, args: Optional[dict], meta: Optional[dict]):
    if not os.path.exists(MCP_SERVICE_SCRIPT):
        raise FileNotFoundError(f"mcp service not found: {MCP_SERVICE_SCRIPT}")

    payload = _build_payload(args, meta, prompt=prompt)
    async with MCPClient(MCP_SERVICE_SCRIPT) as client:
        await client.ping()
        result = await client.call_tool(tool, {"payload": payload})
        return result


# === MCP 转发端点（将请求转发到 mcp_service/service.py） ===
MCP_SERVICE_SCRIPT = str((ROOT_DIR / "mcp_service" / "service.py").resolve())

_AI_AGENT_FN = None  # cache ai_agent callable from backend.client


def _load_backend_client_module():
    """Load backend.client as a module regardless of package context."""
    import sys
    import importlib.util

    module_name = "backend.client"
    client_path = str((ROOT_DIR / "backend" / "client.py").resolve())

    if module_name in sys.modules:
        return sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(module_name, client_path)
    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[attr-defined]
        sys.modules[module_name] = module
        return module

    return importlib.import_module(module_name)


def _generate_tools_from_mcp(service_script_path: str):
    """Return curated DeepSeek tool schemas shared with backend.client."""
    try:
        return get_tool_schemas()
    except Exception:
        return []


def _inject_tools_into_client():
    """If `backend.client` exists, set its `tools` variable to the generated list.
    This makes the tools visible to the LLM calls originating from `client.ai_agent`.
    """
    try:
        spec = _load_backend_client_module()
    except Exception:
        return

    tools = _generate_tools_from_mcp(MCP_SERVICE_SCRIPT)
    if tools:
        try:
            setattr(spec, 'tools', tools)
            print(f"Injected {len(tools)} tools into backend.client.tools")
        except Exception:
            pass


# Try injecting tools at import time so ai_agent sees them
_inject_tools_into_client()


def _get_ai_agent_fn():
    """Return backend.client.ai_agent with generated tools injected."""
    global _AI_AGENT_FN
    if _AI_AGENT_FN:
        return _AI_AGENT_FN

    client_mod = _load_backend_client_module()
    try:
        generated = _generate_tools_from_mcp(MCP_SERVICE_SCRIPT)
        if generated:
            setattr(client_mod, 'tools', generated)
    except Exception:
        pass

    ai_agent_fn = getattr(client_mod, 'ai_agent')
    _AI_AGENT_FN = ai_agent_fn
    return ai_agent_fn


async def _run_agent_loop(prompt: str) -> str:
    if not os.path.exists(MCP_SERVICE_SCRIPT):
        raise FileNotFoundError(f"mcp service not found: {MCP_SERVICE_SCRIPT}")

    ai_agent_fn = _get_ai_agent_fn()
    async with MCPClient(MCP_SERVICE_SCRIPT) as mcp_client:
        return await ai_agent_fn(mcp_client, prompt)


@app.post("/mcp/call")
async def mcp_call(req: MCPCallRequest):
    """在后端内启动 mcp aggregator（作为子进程）并调用指定的工具。

    注意：此接口会启动短生命周期的子进程来执行调用，适用于开发/轻量场景。
    若需高并发，请改为常驻 mcp 服务或用进程池。
    """
    if not os.path.exists(MCP_SERVICE_SCRIPT):
        return {"status": "error", "message": f"mcp service not found: {MCP_SERVICE_SCRIPT}"}

    payload = _build_payload(req.args, req.meta)

    try:
        async with MCPClient(MCP_SERVICE_SCRIPT) as client:
            await client.ping()
            result = await client.call_tool(req.tool, {"payload": payload})
            # 尝试 JSON 化结果
            try:
                return {"status": "success", "result": result}
            except Exception:
                return {"status": "success", "result": str(result)}
    except Exception as e:
        # 记录完整 traceback 到文件，便于离线分析
        try:
            tb = traceback.format_exc()
            with open("mcp_call_error.log", "a", encoding="utf-8") as f:
                f.write("=== MCP CALL ERROR: " + _dt.datetime.now().isoformat() + " ===\n")
                f.write(tb + "\n\n")
        except Exception:
            pass
        return {"status": "error", "message": str(e)}



@app.post("/agent/ask")
async def agent_ask(request: Request, body: AgentAskRequest, x_api_key: Optional[str] = Header(None)):
    """安全的 Agent 提问端点。

    - 支持：当 `server` 与 `tool` 明确传入时，直接调用对应子工具并返回结果。
    - 安全：若环境变量 `AGENT_API_KEY` 被设置，则必须在请求头 `X-API-Key` 中提供相同密钥。
    - 限流：对每个 API Key（或默认匿名键）做简单窗口计数限制。
    """

    # API Key 校验（若未设置 AGENT_API_KEY 则允许匿名访问，便于本地开发）
    env_key = os.environ.get("AGENT_API_KEY")
    if env_key:
        if not x_api_key or x_api_key != env_key:
            raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")

    # 简单速率限制（按 key 或匿名）
    key = x_api_key or "_anon"
    now = _dt.datetime.now().timestamp()
    entry = _AGENT_RATE.get(key)
    if not entry or now - entry.get("start", 0) > _RATE_LIMIT_WINDOW:
        _AGENT_RATE[key] = {"count": 1, "start": now}
    else:
        entry["count"] = entry.get("count", 0) + 1
        if entry["count"] > _RATE_LIMIT_COUNT:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

    # 必须提供 prompt；如果未指定 server/tool，当前实现要求前端先决定要调用的工具
    if not body.prompt or not body.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt required")

    # 如果前端明确指定 server/tool，则直接调用
    if body.server and body.tool:
        try:
            result = await _call_mcp_tool(body.tool, body.prompt, body.args, body.meta)
            return {"status": "success", "result": result}
        except FileNotFoundError as e:
            return {"status": "error", "message": str(e)}
        except Exception as e:
            tb = traceback.format_exc()
            try:
                with open("mcp_call_error.log", "a", encoding="utf-8") as f:
                    f.write("=== AGENT ASK MCP CALL ERROR: " + _dt.datetime.now().isoformat() + " ===\n")
                    f.write(tb + "\n\n")
            except Exception:
                pass
            return {"status": "error", "message": str(e)}

    # 关键字命中时直接转到相应工具
    route = _match_router(body.prompt)
    if route:
        merged_args = dict(route.get("args", {}))
        if body.args:
            merged_args.update(body.args)
        try:
            result = await _call_mcp_tool(route["tool"], body.prompt, merged_args, body.meta)
            return {"status": "success", "result": result}
        except FileNotFoundError as e:
            return {"status": "error", "message": str(e)}
        except Exception as e:
            tb = traceback.format_exc()
            try:
                with open("agent_router_error.log", "a", encoding="utf-8") as f:
                    f.write("=== AGENT ROUTER ERROR: " + _dt.datetime.now().isoformat() + " ===\n")
                    f.write(tb + "\n\n")
            except Exception:
                pass
            return {"status": "error", "message": str(e)}

    auto_error: Optional[str] = None
    if not (body.server and body.tool):
        try:
            auto_result = await _run_agent_loop(body.prompt)
            return {"status": "success", "result": auto_result}
        except FileNotFoundError as e:
            auto_error = str(e)
        except Exception as e:
            auto_error = str(e)
            tb = traceback.format_exc()
            try:
                with open("agent_auto_route_error.log", "a", encoding="utf-8") as f:
                    f.write("=== AGENT AUTO ROUTE ERROR: " + _dt.datetime.now().isoformat() + " ===\n")
                    f.write(tb + "\n\n")
            except Exception:
                pass

    err_msg = "Specify server and tool, or enable automatic tool selection in the backend."
    if auto_error:
        err_msg = f"Auto tool selection failed: {auto_error}"
    return {"status": "error", "message": err_msg}


# === 兼容 client.py 的完整 agent-loop（复用 CLI 客户端的 ai_agent） ===
class AgentRunRequest(PydanticBaseModel):
    prompt: str
    # 可选：限制最大工具调用轮数（由 CLI 内部 loop 控制，这里作为提示）
    max_turns: Optional[int] = None


@app.post("/agent/run")
async def agent_run(body: AgentRunRequest):
    """在后端运行完整 agent loop（复用 `backend/client.py` 的 `ai_agent` 实现）。

    实现方式：在请求处理时动态导入 `backend.client.ai_agent`，并用 `fastmcp.Client`
    启动本地 mcp 聚合器（`MCP_SERVICE_SCRIPT`）作为子进程进行交互。
    返回最终的 agent 输出文本。
    """
    try:
        result = await _run_agent_loop(body.prompt)
        return {"status": "success", "result": result}
    except FileNotFoundError as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        tb = traceback.format_exc()
        try:
            with open("agent_run_error.log", "a", encoding="utf-8") as f:
                f.write("=== AGENT RUN ERROR: " + _dt.datetime.now().isoformat() + " ===\n")
                f.write(tb + "\n\n")
        except Exception:
            pass
        return {"status": "error", "message": str(e)}


# === 设置接口：允许前端提交 Deepseek API Key 等配置 ===
class SettingsRequest(PydanticBaseModel):
    deepseek_api_key: Optional[str] = None
    mysql_host: Optional[str] = None
    mysql_port: Optional[int] = None
    mysql_user: Optional[str] = None
    mysql_password: Optional[str] = None
    mysql_database: Optional[str] = None


@app.get("/settings")
async def get_settings():
    data = _load_settings()
    mysql_env = (
        data.get("mcpServers", {})
        .get("mysql", {})
        .get("env", {})
    )
    mysql_info = {
        "host": mysql_env.get("MYSQL_HOST", ""),
        "port": mysql_env.get("MYSQL_PORT", ""),
        "user": mysql_env.get("MYSQL_USER", ""),
        "database": mysql_env.get("MYSQL_DATABASE", ""),
        "password_set": bool(mysql_env.get("MYSQL_PASSWORD")),
        "configured": bool(mysql_env),
    }
    return {
        "deepseek_api_key_set": bool(data.get("deepseek_api_key")),
        "mysql": mysql_info,
    }


@app.post("/settings")
async def post_settings(body: SettingsRequest):
    payload = _load_settings()
    changed = False
    if body.deepseek_api_key is not None:
        payload["deepseek_api_key"] = body.deepseek_api_key
        os.environ["DEEPSEEK_API_KEY"] = body.deepseek_api_key
        changed = True

    mysql_fields = {
        "MYSQL_HOST": body.mysql_host,
        "MYSQL_PORT": str(body.mysql_port) if body.mysql_port is not None else None,
        "MYSQL_USER": body.mysql_user,
        "MYSQL_PASSWORD": body.mysql_password,
        "MYSQL_DATABASE": body.mysql_database,
    }
    if any(v is not None for v in mysql_fields.values()):
        env = _ensure_mysql_env(payload)
        for key, value in mysql_fields.items():
            if value is not None:
                env[key] = str(value)
                os.environ[key] = str(value)
                changed = True

    if changed:
        _save_settings(payload)

        try:
            import sys, importlib
            if "backend.client" in sys.modules:
                importlib.reload(sys.modules["backend.client"])
            else:
                try:
                    importlib.import_module("backend.client")
                except Exception:
                    spec = importlib.util.spec_from_file_location("backend.client", str((ROOT_DIR / "backend" / "client.py").resolve()))
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)  # type: ignore
                    sys.modules["backend.client"] = mod
            global _AI_AGENT_FN
            _AI_AGENT_FN = None
        except Exception:
            pass

    return {"status": "success", "saved": changed}


class MySQLEnvRequest(PydanticBaseModel):
    mysql_host: Optional[str] = None
    mysql_port: Optional[int] = None
    mysql_user: Optional[str] = None
    mysql_password: Optional[str] = None
    mysql_database: Optional[str] = None


@app.post("/set_mysql_env")
async def set_mysql_env(body: MySQLEnvRequest):
    """仅将用户提供的 MySQL 配置写入当前进程的环境变量（不持久化到 mcp_settings.json）。

    这个接口适用于希望立即生效但不想修改磁盘配置的场景。
    """
    changed = False
    mapping = {
        'MYSQL_HOST': body.mysql_host,
        'MYSQL_PORT': str(body.mysql_port) if body.mysql_port is not None else None,
        'MYSQL_USER': body.mysql_user,
        'MYSQL_PASSWORD': body.mysql_password,
        'MYSQL_DATABASE': body.mysql_database,
    }
    for k, v in mapping.items():
        if v is not None:
            os.environ[k] = str(v)
            changed = True

    return {"status": "success", "applied": changed}


class DeepseekEnvRequest(PydanticBaseModel):
    deepseek_api_key: Optional[str] = None
    deepseek_base_url: Optional[str] = None


@app.post("/set_deepseek_env")
async def set_deepseek_env(body: DeepseekEnvRequest):
    """将 Deepseek API 设置写入当前进程环境（不持久化到磁盘）。

    用于立刻生效但不想修改 `mcp_settings.json` 的场景。
    """
    changed = False
    if body.deepseek_api_key is not None:
        os.environ["DEEPSEEK_API_KEY"] = body.deepseek_api_key
        changed = True
    if body.deepseek_base_url is not None:
        os.environ["DEEPSEEK_BASE_URL"] = body.deepseek_base_url
        changed = True

    # 尝试重新加载依赖于环境变量的模块（例如 backend.client）以使变更生效
    try:
        import sys, importlib
        if "backend.client" in sys.modules:
            importlib.reload(sys.modules["backend.client"])
        global _AI_AGENT_FN
        _AI_AGENT_FN = None
    except Exception:
        pass

    return {"status": "success", "applied": changed}



# 对话文件上传
TEMP_DIR = "temp_uploads"
os.makedirs(TEMP_DIR, exist_ok=True)

ALLOWED_CHAT_EXTS = {'.pdf', '.txt', '.md', '.docx', '.xlsx', '.xls'}
def _chat_ext_ok(filename: str) -> bool:
    _, ext = os.path.splitext(filename or "")
    return ext.lower() in ALLOWED_CHAT_EXTS

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
     # 后缀校验：不支持的类型直接拒绝
    if not _chat_ext_ok(file.filename):
        return {"status": "error", "message": f"不支持的文件类型：{file.filename}（支持: {', '.join(sorted(ALLOWED_CHAT_EXTS))}）"}

    file_id = str(uuid4())
    safe_name = file.filename.replace("/", "_").replace("\\", "_")
     # 保存到磁盘：文件名包含 file_id
    save_path = os.path.join(TEMP_DIR, f"{file_id}__{safe_name}")

    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

     # 返回给前端file_id
    return {"status": "success", "file_id": file_id, "filename": file.filename}

#对话文件内容提取
def _extract_temp_text(file_path: str) -> str:
    p = Path(file_path)
    suf = p.suffix.lower()
    try:
        if suf == ".pdf":
            docs = PyPDFLoader(str(p)).load()
            return "\n".join(d.page_content for d in docs)

        if suf in [".txt", ".md"]:
            try:
                return p.read_text(encoding="utf-8")
            except:
                return p.read_text(encoding="gbk", errors="ignore")

        # xlsx
        if suf == ".xlsx":
            import openpyxl
            wb = openpyxl.load_workbook(str(p), read_only=True, data_only=True)
            lines = []
            for ws in wb.worksheets:
                lines.append(f"【Sheet: {ws.title}】")
                for row in ws.iter_rows(values_only=True):
                    vals = [str(v).strip() for v in row if v is not None and str(v).strip()]
                    if vals:
                        lines.append("\t".join(vals))
            text = "\n".join(lines)
            return text

        if suf == ".docx":
            doc = Document(str(p))
            lines = [para.text for para in doc.paragraphs if para.text and para.text.strip()]
            return "\n".join(lines)

    except Exception as e:
        print(f"[extract] failed for {file_path}: {e}")
        return ""
    return ""



#RAG检索库管理
#  1. 获取文件列表
@app.get("/files")
async def list_files():
    data = _sync_manifest_with_disk()
    items = []
    for filename, info in data.get("files", {}).items():
        items.append({
            "name": filename,
            "enabled": bool(info.get("enabled")),
            "indexed": bool(info.get("indexed")),
        })
    items.sort(key=lambda x: x["name"].lower())
    return items

# 2. 上传并索引 (覆盖之前的 mock upload)
@app.post("/upload_kb")
async def upload_knowledge_base(file: UploadFile = File(...)):
    try:
        if not _kb_ext_ok(file.filename):
            return {
                "status": "error",
                "message": f"不支持的文件类型：{file.filename}（支持: {', '.join(sorted(ALLOWED_KB_EXTS))}）"
            }

        os.makedirs(KB_DIR, exist_ok=True)

        file_path = os.path.join(KB_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        data = _sync_manifest_with_disk()
        info = _ensure_manifest_entry(data, file.filename)

        # 同名覆盖：索引作废（是否重建由 enabled 决定）
        info["indexed"] = False

        # 如果之前就是启用状态：只重建这个文件的索引并继续启用（不会影响其它文件）
        if rag_engine and info.get("enabled"):
            ok, msg = rag_engine.enable_file(
                filename=file.filename,
                file_path=file_path,
                store_id=info["store_id"],
            )
            if ok:
                info["indexed"] = True
            else:
                info["enabled"] = False
                info["indexed"] = False
                _save_manifest(data)
                return {"status": "error", "message": msg}

        info["updated_at"] = datetime.now().isoformat(timespec="seconds")
        _save_manifest(data)

        return {
            "status": "success",
            "message": f"上传成功：{file.filename}（已加入列表，打开开关后才会参与检索）"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
# 3. 删除文件
@app.delete("/files/{filename}")
async def delete_file(filename: str):
    try:
        data = _sync_manifest_with_disk()
        info = data.get("files", {}).get(filename)
        if not info:
            return {"status": "error", "message": "文件不存在"}

        file_path = os.path.join(KB_DIR, filename)
        if os.path.exists(file_path):
            os.remove(file_path)

        if rag_engine:
            rag_engine.disable_file(filename=filename, store_id=info["store_id"], purge=True)

        data["files"].pop(filename, None)
        _save_manifest(data)

        return {"status": "success", "message": f"{filename} 已删除（已同步移除索引）"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


class ToggleKBRequest(BaseModel):
    enabled: bool



#知识库开关生效的核心接口
@app.post("/files/{filename}/toggle")
async def toggle_file(filename: str, req: ToggleKBRequest):

    # 同步 manifest 与磁盘，确保文件列表与状态是最新的
    data = _sync_manifest_with_disk()
    info = data.get("files", {}).get(filename)
    if not info:
        return {"status": "error", "message": "文件不存在"}
    
    # 二次校验
    file_path = os.path.join(KB_DIR, filename)
    if not os.path.exists(file_path):
        return {"status": "error", "message": "文件不存在（磁盘缺失）"}

    if not rag_engine:
        return {"status": "error", "message": "RAG 引擎未启动"}

    if req.enabled:
        ok, msg = rag_engine.enable_file(filename=filename, file_path=file_path, store_id=info["store_id"])
        if ok:
            info["enabled"] = True
            info["indexed"] = True
        else:
            info["enabled"] = False
            info["indexed"] = False
            _save_manifest(data)
            return {"status": "error", "message": msg}
    else:

         # 禁用：从 RAG 的启用集合移除（purge=False 表示保留索引文件以便下次快速启用）
        ok, msg = rag_engine.disable_file(filename=filename, store_id=info["store_id"], purge=False)
        info["enabled"] = False
        info["indexed"] = False

    # 更新时间戳并持久化，确保重启服务后开关状态仍能恢
    info["updated_at"] = datetime.now().isoformat(timespec="seconds")
    _save_manifest(data)
    return {"status": "success", "message": msg, "enabled": info["enabled"], "indexed": info["indexed"]}


 #返回知识库目录中的原始文件，供前端预览或下载  
@app.get("/files/download/{filename}")
async def download_file(filename: str):
    file_path = os.path.join("source_documents", filename)
    if os.path.exists(file_path):
        # filename参数让浏览器下载/打开时显示正确的文件名
        return FileResponse(file_path, filename=filename)
    return {"error": "File not found"}    




# 流式输出
@app.post("/chat")
async def chat_endpoint(request: FrontendChatRequest):
    """根据 mode 自动切换 RAG 或 通用对话"""

    async def event_generator():

        # 统一 prompt（允许为空：只发附件时给默认提示）
        user_prompt = (request.prompt or "").strip()
        if not user_prompt:
            user_prompt = "请阅读我上传的附件，并给出摘要与关键信息。"

        # 统一文件 id 列表：兼容 file_id(单个) + file_ids(多个)
        ids = []
        if getattr(request, "file_ids", None):
            ids = [x for x in (request.file_ids or []) if x]
        if not ids and getattr(request, "file_id", None):
            ids = [request.file_id]

        # 统一抽取附件文本，让 general/course_graph 都能用 
        file_context = ""
        if ids:
            file_blocks = []
            try:
                for fid in ids:
                    prefix = f"{fid}__"
                    temp_path = None
                    temp_name = None

                    # 在 TEMP_DIR 里找对应文件：{file_id}__原文件名
                    for fn in os.listdir(TEMP_DIR):
                        if fn.startswith(prefix):
                            temp_path = os.path.join(TEMP_DIR, fn)
                            temp_name = fn.split("__", 1)[1] if "__" in fn else fn
                            break

                    if not temp_path:
                        print(f"[chat] file_id={fid} not found in {TEMP_DIR}")
                        continue

                    text = _extract_temp_text(temp_path)
                    print(f"[chat] found file={temp_name}, extracted_len={len(text)}")

                    if not text.strip():
                        continue

                    # 限长，避免 prompt 过大
                    text = text[:12000]
                    file_blocks.append(f"【附件：{temp_name}】\n{text}")

            except Exception as e:
                print(f"读取临时文件失败: {e}")

            file_context = "\n\n".join(file_blocks).strip()
        


        # === 分支 A: 专业模式 (RAG + KG) ===
        if request.mode == "course_graph":
            if rag_engine:
                yield json.dumps({
                    "type": "markdown_chunk",
                    "content": "🔍 **正在检索知识库...**\n\n"
                }, ensure_ascii=False) + "\n"
         
                # ========= KG（Excel -> 三元组） =========
                kg_context = ""
                if kg_query_tool:
                    try:
                        kg_context = kg_query_tool(user_prompt) or ""
                       
                        if "未能识别专业术语" in kg_context or kg_context.startswith("Error:"):
                            kg_context = ""
                    except Exception as e:
                        print(f"KG 查询失败: {e}")
                        kg_context = ""
                
         
                # ========= 把“附件内容 + KG结果”拼成 extra_context =========
                extra_parts = []
                if file_context:
                    extra_parts.append("【用户附件内容】\n" + file_context[:12000])
                if kg_context:
                    extra_parts.append("【知识图谱三元组】\n" + kg_context[:8000])
                extra_context = "\n\n".join(extra_parts).strip()
               
         
                try:
                    for piece in rag_engine.chat_stream(
                        user_prompt, 
                        history=request.history,
                        top_k=3, 
                        extra_context=extra_context
                    ):
                        
                        yield json.dumps({
                            "type": "markdown_chunk",
                            "content": piece,
                        }, ensure_ascii=False) + "\n"
                except Exception as e:
                    yield json.dumps({
                        "type": "error",
                        "content": f"RAG/KG 执行出错: {str(e)}"
                    }, ensure_ascii=False) + "\n"
            else:
                yield json.dumps({
                    "type": "markdown_chunk",
                    "content": "⚠️ **知识库未加载**\n\n后端未检测到索引，请先启用知识库文件并构建索引。"
                }, ensure_ascii=False) + "\n"
         

        # === 分支 B: 通用模式 (原生 DeepSeek) ===
        else:
            # 0. 检查工具 (保留你原来的逻辑)
            if request.selected_tools:
                print(f"🔧 用户激活了工具: {request.selected_tools}")

            # 1. 发送思考提示
            yield json.dumps({
                "type": "markdown_chunk",
                "content": "😎 **开始思考 **\n\n"
            }, ensure_ascii=False) + "\n"

            

            # 2. 构造消息（保留你的 Prompt）
            messages = [
                {
                    "role": "system",
                    "content": (
                        "你是一名专业的学习助手，熟悉中外物理学家生平和贡献。"
                        "用户问你任何与物理有关的问题，都应当提供结构清晰、可靠、自然的回答。"
                    )
                }
            ]

            # ✅循环注入历史记录
            for msg in (request.history or []):
                messages.append({
                    "role": msg.get("role"),
                    "content": msg.get("content")
                })

            # ✅ 注入附件内容到 system 
            if file_context:
                messages.append({
                    "role": "system",
                    "content": (
                        "下面是用户上传的附件内容（可能被截断）。回答时必须结合附件信息；"
                        "如果附件信息不足以支持结论，请明确指出缺少什么。\n\n"
                        f"{file_context}"
                    )
                })
            # ========= ✅ 注入结束 =========

            # user 消息最后放
            messages.append({"role": "user", "content": user_prompt})

            try:
                stream = await client.chat.completions.create(
                    model="deepseek-chat",
                    messages=messages,
                    stream=True,
                )

                async for chunk in stream:
                    piece = chunk.choices[0].delta.content or ""
                    if not piece:
                        continue

                    yield json.dumps({
                        "type": "markdown_chunk",
                        "content": piece,
                    }, ensure_ascii=False) + "\n"

            except Exception as e:
                yield json.dumps({
                    "type": "error",
                    "content": f"DeepSeek API 错误：{e}",
                }, ensure_ascii=False) + "\n"

        yield json.dumps({"type": "stream_end"}, ensure_ascii=False) + "\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")




if __name__ == "__main__":
    uvicorn.run("backend_main:app", host="0.0.0.0", port=8000, reload=True)