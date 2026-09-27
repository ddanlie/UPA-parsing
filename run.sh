#!/usr/bin/sh

PYTHON=".venv/bin/python"

"$PYTHON" get_urls.py | awk '!seen[$0]++' | tee url_test.txt | awk 'NR <= 10' | "$PYTHON" parse_urls.py
