import pandas as pd
from typing import Any, Dict, Optional, List
from fastmcp import FastMCP

mcp = FastMCP("Pandas Toolbox Server")

@mcp.tool()
def import_csv(file_path: str, sep: str = ',', header: int | None = None, encoding: str = 'utf-8', dtype: Optional[dict] = None, parse_dates: Optional[list] = None, index_col: Optional[int] = None, usecols: Optional[list] = None) -> Dict[str, Any]:
    """
    Import a CSV file into a pandas DataFrame.

    Args:
        file_path (str): The path to the CSV file or TXT file.
        sep (str, optional): The delimiter to use. Defaults to ','.
        header (int | None, optional): Row number(s) to use as the column names. Defaults to None (let pandas infer).
        encoding (str, optional): The encoding of the file. Defaults to 'utf-8'.
        **kwargs: Additional keyword arguments to pass to pd.read_csv().

    Returns:
        Dict[str, Any]: The imported DataFrame as a dictionary with lists for each column.
    """
    # 将显式参数传递给 pandas.read_csv，header=None 表示让 pandas 自动推断（与原来的 'infer' 行为一致）
    read_header = 'infer' if header is None else header
    df = pd.read_csv(file_path, sep=sep, header=read_header, encoding=encoding, dtype=dtype, parse_dates=parse_dates, index_col=index_col, usecols=usecols)
    
    return df.to_dict(orient="list")

@mcp.tool()
def import_excel(file_path: str, sheet_name: Optional[str] = 0, header: int | None = None, dtype: Optional[dict] = None, usecols: Optional[list] = None) -> Dict[str, Any]:
    """
    Import an Excel file into a pandas DataFrame.

    Args:
        file_path (str): The path to the Excel file.
        **kwargs: Additional keyword arguments to pass to pd.read_excel().

    Returns:
        Dict[str, Any]: The imported DataFrame as a dictionary with lists for each column.
    """
    read_header = 'infer' if header is None else header
    df = pd.read_excel(file_path, sheet_name=sheet_name, header=read_header, dtype=dtype, usecols=usecols)
    
    return df.to_dict(orient="list")

if __name__ == "__main__":
    mcp.run(transport="stdio")
