#!/usr/bin/env sh

python -m venv .venv

PYTHON=".venv/bin/python"

"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install -r requirements.txt
"$PYTHON" -m playwright install

echo "Environment ready"

