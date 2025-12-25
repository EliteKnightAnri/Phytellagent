from bilibili_api import search, sync
from fastapi import FastAPI, Request, HTTPException
from typing import Dict, Any
import uvicorn

# 使用FastAPI创建应用
app = FastAPI(title="Bilibili tool", version="1.0")

# 定义视频搜索功能
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

async def process_request(request: Request) -> Dict[str, Any]:
    try:
        body = await request.json()
        # 打印调试信息
        print(f"Request received: {body}")
        
        # 支持多种可能的字段名
        method = body.get("method") or body.get("function") or body.get("action")
        params = body.get("params") or body.get("arguments") or body.get("parameters") or {}
        
        return {"method": method, "params": params}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")

# 定义搜索端点
@app.post("/search")
async def search_endpoint(request: dict): 
    function_name = request.get("function")
    params = request.get("params", {})
    keyword = params.get("keyword", "") 
    
    print(f"Received searching request - function: {function_name}, keyword: {keyword}")
    
    if not keyword:
        return {"error": "Keyword is required"}
    
    # 调用搜索函数
    result = search_videos(keyword)
    return {"result": result}
    
if __name__ == "__main__":
    uvicorn.run(
        # 0.0.0.0表示监听所有可用的网络接口，如果只想监听本机，可以改成127.0.0.1
        # 如果8080端口被占用，可以换一个端口
        app="service.tools.bilibili_tool:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
    )