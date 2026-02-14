"""Aggregator MCP server that proxies tool calls to child MCP servers.

This server exposes a unified tool surface for the client. Each exported
tool forwards its call to a dedicated child MCP server (e.g., Bilibili,
MySQL, system info). The client only needs to talk to this main server.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, Optional

from fastmcp import Client, FastMCP


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

    async def call_tool(self, server: str, tool_name: str, args: Dict[str, Any]) -> Any:
        client = self._get_client(server)
        lock = self._get_lock(server)

        async with lock:
            async with client:
                await client.ping()
                result = await client.call_tool(tool_name, args)
                return self._normalize_result(result)

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


@mcp.tool()
async def search_videos(keyword: str) -> Any:
    return await manager.call_tool("bilibili", "search_videos", {"keyword": keyword})


@mcp.tool()
async def execute_query(sql: str) -> Any:
    return await manager.call_tool("mysql", "execute_query", {"query": sql})


@mcp.tool()
async def get_system_info(key: Optional[str] = None) -> Any:
    return await manager.call_tool("system_info", "get_system_info", {"key": key})


@mcp.tool()
async def get_environment_variables() -> Any:
    return await manager.call_tool("system_info", "get_environment_variables", {})


@mcp.tool()
async def disk_usage(path: str) -> Any:
    return await manager.call_tool("system_info", "disk_usage", {"path": path})


@mcp.tool()
async def import_csv(file_path: str, sep: str = ',', header: Optional[int] = None, encoding: str = 'utf-8', dtype: Optional[dict] = None, parse_dates: Optional[list] = None, index_col: Optional[int] = None, usecols: Optional[list] = None) -> Any:
    return await manager.call_tool("pandas", "import_csv", {
        "file_path": file_path,
        "sep": sep,
        "header": header,
        "encoding": encoding,
        "dtype": dtype,
        "parse_dates": parse_dates,
        "index_col": index_col,
        "usecols": usecols,
    })


@mcp.tool()
async def least_square_fit_2d(x_data: list, y_data: list, model_func_str: str, initial_params: Optional[list] = None) -> Any:
    return await manager.call_tool("least_square", "least_square_fit_2d", {
        "x_data": x_data,
        "y_data": y_data,
        "model_func_str": model_func_str,
        "initial_params": initial_params,
    })


@mcp.tool()
async def least_square_fit_3d(x_data: list, y_data: list, z_data: list, model_func_str: str, initial_params: Optional[list] = None) -> Any:
    return await manager.call_tool("least_square", "least_square_fit_3d", {
        "x_data": x_data,
        "y_data": y_data,
        "z_data": z_data,
        "model_func_str": model_func_str,
        "initial_params": initial_params,
    })


@mcp.tool()
async def generate_pred_values_2d(x_data: list, model_func_str: str, params: list) -> Any:
    return await manager.call_tool("least_square", "generate_pred_values_2d", {
        "x_data": x_data,
        "model_func_str": model_func_str,
        "params": params,
    })


@mcp.tool()
async def generate_pred_values_3d(x_data: list, y_data: list, model_func_str: str, params: list) -> Any:
    return await manager.call_tool("least_square", "generate_pred_values_3d", {
        "x_data": x_data,
        "y_data": y_data,
        "model_func_str": model_func_str,
        "params": params,
    })


@mcp.tool()
async def plot_in_2d(x_data: list, y_data: list, title: str = "2D Figure", x_label: str = "X-Axis", y_label: str = "Y-Axis", file_path: str = "2d_figure.png") -> Dict[str, Any]:
    return await manager.call_tool("matplotlib", "plot_in_2d", {
        "x_data": x_data,
        "y_data": y_data,
        "title": title,
        "x_label": x_label,
        "y_label": y_label,
        "file_path": file_path
    })


@mcp.tool()
async def plot_in_3d(x_data: list, y_data: list, z_data: list, title: str = "3D Figure", x_label: str = "X-Axis", y_label: str = "Y-Axis", z_label: str = "Z-Axis", file_path: str = "3d_figure.png") -> Dict[str, Any]:
    return await manager.call_tool("matplotlib", "plot_in_3d", {
        "x_data": x_data,
        "y_data": y_data,
        "z_data": z_data,
        "title": title,
        "x_label": x_label,
        "y_label": y_label,
        "z_label": z_label,
        "file_path": file_path
    })


@mcp.tool()
async def double_plot_2d(x1_data: list, y1_data: list, x2_data: list, y2_data: list, title: str = "Double 2D Figure", x_label: str = "X-Axis", y_label: str = "Y-Axis", file_path: str = "double_2d_figure.png") -> Dict[str, Any]:
    return await manager.call_tool("matplotlib", "double_plot_2d", {
        "x1_data": x1_data,
        "y1_data": y1_data,
        "x2_data": x2_data,
        "y2_data": y2_data,
        "title": title,
        "x_label": x_label,
        "y_label": y_label,
        "file_path": file_path
    })


@mcp.tool()
async def double_plot_3d(x1_data: list, y1_data: list, z1_data: list, x2_data: list, y2_data: list, z2_data: list, title: str = "Double 3D Figure", x_label: str = "X-Axis", y_label: str = "Y-Axis", z_label: str = "Z-Axis", file_path: str = "double_3d_figure.png") -> Dict[str, Any]:
    return await manager.call_tool("matplotlib", "double_plot_3d", {
        "x1_data": x1_data,
        "y1_data": y1_data,
        "z1_data": z1_data,
        "x2_data": x2_data,
        "y2_data": y2_data,
        "z2_data": z2_data,
        "title": title,
        "x_label": x_label,
        "y_label": y_label,
        "z_label": z_label,
        "file_path": file_path
    })


@mcp.tool()
async def list_child_tools() -> Dict[str, Any]:
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
            summary[name] = {"error": str(exc)}
    return summary


if __name__ == "__main__":
    mcp.run(transport="stdio")
