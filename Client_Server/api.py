import asyncio
import httpx
import json
import inspect  # 用于判断异步方法
import os
import uuid
from typing import Optional, Union, List
from nicegui import ui

# ==========================================
# 真实后端客户端
# ==========================================
class BackendClient:
    def __init__(self, base_url: str = None):
        # 优先使用环境变量 BACKEND_URL（方便在端口非标准或已调整时快速配置），
        # 否则回退到本仓库常用开发端口 8001（backend 已在 8001 上运行时更可靠）。
        if base_url:
            self.base_url = base_url
        else:
            # 默认指向本地开发后端（端口 8000），可通过环境变量 BACKEND_URL 覆盖
            self.base_url = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")

    # 1. 获取文件列表 (加上 trust_env=False 防止代理拦截)
    async def get_files(self):
        try:
            async with httpx.AsyncClient(trust_env=False) as client:
                resp = await client.get(f"{self.base_url}/files")
                return resp.json()
        except:
            return []

    # 2. 删除文件 (加上 trust_env=False)
    async def delete_file(self, filename: str):
        try:
            # 删除可能触发重建索引，时间较长，设置超时 60s
            async with httpx.AsyncClient(timeout=60.0, trust_env=False) as client:
                resp = await client.delete(f"{self.base_url}/files/{filename}")
                return resp.json()
        except Exception as e:
             return {"status": "error", "message": str(e)}

    # 3. 上传知识库文件 (核心修复版：兼容性读取 + 代理屏蔽)
    async def upload_kb_file(self, file_obj):
        debug_logs = []
        try:
            # --- A. 智能获取文件名 ---
            fname = getattr(file_obj, 'name', None) or getattr(file_obj, 'filename', None)
            
            # 尝试从 content.name 获取 (针对 SpooledTemporaryFile)
            if not fname and hasattr(file_obj, 'content') and hasattr(file_obj.content, 'name'):
                fname = os.path.basename(file_obj.content.name)
            
            # 保底文件名
            if not fname:
                fname = f"upload_{uuid.uuid4().hex[:8]}.txt"

            # --- B. 读取内容  ---
            
            fcontent = None
            try:
                result = file_obj.read()
                fcontent = await result if inspect.isawaitable(result) else result
            except Exception as e:
                debug_logs.append(f"read()失败: {e}")


            # --- C. 最终检查 ---
            if fcontent is None:
                error_msg = "; ".join(debug_logs)
                return {"status": "error", "message": f"读取失败。调试日志: {error_msg}"}

            # 确保是 bytes
            if isinstance(fcontent, str):
                fcontent = fcontent.encode('utf-8')

            # --- D. 发送请求 (关键: trust_env=False) ---
            ftype = getattr(file_obj, 'type', 'application/octet-stream')
            files = {'file': (fname, fcontent, ftype)}
            
            async with httpx.AsyncClient(timeout=60.0, trust_env=False) as client:
                resp = await client.post(f"{self.base_url}/upload_kb", files=files)
                
                # 尝试解析 JSON，如果后端报 500 html 错误则捕获文本
                try:
                    return resp.json()
                except:
                    return {
                        "status": "error", 
                        "message": f"后端异常 (代码 {resp.status_code}): {resp.text[:100]}"
                    }
                
        except Exception as e:
            return {"status": "error", "message": f"系统错误: {str(e)}"}

    # 4. 聊天上传临时文件 (旧接口，顺手加上 trust_env=False)
    async def upload_file(self, file_obj) -> Optional[str]:
        try:
            fname = getattr(file_obj, 'name', None) or getattr(file_obj, 'filename', None) or f"upload_{uuid.uuid4().hex[:8]}.bin"

            fcontent = None
            # 方案 1: 读自身
            if hasattr(file_obj, 'read'):
                try:
                    if hasattr(file_obj, 'seek'):
                        try: file_obj.seek(0)
                        except: pass
                    r = file_obj.read()
                    fcontent = await r if inspect.isawaitable(r) else r
                except:
                    fcontent = None

            # 方案 2: 读内部 file/content
            if fcontent is None:
                inner = getattr(file_obj, 'file', None) or getattr(file_obj, 'content', None)
                if inner is not None:
                    if hasattr(inner, 'read'):
                        r = inner.read()
                        fcontent = await r if inspect.isawaitable(r) else r
                    else:
                        fcontent = inner

            if fcontent is None:
                ui.notify("上传失败：读取文件内容失败", type="negative")
                return None

            if isinstance(fcontent, str):
                fcontent = fcontent.encode('utf-8')

            ftype = getattr(file_obj, 'type', 'application/octet-stream')
            files = {'file': (fname, fcontent, ftype)}

            async with httpx.AsyncClient(timeout=60.0, trust_env=False) as client:
                resp = await client.post(f"{self.base_url}/upload", files=files)
                resp.raise_for_status()
                return resp.json().get("file_id")
        except Exception as e:
            ui.notify(f"上传失败: {e}", type="negative")
            return None


    # 5. 流式对话 (保持原样，确认有 trust_env=False)
    async def stream_chat(
        self,
        prompt: str,
        file_ref: Optional[Union[str, List[str]]],
        mode: str,
        tools: list = None,
        history: list = []
    ):
        # 统一成 ids list
        ids: List[str] = []
        if isinstance(file_ref, list):
            ids = [x for x in file_ref if isinstance(x, str) and x.strip()]
        elif isinstance(file_ref, str) and file_ref.strip():
            ids = [file_ref.strip()]
     
        payload = {
            "prompt": prompt,
            "mode": mode,
            "selected_tools": tools or [],
            # 后端模型里 file_id 是 Optional[str]，这里保证永远是 str / None，不会再塞 list
            "file_id": ids[0] if ids else None,
            # 真正的多文件字段
            "file_ids": ids if ids else None,
            "history": history
        }
     
        try:
            async with httpx.AsyncClient(timeout=None, trust_env=False) as client:
                async with client.stream("POST", f"{self.base_url}/chat", json=payload) as r:
                    r.raise_for_status()
                    async for line in r.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            yield json.loads(line)
                        except Exception:
                            yield {"type": "debug", "content": line}
        except Exception as e:
            yield {"type": "error", "content": str(e)}
     
    # 6 切换知识库文件启用状态（是否参与 RAG）
    async def toggle_file(self, filename: str, enabled: bool):
        try:
            async with httpx.AsyncClient(timeout=60.0, trust_env=False) as client:
                resp = await client.post(
                    f"{self.base_url}/files/{filename}/toggle",
                    json={"enabled": enabled},
                )
                return resp.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def call_mcp(self, server: str, tool: str, args: dict = None, meta: dict = None):
        """Call MCP tool via backend forwarding endpoint `/mcp/call` using the unified payload envelope."""
        payload = {"server": server, "tool": tool, "args": args or {}, "meta": meta or {}}
        try:
            async with httpx.AsyncClient(timeout=60.0, trust_env=False) as client:
                resp = await client.post(f"{self.base_url}/mcp/call", json=payload)
                return resp.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def agent_ask(self, prompt: str, server: Optional[str] = None, tool: Optional[str] = None, args: Optional[dict] = None, meta: Optional[dict] = None, api_key: Optional[str] = None):
        """Call backend `/agent/ask` endpoint with unified payload envelope. If `api_key` provided, sent via `X-API-Key`."""
        payload = {
            "prompt": prompt,
            "server": server,
            "tool": tool,
            "args": args or {},
            "meta": meta or {},
        }
        headers = {}
        if api_key:
            headers["X-API-Key"] = api_key
        try:
            async with httpx.AsyncClient(timeout=None, trust_env=False) as client:
                resp = await client.post(f"{self.base_url}/agent/ask", json=payload, headers=headers)
                return resp.json()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def get_settings(self):
        try:
            async with httpx.AsyncClient(timeout=15.0, trust_env=False) as client:
                resp = await client.get(f"{self.base_url}/settings")
                return resp.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def set_settings(self, deepseek_api_key: Optional[str] = None, mysql_config: Optional[dict] = None):
        try:
            payload = {}
            if deepseek_api_key is not None:
                payload["deepseek_api_key"] = deepseek_api_key
            if mysql_config:
                payload.update({
                    "mysql_host": mysql_config.get("host"),
                    "mysql_port": mysql_config.get("port"),
                    "mysql_user": mysql_config.get("user"),
                    "mysql_password": mysql_config.get("password"),
                    "mysql_database": mysql_config.get("database"),
                })
            if not payload:
                return {"status": "error", "message": "no settings provided"}
            async with httpx.AsyncClient(timeout=15.0, trust_env=False) as client:
                resp = await client.post(f"{self.base_url}/settings", json=payload)
                return resp.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def set_mysql_env(self, mysql_config: dict):
        """Set MySQL env vars in backend process without persisting to disk."""
        try:
            async with httpx.AsyncClient(timeout=15.0, trust_env=False) as client:
                resp = await client.post(f"{self.base_url}/set_mysql_env", json=mysql_config)
                return resp.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def set_deepseek_env(self, deepseek_config: dict):
        """Set Deepseek API key/base_url in backend process without persisting to disk."""
        try:
            async with httpx.AsyncClient(timeout=15.0, trust_env=False) as client:
                resp = await client.post(f"{self.base_url}/set_deepseek_env", json=deepseek_config)
                return resp.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}
   