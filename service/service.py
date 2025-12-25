from mcp.server.fastmcp import FastMCP
from tools.bilibili_tool import general_search
from tools.mysql_tool import execute_query

mcp = FastMCP('MCP service')

mcp.tool()(general_search)
mcp.tool()(execute_query)

if __name__ == "__main__":
    mcp.run(transport='http', host='')