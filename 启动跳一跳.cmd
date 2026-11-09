@echo off
where pythonw.exe >nul 2>nul
if errorlevel 1 (
    echo Python with Tkinter is required.
    pause
    exit /b 1
)
start "" pythonw.exe "%~dp0wechat_jump_space_backspace.py"
