@echo off
setlocal
cd /d "%~dp0"
echo Checking PoroScope Studio project folder...
set "MISSING=0"
if not exist "app.py" (echo MISSING: app.py & set "MISSING=1")
if not exist "requirements.txt" (echo MISSING: requirements.txt & set "MISSING=1")
if not exist ".github\workflows\ci.yml" (echo MISSING: .github\workflows\ci.yml & set "MISSING=1")
if not exist ".streamlit\config.toml" (echo MISSING: .streamlit\config.toml & set "MISSING=1")
for %%F in (__init__.py circularity.py engine.py io.py reporting.py synthetic.py validation.py) do (
    if not exist "poroscope\%%F" (echo MISSING: poroscope\%%F & set "MISSING=1")
)
if "%MISSING%"=="0" (
    echo SUCCESS: All essential files and the poroscope folder are present.
) else (
    echo FAIL: One or more required source files are missing.
)
echo.
echo Source folder contents:
dir /b "poroscope\*.py"
echo.
pause
