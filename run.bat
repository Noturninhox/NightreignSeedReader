@echo off
REM Roda direto do codigo-fonte (precisa do Python 3.11+ instalado)
cd /d "%~dp0"
if not exist .venv (
  echo Criando ambiente virtual...
  py -3 -m venv .venv || python -m venv .venv
  .venv\Scripts\python.exe -m pip install --upgrade pip
  .venv\Scripts\python.exe -m pip install -r requirements.txt
)
start "" .venv\Scripts\pythonw.exe main.py
