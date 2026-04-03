import pandas as pd
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple, Any
from fastmcp import FastMCP

BASE_DIR = Path(__file__).resolve().parents[3]
SRC_DIR = BASE_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
    
from mcp_stack.local_packages.data_memory import data_memory
from mcp_stack.local_packages.status import success, error, split_payload, load_dataset

mcp = FastMCP("Pandas Toolbox Server")


def _split_payload(payload: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    payload = payload or {}
    return payload.get("args") or {}, payload.get("meta") or {}


def _register_dataframe(df: pd.DataFrame, file_path: str) -> Dict[str, Any]:
    data_address = data_memory.store(df)
    return {
        "status": "success",
        "data_address": data_address,
        "file_path": file_path,
        "columns": list(df.columns),
        "shape": {"rows": int(df.shape[0]), "cols": int(df.shape[1])},
    }


@mcp.tool()
def import_csv(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = _split_payload(payload)
    file_path = args.get("file_path") or meta.get("file_path")
    if not file_path:
        return {"status": "error", "message": "file_path is required"}

    header = args.get("header")
    read_header = 'infer' if header is None else header
    df = pd.read_csv(
        file_path,
        sep=args.get("sep", ','),
        header=read_header,
        encoding=args.get("encoding", "utf-8"),
        dtype=args.get("dtype"),
        parse_dates=args.get("parse_dates"),
        index_col=args.get("index_col"),
        usecols=args.get("usecols"),
    )
    return _register_dataframe(df, file_path)


@mcp.tool()
def import_excel(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = _split_payload(payload)
    file_path = args.get("file_path") or meta.get("file_path")
    if not file_path:
        return {"status": "error", "message": "file_path is required"}

    header = args.get("header")
    read_header = 'infer' if header is None else header
    df = pd.read_excel(
        file_path,
        sheet_name=args.get("sheet_name", 0),
        header=read_header,
        dtype=args.get("dtype"),
        usecols=args.get("usecols"),
    )
    return _register_dataframe(df, file_path)

if __name__ == "__main__":
    mcp.run(transport="stdio")
