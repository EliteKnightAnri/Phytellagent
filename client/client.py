import json
import httpx
import uvicorn
# 这个库调试连接的时候可以用到
import subprocess
from openai import AsyncOpenAI
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# 使用FastAPI创建Client应用
app = FastAPI(title="HTTP Client", version="1.0")

SERVERS = {
    "search_videos": {
        "url": "http://127.0.0.1:8080/search",
        "description": "在哔哩哔哩 (Bilibili) 上搜索视频内容。"
    },
    "execute_query": {
        "url": "http://127.0.0.1:8081/query",
        "description": "执行一条SQL语句。查询或修改数据库。"
    }
}

# 这是DeepSeek的工具定义格式，是强制的，改格式会导致工具调用失败
tools = [
    {
        "type": "function",
        "function":{
            "name": "search_videos",
            "description": "在哔哩哔哩 (Bilibili) 上搜索视频内容。",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "要搜索的关键词。"
                    }
                },
                "required": ["keyword"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_query",
            "description": "执行一条SQL语句。查询或修改数据库。",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "要执行的SQL语句。"
                    }
                },
                "required": ["sql"]
            }
        }
    }
]

client = AsyncOpenAI(
    api_key="sk-f39a29f6e7e24ac687c88285fc664dd7",
    base_url="https://api.deepseek.com/v1"
    )

# HTTP POST是典型的IO密集型操作，使用异步函数可以提高并发性能
async def call_tool(function_name: str, params: dict) -> dict:
    url = SERVERS.get(function_name)["url"]
    # 现在的服务器只能解析IPv4地址，所以暂时先替换localhost
    url = url.replace("localhost", "127.0.0.1")
    # 打印调试日志
    print(f"Calling tool {function_name} at {url} with params: {params}")
    if not url:
        raise ValueError(f"Unknown function: {function_name}")

    payload = {
        "function": function_name,
        "params": params
    }
    
    # with是异步上下文管理器，确保资源正确释放
    # AsyncClient是httpx库的异步HTTP客户端，它的所有请求方法都需要await关键字
    async with httpx.AsyncClient() as client:
        # 通过await等待HTTP响应
        response = await client.post(url, json=payload, timeout=30)
        # 打印调试日志，如果是503可以看看是不是跨域问题
        print(f"Response status code from {function_name}: {response.status_code}")
        response.raise_for_status()
        response_data = response.json()
        print(f"Raw response from {function_name}:", response_data)
        
        # 适配不同工具的返回格式
        if "result" in response_data:
            return response_data["result"]
        elif "response" in response_data:
            return response_data["response"]
        else:
            return response_data

# 异步AI agent
async def ai_agent(user_input: str) -> str:
    print("AI agent received input:", user_input)

    # 这段是写给AI agent看的prompt
    messages = [
        {
            "role": "system", 
            "content": "你是一个AI agent，可以使用提供的工具来帮助用户完成任务。请根据用户的问题，自主决定是否需要调用工具，以及调用哪个工具。如果调用工具，请严格按照给定的函数格式进行调用。如果无法调用工具，请向用户返回错误信息来帮助用户完成调试。"         
        },
        {
            "role": "user",
            "content": user_input
        }
    ]

    while True:
        print("Sending messages to AI agent:", messages)
        # AI agent调用chat.completions接口生成响应
        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=tools
        )
        # 如果你希望AI agent不止调用一个工具，可以把下面这行注释掉
        response_message = response.choices[0].message
        # 扩展对话历史，方便AI agent参考之前的内容
        messages.append(response_message)

        if not response_message.tool_calls:
            print("AI agent didn't call any function. Now responding to user...")
            return response_message.content
        
        # tool_calls是一个列表，tool_call是包含函数名和参数的字典元素
        for tool_call in response_message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            tool_call_id = tool_call.id
            
            # 打印调试信息
            print(f"调用工具: {function_name}")
            print(f"参数: {function_args}")
            print(f"调用ID: {tool_call_id}")
            
            # 异步调用工具
            tool_result = await call_tool(function_name, function_args)
            
            # 将工具调用结果添加到对话历史
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "name": function_name,
                "content": json.dumps(tool_result, ensure_ascii=False)
            })

# 定义请求体模型
class UserInput(BaseModel):
    input: str

# 定义聊天端点
@app.post("/chat")
async def chat_endpoint(user_input: UserInput):
        try:
            ai_response = await ai_agent(user_input.input)
            return {"response": ai_response}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # 0.0.0.0表示监听所有可用的网络接口，如果只想监听本机，可以改成127.0.0.1
    # 如果8000端口被占用，可以换一个端口
    uvicorn.run("client:app", host="0.0.0.0", port=8000, reload=True)