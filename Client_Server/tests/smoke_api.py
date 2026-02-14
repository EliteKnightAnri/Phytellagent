"""
简单 smoke 测试脚本：验证后端常用接口

用法：在 `Client_Server` 目录的虚拟环境中运行：
  .\.venv\Scripts\python.exe tests\smoke_api.py

脚本会依次：
- GET /files
- POST /upload (上传一个临时文本文件)
- POST /chat (流式读取若干条响应)
"""
import io
import json
import pathlib
import requests
import sys

BASE = "http://127.0.0.1:8000"


def get_files():
    r = requests.get(f"{BASE}/files", timeout=5)
    print("GET /files ->", r.status_code)
    try:
        print(json.dumps(r.json(), ensure_ascii=False, indent=2))
    except Exception:
        print(r.text)


def post_upload():
    p = pathlib.Path("smoke_upload.txt")
    p.write_text("smoke test upload")
    with open(p, "rb") as f:
        r = requests.post(f"{BASE}/upload", files={"file": f}, timeout=10)
    print("POST /upload ->", r.status_code)
    try:
        print(json.dumps(r.json(), ensure_ascii=False, indent=2))
        return r.json().get("file_id")
    except Exception:
        print(r.text)
    return None


def post_chat(file_id=None, max_events=12):
    payload = {"prompt": "Hello from smoke_api", "file_ids": ([file_id] if file_id else []), "mode": "general", "history": []}
    with requests.post(f"{BASE}/chat", json=payload, stream=True, timeout=60) as r:
        print("POST /chat ->", r.status_code)
        if r.status_code != 200:
            print(r.text)
            return
        cnt = 0
        for line in r.iter_lines():
            if not line:
                continue
            try:
                obj = json.loads(line.decode("utf-8"))
            except Exception:
                print("RAW:", line)
                continue
            t = obj.get("type")
            c = obj.get("content")
            snippet = (c[:200] + "...") if isinstance(c, str) and len(c) > 200 else c
            print(f"STREAM: {t} ->", snippet)
            cnt += 1
            if cnt >= max_events:
                break


def main():
    try:
        get_files()
    except Exception as e:
        print("GET /files failed:", e)
        sys.exit(1)

    try:
        fid = post_upload()
    except Exception as e:
        print("POST /upload failed:", e)
        fid = None

    try:
        post_chat(file_id=fid)
    except Exception as e:
        print("POST /chat failed:", e)


if __name__ == "__main__":
    main()
