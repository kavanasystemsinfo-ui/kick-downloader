@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PROFILE_DIR=%NOTEBOOKLM_CHROME_PROFILE%"
if "%PROFILE_DIR%"=="" set "PROFILE_DIR=%SCRIPT_DIR%chrome_profile"
set "CDP_PORT=%CDP_PORT%"
if "%CDP_PORT%"=="" set "CDP_PORT=9222"
set "CHROME_BIN=%CHROME_BIN%"
if "%CHROME_BIN%"=="" set "CHROME_BIN=chrome"

if not exist "%PROFILE_DIR%" mkdir "%PROFILE_DIR%"

start "" "%CHROME_BIN%" --remote-debugging-port=%CDP_PORT% --user-data-dir="%PROFILE_DIR%" --disable-extensions --no-first-run --no-default-browser-check about:blank

echo NotebookLM CDP endpoint: http://localhost:%CDP_PORT%
echo Run: python "%SCRIPT_DIR%notebook_bridge.py" --cdp-endpoint http://localhost:%CDP_PORT% --notebook-url ^<notebook-url^> --chat-prompt "^<prompt^>"
