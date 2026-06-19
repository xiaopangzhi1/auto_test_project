@echo off
REM PyCharm 运行配置脚本 (Windows版本)
REM 将此脚本添加到 PyCharm 运行配置中

echo ==========================================
echo Android UI 自动化测试 - PyCharm 启动脚本
echo ==========================================

REM 设置项目根目录
set "PROJECT_ROOT=%~dp0"
echo 项目目录: %PROJECT_ROOT%
echo.

REM 检查 Python 环境
echo 检查 Python 环境...
python --version
if errorlevel 1 (
    echo ❌ Python 未安装或不在 PATH 中
    exit /b 1
)

REM 检查虚拟环境
if exist "%PROJECT_ROOT%\.venv\Scripts\python.exe" (
    echo ✅ 检测到虚拟环境: %PROJECT_ROOT%\.venv
    REM 设置虚拟环境 Python
    set "PYTHON_EXE=%PROJECT_ROOT%\.venv\Scripts\python.exe"
) else (
    echo ⚠️  未检测到虚拟环境，使用系统 Python
    set "PYTHON_EXE=python"
)

REM 检查依赖
echo.
echo 检查依赖...
if exist "%PROJECT_ROOT%\requirements.txt" (
    echo ✅ 找到 requirements.txt
    echo    如需安装依赖: pip install -r requirements.txt
) else (
    echo ⚠️  未找到 requirements.txt
)

REM 运行测试
echo.
echo 运行测试...
echo ==========================================

cd /d "%PROJECT_ROOT%"
%PYTHON_EXE% run.py %*