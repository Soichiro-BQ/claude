@echo off
rem === Windows startup script ===
cd /d %~dp0
py serve.py 2>nul || python serve.py
pause
