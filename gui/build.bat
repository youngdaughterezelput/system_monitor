@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

:: Проверка Python
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python not found in PATH
    pause
    exit /b 1
)

:: Установка зависимостей
echo Installing dependencies...
python -m pip install --upgrade pip
python -m pip install pyinstaller psutil matplotlib pyqt5

:: Компиляция
echo Building executable...
python -m PyInstaller ^
    --onefile ^
    --noconsole ^
    --uac-admin ^
    --name "SystemMonitor" ^
    --distpath "build" ^
    --workpath "build/temp" ^
    --hidden-import "matplotlib.backends.backend_qt5agg" ^
    --hidden-import "PyQt5.QtWidgets" ^
    --hidden-import "PyQt5.QtCore" ^
    --hidden-import "PyQt5.QtGui" ^
    --add-data "app.manifest;." ^
    main.py

if %ERRORLEVEL% neq 0 (
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

echo.
echo [SUCCESS] Build completed!
echo Executable: build\SystemMonitor.exe
pause