#!/bin/bash
set -e
cd "$(dirname "$0")"
PYTHON="${XAMR_PYTHON:-python3}"
"$PYTHON" -c 'import sys; assert (3,9) <= sys.version_info[:2] <= (3,12), "Use Python 3.9–3.12 (XAMR_PYTHON can select the interpreter)"'
if [ ! -f .venv-xamr/bin/python ]; then "$PYTHON" -m venv .venv-xamr; fi
if ! .venv-xamr/bin/python -c 'import coval,scipy,typer' >/dev/null 2>&1; then
 .venv-xamr/bin/python -m pip install -r xamr_lab/requirements.txt
fi
.venv-xamr/bin/python xamr_lab/setup_data.py
if command -v open >/dev/null 2>&1; then (sleep 2; open http://127.0.0.1:8767) & fi
exec .venv-xamr/bin/python xamr_lab/server.py --port 8767
