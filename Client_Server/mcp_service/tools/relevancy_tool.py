import numpy as np
from fastmcp import FastMCP
from data_memory import data_memory
from typing import Any, Dict, Optional, Tuple, List

mcp = FastMCP("Relevancy Computation Server")

def _split_payload(payload: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    payload = payload or {}
    return payload.get("args") or {}, payload.get("meta") or {}

def _error(message: str) -> Dict[str, Any]:
    return {"status": "error", "message": message}

def _success(data: Dict[str, Any]) -> Dict[str, Any]:
    return {"status": "success", "data": data}

def _load_dataset(args: Dict[str, Any], meta: Dict[str, Any]) -> Tuple[Optional[Any], Optional[str]]:
    address = args.get("data_address") or meta.get("data_address")
    if not address:
        return None, None
    return data_memory.get(address), address

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


def _extract_from_source(source: Any, column: Optional[str]) -> Optional[list]:
    if source is None:
        return None
    if column is None:
        return _object_to_list(source)

    if isinstance(source, dict):
        if column not in source:
            return None
        return _object_to_list(source[column])

    if hasattr(source, "__getitem__"):
        try:
            selection = source[column]
        except Exception:
            return None
        return _object_to_list(selection)

    return None

def _resolve_series(name: str, args: Dict[str, Any], meta: Dict[str, Any], dataset: Optional[Any]) -> Tuple[Optional[list], Optional[str]]:
    direct = _as_list(args.get(name)) or _as_list(meta.get(name))
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
            return None, f"{name}_address {address} not found"
        extracted = _extract_from_source(source, column)
        if extracted is None:
            if column:
                return None, f"column '{column}' not found for {name}"
            return None, f"{name}_address {address} does not contain compatible data"
        return extracted, None

    if column:
        if dataset is None:
            return None, f"data_address is required when specifying {name}_column"
        extracted = _extract_from_source(dataset, column)
        if extracted is None:
            return None, f"column '{column}' not found for {name}"
        return extracted, None

    return None, None