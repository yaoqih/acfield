@echo off
setlocal
cd /d "%~dp0"

rem Start the real-device backend on all local network interfaces.
set ROBOT_MODE=hardware
if not defined ROBOT_HOST set ROBOT_HOST=0.0.0.0
if not defined ROBOT_UDP_HOST set ROBOT_UDP_HOST=0.0.0.0
if not defined ROBOT_START_VISION set ROBOT_START_VISION=1

call "%~dp0run.bat"
exit /b %errorlevel%
