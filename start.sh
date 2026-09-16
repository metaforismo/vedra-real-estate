#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
PYTHON="${PYTHON:-python3}"
"$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3,11) else "Vedra richiede Python 3.11+")'
if [ ! -x .venv/bin/python ]; then "$PYTHON" -m venv .venv; fi
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/setup.py
exec .venv/bin/python scripts/run.py "$@"
