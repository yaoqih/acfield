@echo off
cd /d "%~dp0"
if not exist "..\.venv\Scripts\python.exe" (
  echo Run "uv sync --python 3.12 --extra test" in the repository root first.
  exit /b 1
)
"..\.venv\Scripts\python.exe" "%~dp0run_windows.py"
exit /b %errorlevel%
