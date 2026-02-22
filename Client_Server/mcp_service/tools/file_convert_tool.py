"""
占位：文件转换工具（原仓库中为空文件）。
可在需要时实现具体转换（例如：docx->txt、pdf->txt 等）。
"""

from fastmcp import FastMCP

mcp = FastMCP("File Convert Tool")

@mcp.tool()
def noop() -> str:
    return "noop"

if __name__ == "__main__":
    mcp.run(transport='stdio')
