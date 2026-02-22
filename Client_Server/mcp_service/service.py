"""Aggregator MCP server that proxies tool calls to child MCP servers.

This server exposes a unified tool surface for the client. Each exported
tool forwards its call to a dedicated child MCP server (e.g., Bilibili,
MySQL, system info). The client only needs to talk to this main server.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from fastmcp import Client, FastMCP
import traceback
from datetime import datetime as _dt


# Paths to child MCP servers.
BASE_DIR = Path(__file__).resolve().parent
TOOLS_DIR = BASE_DIR / "tools"

CHILD_SERVERS: Dict[str, Path] = {
    "bilibili": TOOLS_DIR / "bilibili_tool.py",
    "mysql": TOOLS_DIR / "mysql_tool.py",
    "system_info": TOOLS_DIR / "system_info_tool.py",
    "matplotlib": TOOLS_DIR / "matplotlib_tool.py",
    "pandas": TOOLS_DIR / "pandas_tool.py",
    "least_square": TOOLS_DIR / "least_square_tool.py",
}


mcp = FastMCP(name="Main Aggregator")


class SubServerManager:
    """Lazy manager that proxies calls to child MCP servers."""

    def __init__(self, servers: Dict[str, Path]) -> None:
        self._servers = servers
        self._clients: Dict[str, Client] = {}
        self._locks: Dict[str, asyncio.Lock] = {}

    def _get_client(self, name: str) -> Client:
        if name not in self._servers:
            raise ValueError(f"Unknown child server: {name}")

        if name not in self._clients:
            self._clients[name] = Client(str(self._servers[name]))
        return self._clients[name]

    def _get_lock(self, name: str) -> asyncio.Lock:
        if name not in self._locks:
            self._locks[name] = asyncio.Lock()
        return self._locks[name]

    async def call_tool(self, server: str, tool_name: str, payload: Dict[str, Any]) -> Any:
        client = self._get_client(server)
        lock = self._get_lock(server)
        payload = payload or {}

        async with lock:
            try:
                async with client:
                    await client.ping()
                    result = await client.call_tool(tool_name, {"payload": payload})
                    return self._normalize_result(result)
            except Exception as e:
                # 记录 traceback 到文件，便于诊断子服务器问题
                try:
                    log_path = (Path(__file__).resolve().parent / "mcp_service_error.log")
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write("=== MCP SERVICE ERROR: " + _dt.now().isoformat() + " ===\n")
                        f.write(traceback.format_exc() + "\n\n")
                except Exception:
                    pass
                raise

    @staticmethod
    def _normalize_result(result: Any) -> Any:
        if isinstance(result, str):
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                return result

        if hasattr(result, "structured_content"):
            return result.structured_content

        if hasattr(result, "content"):
            payload = getattr(result, "content")
            if isinstance(payload, list) and payload:
                try:
                    return json.loads(payload[0].text)
                except Exception:
                    return payload[0].text
            return payload

        return result


manager = SubServerManager(CHILD_SERVERS)


def _split_payload(payload: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    payload = payload or {}
    args = payload.get("args") or {}
    meta = payload.get("meta") or {}
    return args, meta


def _child_payload(args: Optional[Dict[str, Any]] = None, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
    return {"args": args or {}, "meta": meta or {}}


@mcp.tool()
async def search_videos(payload: Optional[Dict[str, Any]] = None) -> Any:
    args, meta = _split_payload(payload)
    keyword = args.get("keyword") or meta.get("prompt")
    if not keyword:
        raise ValueError("keyword is required")
    return await manager.call_tool("bilibili", "search_videos", _child_payload({"keyword": keyword}, meta))


@mcp.tool()
async def execute_query(payload: Optional[Dict[str, Any]] = None) -> Any:
    args, meta = _split_payload(payload)
    sql = args.get("sql") or args.get("query") or meta.get("prompt")
    if not sql:
        raise ValueError("sql/query is required")
    return await manager.call_tool("mysql", "execute_query", _child_payload({"query": sql}, meta))


@mcp.tool()
async def get_system_info(payload: Optional[Dict[str, Any]] = None) -> Any:
    args, meta = _split_payload(payload)
    key = args.get("key")
    return await manager.call_tool("system_info", "get_system_info", _child_payload({"key": key}, meta))


@mcp.tool()
async def get_environment_variables(payload: Optional[Dict[str, Any]] = None) -> Any:
    _, meta = _split_payload(payload)
    return await manager.call_tool("system_info", "get_environment_variables", _child_payload({}, meta))


@mcp.tool()
async def disk_usage(payload: Optional[Dict[str, Any]] = None) -> Any:
    args, meta = _split_payload(payload)
    path = args.get("path") or meta.get("path")
    return await manager.call_tool("system_info", "disk_usage", _child_payload({"path": path}, meta))


@mcp.tool()
async def import_csv(payload: Optional[Dict[str, Any]] = None) -> Any:
    args, meta = _split_payload(payload)
    child_args = {
        "file_path": args.get("file_path"),
        "sep": args.get("sep", ","),
        "header": args.get("header"),
        "encoding": args.get("encoding", "utf-8"),
        "dtype": args.get("dtype"),
        "parse_dates": args.get("parse_dates"),
        "index_col": args.get("index_col"),
        "usecols": args.get("usecols"),
    }
    return await manager.call_tool("pandas", "import_csv", _child_payload(child_args, meta))


@mcp.tool()
async def least_square_fit_2d(payload: Optional[Dict[str, Any]] = None) -> Any:
    args, meta = _split_payload(payload)
    child_args = {
        "x_data": args.get("x_data") or [],
        "y_data": args.get("y_data") or [],
        "model_func_str": args.get("model_func_str"),
        "initial_params": args.get("initial_params"),
    }
    return await manager.call_tool("least_square", "least_square_fit_2d", _child_payload(child_args, meta))


@mcp.tool()
async def least_square_fit_3d(payload: Optional[Dict[str, Any]] = None) -> Any:
    args, meta = _split_payload(payload)
    child_args = {
        "x_data": args.get("x_data") or [],
        "y_data": args.get("y_data") or [],
        "z_data": args.get("z_data") or [],
        "model_func_str": args.get("model_func_str"),
        "initial_params": args.get("initial_params"),
    }
    return await manager.call_tool("least_square", "least_square_fit_3d", _child_payload(child_args, meta))


@mcp.tool()
async def generate_pred_values_2d(payload: Optional[Dict[str, Any]] = None) -> Any:
    args, meta = _split_payload(payload)
    child_args = {
        "x_data": args.get("x_data") or [],
        "model_func_str": args.get("model_func_str"),
        "params": args.get("params"),
    }
    return await manager.call_tool("least_square", "generate_pred_values_2d", _child_payload(child_args, meta))


@mcp.tool()
async def generate_pred_values_3d(payload: Optional[Dict[str, Any]] = None) -> Any:
    args, meta = _split_payload(payload)
    child_args = {
        "x_data": args.get("x_data") or [],
        "y_data": args.get("y_data") or [],
        "model_func_str": args.get("model_func_str"),
        "params": args.get("params"),
    }
    return await manager.call_tool("least_square", "generate_pred_values_3d", _child_payload(child_args, meta))


@mcp.tool()
async def plot_in_2d(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = _split_payload(payload)
    child_args = {
        "x_data": args.get("x_data") or [],
        "y_data": args.get("y_data") or [],
        "title": args.get("title", "2D Figure"),
        "x_label": args.get("x_label", "X-Axis"),
        "y_label": args.get("y_label", "Y-Axis"),
        "file_path": args.get("file_path", "2d_figure.png"),
    }
    return await manager.call_tool("matplotlib", "plot_in_2d", _child_payload(child_args, meta))


@mcp.tool()
async def plot_in_3d(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = _split_payload(payload)
    child_args = {
        "x_data": args.get("x_data") or [],
        "y_data": args.get("y_data") or [],
        "z_data": args.get("z_data") or [],
        "title": args.get("title", "3D Figure"),
        "x_label": args.get("x_label", "X-Axis"),
        "y_label": args.get("y_label", "Y-Axis"),
        "z_label": args.get("z_label", "Z-Axis"),
        "file_path": args.get("file_path", "3d_figure.png"),
    }
    return await manager.call_tool("matplotlib", "plot_in_3d", _child_payload(child_args, meta))


@mcp.tool()
async def double_plot_2d(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = _split_payload(payload)
    child_args = {
        "x1_data": args.get("x1_data") or [],
        "y1_data": args.get("y1_data") or [],
        "x2_data": args.get("x2_data") or [],
        "y2_data": args.get("y2_data") or [],
        "title": args.get("title", "Double 2D Figure"),
        "x_label": args.get("x_label", "X-Axis"),
        "y_label": args.get("y_label", "Y-Axis"),
        "file_path": args.get("file_path", "double_2d_figure.png"),
    }
    return await manager.call_tool("matplotlib", "double_plot_2d", _child_payload(child_args, meta))


@mcp.tool()
async def double_plot_3d(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = _split_payload(payload)
    child_args = {
        "x1_data": args.get("x1_data") or [],
        "y1_data": args.get("y1_data") or [],
        "z1_data": args.get("z1_data") or [],
        "x2_data": args.get("x2_data") or [],
        "y2_data": args.get("y2_data") or [],
        "z2_data": args.get("z2_data") or [],
        "title": args.get("title", "Double 3D Figure"),
        "x_label": args.get("x_label", "X-Axis"),
        "y_label": args.get("y_label", "Y-Axis"),
        "z_label": args.get("z_label", "Z-Axis"),
        "file_path": args.get("file_path", "double_3d_figure.png"),
    }
    return await manager.call_tool("matplotlib", "double_plot_3d", _child_payload(child_args, meta))


@mcp.tool()
async def list_child_tools(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """List tools exposed by each child server for debugging/inspection."""

    summary: Dict[str, Any] = {}
    for name in CHILD_SERVERS:
        try:
            client = manager._get_client(name)
            async with manager._get_lock(name):
                async with client:
                    await client.ping()
                    summary[name] = await client.list_tools()
        except Exception as exc:  # noqa: BLE001
            # 记录更详细的异常信息到日志
            try:
                log_path = (Path(__file__).resolve().parent / "mcp_service_error.log")
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write("=== LIST_CHILD_TOOLS ERROR: " + _dt.now().isoformat() + " ===\n")
                    f.write(f"server={name}\n")
                    f.write(traceback.format_exc() + "\n\n")
            except Exception:
                pass
            summary[name] = {"error": str(exc)}
    return summary


if __name__ == "__main__":
    mcp.run(transport="stdio")
