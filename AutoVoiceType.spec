# -*- mode: python ; coding: utf-8 -*-
"""
AutoVoiceType - PyInstaller 打包配置文件

使用方法:
    pyinstaller AutoVoiceType.spec

这将生成可执行文件到 dist/AutoVoiceType/ 目录
"""

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# 项目根目录
ROOT_DIR = os.path.abspath(SPECPATH)

# 源代码目录
SRC_DIR = os.path.join(ROOT_DIR, 'src')

# 资源文件目录
ASSETS_DIR = os.path.join(ROOT_DIR, 'assets')
CONFIG_DIR = os.path.join(ROOT_DIR, 'config')

# 收集数据文件
datas = []

# 添加资源文件
if os.path.exists(ASSETS_DIR):
    datas.append((ASSETS_DIR, 'assets'))

# 添加配置文件
if os.path.exists(CONFIG_DIR):
    datas.append((CONFIG_DIR, 'config'))

# 收集 dashscope 的数据文件
datas += collect_data_files('dashscope')

# 隐藏导入（解决动态导入问题）
hiddenimports = [
    # PyQt5 模块
    'PyQt5.QtCore',
    'PyQt5.QtGui',
    'PyQt5.QtWidgets',
    'PyQt5.QtNetwork',
    
    # 阿里云 DashScope
    'dashscope',
    'dashscope.api_entities',
    'dashscope.audio',
    'dashscope.audio.asr',
    
    # 音频相关
    'pyaudio',
    
    # 键盘钩子
    'pynput',
    'pynput.keyboard',
    'pynput.mouse',
    
    # 剪贴板和输入模拟
    'pyperclip',
    'pyautogui',
    
    # Windows API
    'win32api',
    'win32con',
    'win32gui',
    'win32com',
    'win32com.client',
    'pywintypes',
    
    # 网络通信
    'websocket',
    'websocket._app',
    'websocket._core',
    'websocket._socket',
    
    # 其他依赖
    'logging',
    'logging.handlers',
    'pathlib',
    'json',
    'threading',
    'queue',
]

# 收集所有子模块
hiddenimports += collect_submodules('dashscope')

# 分析主程序
a = Analysis(
    [os.path.join(SRC_DIR, 'main.py')],
    pathex=[SRC_DIR],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的模块以减小体积
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'IPython',
        'jupyter',
        'notebook',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 过滤二进制文件（可选，用于减小体积）
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# 生成可执行文件
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AutoVoiceType',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # 启用 UPX 压缩
    console=False,  # 无控制台窗口（GUI模式）
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # 图标文件（如果有）
    # icon=os.path.join(ASSETS_DIR, 'icon.ico'),
)

# 收集所有文件到目录
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AutoVoiceType',
)

# 注意：
# 1. 如果要生成单文件版本（启动较慢），可以在 EXE() 中添加 one_file=True
# 2. 如果有图标文件，取消注释 icon= 行并确保 icon.ico 存在
# 3. UPX 压缩需要安装 UPX (https://github.com/upx/upx/releases)
# 4. 推荐使用目录模式（one-dir）以提高启动速度

