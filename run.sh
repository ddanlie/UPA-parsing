#!/usr/bin/sh

exec 2>/dev/null

PYTHON=".venv/bin/python"

"$PYTHON" get_urls.py |  awk '!seen[$0]++' | tee url_test.txt | awk 'NR <= 10 { print; if (NR == 10) exit }' | "$PYTHON" parse_urls.py
