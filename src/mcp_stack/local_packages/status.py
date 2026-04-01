import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from .data_memory import data_memory


def split_payload(payload: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """将请求载荷分解为参数和元数据。"""

    payload = payload or {}
    return payload.get("args") or {}, payload.get("meta") or {}


def build_payload(
    args: Optional[Dict[str, Any]] = None,
    meta: Optional[Dict[str, Any]] = None,
    *,
    prompt: Optional[str] = None,
) -> Dict[str, Dict[str, Any]]:
    """生成标准 MCP 调用载荷，确保 args/meta 始终存在。"""

    payload_args = dict(args or {})
    payload_meta = dict(meta or {})
    if prompt:
        payload_meta.setdefault("prompt", prompt)
    return {"args": payload_args, "meta": payload_meta}


def child_payload(
    args: Optional[Dict[str, Any]] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Dict[str, Any]]:
    """聚合器往子服务器转发时使用的简化载荷结构。"""

    return {"args": args or {}, "meta": meta or {}}


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