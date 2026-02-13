import json
import asyncio
from typing import Dict, Any, Optional
# 这个库调试连接的时候可以用到
import subprocess
from openai import AsyncOpenAI
from fastmcp import Client

agent = AsyncOpenAI(
    api_key="sk-f39a29f6e7e24ac687c88285fc664dd7",
    base_url="https://api.deepseek.com/v1"
    )

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
    },
    {
        "type": "function",
        "function": {
            "name": "import_csv",
            "description": "将CSV文件或TXT文件导入为pandas DataFrame。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "CSV或TXT文件的路径。"
                    },
                    "sep": {
                        "type": "string",
                        "description": "分隔符，默认为逗号 ','."
                    },
                    "header": {
                        "type": ["integer", "null"],
                        "description": "指定行数作为列名，默认为None表示自动推断."
                    },
                    "encoding": {
                        "type": "string",
                        "description": "文件编码，默认为'utf-8'."
                    },
                    "dtype": {
                        "type": ["object", "null"],
                        "description": "列的数据类型映射字典，默认为None."
                    },
                    "parse_dates": {
                        "type": ["array", "null"],
                        "description": "需要解析为日期的列名列表，默认为None."
                    },
                    "index_col": {
                        "type": ["integer", "null"],
                        "description": "指定某列作为索引列，默认为None."
                    },
                    "usecols": {
                        "type": ["array", "null"],
                        "description": "需要导入的列名列表，默认为None表示导入所有列."
                    },
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "least_square_fit_2d",
            "description": "对提供的2D数据进行最小二乘拟合，返回优化后的参数和协方差矩阵。对于用户输入的表达式，请转化为遵循Python语法的字符串，如用户输入'ax^2+bx+c'时，转化为'a*x**2+b*x+c'。",
            "parameters": {
                "type": "object",
                "properties": {
                    "x_data": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "自变量数据列表。"
                    },
                    "y_data": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "因变量数据列表。"
                    },
                    "model_func_str": {
                        "type": "string",
                        "description": "模型函数的字符串表示，遵循Python语法。"
                    },
                    "initial_params": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "模型函数的初始参数猜测列表。如果用户未传入初始参数，则这一部分为None。"
                    }
                },
                "required": ["x_data", "y_data", "initial_params"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "least_square_fit_3d",
            "description": "对提供的3D数据进行最小二乘拟合，返回优化后的参数和协方差矩阵。对于用户输入的表达式，请转化为遵循Python语法的字符串，如用户输入'ax^2+bx+c'时，转化为'a*x**2+b*x+c'。",
            "parameters": {
                "type": "object",
                "properties": {
                    "x_data": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "自变量数据列表。"
                    },
                    "y_data": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "自变量数据列表。"
                    },
                    "z_data": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "因变量数据列表。"
                    },
                    "model_func_str": {
                        "type": "string",
                        "description": "模型函数的字符串表示，遵循Python语法。"
                    },
                    "initial_params": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "模型函数的初始参数猜测列表。如果用户未传入初始参数，则这一部分为None。"
                    },
                },
                "required": ["x_data", "y_data", "z_data", "initial_params"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "plot_in_2d",
            "description": "生成一个2D图表并返回图像文件路径。",
            "parameters": {
                "type": "object",
                "properties": {
                    "x_data": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "X轴数据列表。"
                    },
                    "y_data": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Y轴数据列表。"
                    },
                    "title": {
                        "type": "string",
                        "description": "图表标题。"
                    },
                    "x_label": {
                        "type": "string",
                        "description": "X轴标签。"
                    },
                    "y_label": {
                        "type": "string",
                        "description": "Y轴标签。"
                    },
                    "file_path": {
                        "type": "string",
                        "description": "保存图像的文件路径。"
                    }
                },
                "required": ["x_data", "y_data", "title", "x_label", "y_label", "file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "plot_in_3d",
            "description": "生成一个3D图表并返回图像文件路径。",
            "parameters": {
                "type": "object",
                "properties": {
                    "x_data": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "X轴数据列表。"
                    },
                    "y_data": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Y轴数据列表。"
                    },
                    "z_data": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Z轴数据列表。"
                    },
                    "title": {
                        "type": "string",
                        "description": "图表标题。"
                    },
                    "x_label": {
                        "type": "string",
                        "description": "X轴标签。"
                    },
                    "y_label": {
                        "type": "string",
                        "description": "Y轴标签。"
                    },
                    "z_label": {
                        "type": "string",
                        "description": "Z轴标签。"
                    },
                    "file_path": {
                        "type": "string",
                        "description": "保存图像的文件路径。"
                    },
                },
                "required": ["x_data", "y_data", "z_data", "title", "x_label", "y_label", "z_label", "file_path"]
            }
        }
    }
]

async def call_tool(client: Client, function_name: str, function_args: Dict[str, Any]) -> Any:
    await client.ping()

    # 获取元数据方便调试；结果未使用但可用于后续扩展
    await client.list_tools()
    await client.list_resources()
    await client.list_prompts()

    result = await client.call_tool(function_name, function_args)

    try:
        result = json.loads(result)
    except Exception:
        if hasattr(result, "structured_content"):
            result = result.structured_content
        elif hasattr(result, "content"):
            result = json.loads(result.content[0].text)

    return result

async def ai_agent(client: Client, user_input: str) -> str:
    print("AI Agent received input:", user_input)

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
        response = await agent.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        # 如果你希望AI agent不止调用一个工具，可以把下面这行注释掉
        response_message = response.choices[0].message
        if not response_message.tool_calls:
            print("AI agent didn't call any function. Now responding to user...")
            return response_message.content

        # 扩展对话历史，方便AI agent参考上文
        messages.append(response_message)
        
        # tool_calls是一个列表，tool_call是包含函数名和参数的字典元素
        for tool_call in response_message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            tool_call_id = tool_call.id

            # 打印调试信息
            print(f"AI agent is calling tool: {function_name}")
            print(f"With arguments and ID: {function_args}, {tool_call_id}")

            tool_result = await call_tool(client, function_name, function_args)
            print(tool_result)

            # 将工具调用结果添加到对话历史
            # 到这里开始报错TypeError: Object of type CallToolResult is not JSON serializable，记得查一下怎么回事
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "name": function_name,
                "content": json.dumps(tool_result, ensure_ascii=False)
            })

        # 工具结果已加入对话历史，向模型再次询问以生成自然语言答复
        followup = await agent.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        final_message = followup.choices[0].message
        if not final_message.tool_calls:
            return final_message.content

        # 如果模型仍要调用更多工具，必须先执行这些工具并添加对应的tool消息
        messages.append(final_message)
        for tool_call in final_message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            tool_call_id = tool_call.id

            print(f"AI agent is calling tool: {function_name}")
            print(f"With arguments and ID: {function_args}, {tool_call_id}")

            tool_result = await call_tool(client, function_name, function_args)
            print(tool_result)

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "name": function_name,
                "content": json.dumps(tool_result, ensure_ascii=False)
            })
        # 继续循环，向模型再次询问
        continue

async def main() -> None:
    async with Client("E:/local_mcp/service/service.py") as client:
        while True:
            user_input = input("Please enter your query: ")
            if user_input.lower() in ["exit", "quit"]:
                print("Exiting...")
                break
            response = await ai_agent(client, user_input)
            print("AI Agent response:", response)


if __name__ == "__main__":
    asyncio.run(main())