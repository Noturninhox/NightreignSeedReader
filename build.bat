@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo === Nightreign Seed Reader: gerando o instalador ===
echo.

if not exist .venv\Scripts\python.exe (
    echo Criando ambiente Python...
    py -3 -m venv .venv 2>nul || python -m venv .venv
)
if not exist .venv\Scripts\python.exe (
    echo O Python nao foi encontrado. Instale o Python 3.11+ em python.org
    echo marcando "Add python.exe to PATH" e de dois cliques em build.bat de novo.
    pause
    exit /b 1
)

.venv\Scripts\python.exe -m pip install --upgrade pip -q
.venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller -q
if errorlevel 1 (
    echo.
    echo Falha ao instalar as dependencias. Copie as mensagens acima e me envie.
    pause
    exit /b 1
)

.venv\Scripts\pyinstaller.exe --noconfirm --clean --windowed --onefile --log-level WARN ^
    --name "Nightreign Seed Reader" ^
    --icon nrseed\assets\icon.ico ^
    --splash nrseed\assets\splash.png ^
    --version-file version_info.txt ^
    --add-data "nrseed\engine\data;nrseed\engine\data" ^
    --add-data "nrseed\engine\i18n;nrseed\engine\i18n" ^
    --add-data "nrseed\assets;nrseed\assets" ^
    main.py
if errorlevel 1 (
    echo.
    echo O build falhou. Copie as mensagens de erro acima e me envie.
    pause
    exit /b 1
)

REM O mesmo .exe vira o instalador quando o nome tem "Setup"
copy /y "dist\Nightreign Seed Reader.exe" "NightreignSeedReader-Setup.exe" >nul

echo.
echo Pronto! O instalador esta nesta pasta: NightreignSeedReader-Setup.exe
start "" "%~dp0NightreignSeedReader-Setup.exe"
pause
