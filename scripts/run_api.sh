#!/usr/bin/env bash
# Start the ForeBlendCast API on all interfaces (Linux/macOS/Git Bash).
set -e
cd "$(dirname "$0")/.."
PY=.venv/bin/python; [ -x "$PY" ] || PY=.venv/Scripts/python.exe; [ -x "$PY" ] || PY=python
$PY -m pip install -q -r api/requirements.txt
PORT=${1:-8000}
echo "ForeBlendCast API on port $PORT  (emulator: http://10.0.2.2:$PORT, LAN: http://$(hostname -I 2>/dev/null | awk '{print $1}'):$PORT)"
exec $PY -m uvicorn api.main:app --host 0.0.0.0 --port "$PORT" --reload
