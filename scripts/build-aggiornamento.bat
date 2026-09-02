@echo off
setlocal
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build-aggiornamento.ps1"
if errorlevel 1 exit /b 1
echo.
echo Fatto.
exit /b 0
