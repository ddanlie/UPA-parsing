@echo off

set "PYTHON=.venv\Scripts\python.exe"

"%PYTHON%" get_urls.py | powershell -Command "$lines=@($input ^| Select-Object -Unique); [IO.File]::WriteAllLines('url_test.txt',$lines); if($lines.Count -gt 10){$lines[0..9]}else{$lines}" | "%PYTHON%" parse_urls.py
:: For single file: 
:: cmd /c "set PYTHONIOENCODING=utf-16 && .venv\Scripts\python.exe -X utf8 xdomra00_parse_urls.py < urls.txt > data.tsv"