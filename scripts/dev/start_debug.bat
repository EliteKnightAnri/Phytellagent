@echo off
:: 切到项目子目录（包含 .venv），e:\local_mcp改成你的实际根目录
cd /d e:\local_mcp
:: 在独立窗口启动后端（激活 venv），通过 uvicorn 指定 app-dir，日志写到上层 uvicorn.log
start "Backend" cmd /k "cd /d e:\local_mcp\src\mcp_stack\backend && call .venv\Scripts\activate && set PYTHONIOENCODING=utf-8 && python -m uvicorn backend_main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload > ..\uvicorn.log 2>&1"
:: 在独立窗口启动前端（激活 venv），日志写到上层 frontend.log
start "Frontend" cmd /k "cd /d e:\local_mcp\src\mcp_stack\frontend && call .venv\Scripts\activate && python frontend_main.py > ..\\frontend.log 2>&1"