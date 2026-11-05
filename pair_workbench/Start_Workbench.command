#!/bin/zsh
cd -- "$(dirname -- "$0")" || exit 1
if [[ ! -x .venv/bin/python ]]; then
  echo 'Please run setup first: python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt'
  read -r '?Press Enter to close'; exit 1
fi
.venv/bin/python - <<'PYTHON'
import urllib.request, webbrowser, sys
try:
    urllib.request.urlopen('http://127.0.0.1:8765/api/init',timeout=1)
    webbrowser.open('http://127.0.0.1:8765')
except Exception:
    sys.exit(1)
PYTHON
if [[ $? -ne 0 ]]; then
  .venv/bin/python server.py --open-browser
fi
