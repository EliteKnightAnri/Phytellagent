import json
from datetime import datetime
from pathlib import Path
import matplotlib.pyplot as plt
plt.rcParams['font.family'] = 'DejaVu Sans'  # Ensure consistent font rendering across platforms
from typing import Any, Dict, List, Optional, Tuple
from fastmcp import FastMCP

from data_memory import data_memory

mcp = FastMCP("Matplotlib Toolbox Server")

_LOG_FILE = Path(__file__).resolve().parent / "matplotlib_tool.debug.log"


def _log_debug(event: str, details: Optional[Dict[str, Any]] = None) -> None:
    try:
        payload = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "event": event,
            "details": details or {},
        }
        with _LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _split_payload(payload: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    payload = payload or {}
    return payload.get("args") or {}, payload.get("meta") or {}


def _ensure_list(value: Optional[Any]) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _maybe_error(*lists: List[Any]) -> Optional[str]:
    lengths = [len(lst) for lst in lists]
    filtered = [l for l in lengths if l]
    if not filtered:
        return "input data is empty"
    if len(set(filtered)) > 1:
        return f"data length mismatch: {filtered}"
    return None


def _validate_pair(x: List[Any], y: List[Any], label: str) -> Optional[str]:
    if not x or not y:
        return f"{label} data is empty"
    if len(x) != len(y):
        return f"{label} x/y length mismatch: {len(x)} vs {len(y)}"
    return None


def _validate_triplet(x: List[Any], y: List[Any], z: List[Any], label: str) -> Optional[str]:
    if not x or not y or not z:
        return f"{label} data is empty"
    if len(x) != len(y) or len(x) != len(z):
        return f"{label} x/y/z length mismatch: {len(x)}, {len(y)}, {len(z)}"
    return None


def _success(file_path: str) -> Dict[str, Any]:
    return {"status": "success", "file_path": file_path}


def _to_list(value: Any) -> List[Any]:
    if value is None:
        return []
    try:
        if hasattr(value, "tolist") and not isinstance(value, (list, tuple)):
            value = value.tolist()
    except Exception:
        pass
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _extract_series(source: Any, column: Optional[str]) -> Optional[List[Any]]:
    if source is None:
        return None
    target = source
    if column is not None:
        if isinstance(source, dict):
            if column not in source:
                return None
            target = source[column]
        elif isinstance(source, (list, tuple)):
            # 支持字典列表
            collected: List[Any] = []
            handled = False
            for item in source:
                if isinstance(item, dict) and column in item:
                    collected.append(item[column])
                    handled = True
                elif hasattr(item, column):
                    collected.append(getattr(item, column))
                    handled = True
                else:
                    handled = False
                    break
            if handled:
                target = collected
            else:
                return None
        elif hasattr(source, "__getitem__"):
            try:
                target = source[column]
            except Exception:
                return None
        else:
            return None
    return _to_list(target)


def _load_dataset(args: Dict[str, Any], meta: Dict[str, Any]) -> Tuple[Optional[Any], Optional[str]]:
    address = args.get("data_address") or meta.get("data_address")
    if not address:
        return None, None
    return data_memory.get(address), address


def _resolve_plot_input(name: str, args: Dict[str, Any], meta: Dict[str, Any], dataset: Optional[Any]) -> Tuple[List[Any], Optional[str]]:
    direct = _ensure_list(args.get(name)) or _ensure_list(meta.get(name))
    if direct:
        return direct, None

    address = args.get(f"{name}_address") or meta.get(f"{name}_address")
    column = args.get(f"{name}_column") or meta.get(f"{name}_column")
    if not column and name.endswith("_data"):
        alt = f"{name[:-5]}_column"
        column = args.get(alt) or meta.get(alt)

    if address:
        source = data_memory.get(address)
        if source is None:
            return [], f"{name}_address {address} not found"
        extracted = _extract_series(source, column)
        if extracted is None:
            if column:
                return [], f"column '{column}' not found for {name}"
            return [], f"{name}_address {address} does not contain compatible data"
        return extracted, None

    if column:
        if dataset is None:
            return [], f"data_address is required when specifying {name}_column"
        extracted = _extract_series(dataset, column)
        if extracted is None:
            return [], f"column '{column}' not found for {name}"
        return extracted, None

    return [], None


@mcp.tool()
def plot_in_2d(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = _split_payload(payload)
    dataset, dataset_address = _load_dataset(args, meta)
    if dataset_address and dataset is None:
        _log_debug("plot_in_2d_dataset_missing", {"data_address": dataset_address})
        return {"status": "error", "message": f"data_address {dataset_address} not found"}

    x_data, err = _resolve_plot_input("x_data", args, meta, dataset)
    if err:
        _log_debug("plot_in_2d_input_error", {"axis": "x", "error": err, "data_address": dataset_address})
        return {"status": "error", "message": err}
    y_data, err = _resolve_plot_input("y_data", args, meta, dataset)
    if err:
        _log_debug("plot_in_2d_input_error", {"axis": "y", "error": err, "data_address": dataset_address})
        return {"status": "error", "message": err}
    err = _maybe_error(x_data, y_data)
    if err:
        _log_debug("plot_in_2d_validation_error", {"error": err, "len_x": len(x_data), "len_y": len(y_data), "data_address": dataset_address})
        return {"status": "error", "message": err}

    title = args.get("title") or meta.get("title") or "2D Figure"
    x_label = args.get("x_label", "X-Axis")
    y_label = args.get("y_label", "Y-Axis")
    file_path = args.get("file_path", "2d_figure.png")

    plt.figure()
    plt.plot(x_data, y_data, marker='o')
    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.grid(True)

    plt.savefig(file_path)
    plt.close()
    _log_debug("plot_in_2d_success", {"file_path": file_path, "len": len(x_data), "data_address": dataset_address})
    return _success(file_path)


@mcp.tool()
def plot_in_3d(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = _split_payload(payload)
    dataset, dataset_address = _load_dataset(args, meta)
    if dataset_address and dataset is None:
        _log_debug("plot_in_3d_dataset_missing", {"data_address": dataset_address})
        return {"status": "error", "message": f"data_address {dataset_address} not found"}

    x_data, err = _resolve_plot_input("x_data", args, meta, dataset)
    if err:
        _log_debug("plot_in_3d_input_error", {"axis": "x", "error": err, "data_address": dataset_address})
        return {"status": "error", "message": err}
    y_data, err = _resolve_plot_input("y_data", args, meta, dataset)
    if err:
        _log_debug("plot_in_3d_input_error", {"axis": "y", "error": err, "data_address": dataset_address})
        return {"status": "error", "message": err}
    z_data, err = _resolve_plot_input("z_data", args, meta, dataset)
    if err:
        _log_debug("plot_in_3d_input_error", {"axis": "z", "error": err, "data_address": dataset_address})
        return {"status": "error", "message": err}
    err = _maybe_error(x_data, y_data, z_data)
    if err:
        _log_debug("plot_in_3d_validation_error", {"error": err, "len_x": len(x_data), "len_y": len(y_data), "len_z": len(z_data), "data_address": dataset_address})
        return {"status": "error", "message": err}

    title = args.get("title") or meta.get("title") or "3D Figure"
    x_label = args.get("x_label", "X-Axis")
    y_label = args.get("y_label", "Y-Axis")
    z_label = args.get("z_label", "Z-Axis")
    file_path = args.get("file_path", "3d_figure.png")

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.scatter(x_data, y_data, z_data, marker='o')
    ax.set_title(title)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_zlabel(z_label)

    plt.savefig(file_path)
    plt.close()
    _log_debug("plot_in_3d_success", {"file_path": file_path, "len": len(x_data), "data_address": dataset_address})
    return _success(file_path)


@mcp.tool()
def double_plot_2d(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = _split_payload(payload)
    dataset, dataset_address = _load_dataset(args, meta)
    if dataset_address and dataset is None:
        _log_debug("double_plot_2d_dataset_missing", {"data_address": dataset_address})
        return {"status": "error", "message": f"data_address {dataset_address} not found"}

    x1_data, err = _resolve_plot_input("x1_data", args, meta, dataset)
    if err:
        _log_debug("double_plot_2d_input_error", {"axis": "x1", "error": err, "data_address": dataset_address})
        return {"status": "error", "message": err}
    y1_data, err = _resolve_plot_input("y1_data", args, meta, dataset)
    if err:
        return {"status": "error", "message": err}
    x2_data, err = _resolve_plot_input("x2_data", args, meta, dataset)
    if err:
        return {"status": "error", "message": err}
    y2_data, err = _resolve_plot_input("y2_data", args, meta, dataset)
    if err:
        _log_debug("double_plot_2d_input_error", {"axis": "y2", "error": err, "data_address": dataset_address})
        return {"status": "error", "message": err}
    err = _validate_pair(x1_data, y1_data, "series 1")
    if err:
        _log_debug("double_plot_2d_validation_error", {"error": err, "lens": [len(x1_data), len(y1_data)], "series": 1, "data_address": dataset_address})
        return {"status": "error", "message": err}

    if x2_data and y2_data:
        err = _validate_pair(x2_data, y2_data, "series 2")
        if err:
            _log_debug("double_plot_2d_validation_error", {"error": err, "lens": [len(x2_data), len(y2_data)], "series": 2, "data_address": dataset_address})
            return {"status": "error", "message": err}
    else:
        x2_data = []
        y2_data = []

    title = args.get("title") or meta.get("title") or "Double 2D Figure"
    x_label = args.get("x_label", "X-Axis")
    y_label = args.get("y_label", "Y-Axis")
    file_path = args.get("file_path", "double_2d_figure.png")

    plt.figure()
    plt.plot(x1_data, y1_data, marker='o', label='Set 1')
    if x2_data:
        plt.plot(x2_data, y2_data, marker='x', linestyle='none', label='Set 2')
    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.grid(True)
    plt.legend()

    plt.savefig(file_path)
    plt.close()
    _log_debug("double_plot_2d_success", {"file_path": file_path, "lens": [len(x1_data), len(y1_data), len(x2_data), len(y2_data)], "data_address": dataset_address})
    return _success(file_path)


@mcp.tool()
def double_plot_3d(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401 - ensures 3d projection registered

    args, meta = _split_payload(payload)
    dataset, dataset_address = _load_dataset(args, meta)
    if dataset_address and dataset is None:
        _log_debug("double_plot_3d_dataset_missing", {"data_address": dataset_address})
        return {"status": "error", "message": f"data_address {dataset_address} not found"}

    x1_data, err = _resolve_plot_input("x1_data", args, meta, dataset)
    if err:
        _log_debug("double_plot_3d_input_error", {"axis": "x1", "error": err, "data_address": dataset_address})
        return {"status": "error", "message": err}
    y1_data, err = _resolve_plot_input("y1_data", args, meta, dataset)
    if err:
        return {"status": "error", "message": err}
    z1_data, err = _resolve_plot_input("z1_data", args, meta, dataset)
    if err:
        return {"status": "error", "message": err}
    x2_data, err = _resolve_plot_input("x2_data", args, meta, dataset)
    if err:
        return {"status": "error", "message": err}
    y2_data, err = _resolve_plot_input("y2_data", args, meta, dataset)
    if err:
        return {"status": "error", "message": err}
    z2_data, err = _resolve_plot_input("z2_data", args, meta, dataset)
    if err:
        _log_debug("double_plot_3d_input_error", {"axis": "z2", "error": err, "data_address": dataset_address})
        return {"status": "error", "message": err}
    err = _validate_triplet(x1_data, y1_data, z1_data, "series 1")
    if err:
        _log_debug("double_plot_3d_validation_error", {"error": err, "lens": [len(x1_data), len(y1_data), len(z1_data)], "series": 1, "data_address": dataset_address})
        return {"status": "error", "message": err}

    if x2_data and y2_data and z2_data:
        err = _validate_triplet(x2_data, y2_data, z2_data, "series 2")
        if err:
            _log_debug("double_plot_3d_validation_error", {"error": err, "lens": [len(x2_data), len(y2_data), len(z2_data)], "series": 2, "data_address": dataset_address})
            return {"status": "error", "message": err}
    else:
        x2_data = []
        y2_data = []
        z2_data = []

    title = args.get("title") or meta.get("title") or "Double 3D Figure"
    x_label = args.get("x_label", "X-Axis")
    y_label = args.get("y_label", "Y-Axis")
    z_label = args.get("z_label", "Z-Axis")
    file_path = args.get("file_path", "double_3d_figure.png")

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.scatter(x1_data, y1_data, z1_data, marker='o', label='Set 1')
    if x2_data:
        ax.scatter(x2_data, y2_data, z2_data, marker='x', label='Set 2')
    ax.set_title(title)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_zlabel(z_label)
    plt.legend()

    plt.savefig(file_path)
    plt.close()
    _log_debug("double_plot_3d_success", {"file_path": file_path, "lens": [len(x1_data), len(y1_data), len(z1_data), len(x2_data), len(y2_data), len(z2_data)], "data_address": dataset_address})
    return _success(file_path)


if __name__ == "__main__":
    mcp.run(transport="stdio")
