import json
import asyncio
import httpx
import uvicorn
from typing import Dict, Any, Optional
# 这个库调试连接的时候可以用到
import subprocess
from openai import AsyncOpenAI
from fastmcp import Client, FastMCP
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
    },
    "get_system_info": {
        "stdio_cmd": [
            "python",
            "-m",
            "service.tools.system_info_tool",
        ],
        "description": "传入一个系统信息字段名，返回对应的值；不传入则返回所有系统信息。",
    },
    "get_environment_variables": {
        "stdio_cmd": [
            "python",
            "-m",
            "service.tools.system_info_tool",
        ],
        "description": "返回环境变量映射（字典）。",
    },
    "disk_usage": {
        "stdio_cmd": [
            "python",
            "-m",
            "service.tools.system_info_tool",
        ],
        "description": "传入一个路径，返回该路径的磁盘使用情况；不传入则使用系统根路径。",
    },
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
    }, 
    {
        "type": "function",
        "function": {
            "name": "get_system_info",
            "description": "传入一个系统信息字段名，返回对应的值；不传入则返回所有系统信息。",
            "parameters": {
                "type": "object", 
                "properties": {
                    "key": {
                        "type": "string", 
                        "description": "系统信息字段名，可选值有：os, os_version, architecture, cpu_count, memory_total_gb, disk_total_gb, hostname, python_version"
                    }
                }, 
                "required": ["key"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_environment_variables",
            "description": "返回环境变量映射（字典）。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "disk_usage",
            "description": "传入一个路径，返回该路径的磁盘使用情况；不传入则使用系统根路径。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要查询的路径。"
                    }
                },
                "required": ["path"]
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
    server = SERVERS.get(function_name)
    if not server:
        raise ValueError(f"Unknown function: {function_name}")

    # 选择stdio
    if server.get("stdio_cmd"):
        stdio_cmd = server.get("stdio_cmd")
        stdio_client = Client("service.tools.system_info_tool", transport="stdio", cmd=stdio_cmd)
        async with stdio_client:
            await stdio_client.ping()
            print(f"Calling tool {function_name} via stdio with params: {params}")
            response = await stdio_client.call_tool(function_name, **params)
            print(f"Response from {function_name} via stdio:", response)
            return response

    # 选择HTTP
    url = server.get("url")
    if not url:
        raise ValueError(f"Unknown function: {function_name}")

    url = url.replace("localhost", "127.0.0.1")
    # 打印调试日志
    print(f"Calling tool {function_name} at {url} with params: {params}")

    payload = {"function": function_name, "params": params}
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, timeout=30)
        print(f"Response status code from {function_name}: {response.status_code}")
        response.raise_for_status()
        response_data = response.json()
        print(f"Raw response from {function_name}:", response_data)
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