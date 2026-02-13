import asyncio
import sys
from fastmcp import Client

sys.path.append("E:/local_mcp/tools")

async def main():
    client = Client("E:/local_mcp/service/tools/system_info_tool.py")
    async with client:
        await client.ping()
        tools = await client.list_tools()
        print("TOOLS:", tools)

if __name__ == "__main__":
    asyncio.run(main())
