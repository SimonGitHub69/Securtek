@echo off
setlocal
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build-macos-client-installer.ps1"
if errorlevel 1 exit /b 1
echo.
echo Fatto.
exit /b 0
