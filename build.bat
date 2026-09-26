@echo off

set "PYTHON=.venv\Scripts\python.exe"

"%PYTHON%" -m venv .venv
"%PYTHON%" -m pip install --upgrade pip
"%PYTHON%" -m pip install -r requirements.txt
"%PYTHON%" -m playwright install

echo Environment ready