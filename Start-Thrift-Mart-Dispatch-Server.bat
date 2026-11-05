@echo off
cd /d "%~dp0"
if exist "MGC YFC Operations Server Console.exe" (
 start "" "%SystemRoot%\System32\conhost.exe" "%~dp0MGC YFC Operations Server Console.exe" --console
 exit /b 0
)
if exist "MGC YFC Operations Server.exe" (
 start "" "MGC YFC Operations Server.exe"
 exit /b 0
)
title MGC YFC Operations Server
if exist "runtime\python.exe" (
 "runtime\python.exe" launcher.py
) else (
 py -3 launcher.py
)
pause
