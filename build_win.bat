@echo off
chcp 65001 >nul
echo ============================
echo  盈时宝 - Windows 打包
echo ============================
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python，请先安装 Python 3.8+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Install dependencies
echo [1/4] 安装依赖...
pip install flask pywebview python-docx pyinstaller -q
echo 完成

REM Build
echo [2/4] 打包中...
pyinstaller --name="盈时宝计时计费系统" ^
  --add-data="templates;templates" ^
  --add-data="盈时宝.ico;." ^
  --windowed ^
  --onedir ^
  --clean ^
  --icon="盈时宝.ico" ^
  --hidden-import=xlsxwriter ^
  --hidden-import=webview ^
  --collect-all=flask ^
  main.py

echo 完成

echo [3/4] 清理临时文件...
rmdir /s /q build >nul 2>&1
del /q *.spec >nul 2>&1

echo [4/4] 打包完成!
echo.
echo ============================
echo  输出: dist\盈时宝计时计费系统\
echo ============================
echo  版本: 1.0.2
echo  桌面快捷方式指向 dist\盈时宝计时计费系统\盈时宝计时计费系统.exe
echo ============================
pause
