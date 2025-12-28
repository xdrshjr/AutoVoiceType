# AutoVoiceType 开发者文档

**版本：** 1.0.0  
**更新日期：** 2025-12-28

---

## 📋 目录

1. [项目概述](#1-项目概述)
2. [架构设计](#2-架构设计)
3. [项目结构](#3-项目结构)
4. [开发环境搭建](#4-开发环境搭建)
5. [核心模块详解](#5-核心模块详解)
6. [代码规范](#6-代码规范)
7. [测试指南](#7-测试指南)
8. [构建和部署](#8-构建和部署)
9. [API参考](#9-api参考)
10. [贡献指南](#10-贡献指南)

---

## 1. 项目概述

### 1.1 项目简介

**AutoVoiceType** 是一款基于 Python 开发的智能语音输入工具，集成了阿里云 DashScope 语音识别服务，提供全局快捷键触发的语音转文字功能。

### 1.2 技术栈

| 类别 | 技术 | 版本要求 | 用途 |
|------|------|---------|------|
| **编程语言** | Python | 3.8+ | 主要开发语言 |
| **UI框架** | PyQt5 | 5.15+ | 图形界面 |
| **全局快捷键** | pynput | 1.7.6+ | 键盘钩子 |
| **音频采集** | PyAudio | 0.2.11+ | 麦克风音频流 |
| **语音识别** | DashScope SDK | 1.10+ | 阿里云语音识别 |
| **网络通信** | websocket-client | 1.3+ | WebSocket 连接 |
| **文本输入** | pyperclip, pyautogui | - | 模拟输入 |
| **系统集成** | pywin32 | 305+ | Windows API |
| **打包工具** | PyInstaller | 5.0+ | 可执行文件打包 |

### 1.3 核心特性

- 🎯 全局快捷键监听（右Ctrl键）
- 🎤 实时语音识别（流式传输）
- ⌨️ 跨应用文本输入（三级降级策略）
- 🎨 现代化图形界面（macOS风格）
- 📦 系统托盘集成
- 🔧 完整的配置管理
- 📝 详细的日志记录

---

## 2. 架构设计

### 2.1 系统架构

AutoVoiceType 采用分层架构设计：

```
┌─────────────────────────────────────────────────────────────┐
│                      表示层 (UI Layer)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  TrayApp     │  │SettingsWindow│  │RecordingWidget│     │
│  │  (托盘应用)   │  │  (设置界面)   │  │  (录音动画)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    业务逻辑层 (Business Layer)                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │HotkeyManager │  │VoiceRecognizer│  │TextSimulator │      │
│  │(快捷键管理)   │  │  (语音识别)   │  │  (文本输入)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐                         │
│  │ConfigManager │  │AutoStartMgr  │                         │
│  │  (配置管理)   │  │ (自启动管理)  │                         │
│  └──────────────┘  └──────────────┘                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                 数据访问层 (Data Access Layer)                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │DashScope API │  │AudioCapture  │  │ConfigStorage │      │
│  │  (语音API)    │  │  (音频采集)   │  │  (配置存储)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│               系统接口层 (System Interface Layer)             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │Windows API   │  │Global Hook   │  │Clipboard     │      │
│  │  (Win32)     │  │ (键盘监听)    │  │  (剪贴板)     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 数据流

**语音输入完整流程：**

```
用户按下右Ctrl键
        ↓
HotkeyManager 检测按键
        ↓
触发 on_press 回调
        ↓
AutoVoiceTypeApp.on_hotkey_press()
        ↓
┌──────────────────────────────┐
│ 显示录音动画                   │
│ RecordingWidget.show_recording()│
└──────────────────────────────┘
        ↓
┌──────────────────────────────┐
│ 启动录音和识别                 │
│ VoiceRecognizer.start_recording()│
│   ├─ 建立 WebSocket 连接      │
│   ├─ 打开麦克风音频流          │
│   └─ 开始发送音频数据          │
└──────────────────────────────┘
        ↓
用户说话（持续按住按键）
        ↓
音频数据通过 WebSocket 发送到 DashScope API
        ↓
实时接收识别结果（部分结果）
        ↓
用户松开右Ctrl键
        ↓
HotkeyManager 检测按键释放
        ↓
触发 on_release 回调
        ↓
AutoVoiceTypeApp.on_hotkey_release()
        ↓
┌──────────────────────────────┐
│ 停止录音和识别                 │
│ VoiceRecognizer.stop_recording()│
│   ├─ 停止音频发送              │
│   ├─ 关闭 WebSocket 连接      │
│   └─ 关闭音频流               │
└──────────────────────────────┘
        ↓
隐藏录音动画
        ↓
等待最终识别结果
        ↓
VoiceRecognitionCallback.on_complete()
        ↓
触发结果回调
        ↓
AutoVoiceTypeApp.on_recognition_result(text)
        ↓
┌──────────────────────────────┐
│ 自动输入文本                   │
│ TextSimulator.input_text(text) │
│   ├─ 尝试剪贴板方案            │
│   ├─ 失败则降级到Win32方案      │
│   └─ 再失败则降级到逐字输入     │
└──────────────────────────────┘
        ↓
文本出现在当前光标位置
        ↓
显示通知提示用户
```

### 2.3 设计模式

#### 2.3.1 单例模式（Singleton）

**应用场景：** ConfigManager

```python
class ConfigManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

**优点：**
- 全局唯一的配置管理器实例
- 避免重复加载配置文件
- 保证配置一致性

#### 2.3.2 回调模式（Callback）

**应用场景：** HotkeyManager, VoiceRecognizer

```python
class HotkeyManager:
    def set_callbacks(self, on_press, on_release):
        self._press_callback = on_press
        self._release_callback = on_release
```

**优点：**
- 解耦模块之间的依赖
- 灵活的事件处理
- 易于扩展

#### 2.3.3 策略模式（Strategy）

**应用场景：** TextSimulator 的输入方法

```python
class TextSimulator:
    def _try_input_with_method(self, text, method):
        if method == InputMethod.CLIPBOARD:
            return self._input_via_clipboard(text)
        elif method == InputMethod.WIN32:
            return self._input_via_win32(text)
        elif method == InputMethod.PYAUTOGUI:
            return self._input_via_pyautogui(text)
```

**优点：**
- 多种输入策略可切换
- 降级机制实现简单
- 易于添加新策略

#### 2.3.4 观察者模式（Observer）

**应用场景：** Qt 信号槽机制

```python
class SettingsWindow(QWidget):
    config_saved = pyqtSignal()  # 信号
    
    def save_config(self):
        # 保存配置
        self.config_saved.emit()  # 触发信号

# 订阅信号
settings_window.config_saved.connect(on_config_saved)
```

**优点：**
- UI 与业务逻辑解耦
- 事件驱动编程
- PyQt5 内置支持

---

## 3. 项目结构

### 3.1 目录结构

```
AutoVoiceType/
├── src/                          # 源代码目录
│   ├── main.py                   # 应用主入口
│   ├── version.py                # 版本信息
│   ├── config_manager.py         # 配置管理模块
│   ├── hotkey_manager.py         # 快捷键管理模块
│   ├── voice_recognizer.py       # 语音识别模块
│   ├── text_simulator.py         # 文本输入模拟模块
│   └── ui/                       # UI模块
│       ├── __init__.py           # UI模块导出
│       ├── tray_app.py           # 系统托盘应用
│       ├── recording_widget.py   # 录音动画窗口
│       ├── settings_window.py    # 设置窗口主模块
│       ├── settings_pages.py     # 设置页面实现
│       └── auto_start.py         # 自动启动管理
│
├── assets/                       # 资源文件
│   ├── styles.qss                # QSS样式表（macOS风格）
│   └── icon.ico                  # 应用图标（需要创建）
│
├── config/                       # 配置文件
│   └── default_config.json       # 默认配置模板
│
├── docs/                         # 文档目录
│   ├── PROJECT_PLAN.md           # 项目开发方案
│   ├── TASK_LIST.md              # 开发任务清单
│   ├── USER_MANUAL.md            # 用户手册
│   ├── DEVELOPER.md              # 开发者文档（本文件）
│   ├── BUILD_GUIDE.md            # 构建指南
│   ├── CHANGELOG.md              # 版本变更日志
│   ├── INSTALLATION.md           # 安装说明
│   ├── QUICK_REFERENCE.md        # 快速参考
│   └── example-code.py           # 参考代码示例
│
├── tests/                        # 测试目录
│   ├── __init__.py
│   ├── test_config_manager.py
│   ├── test_hotkey_manager.py
│   ├── test_voice_recognizer.py
│   └── test_text_simulator.py
│
├── build/                        # 构建临时文件（.gitignore）
├── dist/                         # 打包输出目录（.gitignore）
│
├── AutoVoiceType.spec            # PyInstaller 配置文件
├── installer.iss                 # Inno Setup 安装脚本
├── build.bat                     # Windows 构建脚本
├── build_installer.bat           # 安装程序构建脚本
├── run.bat                       # 快速启动脚本
├── check_environment.bat         # 环境检查脚本
├── check_environment.py          # 环境检查Python脚本
├── requirements.txt              # Python依赖清单
├── README.md                     # 项目说明
├── LICENSE                       # 许可证文件
└── .gitignore                    # Git忽略文件
```

### 3.2 模块职责

| 模块 | 文件 | 职责 | 依赖 |
|------|------|------|------|
| **主应用** | `main.py` | 应用启动、模块初始化、事件协调 | 所有模块 |
| **配置管理** | `config_manager.py` | 配置加载、保存、验证 | JSON, pathlib |
| **快捷键管理** | `hotkey_manager.py` | 全局键盘监听、右Ctrl键检测 | pynput |
| **语音识别** | `voice_recognizer.py` | 音频采集、WebSocket通信、识别结果处理 | PyAudio, dashscope |
| **文本输入** | `text_simulator.py` | 剪贴板操作、模拟输入、降级策略 | pyperclip, pyautogui, pywin32 |
| **系统托盘** | `tray_app.py` | 托盘图标、右键菜单、通知 | PyQt5 |
| **录音动画** | `recording_widget.py` | 悬浮窗口、动画效果 | PyQt5 |
| **设置窗口** | `settings_window.py` | 设置界面主窗口、首次运行向导 | PyQt5 |
| **设置页面** | `settings_pages.py` | 各个配置页面的实现 | PyQt5 |
| **自启动** | `auto_start.py` | 注册表操作、开机启动设置 | pywin32 |

### 3.3 配置文件结构

**默认配置文件：** `~/.autovoicetype/config.json`

```json
{
    "api": {
        "dashscope_api_key": "",
        "base_websocket_url": "wss://dashscope.aliyuncs.com/api-ws/v1/inference",
        "model": "fun-asr-realtime"
    },
    "audio": {
        "sample_rate": 16000,
        "channels": 1,
        "chunk_size": 3200,
        "format": "pcm"
    },
    "input": {
        "preferred_method": "clipboard",
        "input_delay": 0.05,
        "paste_delay": 0.1,
        "max_input_length": 10000,
        "restore_clipboard": true
    },
    "recognition": {
        "semantic_punctuation_enabled": false,
        "timeout": 30
    },
    "general": {
        "auto_start": false,
        "language": "zh-CN",
        "log_level": "INFO"
    },
    "hotkey": {
        "trigger_key": "ctrl_r"
    }
}
```

---

## 4. 开发环境搭建

### 4.1 环境要求

- **操作系统：** Windows 10/11 (64位)
- **Python：** 3.8 或更高版本
- **IDE：** 推荐 VS Code, PyCharm, 或 Sublime Text
- **Git：** 版本控制工具

### 4.2 安装步骤

#### 4.2.1 克隆代码仓库

```bash
git clone https://github.com/yourusername/AutoVoiceType.git
cd AutoVoiceType
```

#### 4.2.2 创建虚拟环境（推荐）

**使用 venv：**
```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

**使用 conda：**
```bash
conda create -n autovoicetype python=3.8
conda activate autovoicetype
```

#### 4.2.3 安装依赖

```bash
pip install -r requirements.txt
```

**注意：** PyAudio 在 Windows 上可能需要预编译的 wheel 文件：

```bash
# 下载对应版本的 wheel 文件
# https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio

pip install PyAudio‑0.2.11‑cp38‑cp38‑win_amd64.whl
```

#### 4.2.4 配置 API 密钥

编辑 `~/.autovoicetype/config.json`：

```json
{
    "api": {
        "dashscope_api_key": "sk-your-api-key-here"
    }
}
```

或在首次运行时通过配置向导设置。

#### 4.2.5 运行应用

```bash
cd src
python main.py
```

### 4.3 IDE 配置

#### VS Code 推荐插件

- **Python** - Microsoft 官方插件
- **Pylance** - Python 语言服务器
- **Python Docstring Generator** - 文档字符串生成器
- **GitLens** - Git 增强
- **Better Comments** - 注释高亮

#### VS Code 配置文件

**.vscode/settings.json**

```json
{
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.formatting.provider": "autopep8",
    "python.linting.pylintArgs": [
        "--max-line-length=120"
    ],
    "editor.rulers": [120],
    "files.encoding": "utf8"
}
```

**.vscode/launch.json**

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Main",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/src/main.py",
            "console": "integratedTerminal",
            "cwd": "${workspaceFolder}"
        }
    ]
}
```

### 4.4 开发工具

#### 代码格式化

```bash
# 安装 autopep8
pip install autopep8

# 格式化文件
autopep8 --in-place --aggressive --aggressive <filename>
```

#### 代码检查

```bash
# 安装 pylint
pip install pylint

# 检查代码
pylint src/
```

#### 类型检查

```bash
# 安装 mypy
pip install mypy

# 类型检查
mypy src/
```

---

## 5. 核心模块详解

### 5.1 ConfigManager（配置管理器）

**文件：** `src/config_manager.py`

**职责：**
- 加载和保存配置文件
- 提供配置项访问接口
- 配置合并和验证
- 敏感信息处理

**核心方法：**

```python
class ConfigManager:
    def __init__(self):
        """初始化配置管理器"""
        
    def load_config(self) -> None:
        """从文件加载配置"""
        
    def save_config(self) -> bool:
        """保存配置到文件"""
        
    def get(self, key_path: str, default=None):
        """获取配置项（支持点号路径）"""
        
    def set(self, key_path: str, value) -> None:
        """设置配置项"""
        
    def validate_api_key(self) -> bool:
        """验证API密钥格式"""
        
    def is_first_run(self) -> bool:
        """检查是否首次运行"""
```

**使用示例：**

```python
from config_manager import ConfigManager

# 创建实例
config_mgr = ConfigManager()

# 获取配置
api_key = config_mgr.get('api.dashscope_api_key')
log_level = config_mgr.get('general.log_level', 'INFO')

# 设置配置
config_mgr.set('general.auto_start', True)
config_mgr.save_config()
```

**配置路径格式：**

```python
# 点号分隔的路径
"api.dashscope_api_key"  # 等价于 config['api']['dashscope_api_key']
"audio.sample_rate"      # 等价于 config['audio']['sample_rate']
```

### 5.2 HotkeyManager（快捷键管理器）

**文件：** `src/hotkey_manager.py`

**职责：**
- 全局键盘事件监听
- 识别右Ctrl键按下和释放
- 防止重复触发
- 回调函数管理

**核心方法：**

```python
class HotkeyManager:
    def set_callbacks(self, on_press, on_release):
        """设置回调函数"""
        
    def is_right_ctrl(self, key) -> bool:
        """判断是否为右Ctrl键"""
        
    def start_listening(self) -> bool:
        """启动全局监听"""
        
    def stop_listening(self) -> bool:
        """停止监听"""
        
    def is_key_currently_pressed(self) -> bool:
        """检查按键是否按下"""
```

**使用示例：**

```python
from hotkey_manager import HotkeyManager

# 创建实例
hotkey_mgr = HotkeyManager()

# 设置回调
def on_press():
    print("Right Ctrl pressed!")
    
def on_release():
    print("Right Ctrl released!")

hotkey_mgr.set_callbacks(on_press=on_press, on_release=on_release)

# 启动监听
hotkey_mgr.start_listening()
```

**技术实现：**

使用 `pynput.keyboard.Listener` 实现全局键盘钩子：

```python
from pynput import keyboard

def _on_press(self, key):
    if hasattr(key, 'vk') and key.vk == 0xA3:  # VK_RCONTROL
        if not self._is_key_pressed:
            self._is_key_pressed = True
            if self._press_callback:
                self._press_callback()

listener = keyboard.Listener(on_press=_on_press, on_release=_on_release)
listener.start()
```

### 5.3 VoiceRecognizer（语音识别器）

**文件：** `src/voice_recognizer.py`

**职责：**
- 音频流采集（PyAudio）
- WebSocket 连接管理
- 音频数据发送
- 识别结果处理

**核心类：**

```python
class VoiceRecognitionCallback(RecognitionCallback):
    """识别回调处理类"""
    def on_open(self):
        """连接建立"""
    def on_close(self):
        """连接关闭"""
    def on_complete(self):
        """识别完成"""
    def on_error(self, message):
        """识别错误"""
    def on_event(self, result):
        """识别结果事件"""

class VoiceRecognizer:
    """语音识别器主类"""
    def set_result_callback(self, callback):
        """设置结果回调"""
    def start_recording(self) -> bool:
        """开始录音和识别"""
    def stop_recording(self) -> bool:
        """停止录音和识别"""
    def is_currently_recording(self) -> bool:
        """检查是否正在录音"""
```

**使用示例：**

```python
from voice_recognizer import VoiceRecognizer

# 配置
api_key = "sk-your-api-key"
audio_config = {
    'sample_rate': 16000,
    'channels': 1,
    'chunk_size': 3200,
    'format': 'pcm'
}
api_config = {
    'model': 'fun-asr-realtime',
    'semantic_punctuation_enabled': False
}

# 创建实例
recognizer = VoiceRecognizer(api_key, audio_config, api_config)

# 设置回调
def on_result(text):
    print(f"Recognized: {text}")

recognizer.set_result_callback(on_result)

# 开始录音
recognizer.start_recording()
# ... 用户说话 ...
# 停止录音
recognizer.stop_recording()
```

**音频流处理：**

```python
# 打开音频流
stream = mic.open(
    format=pyaudio.paInt16,
    channels=1,
    rate=16000,
    input=True,
    frames_per_buffer=3200
)

# 读取音频数据
while is_recording:
    audio_data = stream.read(chunk_size, exception_on_overflow=False)
    recognition.send_audio_frame(audio_data)
```

### 5.4 TextSimulator（文本输入模拟器）

**文件：** `src/text_simulator.py`

**职责：**
- 获取当前活动窗口
- 多种输入方式实现
- 输入策略降级
- 剪贴板保护

**核心方法：**

```python
class TextSimulator:
    def input_text(self, text: str) -> bool:
        """输入文本（自动降级）"""
        
    def get_active_window_info(self) -> dict:
        """获取活动窗口信息"""
        
    def test_input_methods(self) -> dict:
        """测试输入方法可用性"""
        
    def set_input_method(self, method: InputMethod):
        """设置首选输入方法"""
```

**输入方法：**

```python
from enum import Enum

class InputMethod(Enum):
    CLIPBOARD = "clipboard"     # 剪贴板+Ctrl+V
    WIN32 = "win32"             # Win32 SendInput API
    PYAUTOGUI = "pyautogui"     # 逐字输入
```

**使用示例：**

```python
from text_simulator import TextSimulator, InputMethod

# 配置
input_config = {
    'preferred_method': 'clipboard',
    'input_delay': 0.05,
    'paste_delay': 0.1,
    'max_input_length': 10000,
    'restore_clipboard': True
}

# 创建实例
simulator = TextSimulator(config=input_config)

# 输入文本
success = simulator.input_text("Hello, World!")
if success:
    print("Text input successful")
else:
    print("Text input failed")
```

**剪贴板方案实现：**

```python
def _input_via_clipboard(self, text: str) -> bool:
    # 1. 备份剪贴板
    original = pyperclip.paste()
    
    # 2. 写入文本到剪贴板
    pyperclip.copy(text)
    
    # 3. 模拟 Ctrl+V
    pyautogui.hotkey('ctrl', 'v')
    
    # 4. 恢复剪贴板
    pyperclip.copy(original)
    
    return True
```

### 5.5 UI模块

#### 5.5.1 TrayApp（系统托盘）

**文件：** `src/ui/tray_app.py`

**职责：**
- 创建托盘图标
- 显示右键菜单
- 发送系统通知

**核心方法：**

```python
class TrayApp:
    def __init__(self, qt_app):
        """初始化托盘应用"""
        
    def set_callbacks(self, on_settings, on_quit):
        """设置回调函数"""
        
    def show(self):
        """显示托盘图标"""
        
    def show_message(self, title, message, icon, duration=3000):
        """显示通知"""
```

**使用示例：**

```python
from PyQt5.QtWidgets import QApplication
from ui import TrayApp

app = QApplication([])
tray = TrayApp(app)

# 设置回调
tray.set_callbacks(
    on_settings=lambda: print("Settings clicked"),
    on_quit=lambda: app.quit()
)

# 显示托盘
tray.show()

# 显示通知
tray.show_message("标题", "消息内容", tray.tray_icon.Information)

app.exec_()
```

#### 5.5.2 RecordingWidget（录音动画）

**文件：** `src/ui/recording_widget.py`

**职责：**
- 显示录音提示动画
- 屏幕底部居中显示
- 淡入淡出效果

**核心方法：**

```python
class RecordingWidget(QWidget):
    def show_recording(self):
        """显示录音动画"""
        
    def hide_recording(self):
        """隐藏录音动画"""
```

**使用示例：**

```python
from ui import RecordingWidget

widget = RecordingWidget()

# 显示动画
widget.show_recording()

# 隐藏动画
widget.hide_recording()
```

#### 5.5.3 SettingsWindow（设置窗口）

**文件：** `src/ui/settings_window.py`

**职责：**
- 配置界面主窗口
- 首次运行向导
- 配置变更管理

**信号：**

```python
class SettingsWindow(QWidget):
    config_saved = pyqtSignal()  # 配置保存信号
```

**核心方法：**

```python
class SettingsWindow(QWidget):
    def show_first_run_wizard(self) -> bool:
        """显示首次运行向导"""
        
    def show(self):
        """显示设置窗口"""
        
    def _apply_changes(self):
        """应用配置变更"""
        
    def _save_and_close(self):
        """保存并关闭"""
```

---

## 6. 代码规范

### 6.1 Python 代码规范

遵循 **PEP 8** 规范，以下是关键要点：

#### 6.1.1 命名规范

```python
# 模块名：小写+下划线
config_manager.py
hotkey_manager.py

# 类名：大驼峰（PascalCase）
class ConfigManager:
class VoiceRecognizer:

# 函数名：小写+下划线
def load_config():
def start_recording():

# 常量：大写+下划线
MAX_BUFFER_SIZE = 8192
DEFAULT_SAMPLE_RATE = 16000

# 私有方法：前缀下划线
def _internal_method(self):

# 变量名：小写+下划线
api_key = "sk-xxx"
sample_rate = 16000
```

#### 6.1.2 代码布局

```python
# 导入顺序
# 1. 标准库
import os
import sys
import logging

# 2. 第三方库
import pyaudio
from PyQt5.QtWidgets import QApplication

# 3. 本地模块
from config_manager import ConfigManager
from hotkey_manager import HotkeyManager

# 类定义前后各2个空行
class MyClass:
    pass


class AnotherClass:
    pass

# 函数定义前后各2个空行
def my_function():
    pass


def another_function():
    pass

# 方法之间1个空行
class MyClass:
    def method1(self):
        pass
    
    def method2(self):
        pass
```

#### 6.1.3 代码长度

```python
# 每行最大120个字符（项目标准，PEP 8为79）
# 超过时使用括号换行

# 好的做法
result = some_function_with_long_name(
    parameter1=value1,
    parameter2=value2,
    parameter3=value3
)

# 字符串换行
message = (
    "这是一个很长的消息，"
    "需要分成多行显示，"
    "以便提高可读性。"
)
```

### 6.2 文档字符串（Docstring）

使用 Google 风格的文档字符串：

```python
def my_function(param1: str, param2: int = 0) -> bool:
    """
    函数的简短描述（一行）
    
    详细描述（可选，多行）
    这里可以详细说明函数的功能、算法、注意事项等。
    
    Args:
        param1: 第一个参数的说明
        param2: 第二个参数的说明，默认为0
        
    Returns:
        bool: 返回值说明，True表示成功，False表示失败
        
    Raises:
        ValueError: 什么情况下会抛出此异常
        RuntimeError: 什么情况下会抛出此异常
        
    Examples:
        >>> my_function("test", 123)
        True
        
    Note:
        特别注意事项
    """
    pass
```

**类的文档字符串：**

```python
class MyClass:
    """
    类的简短描述
    
    详细描述（可选）
    
    Attributes:
        attr1: 属性1的说明
        attr2: 属性2的说明
        
    Examples:
        >>> obj = MyClass()
        >>> obj.method1()
    """
    
    def __init__(self, param1: str):
        """
        初始化方法
        
        Args:
            param1: 参数说明
        """
        self.attr1 = param1
```

### 6.3 类型提示（Type Hints）

使用类型提示提高代码可读性和类型安全：

```python
from typing import Optional, List, Dict, Callable, Union

def process_data(
    data: List[str], 
    callback: Optional[Callable] = None
) -> Dict[str, int]:
    """
    处理数据
    
    Args:
        data: 字符串列表
        callback: 可选的回调函数
        
    Returns:
        Dict[str, int]: 字符串到整数的映射
    """
    result: Dict[str, int] = {}
    for item in data:
        result[item] = len(item)
    return result

# 类型别名
ConfigDict = Dict[str, Union[str, int, bool]]

def load_config() -> ConfigDict:
    pass
```

### 6.4 错误处理

```python
import logging

logger = logging.getLogger(__name__)

def my_function():
    try:
        # 可能出错的代码
        risky_operation()
    except SpecificException as e:
        # 处理特定异常
        logger.error(f"特定错误: {e}", exc_info=True)
        return False
    except Exception as e:
        # 处理其他异常
        logger.error(f"未预期的错误: {e}", exc_info=True)
        raise
    finally:
        # 清理资源
        cleanup()
    
    return True
```

### 6.5 日志记录

```python
import logging

logger = logging.getLogger(__name__)

# 日志级别使用规范
logger.debug("详细的调试信息，用于开发和调试")
logger.info("一般性信息，记录程序正常运行状态")
logger.warning("警告信息，程序可以继续但可能有问题")
logger.error("错误信息，功能失败但程序可以继续")
logger.critical("严重错误，程序可能无法继续运行")

# 示例
def start_recording(self):
    logger.info("开始录音和识别")
    
    try:
        self._init_audio_stream()
        logger.debug(f"音频流已初始化，参数: {self.audio_config}")
    except Exception as e:
        logger.error(f"初始化音频流失败: {e}", exc_info=True)
        return False
    
    logger.info("录音和识别已启动")
    return True
```

### 6.6 注释规范

```python
# 1. 单行注释：井号后跟一个空格
# 这是一个单行注释

# 2. 行尾注释：代码后两个空格，然后井号和一个空格
x = 5  # 这是行尾注释

# 3. 块注释：注释整段代码
# 这是一个块注释
# 它可以有多行
# 用于说明下面的代码块

# 4. TODO注释：标记待办事项
# TODO: 实现这个功能
# FIXME: 修复这个bug
# NOTE: 重要说明
# HACK: 临时解决方案
```

---

## 7. 测试指南

### 7.1 单元测试

使用 `pytest` 框架进行单元测试。

#### 7.1.1 安装测试依赖

```bash
pip install pytest pytest-cov pytest-mock
```

#### 7.1.2 测试文件结构

```
tests/
├── __init__.py
├── test_config_manager.py
├── test_hotkey_manager.py
├── test_voice_recognizer.py
└── test_text_simulator.py
```

#### 7.1.3 编写测试

**tests/test_config_manager.py**

```python
import pytest
from src.config_manager import ConfigManager

class TestConfigManager:
    """配置管理器测试"""
    
    def setup_method(self):
        """每个测试方法前执行"""
        self.config_mgr = ConfigManager()
    
    def teardown_method(self):
        """每个测试方法后执行"""
        pass
    
    def test_load_config(self):
        """测试加载配置"""
        self.config_mgr.load_config()
        assert self.config_mgr.config is not None
    
    def test_get_config_value(self):
        """测试获取配置值"""
        value = self.config_mgr.get('general.log_level', 'INFO')
        assert value in ['DEBUG', 'INFO', 'WARNING', 'ERROR']
    
    def test_set_config_value(self):
        """测试设置配置值"""
        self.config_mgr.set('general.log_level', 'DEBUG')
        value = self.config_mgr.get('general.log_level')
        assert value == 'DEBUG'
    
    def test_validate_api_key(self):
        """测试API密钥验证"""
        self.config_mgr.set('api.dashscope_api_key', 'sk-test123')
        assert self.config_mgr.validate_api_key()
        
        self.config_mgr.set('api.dashscope_api_key', '')
        assert not self.config_mgr.validate_api_key()
```

#### 7.1.4 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_config_manager.py

# 运行特定测试函数
pytest tests/test_config_manager.py::TestConfigManager::test_load_config

# 显示详细输出
pytest -v

# 生成代码覆盖率报告
pytest --cov=src --cov-report=html
```

### 7.2 集成测试

**tests/test_integration.py**

```python
import pytest
from src.main import AutoVoiceTypeApp
from PyQt5.QtWidgets import QApplication

class TestIntegration:
    """集成测试"""
    
    def test_app_initialization(self):
        """测试应用初始化"""
        app = QApplication([])
        auto_voice_app = AutoVoiceTypeApp(app)
        
        # 测试初始化（需要有效的API密钥）
        # result = auto_voice_app.initialize()
        # assert result is True
        
    def test_hotkey_to_recognition_flow(self):
        """测试从快捷键到识别的完整流程"""
        # TODO: 实现集成测试
        pass
```

### 7.3 手动测试清单

在发布前，进行以下手动测试：

#### 7.3.1 功能测试

- [ ] 应用启动正常
- [ ] 托盘图标显示
- [ ] 首次运行向导显示（新安装）
- [ ] API密钥配置成功
- [ ] 右Ctrl键触发录音
- [ ] 录音动画显示
- [ ] 识别结果正确
- [ ] 文本自动输入
- [ ] 设置窗口打开
- [ ] 各配置项可修改
- [ ] 配置保存成功
- [ ] 开机自启动设置
- [ ] 退出应用正常

#### 7.3.2 兼容性测试

测试应用在以下环境中：

| 应用程序 | 输入成功 | 备注 |
|---------|---------|------|
| 记事本 | ✅ |  |
| Word | ✅ |  |
| Chrome | ✅ |  |
| Edge | ✅ |  |
| Firefox | ✅ |  |
| 微信 | ✅ |  |
| QQ | ✅ |  |
| VS Code | ✅ |  |
| PyCharm | ✅ |  |

#### 7.3.3 性能测试

- [ ] 启动时间 <3秒
- [ ] 内存占用 <150MB
- [ ] 待机CPU占用 <2%
- [ ] 录音CPU占用 <25%
- [ ] 识别延迟 <500ms
- [ ] 连续使用1小时无异常

#### 7.3.4 异常测试

- [ ] 网络断开时的表现
- [ ] API密钥错误时的提示
- [ ] 麦克风不可用时的提示
- [ ] 配置文件损坏时的处理
- [ ] 磁盘空间不足时的处理

---

## 8. 构建和部署

### 8.1 使用 PyInstaller 打包

#### 8.1.1 安装 PyInstaller

```bash
pip install pyinstaller
```

#### 8.1.2 运行构建脚本

```bash
# Windows
build.bat

# 或手动执行
pyinstaller AutoVoiceType.spec
```

#### 8.1.3 验证构建结果

```bash
# 检查输出目录
dir dist\AutoVoiceType

# 测试可执行文件
cd dist\AutoVoiceType
AutoVoiceType.exe
```

### 8.2 创建安装程序

#### 8.2.1 安装 Inno Setup

下载并安装 Inno Setup 6：
https://jrsoftware.org/isdl.php

#### 8.2.2 运行安装程序构建脚本

```bash
build_installer.bat
```

#### 8.2.3 测试安装程序

```bash
# 安装程序位于
dist\installer\AutoVoiceType_Setup_1.0.0.exe

# 测试安装
# 1. 双击运行安装程序
# 2. 完成安装
# 3. 运行安装的应用
# 4. 测试卸载功能
```

### 8.3 版本发布流程

1. **更新版本号**
   - 编辑 `src/version.py`
   - 更新 `__version__`
   - 更新 `VERSION_HISTORY`

2. **更新文档**
   - 更新 `docs/CHANGELOG.md`
   - 更新 `README.md`
   - 更新 `docs/USER_MANUAL.md`（如有变化）

3. **测试**
   - 运行单元测试：`pytest`
   - 执行手动测试清单
   - 性能测试

4. **构建**
   - 清理旧的构建文件
   - 运行 `build.bat`
   - 验证构建结果

5. **创建安装程序**
   - 运行 `build_installer.bat`
   - 测试安装和卸载

6. **Git 操作**
   ```bash
   git add .
   git commit -m "Release v1.0.0"
   git tag v1.0.0
   git push origin main --tags
   ```

7. **发布**
   - 在 GitHub 创建 Release
   - 上传安装程序
   - 上传便携版压缩包
   - 编写 Release Notes

### 8.4 持续集成（CI/CD）

#### GitHub Actions 配置示例

**.github/workflows/build.yml**

```yaml
name: Build and Test

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: windows-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.8
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run tests
      run: pytest --cov=src
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2

  build:
    needs: test
    runs-on: windows-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.8
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pyinstaller
    
    - name: Build executable
      run: build.bat
    
    - name: Upload artifact
      uses: actions/upload-artifact@v2
      with:
        name: AutoVoiceType
        path: dist/AutoVoiceType/
```

---

## 9. API参考

详细的 API 文档请参考各模块的文档字符串。

### 9.1 ConfigManager API

```python
class ConfigManager:
    def __init__(self) -> None
    def load_config(self) -> None
    def save_config(self) -> bool
    def get(self, key_path: str, default=None) -> Any
    def set(self, key_path: str, value: Any) -> None
    def validate_api_key(self) -> bool
    def is_first_run(self) -> bool
    def get_api_key(self) -> str
    def get_audio_config(self) -> dict
    def get_input_config(self) -> dict
    def get_log_level(self) -> str
```

### 9.2 HotkeyManager API

```python
class HotkeyManager:
    def __init__(self) -> None
    def set_callbacks(
        self, 
        on_press: Optional[Callable] = None,
        on_release: Optional[Callable] = None
    ) -> None
    def is_right_ctrl(self, key) -> bool
    def start_listening(self) -> bool
    def stop_listening(self) -> bool
    def is_key_currently_pressed(self) -> bool
```

### 9.3 VoiceRecognizer API

```python
class VoiceRecognizer:
    def __init__(
        self, 
        api_key: str, 
        audio_config: dict, 
        api_config: dict
    ) -> None
    def set_result_callback(self, callback: Callable[[str], None]) -> None
    def start_recording(self) -> bool
    def stop_recording(self) -> bool
    def is_currently_recording(self) -> bool
```

### 9.4 TextSimulator API

```python
class TextSimulator:
    def __init__(self, config: Optional[dict] = None) -> None
    def input_text(self, text: str) -> bool
    def get_active_window_info(self) -> Optional[dict]
    def set_input_method(self, method: InputMethod) -> None
    def test_input_methods(self) -> dict
```

---

## 10. 贡献指南

### 10.1 如何贡献

我们欢迎任何形式的贡献！

1. **报告Bug**
   - 在 GitHub Issues 中创建新问题
   - 描述问题的详细步骤
   - 附加日志文件和截图

2. **提出功能建议**
   - 在 GitHub Issues 中创建功能请求
   - 说明功能的用途和价值
   - 如有可能，提供实现思路

3. **提交代码**
   - Fork 项目仓库
   - 创建功能分支：`git checkout -b feature/your-feature`
   - 编写代码和测试
   - 提交：`git commit -m "Add your feature"`
   - 推送：`git push origin feature/your-feature`
   - 创建 Pull Request

### 10.2 代码审查流程

1. 创建 Pull Request
2. 自动运行 CI/CD测试
3. 代码审查（Code Review）
4. 修改反馈的问题
5. 合并到主分支

### 10.3 分支管理策略

使用 Git Flow 工作流：

```
main         # 主分支，稳定版本
  └─ develop     # 开发分支
      ├─ feature/xxx  # 功能分支
      ├─ bugfix/xxx   # Bug修复分支
      └─ release/xxx  # 发布分支
```

### 10.4 提交信息规范

使用约定式提交（Conventional Commits）：

```
feat: 添加新功能
fix: 修复Bug
docs: 文档更新
style: 代码格式调整
refactor: 代码重构
test: 测试相关
chore: 构建/工具相关
```

**示例：**

```bash
git commit -m "feat: 添加自定义快捷键功能"
git commit -m "fix: 修复剪贴板恢复失败的问题"
git commit -m "docs: 更新用户手册中的FAQ部分"
```

---

## 📚 附录

### A. 常用命令

```bash
# 开发
python src/main.py                    # 运行应用
python check_environment.py           # 检查环境

# 测试
pytest                                # 运行测试
pytest --cov=src --cov-report=html    # 测试+覆盖率

# 代码质量
pylint src/                           # 代码检查
autopep8 --in-place --aggressive src/ # 代码格式化
mypy src/                             # 类型检查

# 构建
build.bat                             # 构建应用
build_installer.bat                   # 构建安装程序
```

### B. 相关资源

- **Python 官方文档：** https://docs.python.org/3/
- **PyQt5 文档：** https://www.riverbankcomputing.com/static/Docs/PyQt5/
- **DashScope 文档：** https://help.aliyun.com/zh/dashscope/
- **pynput 文档：** https://pynput.readthedocs.io/
- **PyInstaller 文档：** https://pyinstaller.readthedocs.io/

### C. 联系方式

- **GitHub：** https://github.com/yourusername/AutoVoiceType
- **Email：** dev@autovoicetype.com
- **Issues：** https://github.com/yourusername/AutoVoiceType/issues

---

**文档版本：** 1.0  
**最后更新：** 2025-12-28  
**维护者：** AutoVoiceType Team

---

**感谢您的贡献！** 🎉

