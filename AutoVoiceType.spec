# -*- mode: python ; coding: utf-8 -*-
"""
AutoVoiceType - PyInstaller 打包配置文件

使用方法:
    pyinstaller AutoVoiceType.spec

这将生成可执行文件到 dist/AutoVoiceType/ 目录
"""

import sys
import os
import logging
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_all

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

# 收集 PyQt5 的数据文件（插件、翻译等）
try:
    datas += collect_data_files('PyQt5')
except Exception as e:
    print(f"警告: 收集 PyQt5 数据文件时出错: {e}")

# 收集 numpy 的数据文件
try:
    datas += collect_data_files('numpy')
except Exception as e:
    print(f"警告: 收集 numpy 数据文件时出错: {e}")

# 收集 pyaudio 的数据文件
try:
    datas += collect_data_files('pyaudio')
except Exception as e:
    print(f"警告: 收集 pyaudio 数据文件时出错: {e}")

# 收集 dashscope 的数据文件
try:
    datas += collect_data_files('dashscope')
except Exception as e:
    print(f"警告: 收集 dashscope 数据文件时出错: {e}")

# 收集 pyautogui 的数据文件
try:
    datas += collect_data_files('pyautogui')
except Exception as e:
    print(f"警告: 收集 pyautogui 数据文件时出错: {e}")

# 隐藏导入（解决动态导入问题）
hiddenimports = [
    # PyQt5 核心模块
    'PyQt5',
    'PyQt5.QtCore',
    'PyQt5.QtGui',
    'PyQt5.QtWidgets',
    'PyQt5.QtNetwork',
    'PyQt5.sip',
    
    # 阿里云 DashScope
    'dashscope',
    'dashscope.api_entities',
    'dashscope.audio',
    'dashscope.audio.asr',
    
    # 音频相关
    'pyaudio',
    '_portaudio',  # pyaudio 的底层依赖
    'numpy',
    'numpy.core',
    'numpy.core._multiarray_umath',
    'numpy.core.multiarray',
    'numpy.core.umath',
    
    # 键盘钩子
    'pynput',
    'pynput.keyboard',
    'pynput.keyboard._win32',
    'pynput.mouse',
    'pynput.mouse._win32',
    
    # 剪贴板和输入模拟
    'pyperclip',
    'pyautogui',
    'pyautogui._pyautogui_win',
    'pyautogui._pyautogui_x11',
    'pyautogui._pyautogui_osx',
    
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
    'websocket._exceptions',
    'websocket._handshake',
    'websocket._http',
    'websocket._logging',
    'websocket._ssl_compat',
    'websocket._url',
    'websocket._utils',
    'websocket-client',
    
    # 其他依赖
    'logging',
    'logging.handlers',
    'pathlib',
    'json',
    'threading',
    'queue',
]

# 收集所有主要依赖的子模块
dependency_modules = [
    'PyQt5',
    'pynput',
    'dashscope',
    'numpy',
    'pyaudio',
    'pyautogui',
    'websocket',
]

for module_name in dependency_modules:
    try:
        submodules = collect_submodules(module_name)
        hiddenimports += submodules
        print(f"已收集 {module_name} 的 {len(submodules)} 个子模块")
    except Exception as e:
        print(f"警告: 收集 {module_name} 子模块时出错: {e}")

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
        # 'numpy',  # 注释掉，因为可能被其他模块使用
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
# 图标文件路径（如果存在）
# 优先使用 logo.ico（Windows任务栏需要ICO格式）
icon_path = os.path.join(ASSETS_DIR, 'logo.ico')
if not os.path.exists(icon_path):
    logger.warning(f"图标文件不存在: {icon_path}，将使用默认图标")
    logger.info("提示：请确保 assets/logo.ico 文件存在，用于设置exe文件图标和Windows任务栏图标")
    icon_path = None
else:
    logger.info(f"找到exe图标文件: {icon_path}")

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AutoVoiceType',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # 禁用 UPX 压缩（避免 DLL 加载问题）
    console=False,  # 无控制台窗口（GUI模式）
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # 图标文件（如果存在）
    icon=icon_path if icon_path and os.path.exists(icon_path) else None,
)

# 收集所有文件到目录
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,  # 禁用 UPX 压缩（避免 DLL 加载问题）
    upx_exclude=[],
    name='AutoVoiceType',
)

# 注意：
# 1. 如果要生成单文件版本（启动较慢），可以在 EXE() 中添加 one_file=True
# 2. 如果有图标文件，取消注释 icon= 行并确保 icon.ico 存在
# 3. UPX 压缩已禁用（upx=False），因为 UPX 压缩可能导致 "Failed to load python dll" 错误
#    如果确实需要压缩，可以尝试启用，但需要确保 DLL 能正常加载
# 4. 推荐使用目录模式（one-dir）以提高启动速度
# 5. 如果遇到 DLL 加载问题，确保系统已安装 Visual C++ Redistributable

