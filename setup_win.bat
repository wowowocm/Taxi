@echo off
REM ============================================================
REM 城市出租车出行数据分析系统 - Windows 环境一键安装脚本
REM 适用: Windows 10/11, Python 3.8.10 (最接近 3.8.12 的Win发行版)
REM 用法: 双击或在cmd中运行 setup_win.bat
REM ============================================================

echo ========================================
echo  出租车数据分析系统 - Windows环境安装
echo  Python版本: 3.8.10
echo ========================================
echo.

set PYTHON_VERSION=3.8.10
set PYTHON_EXE=python-3.8.10-amd64.exe
set PYTHON_URL=https://www.python.org/ftp/python/3.8.10/%PYTHON_EXE%
set INSTALL_DIR=D:\python3.8.10
set VENV_DIR=.venv_py38
set REQUIREMENTS_FILE=requirements_py38.txt

REM ----------------------------------------------------------
REM Step 1: 下载 Python 3.8.10
REM ----------------------------------------------------------
echo [Step 1/4] 检查 Python 3.8.10...
if exist "%INSTALL_DIR%\python.exe" (
    echo   -> Python 3.8.10 已安装, 跳过
    goto :skip_python
)

echo   -> 正在下载 %PYTHON_EXE% ...
curl -L -o "%TEMP%\%PYTHON_EXE%" "%PYTHON_URL%"

echo   -> 正在安装 (静默)...
"%TEMP%\%PYTHON_EXE%" /quiet InstallAllUsers=0 TargetDir=%INSTALL_DIR% PrependPath=0 Include_test=0
echo   -> 等待安装完成...
timeout /t 10 /nobreak >nul

:skip_python
echo   -> Python: %INSTALL_DIR%\python.exe
%INSTALL_DIR%\python.exe --version

REM ----------------------------------------------------------
REM Step 2: 创建虚拟环境
REM ----------------------------------------------------------
echo.
echo [Step 2/4] 创建虚拟环境...
if exist "%VENV_DIR%\Scripts\python.exe" (
    echo   -> 虚拟环境已存在, 跳过
) else (
    %INSTALL_DIR%\python.exe -m venv %VENV_DIR%
    echo   -> 虚拟环境创建于: %VENV_DIR%
)

REM ----------------------------------------------------------
REM Step 3: 安装依赖
REM ----------------------------------------------------------
echo.
echo [Step 3/4] 安装依赖...
call "%VENV_DIR%\Scripts\activate.bat"
pip install --upgrade pip -q
pip install -r %REQUIREMENTS_FILE%
call deactivate
echo   -> 依赖安装完成

REM ----------------------------------------------------------
REM Step 4: 验证
REM ----------------------------------------------------------
echo.
echo [Step 4/4] 验证安装...
call "%VENV_DIR%\Scripts\activate.bat"
python --version
python -c "import pandas, numpy, matplotlib, seaborn, folium, sklearn, flask, pymysql; print('所有依赖导入成功!')"
call deactivate

echo.
echo ========================================
echo  安装完成!
echo ========================================
echo.
echo  激活环境:
echo    %VENV_DIR%\Scripts\activate.bat
echo.
echo  运行项目:
echo    python main.py
echo    python main.py --web
echo.
pause
