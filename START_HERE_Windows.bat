@echo off
setlocal
cd /d "%~dp0"
title PoroScope Studio - Local Launcher
where py >nul 2>&1
if %errorlevel%==0 (
    set "PY=py -3"
) else (
    set "PY=python"
)
echo.
echo ==============================================
echo        PoroScope Studio - Start Here
echo ==============================================
echo.
echo Checking Python...
%PY% --version
if errorlevel 1 (
    echo Python was not found. Install Python 3.11 or 3.12 and try again.
    pause
    exit /b 1
)
echo.
echo Installing any missing dependencies...
%PY% -m pip install -r requirements.txt
if errorlevel 1 (
    echo Package installation failed. Review the messages above.
    pause
    exit /b 1
)
echo.
echo Starting your local project. Keep this window open.
%PY% -m streamlit run app.py
pause
