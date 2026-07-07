@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%"

set "PYTHON_EXE=python"
if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" set "PYTHON_EXE=%SCRIPT_DIR%.venv\Scripts\python.exe"
if exist "%SCRIPT_DIR%venv\Scripts\python.exe" set "PYTHON_EXE=%SCRIPT_DIR%venv\Scripts\python.exe"

if not exist "%SCRIPT_DIR%start_feelz.py" (
    echo Could not find start_feelz.py in "%SCRIPT_DIR%".
    popd
    exit /b 1
)

%PYTHON_EXE% "%SCRIPT_DIR%start_feelz.py"
set "EXIT_CODE=%ERRORLEVEL%"

popd
exit /b %EXIT_CODE%
