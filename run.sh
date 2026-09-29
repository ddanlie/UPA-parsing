#!/usr/bin/sh

PYTHON=".venv/bin/python"

"$PYTHON" get_urls.py |  awk '!seen[$0]++ { print; fflush() }' | tee url_test.txt | "$PYTHON" parse_urls.py | head -n 10
