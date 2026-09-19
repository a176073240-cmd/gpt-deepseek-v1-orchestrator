@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

set "GPTDS_PYTHON="
set "GPTDS_PYTHON_ARGS="

if exist ".venv\Scripts\python.exe" (
    set "GPTDS_PYTHON=%CD%\.venv\Scripts\python.exe"
    goto python_found
)

where py >nul 2>&1
if not errorlevel 1 (
    set "GPTDS_PYTHON=py"
    set "GPTDS_PYTHON_ARGS=-3"
    goto python_found
)

where python >nul 2>&1
if not errorlevel 1 (
    set "GPTDS_PYTHON=python"
    goto python_found
)

echo [错误] 未找到 Python。
echo 请先安装 Python 3.10 或更高版本，并在安装时勾选 Add Python to PATH。
pause
exit /b 1

:python_found
"%GPTDS_PYTHON%" %GPTDS_PYTHON_ARGS% -c "import sys; raise SystemExit(0 if sys.version_info ^>= (3, 10) else 1)" >nul 2>&1
if errorlevel 1 (
    echo [错误] GPT-DeepSeek 需要 Python 3.10 或更高版本。
    "%GPTDS_PYTHON%" %GPTDS_PYTHON_ARGS% --version
    pause
    exit /b 1
)

"%GPTDS_PYTHON%" %GPTDS_PYTHON_ARGS% -c "import PySide6" >nul 2>&1
if errorlevel 1 goto install_gui
goto launch_gui

:install_gui
echo [提示] 尚未安装 GUI 依赖 PySide6。
choice /C YN /N /M "是否现在安装 GUI 依赖？[Y/N] "
if errorlevel 2 exit /b 1
"%GPTDS_PYTHON%" %GPTDS_PYTHON_ARGS% -m pip install -e ".[gui]"
if errorlevel 1 (
    echo [错误] GUI 依赖安装失败。请检查网络后重试。
    pause
    exit /b 1
)

:launch_gui
"%GPTDS_PYTHON%" %GPTDS_PYTHON_ARGS% "launcher\main.py"
if errorlevel 1 (
    echo.
    echo [错误] GUI 未能正常启动。请查看上方错误信息。
    echo 详细说明：docs\gui-launcher.md
    pause
    exit /b 1
)

exit /b 0
