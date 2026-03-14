import numpy as np
from scipy.signal import find_peaks
from fastmcp import FastMCP
from data_memory import data_memory
from typing import Any, Dict, Optional, Tuple, List

mcp = FastMCP("Peak Detection Server")


def _split_payload(payload: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    payload = payload or {}
    return payload.get("args") or {}, payload.get("meta") or {}


def _error(message: str) -> Dict[str, Any]:
    return {"status": "error", "message": message}


def _success(data: Dict[str, Any]) -> Dict[str, Any]:
    return {"status": "success", "data": data}


def _ensure_list(value: Optional[Any]) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


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


def _resolve_series(name: str, args: Dict[str, Any], meta: Dict[str, Any], dataset: Optional[Any]) -> Tuple[List[Any], Optional[str]]:
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


def _bind_xy_pairs(x_series: List[Any], y_series: List[Any], indices: Any) -> List[Dict[str, Any]]:
    if indices is None:
        return []
    try:
        iterable = indices.tolist() if hasattr(indices, "tolist") else list(indices)
    except TypeError:
        iterable = []

    bound: List[Dict[str, Any]] = []
    x_len = len(x_series)
    y_len = len(y_series)
    for idx in iterable:
        try:
            idx_int = int(idx)
        except (TypeError, ValueError):
            continue
        if idx_int < 0 or idx_int >= y_len:
            continue
        point: Dict[str, Any] = {
            "index": idx_int,
            "y": y_series[idx_int],
            "x": x_series[idx_int] if idx_int < x_len else None,
        }
        bound.append(point)
    return bound


def _prepare_valley_height(height: Optional[Any]) -> Optional[Any]:
    if height is None:
        return None
    if isinstance(height, (int, float)):
        return -height
    if isinstance(height, (list, tuple)):
        negated = [
            -value if isinstance(value, (int, float)) else value
            for value in height
        ]
        return type(height)(negated)
    return height


@mcp.tool()
def detect_peaks(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = _split_payload(payload)
    dataset, dataset_address = _load_dataset(args, meta)
    if dataset is None and dataset_address is not None:
        return _error(f"data_address {dataset_address} not found")

    x_data, error = _resolve_series("x_data", args, meta, dataset)
    if error:
        return _error(error)
    if not x_data:
        return _error("No data provided for 'x_data'")
    
    y_data, error = _resolve_series("y_data", args, meta, dataset)
    if error:
        return _error(error)
    if not y_data:
        return _error("No data provided for 'y_data'")

    height = args.get("height") or meta.get("height")
    distance = args.get("distance") or meta.get("distance")
    distance = int(distance) if distance is not None else 5
    peaks, properties = find_peaks(y_data, height=height, distance=distance)

    peak_points = _bind_xy_pairs(x_data, y_data, peaks)
    peak_points_address = data_memory.store(peak_points)
    result = {
        "peak_points_address": peak_points_address,
        "peak_count": len(peaks),
        "properties": {k: v.tolist() for k, v in properties.items()}
    }
    
    return _success(result)

@mcp.tool()
def detect_valleys(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = _split_payload(payload)
    dataset, dataset_address = _load_dataset(args, meta)
    if dataset is None and dataset_address is not None:
        return _error(f"data_address {dataset_address} not found")

    x_data, error = _resolve_series("x_data", args, meta, dataset)
    if error:
        return _error(error)
    if not x_data:
        return _error("No data provided for 'x_data'")
    
    y_data, error = _resolve_series("y_data", args, meta, dataset)
    if error:
        return _error(error)
    if not y_data:
        return _error("No data provided for 'y_data'")

    raw_height = args.get("height") or meta.get("height")
    height = _prepare_valley_height(raw_height)
    distance = args.get("distance") or meta.get("distance")
    distance = int(distance) if distance is not None else 5
    inverted_y = [-y for y in y_data]
    valleys, properties = find_peaks(inverted_y, height=height, distance=distance)
    if "peak_heights" in properties:
        properties["peak_heights"] = -np.asarray(properties["peak_heights"])

    valley_points = _bind_xy_pairs(x_data, y_data, valleys)
    valley_points_address = data_memory.store(valley_points)
    result = {
        "valley_points_address": valley_points_address,
        "valley_count": len(valleys),
        "properties": {k: v.tolist() for k, v in properties.items()}
    }

    return _success(result)

if __name__ == "__main__":
    mcp.run(transport="stdio")