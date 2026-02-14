import pandas as pd
from typing import Any, Dict, Optional, List
from fastmcp import FastMCP

mcp = FastMCP("Pandas Toolbox Server")

@mcp.tool()
def import_csv(file_path: str, sep: str = ',', header: int | None = None, encoding: str = 'utf-8', dtype: Optional[dict] = None, parse_dates: Optional[list] = None, index_col: Optional[int] = None, usecols: Optional[list] = None) -> Dict[str, Any]:
    read_header = 'infer' if header is None else header
    df = pd.read_csv(file_path, sep=sep, header=read_header, encoding=encoding, dtype=dtype, parse_dates=parse_dates, index_col=index_col, usecols=usecols)
    return df.to_dict(orient="list")

@mcp.tool()
def import_excel(file_path: str, sheet_name: Optional[str] = 0, header: int | None = None, dtype: Optional[dict] = None, usecols: Optional[list] = None) -> Dict[str, Any]:
    read_header = 'infer' if header is None else header
    df = pd.read_excel(file_path, sheet_name=sheet_name, header=read_header, dtype=dtype, usecols=usecols)
    return df.to_dict(orient="list")

if __name__ == "__main__":
    mcp.run(transport="stdio")
