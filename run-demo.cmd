@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\run-demo.ps1" %*
exit /b %ERRORLEVEL%
