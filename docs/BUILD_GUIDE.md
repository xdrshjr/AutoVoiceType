# AutoVoiceType 构建指南

本文档详细说明如何从源代码构建 AutoVoiceType 的可执行文件和安装程序。

---

## 📋 目录

1. [环境准备](#环境准备)
2. [构建可执行文件](#构建可执行文件)
3. [创建安装程序](#创建安装程序)
4. [故障排除](#故障排除)
5. [高级配置](#高级配置)

---

## 环境准备

### 必需软件

1. **Python 3.8+**
   - 下载：https://www.python.org/downloads/
   - 安装时勾选"Add Python to PATH"

2. **PyInstaller**
   ```bash
   pip install pyinstaller
   ```

3. **Inno Setup 6**（可选，用于创建安装程序）
   - 下载：https://jrsoftware.org/isdl.php
   - 默认安装路径：`C:\Program Files (x86)\Inno Setup 6\`

4. **UPX**（可选，用于压缩可执行文件）
   - 下载：https://github.com/upx/upx/releases
   - 解压到 PATH 环境变量中的目录

### 安装项目依赖

```bash
cd AutoVoiceType
pip install -r requirements.txt
```

---

## 构建可执行文件

### 方法一：使用构建脚本（推荐）

1. **运行构建脚本**
   ```bash
   build.bat
   ```

2. **等待构建完成**
   - 脚本会自动清理旧文件
   - 运行 PyInstaller
   - 复制必要的资源文件

3. **查看构建结果**
   ```
   dist\AutoVoiceType\
   ├── AutoVoiceType.exe    # 主程序
   ├── assets\              # 资源文件
   ├── config\              # 配置文件
   ├── docs\                # 文档
   └── ... (其他依赖文件)
   ```

### 方法二：手动构建

1. **清理旧的构建文件**
   ```bash
   rmdir /s /q build
   rmdir /s /q dist\AutoVoiceType
   ```

2. **运行 PyInstaller**
   ```bash
   pyinstaller AutoVoiceType.spec
   ```

3. **复制资源文件**
   ```bash
   xcopy /E /I /Y config dist\AutoVoiceType\config
   xcopy /E /I /Y assets dist\AutoVoiceType\assets
   xcopy /E /I /Y docs\USER_MANUAL.md dist\AutoVoiceType\docs\
   copy /Y README.md dist\AutoVoiceType\
   ```

### 构建选项说明

**AutoVoiceType.spec** 中的关键配置：

```python
# 单文件 vs 目录模式
# 单文件模式（启动慢，但便于分发）
exe = EXE(..., one_file=True, ...)

# 目录模式（启动快，推荐）
exe = EXE(..., exclude_binaries=True, ...)

# 控制台窗口
console=False  # 不显示控制台（GUI应用）
console=True   # 显示控制台（调试时使用）

# UPX 压缩
upx=True       # 启用压缩（需要安装UPX）
upx=False      # 禁用压缩

# 图标
icon='assets/icon.ico'  # 应用图标（需要先创建）
```

---

## 创建安装程序

### 前提条件

- 已成功构建可执行文件（完成上一步）
- 已安装 Inno Setup 6

### 方法一：使用构建脚本（推荐）

1. **运行安装程序构建脚本**
   ```bash
   build_installer.bat
   ```

2. **等待编译完成**
   - 脚本会检查 Inno Setup 是否安装
   - 编译 `installer.iss`
   - 输出安装程序到 `dist\installer\`

3. **查看输出**
   ```
   dist\installer\AutoVoiceType_Setup_1.0.0.exe
   ```

### 方法二：手动创建

1. **打开 Inno Setup Compiler**
   - 开始菜单 → Inno Setup → Inno Setup Compiler

2. **打开脚本文件**
   - File → Open → 选择 `installer.iss`

3. **编译脚本**
   - Build → Compile
   - 或按 Ctrl+F9

4. **查看输出**
   - 安装程序位于 `dist\installer\` 目录

### 安装程序配置说明

**installer.iss** 中的关键配置：

```iss
; 应用信息
#define MyAppVersion "1.0.0"     ; 版本号
#define MyAppPublisher "..."     ; 发布者

; 输出配置
OutputDir=dist\installer          ; 输出目录
OutputBaseFilename=AutoVoiceType_Setup_{#MyAppVersion}  ; 文件名

; 压缩选项
Compression=lzma2/max            ; 最大压缩
SolidCompression=yes             ; 固实压缩

; 权限要求
PrivilegesRequired=admin         ; 需要管理员权限

; 安装选项
[Tasks]
Name: "desktopicon"              ; 桌面快捷方式
Name: "autostart"                ; 开机自启动
```

---

## 故障排除

### 问题1：PyInstaller 找不到模块

**错误信息：**
```
ModuleNotFoundError: No module named 'xxx'
```

**解决方法：**
1. 检查模块是否安装：`pip list`
2. 添加到 hidden imports：
   ```python
   # AutoVoiceType.spec
   hiddenimports=[
       'xxx',  # 添加缺失的模块
   ]
   ```

### 问题2：打包后运行报错

**错误信息：**
```
FileNotFoundError: [Errno 2] No such file or directory: 'assets/xxx'
```

**解决方法：**
1. 确认资源文件已添加到 `datas`：
   ```python
   # AutoVoiceType.spec
   datas=[
       ('assets', 'assets'),  # 添加资源目录
       ('config', 'config'),
   ]
   ```

### 问题3：UPX 压缩失败

**错误信息：**
```
UPX is not available
```

**解决方法：**
1. 下载 UPX：https://github.com/upx/upx/releases
2. 解压到 PATH 目录，或：
3. 禁用 UPX：
   ```python
   # AutoVoiceType.spec
   upx=False
   ```

### 问题4：Inno Setup 找不到

**错误信息：**
```
未找到 Inno Setup 编译器
```

**解决方法：**
1. 确认已安装 Inno Setup 6
2. 检查安装路径是否为默认路径
3. 或修改 `build_installer.bat` 中的路径：
   ```batch
   set "ISCC_PATH=D:\Your\Path\ISCC.exe"
   ```

### 问题5：打包文件过大

**可能原因：**
- 包含了不必要的依赖
- 未启用压缩

**优化方法：**

1. **排除不需要的模块**
   ```python
   # AutoVoiceType.spec
   excludes=[
       'tkinter',
       'matplotlib',
       'numpy',
       'pandas',
   ]
   ```

2. **启用 UPX 压缩**
   ```python
   upx=True
   ```

3. **使用目录模式而非单文件**
   - 单文件模式会增大体积

### 问题6：杀毒软件误报

**原因：**
- PyInstaller 打包的程序容易被误报
- 使用了全局钩子

**解决方法：**
1. 添加到杀毒软件白名单
2. 购买代码签名证书（推荐）
3. 从官方渠道分发，建立信任

---

## 高级配置

### 自定义打包选项

**创建自定义 .spec 文件：**

```bash
pyi-makespec src/main.py \
  --name AutoVoiceType \
  --windowed \
  --icon assets/icon.ico \
  --add-data "assets;assets" \
  --add-data "config;config" \
  --hidden-import PyQt5 \
  --hidden-import dashscope
```

然后编辑生成的 `.spec` 文件进行更多定制。

### 代码签名

**使用 SignTool 签名：**

```bash
# 需要代码签名证书

signtool sign /f "your_certificate.pfx" /p "password" /t "http://timestamp.server" "AutoVoiceType.exe"
```

**好处：**
- 通过 Windows SmartScreen
- 建立软件发布者信任
- 减少杀毒软件误报

### 创建便携版

**制作免安装版本：**

1. 构建可执行文件（目录模式）
2. 打包为 ZIP：
   ```bash
   cd dist
   tar -a -c -f AutoVoiceType_Portable_1.0.0.zip AutoVoiceType
   ```

3. 添加说明文件：
   ```
   AutoVoiceType_Portable/
   ├── AutoVoiceType.exe
   ├── README_PORTABLE.txt
   └── ... (其他文件)
   ```

### 自动化构建（CI/CD）

**GitHub Actions 示例：**

```yaml
name: Build

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.8'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pyinstaller
      - name: Build
        run: build.bat
      - name: Upload artifact
        uses: actions/upload-artifact@v2
        with:
          name: AutoVoiceType
          path: dist/AutoVoiceType/
```

---

## 构建清单

发布前的检查清单：

- [ ] 更新版本号（`src/version.py`）
- [ ] 更新 CHANGELOG
- [ ] 运行所有测试（`pytest`）
- [ ] 清理构建目录
- [ ] 构建可执行文件（`build.bat`）
- [ ] 测试可执行文件运行
- [ ] 测试所有功能正常
- [ ] 创建安装程序（`build_installer.bat`）
- [ ] 测试安装和卸载
- [ ] 检查文件大小（<100MB）
- [ ] 在干净的系统上测试
- [ ] 代码签名（如有证书）
- [ ] 创建 Git 标签
- [ ] 创建 GitHub Release
- [ ] 上传安装程序
- [ ] 编写 Release Notes

---

## 📞 需要帮助？

如果在构建过程中遇到问题：

1. 查看本文档的"故障排除"部分
2. 检查日志文件（`build\` 目录）
3. 搜索错误信息
4. 在 GitHub Issues 中提问
5. 联系开发团队

---

**文档版本：** 1.0  
**最后更新：** 2025-12-28  
**适用于：** AutoVoiceType v1.0.0

---

**祝构建顺利！** 🚀

