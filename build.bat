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

echo [OK] 依赖检查完成
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

pause

