import numpy as np
from fastmcp import FastMCP
from typing import Any, Dict, Optional, Tuple

mcp = FastMCP("Relevancy Computation Server")

def _split_payload(payload: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    payload = payload or {}
    return payload.get("args") or {}, payload.get("meta") or {}

