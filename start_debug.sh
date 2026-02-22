#!/bin/bash
cd "$(dirname "$0")"
source .venv/bin/activate
gnome-terminal -- bash -c "cd backend && python backend_main.py; exec bash"
gnome-terminal -- bash -c "python main.py; exec bash"