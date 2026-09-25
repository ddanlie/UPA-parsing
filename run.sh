#!/usr/bin/sh

.venv/bin/python get_urls.py | tee url_test.txt | head -n 10 | .venv/bin/python parse_urls.py

