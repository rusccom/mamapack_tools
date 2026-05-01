@echo off
setlocal
chcp 65001 >nul
python "%~dp0run_export.py"
echo.
pause
