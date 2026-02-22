@echo off
if not exist .venv (
    python -m venv .venv
)
call .venv\Scripts\activate
python -m pip install --upgrade pip
if exist requirements.txt (
    python -m pip install -r requirements.txt
)
python -m pip install uvicorn fastmcp
REM Optional: install faiss if you want FAISS support (may be heavy)
REM python -m pip install faiss-cpu

python -m uvicorn backend.backend_main:app --reload --port 8000
