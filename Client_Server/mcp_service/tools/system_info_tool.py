import platform
import os
import psutil
from typing import Optional, Dict, Any, Tuple
from fastmcp import FastMCP

mcp = FastMCP('System Info MCP Server')

def default_root() -> str:
    if platform.system().lower().startswith("win"):
        drive = os.path.splitdrive(os.getcwd())[0]
        return drive + os.sep if drive else os.sep
    return os.sep

def _split_payload(payload: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    payload = payload or {}
    return payload.get("args") or {}, payload.get("meta") or {}


@mcp.tool()
def get_system_info(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, _ = _split_payload(payload)
    key = args.get("key")
    info = {
        "os": platform.system(),
        "os_version": platform.version(),
        "architecture": platform.machine(),
        "cpu_count": psutil.cpu_count(logical=True),
        "memory_total_gb": round(psutil.virtual_memory().total / (1024 ** 3), 2),
        "disk_total_gb": round(psutil.disk_usage(default_root()).total / (1024 ** 3), 2),
        "hostname": platform.node(),
        "python_version": platform.python_version(),
    }
    if key:
        return {"status": "success", "data": info.get(key), "key": key}
    return {"status": "success", "data": info}

@mcp.tool()
def get_environment_variables(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    _split_payload(payload)  # 保持接口一致
    return {"status": "success", "data": dict(os.environ)}

@mcp.tool()
def disk_usage(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = _split_payload(payload)
    path = args.get("path") or meta.get("path") or default_root()
    usage = psutil.disk_usage(path)
    return {
        "status": "success",
        "path": path,
        "total_gb": round(usage.total / (1024 ** 3), 2),
        "used_gb": round(usage.used / (1024 ** 3), 2),
        "free_gb": round(usage.free / (1024 ** 3), 2),
        "percent_used": usage.percent,
    }

if __name__ == "__main__":
    mcp.run(transport='stdio')
