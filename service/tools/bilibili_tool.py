from bilibili_api import search, sync
from fastmcp import FastMCP

# 使用FastMCP创建服务器
mcp = FastMCP(name="Bilibili tool")

# 定义视频搜索功能
@mcp.tool()
def search_videos(keyword: str) -> dict:
    """
    Search Bilibili for the given keyword and return the results as a dictionary.

    Args:
        keyword (str): Search term to query on Bilibili.

    Returns:
        dict: A dictionary containing the search results.
    """

    # sync是一个同步执行异步函数的工具
    return sync(search.search(keyword))

if __name__ == "__main__":
    mcp.run(transport="stdio")