# Create venv, install requirements and start backend (PowerShell)
$venv = ".venv"
if (-not (Test-Path $venv)) {
    python -m venv $venv
}
# Activate venv for this session
& "$venv/Scripts/Activate.ps1"

python -m pip install --upgrade pip
if (Test-Path "requirements.txt") {
    python -m pip install -r requirements.txt
}
# Ensure runtime packages present
python -m pip install uvicorn fastmcp
# Optional: install faiss if you want FAISS support (may be heavy)
# python -m pip install faiss-cpu

# Start the backend (runs in current terminal)
python -m uvicorn backend.backend_main:app --reload --port 8000
