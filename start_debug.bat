@echo off
<<<<<<< HEAD
:: 切到项目子目录（包含 .venv），e:\local_mcp改成你的实际根目录
=======
:: 切到项目子目录（包含 .venv）
>>>>>>> c7609d2ed2a31afda6dd18e33262929ad9bef632
cd /d e:\local_mcp\Client_Server
:: 在独立窗口启动后端（激活 venv），通过 uvicorn 指定 app-dir，日志写到上层 uvicorn.log
start "Backend" cmd /k "cd /d e:\local_mcp\Client_Server && call .venv\Scripts\activate && set PYTHONIOENCODING=utf-8 && python -m uvicorn backend_main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload > ..\uvicorn.log 2>&1"
:: 在独立窗口启动前端（激活 venv），日志写到上层 frontend.log
start "Frontend" cmd /k "cd /d e:\local_mcp\Client_Server && call .venv\Scripts\activate && python main.py > ..\\frontend.log 2>&1"