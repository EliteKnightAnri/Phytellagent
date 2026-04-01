from typing import Any, Dict, Optional, Tuple, List

import httpx
from fastmcp import FastMCP

mcp = FastMCP(name="Bilibili tool")

API_URL = "https://api.bilibili.com/x/web-interface/search/type"
DEFAULT_PAGE_SIZE = 5
MAX_PAGE_SIZE = 20


def _split_payload(payload: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    payload = payload or {}
    return payload.get("args") or {}, payload.get("meta") or {}


def _coerce_positive_int(value: Any, default: int, upper: int) -> int:
    try:
        num = int(value)
        if num <= 0:
            return default
        return min(num, upper)
    except (TypeError, ValueError):
        return default


def _extract_videos(result_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    videos = []
    data = result_payload.get("result") or {}
    video_list = data.get("video") or []
    for item in video_list:
        videos.append({
            "title": item.get("title"),
            "description": item.get("description"),
            "author": item.get("author"),
            "play": item.get("play"),
            "danmaku": item.get("danmaku"),
            "duration": item.get("duration"),
            "pubdate": item.get("pubdate"),
            "arcurl": item.get("arcurl"),
            "bvid": item.get("bvid"),
            "cover": item.get("pic"),
        })
    return videos


async def _search_bilibili(keyword: str, page: int, page_size: int) -> Dict[str, Any]:
    params = {
        "search_type": "video",
        "keyword": keyword,
        "page": page,
        "page_size": page_size,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(API_URL, params=params)
        resp.raise_for_status()
        payload = resp.json()
    if payload.get("code") != 0:
        raise RuntimeError(payload.get("message") or "Bilibili API error")
    return payload.get("data") or {}


@mcp.tool()
async def search_videos(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    args, meta = _split_payload(payload)
    keyword = (args.get("keyword") or meta.get("prompt") or "").strip()
    if not keyword:
        return {"status": "error", "message": "keyword is required"}

    page = _coerce_positive_int(args.get("page"), 1, upper=100)
    page_size = _coerce_positive_int(args.get("page_size"), DEFAULT_PAGE_SIZE, upper=MAX_PAGE_SIZE)

    try:
        raw_data = await _search_bilibili(keyword, page, page_size)
        videos = _extract_videos(raw_data)
        return {
            "status": "success",
            "used_keyword": keyword,
            "page": page,
            "page_size": page_size,
            "total": raw_data.get("numResults"),
            "data": videos,
        }
    except httpx.HTTPError as exc:
        return {"status": "error", "message": f"Network error: {exc}"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "message": str(exc)}

if __name__ == "__main__":
    mcp.run(transport="stdio")
