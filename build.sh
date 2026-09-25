#!/usr/bin/env sh

set -eu

PYTHON=".venv/bin/python"

"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install -r requirements.txt
"$PYTHON" -m playwright install

printf '%s\n' "Environment ready"

