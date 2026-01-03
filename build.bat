@echo off
REM AutoVoiceType - 构建脚本
REM 用于自动化构建可执行文件和安装程序

echo ========================================
echo AutoVoiceType 构建脚本
echo ========================================
echo.

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

echo [1/5] 检查依赖...
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo [警告] PyInstaller 未安装，正在安装...
    pip install pyinstaller
    if errorlevel 1 (
        echo [错误] PyInstaller 安装失败
        pause
        exit /b 1
    )
)

REM 检查所有关键依赖
echo [检查] 检查关键依赖模块...
python -c "import PyQt5" >nul 2>&1
if errorlevel 1 (
    echo [警告] PyQt5 未安装，正在安装...
    pip install PyQt5
    if errorlevel 1 (
        echo [错误] PyQt5 安装失败
        pause
        exit /b 1
    )
)
python -c "import numpy" >nul 2>&1
if errorlevel 1 (
    echo [警告] numpy 未安装，正在安装...
    pip install numpy
    if errorlevel 1 (
        echo [错误] numpy 安装失败
        pause
        exit /b 1
    )
)

python -c "import pyaudio" >nul 2>&1
if errorlevel 1 (
    echo [警告] pyaudio 未安装，正在安装...
    pip install pyaudio
    if errorlevel 1 (
        echo [错误] pyaudio 安装失败
        pause
        exit /b 1
    )
)

python -c "import pynput" >nul 2>&1
if errorlevel 1 (
    echo [警告] pynput 未安装，正在安装...
    pip install pynput
    if errorlevel 1 (
        echo [错误] pynput 安装失败
        pause
        exit /b 1
    )
)

python -c "import pyperclip" >nul 2>&1
if errorlevel 1 (
    echo [警告] pyperclip 未安装，正在安装...
    pip install pyperclip
    if errorlevel 1 (
        echo [错误] pyperclip 安装失败
        pause
        exit /b 1
    )
)

python -c "import pyautogui" >nul 2>&1
if errorlevel 1 (
    echo [警告] pyautogui 未安装，正在安装...
    pip install pyautogui
    if errorlevel 1 (
        echo [错误] pyautogui 安装失败
        pause
        exit /b 1
    )
)

python -c "import websocket" >nul 2>&1
if errorlevel 1 (
    echo [警告] websocket-client 未安装，正在安装...
    pip install websocket-client
    if errorlevel 1 (
        echo [错误] websocket-client 安装失败
        pause
        exit /b 1
    )
)

python -c "import dashscope" >nul 2>&1
if errorlevel 1 (
    echo [警告] dashscope 未安装，正在安装...
    pip install dashscope
    if errorlevel 1 (
        echo [警告] dashscope 安装失败，但将继续构建
    )
)

REM 检查 Windows 特定依赖
python -c "import win32api" >nul 2>&1
if errorlevel 1 (
    echo [警告] pywin32 未安装，正在安装...
    pip install pywin32
    if errorlevel 1 (
        echo [警告] pywin32 安装失败，但将继续构建（某些功能可能不可用）
    )
)

echo [OK] 依赖检查完成
echo.

echo [1.5/5] 检查并生成图标文件...
if not exist "assets\icon.ico" (
    echo [信息] ICO 图标文件不存在，尝试从 SVG 生成...
    python tools\convert_svg_to_ico.py
    if errorlevel 1 (
        echo [警告] ICO 图标生成失败，将使用默认图标
        echo [提示] 如果已安装 Pillow，可以手动运行: python tools\convert_svg_to_ico.py
    ) else (
        echo [OK] ICO 图标文件已生成: assets\icon.ico
    )
) else (
    echo [OK] ICO 图标文件已存在: assets\icon.ico
)
echo.

echo [2/5] 清理旧的构建文件...
if exist "build" rmdir /s /q "build"
if exist "dist\AutoVoiceType" rmdir /s /q "dist\AutoVoiceType"
echo [OK] 清理完成
echo.

echo [3/5] 使用 PyInstaller 打包应用...
pyinstaller AutoVoiceType.spec
if errorlevel 1 (
    echo [错误] PyInstaller 打包失败
    pause
    exit /b 1
)
echo [OK] 打包完成
echo.

echo [4/5] 检查打包结果...
if not exist "dist\AutoVoiceType\AutoVoiceType.exe" (
    echo [错误] 可执行文件未生成
    pause
    exit /b 1
)
echo [OK] 可执行文件已生成: dist\AutoVoiceType\AutoVoiceType.exe

REM 检查 Python DLL 是否存在
if exist "dist\AutoVoiceType\_internal\python*.dll" (
    echo [OK] Python DLL 已包含在打包文件中
) else (
    echo [警告] 未找到 Python DLL，这可能导致运行时错误
    echo [提示] 请确保 PyInstaller 版本与 Python 版本兼容
)
echo.

echo [5/5] 复制必要文件...
if not exist "dist\AutoVoiceType\config" mkdir "dist\AutoVoiceType\config"
copy /Y "config\default_config.json" "dist\AutoVoiceType\config\" >nul 2>&1
if not exist "dist\AutoVoiceType\docs" mkdir "dist\AutoVoiceType\docs"
copy /Y "docs\USER_MANUAL.md" "dist\AutoVoiceType\docs\" >nul 2>&1
copy /Y "README.md" "dist\AutoVoiceType\" >nul 2>&1
echo [OK] 文件复制完成
echo.

echo ========================================
echo 构建成功完成！
echo ========================================
echo.
echo 输出目录: dist\AutoVoiceType\
echo 主程序: dist\AutoVoiceType\AutoVoiceType.exe
echo.
echo 提示：
echo - 可以直接运行 dist\AutoVoiceType\AutoVoiceType.exe 测试
echo - 如需创建安装程序，请运行 build_installer.bat
echo - 或手动使用 Inno Setup 编译 installer.iss
echo.
echo 重要提示：
echo - 如果运行时出现 DLL 加载错误：
echo   1. 确保系统已安装 Visual C++ Redistributable
echo   2. 检查 PyInstaller 版本是否与 Python 版本兼容
echo   3. 尝试在干净的虚拟环境中重新构建
echo.

pause

