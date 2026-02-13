import json
import asyncio
from typing import Dict, Any, Optional, List
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
            "name": "generate_pred_values_2d",
            "description": "使用拟合得到的模型函数和参数，生成对应的预测值列表。对于用户输入的表达式，请转化为遵循Python语法的字符串，如用户输入'ax^2+bx+c'时，转化为'a*x**2+b*x+c'。",
            "parameters": {
                "type": "object",
                "properties": {
                    "x_data": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "用于生成预测值的自变量x数据列表。"
                    },                    
                    "model_func_str": {
                        "type": "string",
                        "description": "模型函数的字符串表示，遵循Python语法。"
                    },
                    "params": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "模型函数的参数列表。"
                    }
                },
                "required": ["model_func_str", "params", "x_data"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_pred_values_3d",
            "description": "使用拟合得到的模型函数和参数，生成对应的预测值列表。对于用户输入的表达式，请转化为遵循Python语法的字符串，如用户输入'ax^2+by^2+cx+dy+e'时，转化为'a*x**2+b*y**2+c*x+d*y+e'。",
            "parameters": {
                "type": "object",
                "properties": {
                    "x_data": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "用于生成预测值的自变量x数据列表。"
                    },
                    "y_data": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "用于生成预测值的自变量y数据列表。"
                    },                    
                    "model_func_str": {
                        "type": "string",
                        "description": "模型函数的字符串表示，遵循Python语法。"
                    },
                    "params": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "模型函数的参数列表。"
                    }
                },
                "required": ["model_func_str", "params", "x_data", "y_data"]
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
    },
    {
        "type": "function",
        "function": {
            "name": "double_plot_2d",
            "description": "生成一个包含两组数据的2D图表并返回图像文件路径。",
            "parameters": {
                "type": "object",
                "properties": {
                    "x1_data": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "第一组数据的X轴数据列表。"
                    },
                    "y1_data": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "第一组数据的Y轴数据列表。"
                    },
                    "x2_data": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "第二组数据的X轴数据列表。"
                    },
                    "y2_data": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "第二组数据的Y轴数据列表。"
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
                "required": ["x1_data", "y1_data", "x2_data", "y2_data", 	"title",	"x_label",	"y_label",	"file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "double_plot_3d",
            "description": "生成一个包含两组数据的3D图表并返回图像文件路径。",
            "parameters": {
                "type": "object",
                "properties": {
                    "x1_data": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "第一组数据的X轴数据列表。"
                    },
                    "y1_data": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "第一组数据的Y轴数据列表。"
                    },
                    "z1_data": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "第一组数据的Z轴数据列表。"
                    },
                    "x2_data": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "第二组数据的X轴数据列表。"
                    },
                    "y2_data": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "第二组数据的Y轴数据列表。"
                    },
                    "z2_data": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "第二组数据的Z轴数据列表。"
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
                        "description": 	"保存图像的文件路径。"
                    }
                },
                "required": ["x1_data", "y1_data", "z1_data", "x2_data", "y2_data", "z2_data", "title", "x_label", "y_label", "z_label", "file_path"]
            }
        }
    }
]


def _normalize_content(content: Any) -> Optional[str]:
    """Convert message content to a plain string."""
    if content is None:
        return None
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_fragments: List[str] = []
        for part in content:
            if isinstance(part, dict):
                text_fragments.append(part.get("text") or "")
            elif isinstance(part, str):
                text_fragments.append(part)
        normalized = "".join(text_fragments)
        return normalized or None
    return str(content)


def _message_to_dict(message: Any) -> Dict[str, Any]:
    """Convert OpenAI SDK message objects into plain dictionaries."""
    if isinstance(message, dict):
        return {
            "role": message.get("role"),
            "content": _normalize_content(message.get("content")),
            "tool_calls": message.get("tool_calls") or [],
        }

    data = message.model_dump()
    return {
        "role": data.get("role", "assistant"),
        "content": _normalize_content(data.get("content")),
        "tool_calls": data.get("tool_calls") or [],
    }


async def _stream_chat_completion(messages: List[Dict[str, Any]], emit_tokens: bool = True) -> Dict[str, Any]:
    """Stream tokens from the model while assembling a structured response."""
    stream = await agent.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        tools=tools,
        tool_choice="auto",
        stream=True,
    )

    content_parts: List[str] = []
    tool_calls: Dict[int, Dict[str, Any]] = {}

    async for chunk in stream:
        chunk_dict = chunk.model_dump()
        choices = chunk_dict.get("choices") or []
        if not choices:
            continue

        delta = choices[0].get("delta") or {}

        for part in delta.get("content") or []:
            text = part.get("text") if isinstance(part, dict) else part
            if text:
                content_parts.append(text)
                if emit_tokens:
                    print(text, end="", flush=True)

        for tool_delta in delta.get("tool_calls") or []:
            index = tool_delta.get("index", 0)
            tool_entry = tool_calls.setdefault(
                index,
                {
                    "id": tool_delta.get("id"),
                    "type": tool_delta.get("type", "function"),
                    "function": {"name": "", "arguments": ""},
                },
            )

            if tool_delta.get("id"):
                tool_entry["id"] = tool_delta["id"]

            function_payload = tool_delta.get("function") or {}
            if function_payload.get("name"):
                tool_entry["function"]["name"] = function_payload["name"]
            if function_payload.get("arguments"):
                tool_entry["function"]["arguments"] += function_payload["arguments"]

    if emit_tokens and content_parts:
        print()

    ordered_tool_calls = [
        {
            "id": entry.get("id"),
            "type": entry.get("type", "function"),
            "function": entry["function"],
        }
        for _, entry in sorted(tool_calls.items())
    ]

    return {
        "role": "assistant",
        "content": "".join(content_parts) if content_parts else None,
        "tool_calls": ordered_tool_calls,
    }


async def create_chat_completion(messages: List[Dict[str, Any]], stream_output: bool = True) -> Dict[str, Any]:
    """Create a chat completion, optionally streaming tokens to stdout."""
    if stream_output:
        return await _stream_chat_completion(messages)

    response = await agent.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )
    return _message_to_dict(response.choices[0].message)

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
        response_message = await create_chat_completion(messages, stream_output=True)

        # 扩展对话历史，方便AI agent参考上文
        messages.append(response_message)

        tool_calls = response_message.get("tool_calls") or []
        if not tool_calls:
            print("AI agent didn't call any function. Now responding to user...")
            return response_message.get("content")

        # tool_calls是一个列表，tool_call是包含函数名和参数的字典元素
        for tool_call in tool_calls:
            function_payload = tool_call.get("function") or {}
            function_name = function_payload.get("name")
            function_args = json.loads(function_payload.get("arguments", "{}"))
            tool_call_id = tool_call.get("id")

            # 打印调试信息
            print(f"AI agent is calling tool: {function_name}")
            print(f"With arguments and ID: {function_args}, {tool_call_id}")

            tool_result = await call_tool(client, function_name, function_args)
            print(tool_result)

            # 将工具调用结果添加到对话历史
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "name": function_name,
                "content": json.dumps(tool_result, ensure_ascii=False)
            })
        # 工具结果已加入对话历史，继续循环
        continue

async def main() -> None:
    async with Client("E:/local_mcp/service/service.py") as client:
        while True:
            user_input = input("Please enter your query: ")
            if user_input.lower() in ["exit", "quit"]:
                print("Exiting...")
                break
            await ai_agent(client, user_input)


if __name__ == "__main__":
    asyncio.run(main())