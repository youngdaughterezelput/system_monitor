@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

:: 1. Проверка Python
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python не найден в PATH
    pause
    exit /b 1
)

:: 2. Установка зависимостей
echo Устанавливаем PyInstaller и зависимости...
python -m pip install --upgrade pyinstaller psutil matplotlib pyqt5

:: 3. Компиляция через Python модуль (без вызова pyinstaller напрямую)
echo Запускаем сборку...
python -m PyInstaller ^
    --onefile ^
    --noconsole ^
    --name "SystemMonitor" ^
    --distpath "build" ^
    --workpath "build/temp" ^
    --hidden-import "matplotlib.backends.backend_qt5agg" ^
    --hidden-import "PyQt5.QtWidgets" ^
    --add-data "*.ui;." ^
    main.py

if %ERRORLEVEL% neq 0 (
    echo [ERROR] Сборка не удалась!
    echo Проверьте ошибки выше
    pause
    exit /b 1
)

echo.
echo [SUCCESS] Сборка завершена!
echo Исполняемый файл: build\SystemMonitor.exe
pause