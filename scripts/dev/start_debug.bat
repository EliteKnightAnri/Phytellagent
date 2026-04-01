@echo off
:: 切到项目根目录（包含 .venv）
cd /d e:\local_mcp
:: 在独立窗口启动后端（激活 venv），直接以包路径运行 uvicorn，日志写到根目录 uvicorn.log
start "Backend" cmd /k "cd /d e:\local_mcp && call .venv\Scripts\activate && set PYTHONIOENCODING=utf-8 && set PYTHONPATH=e:\local_mcp\src;e:\local_mcp\src\mcp_stack && python -m uvicorn mcp_stack.backend.backend_main:app --host 0.0.0.0 --port 8000 --reload > scripts\dev\uvicorn.log 2>&1"
:: 在独立窗口启动前端（激活 venv），使用 python -m 运行包入口，日志写到根目录 frontend.log
start "Frontend" cmd /k "cd /d e:\local_mcp && call .venv\Scripts\activate && set PYTHONPATH=e:\local_mcp\src;e:\local_mcp\src\mcp_stack && python -m mcp_stack.frontend.frontend_main > scripts\dev\frontend.log 2>&1"