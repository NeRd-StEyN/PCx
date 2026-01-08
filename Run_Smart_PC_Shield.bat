@echo off
pushd "%CD%"
CD /D "%~dp0"
:--------------------------------------

title PCx Shield Launcher
set "MINIMIZED=0"
for %%a in (%*) do if "%%a"=="--minimized" set "MINIMIZED=1"

echo [Step 1] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed.
    if "%MINIMIZED%"=="0" pause
    exit /b
)

:: Faster dependency check - only runs pip if an import fails
echo [Step 2] Validating environment...
python -c "import psutil, webview, langchain_groq, pystray, PIL, dotenv" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Installing missing dependencies...
    pip install psutil pywebview langchain langchain-groq python-dotenv pystray Pillow --quiet --no-warn-script-location
)

echo [Step 3] Launching PCx...
:: Use start /b to run in same process or just call python
python app.py %*

if %errorlevel% neq 0 (
    if "%MINIMIZED%"=="0" (
        echo.
        echo [CRASH] Application crashed with error code %errorlevel%.
        pause
    )
)
exit
