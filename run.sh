#!/usr/bin/sh

PYTHON=".venv/bin/python"

"$PYTHON" get_urls.py | tee url_test.txt | head -n 10 | "$PYTHON" parse_urls.py

