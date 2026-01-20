"""System info tool

提供两种运行模式：
- HTTP：运行 FastAPI 应用，便于远程/HTTP 调用
- stdio：从 stdin 读取 JSON 请求（逐行），输出 JSON 响应（逐行），便于本地 stdio 通信

用法：
    python -m service.tools.system_info_tool        # 启动 HTTP 服务，默认端口 8082
    python -m service.tools.system_info_tool --stdio   # 启动 stdio 模式
"""
import platform
import os
import sys
import json
from typing import Optional, Dict, Any

import psutil
from fastapi import FastAPI, HTTPException
import uvicorn

app = FastAPI(title="System Info tool", version="1.0")


def _default_root() -> str:
    if platform.system().lower().startswith("win"):
        drive = os.path.splitdrive(os.getcwd())[0]
        return drive + os.sep if drive else os.sep
    return os.sep


def get_system_info() -> Dict[str, Any]:
    """获取系统信息"""
    info = {
        "os": platform.system(),
        "os_version": platform.version(),
        "architecture": platform.machine(),
        "cpu_count": psutil.cpu_count(logical=True),
        "memory_total_gb": round(psutil.virtual_memory().total / (1024 ** 3), 2),
        "disk_total_gb": round(psutil.disk_usage(_default_root()).total / (1024 ** 3), 2),
        "hostname": platform.node(),
        "python_version": platform.python_version(),
    }
    return info


def get_environment_variables() -> Dict[str, str]:
    """获取环境变量"""
    return dict(os.environ)


def disk_usage(path: Optional[str] = None) -> Dict[str, Any]:
    """获取指定路径的磁盘使用情况（默认为系统根路径）"""
    if not path:
        path = _default_root()
    usage = psutil.disk_usage(path)
    return {
        "path": path,
        "total_gb": round(usage.total / (1024 ** 3), 2),
        "used_gb": round(usage.used / (1024 ** 3), 2),
        "free_gb": round(usage.free / (1024 ** 3), 2),
        "percent_used": usage.percent,
    }


@app.get("/info")
def http_info():
    return {"result": get_system_info()}


@app.get("/env")
def http_env():
    return {"result": get_environment_variables()}


@app.get("/disk")
def http_disk(path: Optional[str] = None):
    try:
        return {"result": disk_usage(path)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def _handle_request_obj(req: Dict[str, Any]) -> Dict[str, Any]:
    func = (req.get("function") or req.get("method") or req.get("action"))
    params = req.get("params") or {}

    if func in (None, "get_system_info", "info"):
        return {"result": get_system_info()}
    if func in ("get_environment_variables", "env"):
        return {"result": get_environment_variables()}
    if func in ("disk_usage", "disk"):
        path = params.get("path") if isinstance(params, dict) else None
        return {"result": disk_usage(path)}

    return {"error": f"Unknown function: {func}"}


def stdio_main() -> None:
    """StdIO 驱动：从 stdin 逐行读取 JSON 请求，逐行输出 JSON 响应。"""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception as e:
            out = {"id": None, "error": f"Invalid JSON: {e}"}
            sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
            sys.stdout.flush()
            continue

        try:
            res = _handle_request_obj(req)
            out = {"id": req.get("id"), **res}
        except Exception as e:
            out = {"id": req.get("id"), "error": str(e)}

        sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
        sys.stdout.flush()


def main(argv=None):
    argv = argv or sys.argv[1:]
    if "--stdio" in argv or os.environ.get("FASTMCP_STDIO") == "1":
        stdio_main()
        return

    # default: run HTTP server
    port = 8082
    if "--port" in argv:
        try:
            idx = argv.index("--port")
            port = int(argv[idx + 1])
        except Exception:
            pass

    uvicorn.run(app="service.tools.system_info_tool:app", host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
