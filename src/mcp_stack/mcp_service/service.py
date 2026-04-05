"""
MCP聚合器，将多个子MCP服务器聚合成一个统一的接口供客户端调用。

This server exposes a unified tool surface for the client. Each exported
tool forwards its call to a dedicated child MCP server (e.g., Bilibili,
MySQL, system info). The client only needs to talk to this main server.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from fastmcp import Client, FastMCP
import traceback
from datetime import datetime as _dt


# 通向子服务器的路径配置（相对于 src/mcp_stack/tools 目录）
BASE_DIR = Path(__file__).resolve().parents[3]
SRC_DIR = BASE_DIR / "src"

# 确保 src 目录在 sys.path 中，以便正确导入本地包
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcp_stack.local_packages.status import split_payload, child_payload

TOOLS_DIR = BASE_DIR / "src" / "mcp_stack" / "tools"

CHILD_SERVERS: Dict[str, Path] = {
    "bilibili": TOOLS_DIR / "bilibili_tool.py",
    "mysql": TOOLS_DIR / "mysql_tool.py",
    "system_info": TOOLS_DIR / "system_info_tool.py",
    "matplotlib": TOOLS_DIR / "matplotlib_tool.py",
    "pandas": TOOLS_DIR / "pandas_tool.py",
    "least_square": TOOLS_DIR / "least_square_tool.py",
    "differential_equations": TOOLS_DIR / "differential_equations_tool.py",
    "fourier": TOOLS_DIR / "fourier_tool.py",
    "peak_and_valley": TOOLS_DIR / "peak_tool.py",
    "draw_function": TOOLS_DIR / "draw_function_tool.py",
    "compute_relevancy": TOOLS_DIR / "relevancy_tool.py",
    "signal_generate": TOOLS_DIR / "signal_generate_tool.py",
    "crystal_basic": TOOLS_DIR / "crystal_basic_tool.py",
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


def _omit_none(values: Dict[str, Any]) -> Dict[str, Any]:
    """Remove keys whose value is None so child tools can apply their own defaults."""
    return {key: value for key, value in values.items() if value is not None}


@mcp.tool()
async def search_videos(payload: Optional[Dict[str, Any]] = None) -> Any:
    args, meta = split_payload(payload)
    keyword = args.get("keyword") or meta.get("prompt")
    if not keyword:
        raise ValueError("keyword is required")
    return await manager.call_tool("bilibili", "search_videos", child_payload({"keyword": keyword}, meta))


@mcp.tool()
async def SQL_query(payload: Optional[Dict[str, Any]] = None) -> Any:
    args, meta = split_payload(payload)
    sql = args.get("sql") or args.get("query") or meta.get("prompt")
    if not sql:
        raise ValueError("sql/query is required")
    return await manager.call_tool("mysql", "SQL_query", child_payload({"query": sql}, meta))


@mcp.tool()
async def get_system_info(payload: Optional[Dict[str, Any]] = None) -> Any:
    args, meta = split_payload(payload)
    key = args.get("key")
    return await manager.call_tool("system_info", "get_system_info", child_payload({"key": key}, meta))


@mcp.tool()
async def get_environment_variables(payload: Optional[Dict[str, Any]] = None) -> Any:
    _, meta = split_payload(payload)
    return await manager.call_tool("system_info", "get_environment_variables", child_payload({}, meta))


@mcp.tool()
async def disk_usage(payload: Optional[Dict[str, Any]] = None) -> Any:
    args, meta = split_payload(payload)
    path = args.get("path") or meta.get("path")
    return await manager.call_tool("system_info", "disk_usage", child_payload({"path": path}, meta))


@mcp.tool()
async def import_csv(payload: Optional[Dict[str, Any]] = None) -> Any:
    args, meta = split_payload(payload)
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
    return await manager.call_tool("pandas", "import_csv", child_payload(child_args, meta))

@mcp.tool()
async def import_excel(payload: Optional[Dict[str, Any]] = None) -> Any:
    args, meta = split_payload(payload)
    child_args = {
        "file_path": args.get("file_path"),
        "sheet_name": args.get("sheet_name", 0),
        "header": args.get("header"),
        "encoding": args.get("encoding", "utf-8"),
        "dtype": args.get("dtype"),
        "parse_dates": args.get("parse_dates"),
        "index_col": args.get("index_col"),
        "usecols": args.get("usecols"),
    }
    return await manager.call_tool("pandas", "import_excel", child_payload(child_args, meta))

@mcp.tool()
async def least_square_fit_2d(payload: Optional[Dict[str, Any]] = None) -> Any:
    args, meta = split_payload(payload)
    child_args = {
        "x_data": args.get("x_data") or [],
        "y_data": args.get("y_data") or [],
        "data_address": args.get("data_address"),
        "x_data_address": args.get("x_data_address"),
        "y_data_address": args.get("y_data_address"),
        "x_data_column": args.get("x_data_column"),
        "y_data_column": args.get("y_data_column"),
        "model_func_str": args.get("model_func_str"),
        "initial_params": args.get("initial_params"),
    }
    return await manager.call_tool("least_square", "least_square_fit_2d", child_payload(child_args, meta))


@mcp.tool()
async def least_square_fit_3d(payload: Optional[Dict[str, Any]] = None) -> Any:
    args, meta = split_payload(payload)
    child_args = {
        "x_data": args.get("x_data") or [],
        "y_data": args.get("y_data") or [],
        "z_data": args.get("z_data") or [],
        "data_address": args.get("data_address"),
        "x_data_address": args.get("x_data_address"),
        "y_data_address": args.get("y_data_address"),
        "z_data_address": args.get("z_data_address"),
        "x_data_column": args.get("x_data_column"),
        "y_data_column": args.get("y_data_column"),
        "z_data_column": args.get("z_data_column"),
        "model_func_str": args.get("model_func_str"),
        "initial_params": args.get("initial_params"),
    }
    return await manager.call_tool("least_square", "least_square_fit_3d", child_payload(child_args, meta))


@mcp.tool()
async def generate_pred_values_2d(payload: Optional[Dict[str, Any]] = None) -> Any:
    args, meta = split_payload(payload)
    child_args = {
        "x_data": args.get("x_data") or [],
        "data_address": args.get("data_address"),
        "x_data_address": args.get("x_data_address"),
        "x_data_column": args.get("x_data_column"),
        "model_func_str": args.get("model_func_str"),
        "params": args.get("params"),
    }
    return await manager.call_tool("least_square", "generate_pred_values_2d", child_payload(child_args, meta))


@mcp.tool()
async def generate_pred_values_3d(payload: Optional[Dict[str, Any]] = None) -> Any:
    args, meta = split_payload(payload)
    child_args = {
        "x_data": args.get("x_data") or [],
        "y_data": args.get("y_data") or [],
        "data_address": args.get("data_address"),
        "x_data_address": args.get("x_data_address"),
        "y_data_address": args.get("y_data_address"),
        "x_data_column": args.get("x_data_column"),
        "y_data_column": args.get("y_data_column"),
        "model_func_str": args.get("model_func_str"),
        "params": args.get("params"),
    }
    return await manager.call_tool("least_square", "generate_pred_values_3d", child_payload(child_args, meta))


@mcp.tool()
async def plot_in_2d(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = split_payload(payload)
    child_args = {
        "x_data": args.get("x_data") or [],
        "y_data": args.get("y_data") or [],
        "data_address": args.get("data_address"),
        "x_data_address": args.get("x_data_address"),
        "y_data_address": args.get("y_data_address"),
        "x_data_column": args.get("x_data_column"),
        "y_data_column": args.get("y_data_column"),
        "title": args.get("title", "2D Figure"),
        "x_label": args.get("x_label", "X-Axis"),
        "y_label": args.get("y_label", "Y-Axis"),
        "file_path": args.get("file_path", "2d_figure.png"),
    }
    return await manager.call_tool("matplotlib", "plot_in_2d", child_payload(child_args, meta))


@mcp.tool()
async def plot_in_3d(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = split_payload(payload)
    child_args = {
        "x_data": args.get("x_data") or [],
        "y_data": args.get("y_data") or [],
        "z_data": args.get("z_data") or [],
        "data_address": args.get("data_address"),
        "x_data_address": args.get("x_data_address"),
        "y_data_address": args.get("y_data_address"),
        "z_data_address": args.get("z_data_address"),
        "x_data_column": args.get("x_data_column"),
        "y_data_column": args.get("y_data_column"),
        "z_data_column": args.get("z_data_column"),
        "title": args.get("title", "3D Figure"),
        "x_label": args.get("x_label", "X-Axis"),
        "y_label": args.get("y_label", "Y-Axis"),
        "z_label": args.get("z_label", "Z-Axis"),
        "file_path": args.get("file_path", "3d_figure.png"),
    }
    return await manager.call_tool("matplotlib", "plot_in_3d", child_payload(child_args, meta))


@mcp.tool()
async def double_plot_2d(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = split_payload(payload)
    x2_data_address = args.get("x2_data_address")
    y2_data_address = args.get("y2_data_address")
    x2_data_column = args.get("x2_data_column")
    y2_data_column = args.get("y2_data_column")
    if not x2_data_column and x2_data_address:
        x2_data_column = "x"
    if not y2_data_column and y2_data_address:
        y2_data_column = "y"
    child_args = {
        "x1_data": args.get("x1_data") or [],
        "y1_data": args.get("y1_data") or [],
        "x2_data": args.get("x2_data") or [],
        "y2_data": args.get("y2_data") or [],
        "data_address": args.get("data_address"),
        "x1_data_address": args.get("x1_data_address"),
        "y1_data_address": args.get("y1_data_address"),
        "x2_data_address": x2_data_address,
        "y2_data_address": y2_data_address,
        "x1_data_column": args.get("x1_data_column") or args.get("x_data_column"),
        "y1_data_column": args.get("y1_data_column") or args.get("y_data_column"),
        "x2_data_column": x2_data_column,
        "y2_data_column": y2_data_column,
        "title": args.get("title", "Double 2D Figure"),
        "x_label": args.get("x_label", "X-Axis"),
        "y_label": args.get("y_label", "Y-Axis"),
        "file_path": args.get("file_path", "double_2d_figure.png"),
    }
    return await manager.call_tool("matplotlib", "double_plot_2d", child_payload(child_args, meta))


@mcp.tool()
async def double_plot_3d(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = split_payload(payload)
    x2_data_address = args.get("x2_data_address")
    y2_data_address = args.get("y2_data_address")
    z2_data_address = args.get("z2_data_address")
    x2_data_column = args.get("x2_data_column")
    y2_data_column = args.get("y2_data_column")
    z2_data_column = args.get("z2_data_column")
    if not x2_data_column and x2_data_address:
        x2_data_column = "x"
    if not y2_data_column and y2_data_address:
        y2_data_column = "y"
    if not z2_data_column and z2_data_address:
        z2_data_column = "z"
    child_args = {
        "x1_data": args.get("x1_data") or [],
        "y1_data": args.get("y1_data") or [],
        "z1_data": args.get("z1_data") or [],
        "x2_data": args.get("x2_data") or [],
        "y2_data": args.get("y2_data") or [],
        "z2_data": args.get("z2_data") or [],
        "data_address": args.get("data_address"),
        "x1_data_address": args.get("x1_data_address"),
        "y1_data_address": args.get("y1_data_address"),
        "z1_data_address": args.get("z1_data_address"),
        "x2_data_address": x2_data_address,
        "y2_data_address": y2_data_address,
        "z2_data_address": z2_data_address,
        "x1_data_column": args.get("x1_data_column"),
        "y1_data_column": args.get("y1_data_column"),
        "z1_data_column": args.get("z1_data_column"),
        "x2_data_column": x2_data_column,
        "y2_data_column": y2_data_column,
        "z2_data_column": z2_data_column,
        "title": args.get("title", "Double 3D Figure"),
        "x_label": args.get("x_label", "X-Axis"),
        "y_label": args.get("y_label", "Y-Axis"),
        "z_label": args.get("z_label", "Z-Axis"),
        "file_path": args.get("file_path", "double_3d_figure.png"),
    }
    return await manager.call_tool("matplotlib", "double_plot_3d", child_payload(child_args, meta))

@mcp.tool()
async def euler_diff_solver(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = split_payload(payload)
    child_args = {
        "diff_equation": args.get("diff_equation"),
        "x0": args.get("x0", 0),
        "y0": args.get("y0", 1),
        "x_end": args.get("x_end", 10),
        "step": args.get("step", 0.1),
    }
    return await manager.call_tool("differential_equations", "euler_diff_solver", child_payload(child_args, meta))

@mcp.tool()
async def trapezoidal_diff_solver(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = split_payload(payload)
    child_args = {
        "diff_equation": args.get("diff_equation"),
        "x0": args.get("x0", 0),
        "y0": args.get("y0", 1),
        "x_end": args.get("x_end", 10),
        "step": args.get("step", 0.1),
        "eps": args.get("eps", 1e-6),
    }
    return await manager.call_tool("differential_equations", "trapezoidal_diff_solver", child_payload(child_args, meta))

@mcp.tool()
async def fourier_transform(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = split_payload(payload)
    child_args = {
        "signal": args.get("signal"),
        "sample_rate": args.get("sample_rate", 1.0),
        "window": args.get("window", "rect"),
        "normalize": args.get("normalize", False),
    }
    return await manager.call_tool("fourier", "fourier_transform", child_payload(child_args, meta))

@mcp.tool()
async def inverse_fourier_transform(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = split_payload(payload)
    child_args = {
        "real": args.get("real"),
        "imag": args.get("imag"),
        "normalize": args.get("normalize", False),
    }
    return await manager.call_tool("fourier", "inverse_fourier_transform", child_payload(child_args, meta))

@mcp.tool()
async def short_time_fourier_transform(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = split_payload(payload)
    child_args = {
        "signal": args.get("signal"),
        "window_size": args.get("window_size", 256),
        "hop_length": args.get("hop_length", 64),
        "window": args.get("window", "hann"),
        "sample_rate": args.get("sample_rate", 1.0),
    }
    return await manager.call_tool("fourier", "short_time_fourier_transform", child_payload(child_args, meta))

@mcp.tool()
async def power_spectrum(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = split_payload(payload)
    child_args = {
        "signal": args.get("signal"),
        "sample_rate": args.get("sample_rate", 1.0),
        "window": args.get("window", "rect"),
        "only_positive": args.get("only_positive", True),
    }
    return await manager.call_tool("fourier", "power_spectrum", child_payload(child_args, meta))

@mcp.tool()
async def detect_peaks(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = split_payload(payload)
    child_args = {
        "data_address": args.get("data_address"),
        "x_data": args.get("x_data") or [],
        "y_data": args.get("y_data") or [],
        "x_data_address": args.get("x_data_address"),
        "y_data_address": args.get("y_data_address"),
        "x_data_column": args.get("x_data_column"),
        "y_data_column": args.get("y_data_column"),
        "height": args.get("height"),
        "distance": args.get("distance"),
    }
    return await manager.call_tool("peak_and_valley", "detect_peaks", child_payload(child_args, meta))

@mcp.tool()
async def detect_valleys(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = split_payload(payload)
    child_args = {
        "data_address": args.get("data_address"),
        "x_data": args.get("x_data") or [],
        "y_data": args.get("y_data") or [],
        "x_data_address": args.get("x_data_address"),
        "y_data_address": args.get("y_data_address"),
        "x_data_column": args.get("x_data_column"),
        "y_data_column": args.get("y_data_column"),
        "height": args.get("height"),
        "distance": args.get("distance"),
    }
    return await manager.call_tool("peak_and_valley", "detect_valleys", child_payload(child_args, meta))

@mcp.tool()
async def generate_2d_points(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = split_payload(payload)
    child_args = {
        "function": args.get("function", "x ** 2") or meta.get("function", "x ** 2") or "x ** 2",  
        "variable": args.get("variable", "x"),
        "x_range": args.get("x_range", [-10, 10]),
        "num_points": args.get("num_points", 100),
    }
    return await manager.call_tool("draw_function", "generate_2d_points", child_payload(child_args, meta))

@mcp.tool()
async def generate_3d_points(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = split_payload(payload)
    child_args = {
        "function": args.get("function", "x + y") or meta.get("function", "x + y") or "x + y",
        "variables": args.get("variables", "x,y"),
        "x_range": args.get("x_range", [-10, 10]),
        "y_range": args.get("y_range", [-10, 10]),
        "num_points": args.get("num_points", 100),
    }
    return await manager.call_tool("draw_function", "generate_3d_points", child_payload(child_args, meta))

@mcp.tool()
async def plot_2d_function(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = split_payload(payload)
    child_args = {
        "function": args.get("function", "x ** 2") or meta.get("function", "x ** 2") or "x ** 2",
        "variable": args.get("variable", "x"),
        "x_range": args.get("x_range", [-10, 10]),
        "num_points": args.get("num_points", 100),
        "file_path": args.get("file_path", "function_plot.png") or meta.get("file_path", "function_plot.png") or "function_plot.png",
    }
    return await manager.call_tool("draw_function", "plot_2d_function", child_payload(child_args, meta))

@mcp.tool()
async def plot_3d_function(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = split_payload(payload)
    child_args = {
        "function": args.get("function", "x + y") or meta.get("function", "x + y") or "x + y",
        "variables": args.get("variables", "x,y"),
        "x_range": args.get("x_range", [-10, 10]),
        "y_range": args.get("y_range", [-10, 10]),
        "num_points": args.get("num_points", 100),
        "file_path": args.get("file_path", "function_3d_plot.png") or meta.get("file_path", "function_3d_plot.png") or "function_3d_plot.png",
    }
    return await manager.call_tool("draw_function", "plot_3d_function", child_payload(child_args, meta))

@mcp.tool()
async def compute_relevancy(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = split_payload(payload)
    child_args = {
        "data_address": args.get("data_address") or meta.get("data_address"),
        "x_data": args.get("x_data") or [],
        "y_data": args.get("y_data") or [],
        "x_data_address": args.get("x_data_address"),
        "y_data_address": args.get("y_data_address"),
        "x_data_column": args.get("x_data_column"),
        "y_data_column": args.get("y_data_column"),
    }
    return await manager.call_tool("compute_relevancy", "compute_relevancy", child_payload(child_args, meta))

@mcp.tool()
async def compute_variance(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = split_payload(payload)
    child_args = {
        "data_address": args.get("data_address") or meta.get("data_address"),
        "x_data": args.get("x_data") or [],
        "x_data_address": args.get("x_data_address"),
        "x_data_column": args.get("x_data_column"),
    }
    return await manager.call_tool("compute_relevancy", "compute_variance", child_payload(child_args, meta))

@mcp.tool()
async def generate_square_signal(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = split_payload(payload)
    child_args = {
        "frequency": args.get("frequency", 1.0),
        "positive_ratio": args.get("positive_ratio", 0.5),
        "positive_amplitude": args.get("positive_amplitude", 1.0),
        "negative_amplitude": args.get("negative_amplitude", 0.0),
        "x_start": args.get("x_start", 0.0),
        "x_end": args.get("x_end", 1.0),
        "sampling_step": args.get("sampling_step"),
    }
    return await manager.call_tool("signal_generate", "generate_square_signal", child_payload(child_args, meta))

@mcp.tool()
async def generate_sine_signal(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = split_payload(payload)
    child_args = {
        "frequency": args.get("frequency", 1.0),
        "amplitude": args.get("amplitude", 1.0),
        "phase": args.get("phase", 0.0),
        "x_start": args.get("x_start", 0.0),
        "x_end": args.get("x_end", 1.0),
        "sampling_step": args.get("sampling_step"),
    }
    return await manager.call_tool("signal_generate", "generate_sine_signal", child_payload(child_args, meta))

@mcp.tool()
async def generate_discrete_signal(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = split_payload(payload)
    child_args = _omit_none({
        "source_address": args.get("source_address"),
        "data_address": args.get("data_address"),
        "values": args.get("values"),
        "x_start": args.get("x_start"),
        "x_end": args.get("x_end"),
        "sampling_period": args.get("sampling_period"),
        "sampling_start": args.get("sampling_start"),
        "sampling_end": args.get("sampling_end"),
        "num_samples": args.get("num_samples"),
    })
    return await manager.call_tool("signal_generate", "generate_discrete_signal", child_payload(child_args, meta))

@mcp.tool()
async def draw_signal(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = split_payload(payload)
    child_args = {
        "source_address": args.get("source_address"),
        "data_address": args.get("data_address"),
        "values": args.get("values"),
        "x_start": args.get("x_start"),
        "x_end": args.get("x_end"),
        "sampling_period": args.get("sampling_period"),
        "sampling_start": args.get("sampling_start"),
        "sampling_end": args.get("sampling_end"),
        "num_samples": args.get("num_samples"),
        "figsize": args.get("figsize", (6, 4)),
        "title": args.get("title", "Signal Visualization"),
        "x_label": args.get("x_label", "X-axis"),
        "y_label": args.get("y_label", "Y-axis"),
        "file_path": args.get("file_path", "temp_signal_plot.png"),
    }
    child_args = _omit_none(child_args)
    return await manager.call_tool("signal_generate", "draw_signal", child_payload(child_args, meta))


@mcp.tool()
async def draw_discrete_signal(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = split_payload(payload)
    child_args = {
        "source_address": args.get("source_address"),
        "data_address": args.get("data_address"),
        "values": args.get("values"),
        "x_start": args.get("x_start"),
        "x_end": args.get("x_end"),
        "sampling_period": args.get("sampling_period"),
        "sampling_start": args.get("sampling_start"),
        "sampling_end": args.get("sampling_end"),
        "num_samples": args.get("num_samples"),
        "figsize": args.get("figsize", (6, 4)),
        "title": args.get("title", "Discrete Signal"),
        "x_label": args.get("x_label", "Sample Index"),
        "y_label": args.get("y_label", "Amplitude"),
        "file_path": args.get("file_path", "temp_discrete_signal_plot.png"),
        "linefmt": args.get("linefmt", "C0-"),
        "markerfmt": args.get("markerfmt", "C0o"),
        "basefmt": args.get("basefmt", "k-"),
    }
    child_args = _omit_none(child_args)
    return await manager.call_tool("signal_generate", "draw_discrete_signal", child_payload(child_args, meta))


@mcp.tool()
async def crystal_orientation_for_cubics(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = split_payload(payload)
    child_args = {
        "uvw": args.get("uvw", [1, 0, 0]),
        "hkl": args.get("hkl", [1, 0, 0]),
        "input_type": args.get("input_type", "uvw"),
        "figsize": args.get("figsize", (6, 6)),
        "title": args.get("title", "Crystal Orientation"),
        "file_path": args.get("file_path", "docs/generated_images/crystal_orientation.png"),
    }
    return await manager.call_tool("crystal_basic", "crystal_orientation_for_cubics", child_payload(child_args, meta))

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
