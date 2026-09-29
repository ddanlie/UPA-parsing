#!/usr/bin/sh

PYTHON=".venv/bin/python"

"$PYTHON" get_urls.py |  awk '!seen[$0]++ { print; fflush() }' | tee url_test.txt | "$PYTHON" -c 'import signal,runpy; signal.signal(signal.SIGPIPE, signal.SIG_DFL); runpy.run_path("parse_urls.py", run_name="__main__")' | head -n 10
