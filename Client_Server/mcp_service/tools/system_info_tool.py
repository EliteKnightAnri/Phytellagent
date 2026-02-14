import platform
import os
import psutil
from typing import Optional, Dict, Any
from fastmcp import FastMCP

mcp = FastMCP('System Info MCP Server')

def default_root() -> str:
    if platform.system().lower().startswith("win"):
        drive = os.path.splitdrive(os.getcwd())[0]
        return drive + os.sep if drive else os.sep
    return os.sep

@mcp.tool()
def get_system_info(key: Optional[str] = None) -> Dict[str, Any]:
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
        return {"result": info.get(key)}
    return {"result": info}

@mcp.tool()
def get_environment_variables() -> Dict[str, str]:
    return dict(os.environ)

@mcp.tool()
def disk_usage(path: Optional[str] = None) -> Dict[str, Any]:
    if not path:
        path = default_root()
    usage = psutil.disk_usage(path)
    return {
        "path": path,
        "total_gb": round(usage.total / (1024 ** 3), 2),
        "used_gb": round(usage.used / (1024 ** 3), 2),
        "free_gb": round(usage.free / (1024 ** 3), 2),
        "percent_used": usage.percent,
    }

if __name__ == "__main__":
    mcp.run(transport='stdio')
