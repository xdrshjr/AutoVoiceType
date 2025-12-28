@echo off
REM AutoVoiceType - 安装程序构建脚本
REM 使用 Inno Setup 创建安装程序

echo ========================================
echo AutoVoiceType 安装程序构建脚本
echo ========================================
echo.

REM 检查是否已经完成应用打包
if not exist "dist\AutoVoiceType\AutoVoiceType.exe" (
    echo [错误] 未找到已打包的应用程序
    echo 请先运行 build.bat 完成应用打包
    pause
    exit /b 1
)

echo [1/3] 检查 Inno Setup...
set "ISCC_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist "%ISCC_PATH%" (
    echo [警告] 未找到 Inno Setup 编译器
    echo.
    echo 请安装 Inno Setup 6:
    echo https://jrsoftware.org/isdl.php
    echo.
    echo 或手动指定 ISCC.exe 路径
    pause
    exit /b 1
)
echo [OK] Inno Setup 已找到
echo.

echo [2/3] 创建必要的文件...
REM 创建临时的 LICENSE.txt（如果不存在）
if not exist "LICENSE.txt" (
    echo MIT License > LICENSE.txt
    echo. >> LICENSE.txt
    echo Copyright (c) 2025 AutoVoiceType Team >> LICENSE.txt
    echo. >> LICENSE.txt
    echo Permission is hereby granted... >> LICENSE.txt
)
echo [OK] 文件准备完成
echo.

echo [3/3] 编译安装程序...
"%ISCC_PATH%" installer.iss
if errorlevel 1 (
    echo [错误] 安装程序编译失败
    pause
    exit /b 1
)
echo [OK] 安装程序编译完成
echo.

echo ========================================
echo 安装程序构建成功！
echo ========================================
echo.
echo 输出目录: dist\installer\
echo 安装程序: dist\installer\AutoVoiceType_Setup_1.0.0.exe
echo.
echo 提示：
echo - 安装程序已经包含所有必要的文件
echo - 用户无需安装 Python 或其他依赖
echo - 支持静默安装参数: /VERYSILENT /NORESTART
echo.

pause

