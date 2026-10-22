@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "F="
for /f "delims=" %%i in ('dir /b /o-d "运动记录-*.json" 2^>nul') do if not defined F set "F=%%i"

if not defined F (
  echo.
  echo   No "运动记录-*.json" found in this folder.
  echo   Open index.html, click "导出 JSON", and move the file here.
  echo.
  pause
  exit /b 1
)

echo.
echo   Using: %F%
echo.
python stats.py "%F%" %*
echo.
pause
