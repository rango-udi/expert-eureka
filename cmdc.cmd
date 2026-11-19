@echo off
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\cmdc.ps1" %*
exit /b %errorlevel%
