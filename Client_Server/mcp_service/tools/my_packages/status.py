import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from my_packages.data_memory import data_memory


def split_payload(payload: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    将请求载荷分解为参数和元数据
    
    Args:
        payload: 包含请求数据的字典，通常包含 "args" 和 "meta" 两个键
    Returns:
        一个元组，包含两个字典：第一个是参数字典（args），第二个是元数据字典（meta）。如果payload中缺少这些键，则返回空字典。
    """

    payload = payload or {}
    return payload.get("args") or {}, payload.get("meta") or {}


def success(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    构造一个成功响应的状态字典
    
    Args:
        data: 包含响应数据的字典，将被包含在成功响应中

    Returns:
        一个字典，表示成功状态和包含的数据
        
    """

    return {"status": "success", "data": data}


def error(message: str) -> Dict[str, Any]:
    """
    构造一个错误响应的状态字典
    
    Args:
        message: 错误信息
    
    Returns:
        一个字典，表示错误状态和错误信息

    """

    return {"status": "error", "message": message}


def load_dataset(args: Dict[str, Any], meta: Dict[str, Any]) -> Tuple[Optional[Any], Optional[str]]:
    """
    从数据的内存地址中加载数据

    Args:
        args: 包含请求参数的字典，可能包含 "data_address" 键
        meta: 包含元数据的字典，可能包含 "data_address" 键

    Returns:
        一个元组，包含加载的数据和数据地址，如果未找到数据则返回 (None, None)

    """
    address = args.get("data_address") or meta.get("data_address")
    if not address:
        return None, None
    return data_memory.get(address), address


def log_debug(log_file: str, event: str, details: Optional[Dict[str, Any]] = None) -> None:
    _LOG_FILE = Path(__file__).resolve().parent / log_file
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