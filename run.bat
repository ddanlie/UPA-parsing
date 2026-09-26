@echo off

set "PYTHON=.venv\Scripts\python.exe"

"%PYTHON%" get_urls.py | powershell -Command "$input | Tee-Object url_test.txt | Select-Object -First 10" | "%PYTHON%" parse_urls.py