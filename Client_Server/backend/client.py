import json
import asyncio
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import subprocess
from openai import AsyncOpenAI
from fastmcp import Client

try:
    from .tool_specs import get_tool_schemas
except ImportError:  # pragma: no cover - fallback for script execution
    from tool_specs import get_tool_schemas  # type: ignore

# 使用环境变量配置 API Key 与 base_url，避免将密钥写入代码
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

agent = AsyncOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
)

tools = get_tool_schemas()
logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)


def _normalize_content(content: Any) -> Optional[str]:
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


def _latest_user_prompt(messages: List[Dict[str, Any]]) -> Optional[str]:
    for msg in reversed(messages):
        if msg.get("role") == "user":
            return msg.get("content") or None
    return None


async def call_tool(client: Client, function_name: str, function_args: Dict[str, Any], messages: List[Dict[str, Any]]) -> Any:
    await client.ping()
    await client.list_tools()
    await client.list_resources()
    await client.list_prompts()

    args = function_args or {}
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except Exception:
            args = {"raw": args}

    payload = {
        "args": args,
        "meta": {},
    }
    user_prompt = _latest_user_prompt(messages)
    if user_prompt:
        payload["meta"]["prompt"] = user_prompt

    logger.info(
        "[call_tool] name=%s args=%s meta_keys=%s",
        function_name,
        json.dumps(args, ensure_ascii=False),
        list(payload.get("meta", {}).keys()),
    )

    result = await client.call_tool(function_name, {"payload": payload})

    try:
        result = json.loads(result)
    except Exception:
        if hasattr(result, "structured_content"):
            result = result.structured_content
        elif hasattr(result, "content"):
            result = json.loads(result.content[0].text)

    logger.info(
        "[call_tool_result] name=%s status=%s keys=%s",
        function_name,
        (result or {}).get("status"),
        list((result or {}).keys()),
    )

    return result


async def ai_agent(client: Client, user_input: str) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "你是一个 AI Agent，可以调用 MCP 工具获取实时信息。"
                "当导入的工具返回内存地址data_address时，绘图、拟合等需要大量数据的工具需传入该内存地址和列名。"
            ),
        },
        {"role": "user", "content": user_input},
    ]

    while True:
        response_message = await create_chat_completion(messages, stream_output=True)
        messages.append(response_message)

        tool_calls = response_message.get("tool_calls") or []
        if not tool_calls:
            return response_message.get("content")

        for tool_call in tool_calls:
            function_payload = tool_call.get("function") or {}
            function_name = function_payload.get("name")
            function_args = json.loads(function_payload.get("arguments", "{}"))
            tool_call_id = tool_call.get("id")

            tool_result = await call_tool(client, function_name, function_args, messages)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "name": function_name,
                "content": json.dumps(tool_result, ensure_ascii=False),
            })
        continue


async def _stream_chat_completion(messages: List[Dict[str, Any]], emit_tokens: bool = True) -> Dict[str, Any]:
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
                {"id": tool_delta.get("id"), "type": tool_delta.get("type", "function"), "function": {"name": "", "arguments": ""}},
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
        {"id": entry.get("id"), "type": entry.get("type", "function"), "function": entry["function"]}
        for _, entry in sorted(tool_calls.items())
    ]

    return {"role": "assistant", "content": "".join(content_parts) if content_parts else None, "tool_calls": ordered_tool_calls}


async def create_chat_completion(messages: List[Dict[str, Any]], stream_output: bool = True) -> Dict[str, Any]:
    if stream_output:
        return await _stream_chat_completion(messages)

    response = await agent.chat.completions.create(model="deepseek-chat", messages=messages, tools=tools, tool_choice="auto")
    return _message_to_dict(response.choices[0].message)


async def main() -> None:
    # 以相对路径定位 mcp 服务入口（mcp_service/service.py）
    client_script = Path(__file__).resolve().parent.joinpath('..', 'mcp_service', 'service.py').resolve()
    async with Client(str(client_script)) as client:
        while True:
            user_input = input("Please enter your query: ")
            if user_input.lower() in ["exit", "quit"]:
                break
            await ai_agent(client, user_input)


if __name__ == "__main__":
    asyncio.run(main())
