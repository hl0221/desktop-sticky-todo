@echo off
set "APP_DIR=%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    start "" py -3 "%APP_DIR%sticky_todo.py"
    exit /b
)

where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw "%APP_DIR%sticky_todo.py"
    exit /b
)

where python >nul 2>nul
if %errorlevel%==0 (
    start "" python "%APP_DIR%sticky_todo.py"
    exit /b
)

echo Python was not found. Please install Python 3 with Tkinter.
pause
