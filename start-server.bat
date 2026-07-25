@echo off
chcp 65001 >nul
cd /d %~dp0
echo ============================================
echo   Camp Recreation Sync Server (Windows)
echo ============================================
where py >nul 2>nul
if %errorlevel%==0 (
  py serve.py
  goto :end
)
where python >nul 2>nul
if %errorlevel%==0 (
  python serve.py
  goto :end
)
echo.
echo [ERROR] Python not found. / Python が見つかりません。
echo.
echo   1. https://www.python.org/downloads/ からダウンロード
echo   2. インストール時に "Add python.exe to PATH" に必ずチェック
echo   3. インストール後、このファイルをもう一度ダブルクリック
echo.
:end
pause
