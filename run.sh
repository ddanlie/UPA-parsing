#!/usr/bin/sh

exec 2>/dev/null

PYTHON=".venv/bin/python"

"$PYTHON" get_urls.py |  awk '!seen[$0]++ { print; fflush() }' | tee url_test.txt | "$PYTHON" parse_urls.py | awk '{ print; fflush() }; NR == 10 { exit }'
