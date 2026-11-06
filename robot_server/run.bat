@echo off
cd /d "%~dp0"
if not defined ROBOT_MODE set ROBOT_MODE=hardware
if not defined ROBOT_HOST set ROBOT_HOST=0.0.0.0
if not defined ROBOT_UDP_HOST set ROBOT_UDP_HOST=0.0.0.0
if not defined ROBOT_ALLOW_UNLOCALIZED_CONTROL set ROBOT_ALLOW_UNLOCALIZED_CONTROL=1
if not exist "..\.venv\Scripts\python.exe" (
  echo Run "uv sync --python 3.12 --extra test" in the repository root first.
  exit /b 1
)
"..\.venv\Scripts\python.exe" "%~dp0run_windows.py"
exit /b %errorlevel%
