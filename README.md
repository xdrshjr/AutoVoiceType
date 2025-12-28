# AutoVoiceType - 智能语音输入法

## 项目简介

AutoVoiceType 是一款专为 Windows 平台设计的智能语音输入工具，通过全局快捷键实现"按住即说"的无缝语音输入体验。

## 当前进度

✅ **所有任务已完成** - AutoVoiceType v1.0.0 正式发布！

### 已实现功能

#### 核心功能
1. ✅ 全局快捷键监听（右Ctrl键）
2. ✅ 实时语音识别（阿里云DashScope API）
3. ✅ 自动文本输入（三级降级策略）
4. ✅ 系统托盘应用
5. ✅ 录音动画提示
6. ✅ 配置管理界面（macOS风格）
7. ✅ 首次运行向导
8. ✅ 开机自启动支持

#### 打包部署
1. ✅ PyInstaller 打包配置
2. ✅ Inno Setup 安装程序
3. ✅ 自动化构建脚本
4. ✅ 完整的文档体系

## 快速开始

### 方式 1: 使用快捷脚本（推荐）

**Windows 用户:**

1. 双击运行 `check_environment.bat` - 检查环境配置
2. 按照提示安装依赖和配置 API 密钥
3. 双击运行 `run.bat` - 启动程序

### 方式 2: 命令行

#### 1. 检查环境

```bash
python check_environment.py
```

这个脚本会自动检查：
- Python 版本
- 依赖包安装情况
- 配置文件状态
- 音频设备可用性

#### 2. 安装依赖

```bash
pip install -r requirements.txt
```

**注意：** 
- Windows 上安装 PyAudio 可能需要预编译的 wheel 文件
- 可以从 https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio 下载对应版本

#### 3. 配置 API 密钥

首次运行会自动创建配置文件：`~/.autovoicetype/config.json`

编辑配置文件，设置阿里云 DashScope API 密钥：

```json
{
    "api": {
        "dashscope_api_key": "sk-your-api-key-here"
    }
}
```

**获取 API 密钥：** https://help.aliyun.com/zh/model-studio/get-api-key

#### 4. 运行程序

```bash
cd src
python main.py
```

或直接双击 `run.bat`

### 使用方法

1. 运行程序后，它会在后台监听键盘事件
2. **按住右Ctrl键** - 开始录音和语音识别
3. **释放右Ctrl键** - 停止录音，识别结果会输出到控制台
4. **按 Ctrl+C** - 退出程序

## 项目结构

```
AutoVoiceType/
├── src/
│   ├── main.py                 # 主程序入口
│   ├── config_manager.py       # 配置管理模块
│   ├── hotkey_manager.py       # 快捷键监听模块
│   ├── voice_recognizer.py     # 语音识别模块
│   └── ui/                     # UI模块（待开发）
├── assets/                     # 资源文件（待开发）
├── config/
│   └── default_config.json     # 默认配置模板
├── docs/                       # 文档
├── tests/                      # 测试（待开发）
├── requirements.txt            # Python依赖
└── README.md                   # 本文件
```

## 日志文件

日志文件保存在：`~/.autovoicetype/logs/`

日志文件名格式：`autovoicetype_YYYYMMDD.log`

## 配置说明

### API 配置

- `dashscope_api_key`: 阿里云 DashScope API 密钥（必填）
- `base_websocket_url`: WebSocket API 地址
- `model`: 识别模型（默认：fun-asr-realtime）

### 音频配置

- `sample_rate`: 采样率（默认：16000Hz）
- `channels`: 声道数（默认：1，单声道）
- `chunk_size`: 音频块大小（默认：3200字节）
- `format`: 音频格式（默认：pcm）

### 快捷键配置

- `trigger_key`: 触发键（默认：ctrl_r，右Ctrl键）

### 通用配置

- `auto_start`: 开机自启动（待实现）
- `language`: 识别语言（默认：zh-CN）
- `log_level`: 日志级别（DEBUG/INFO/WARNING/ERROR）

## 完成的任务

- ✅ **任务1：** 项目基础架构搭建与核心模块开发
- ✅ **任务2：** 文本输入模拟与跨应用兼容性实现
- ✅ **任务3：** 系统托盘与基础UI实现
- ✅ **任务4：** 配置管理界面开发
- ✅ **任务5：** 集成测试、打包部署与文档编写

## 文档

### 用户文档
- 📘 **[用户手册](docs/USER_MANUAL.md)** - 详细的使用指南
- 📋 **[快速参考](docs/QUICK_REFERENCE.md)** - 常用操作快速查询
- 🔧 **[安装说明](docs/INSTALLATION.md)** - 安装步骤详解
- 📝 **[更新日志](docs/CHANGELOG.md)** - 版本更新记录

### 开发者文档
- 💻 **[开发者指南](docs/DEVELOPER.md)** - 架构设计和开发指南
- 🏗️ **[构建指南](docs/BUILD_GUIDE.md)** - 打包和部署说明
- 📋 **[项目计划](docs/PROJECT_PLAN.md)** - 项目设计方案
- ✅ **[任务清单](docs/TASK_LIST.md)** - 开发任务详解

## 技术栈

- **Python**: 3.8+
- **UI框架**: PyQt5（待实现）
- **全局快捷键**: pynput
- **音频采集**: PyAudio
- **语音识别**: 阿里云 DashScope API
- **网络通信**: websocket-client

## 常见问题

### 1. PyAudio 安装失败

**问题：** Windows 上直接 pip install 可能失败

**解决方案：**
- 下载预编译的 wheel 文件：https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
- 选择对应 Python 版本和架构的文件
- 使用 `pip install PyAudio‑xxx.whl` 安装

### 2. API 密钥配置

**问题：** 不知道如何获取 API 密钥

**解决方案：**
- 访问：https://help.aliyun.com/zh/model-studio/get-api-key
- 注册阿里云账号
- 开通 DashScope 服务
- 获取 API Key

### 3. 识别无结果

**问题：** 按下快捷键但没有识别结果

**解决方案：**
- 检查日志文件：`~/.autovoicetype/logs/`
- 确认 API 密钥配置正确
- 确认网络连接正常
- 检查麦克风权限

## 开发者信息

- **项目文档**: `docs/PROJECT_PLAN.md`
- **任务清单**: `docs/TASK_LIST.md`
- **参考代码**: `docs/example-code.py`

## 许可证

待定

---

**版本**: v1.0.0  
**更新日期**: 2025-12-28  
**状态**: ✅ 正式发布

