# AutoVoiceType - 安装指南

## 系统要求

- **操作系统**: Windows 10 / Windows 11
- **Python**: 3.8 或更高版本
- **网络**: 需要连接到互联网（用于调用语音识别API）
- **硬件**: 麦克风设备

## 安装步骤

### 步骤 1: 克隆或下载项目

```bash
git clone <repository-url>
cd AutoVoiceType
```

或者直接下载项目压缩包并解压。

### 步骤 2: 安装 Python 依赖

#### 方案 A: 一键安装（推荐）

```bash
pip install -r requirements.txt
```

#### 方案 B: 手动安装（如果方案A失败）

**特别注意 PyAudio 的安装：**

Windows 用户可能需要手动安装 PyAudio：

1. 访问：https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
2. 下载对应的 wheel 文件：
   - Python 3.8 64位: `PyAudio‑0.2.11‑cp38‑cp38‑win_amd64.whl`
   - Python 3.9 64位: `PyAudio‑0.2.11‑cp39‑cp39‑win_amd64.whl`
   - Python 3.10 64位: `PyAudio‑0.2.11‑cp310‑cp310‑win_amd64.whl`
   - Python 3.11 64位: `PyAudio‑0.2.11‑cp311‑cp311‑win_amd64.whl`
3. 安装下载的文件：
   ```bash
   pip install PyAudio‑0.2.11‑cp3xx‑cp3xx‑win_amd64.whl
   ```
4. 安装其他依赖：
   ```bash
   pip install PyQt5>=5.15.0
   pip install pynput>=1.7.6
   pip install websocket-client>=1.3.0
   pip install dashscope>=1.10.0
   pip install pyperclip>=1.8.2
   pip install pyautogui>=0.9.53
   pip install pywin32>=305
   ```

### 步骤 3: 配置 API 密钥

#### 3.1 获取阿里云 DashScope API 密钥

1. 访问：https://help.aliyun.com/zh/model-studio/get-api-key
2. 注册或登录阿里云账号
3. 开通 DashScope 服务（免费额度通常够测试使用）
4. 获取 API Key（格式类似：sk-xxxxxxxxxxxxxxxx）

#### 3.2 配置 API 密钥

**方式 1: 通过配置文件（推荐）**

首次运行程序后，配置文件会自动创建在：

```
Windows: C:\Users\<用户名>\.autovoicetype\config.json
```

编辑该文件，将 API 密钥填入：

```json
{
    "api": {
        "dashscope_api_key": "sk-your-actual-api-key-here"
    }
}
```

**方式 2: 通过环境变量**

设置环境变量（可选）：

```bash
# PowerShell
$env:DASHSCOPE_API_KEY="sk-your-api-key"

# CMD
set DASHSCOPE_API_KEY=sk-your-api-key
```

### 步骤 4: 运行程序

```bash
cd src
python main.py
```

成功启动后，你会看到：

```
============================================================
🚀 AutoVoiceType 已启动
============================================================
📌 按住【右Ctrl键】开始语音输入
📌 释放【右Ctrl键】结束输入
📌 按【Ctrl+C】退出程序
============================================================
```

### 步骤 5: 测试功能

1. **按住右Ctrl键**
2. 对着麦克风说话（例如："你好，这是一个测试"）
3. **释放右Ctrl键**
4. 在控制台查看识别结果

## 故障排除

### 问题 1: 找不到 PyAudio 模块

**错误信息:**
```
ModuleNotFoundError: No module named 'pyaudio'
```

**解决方案:**
- 参考上面的"步骤 2 - 方案 B"手动安装 PyAudio wheel 文件

### 问题 2: API 连接失败

**错误信息:**
```
语音识别错误 - 错误信息: Invalid API Key
```

**解决方案:**
- 检查 API 密钥是否正确配置
- 检查 config.json 文件中的 `dashscope_api_key` 字段
- 确认 API 密钥有效且未过期

### 问题 3: 麦克风无法使用

**错误信息:**
```
打开音频流失败
```

**解决方案:**
1. 检查麦克风是否正确连接
2. 在 Windows 设置中检查麦克风权限：
   - 设置 → 隐私 → 麦克风 → 允许应用访问麦克风
3. 测试麦克风是否在其他应用中正常工作

### 问题 4: 快捷键无响应

**可能原因:**
- 程序需要管理员权限
- 其他程序占用了右Ctrl键

**解决方案:**
- 右键点击 PowerShell/CMD，选择"以管理员身份运行"
- 关闭可能冲突的快捷键程序
- 检查日志文件：`~\.autovoicetype\logs\`

### 问题 5: 识别结果为空

**可能原因:**
- 网络连接问题
- 音频质量太差
- 说话声音太小

**解决方案:**
- 检查网络连接
- 靠近麦克风清晰说话
- 检查日志文件中的错误信息

## 日志文件位置

程序运行时会自动记录日志：

```
Windows: C:\Users\<用户名>\.autovoicetype\logs\autovoicetype_YYYYMMDD.log
```

如果遇到问题，请查看日志文件以获取详细的错误信息。

## 配置文件位置

```
Windows: C:\Users\<用户名>\.autovoicetype\config.json
```

## 卸载

如需卸载程序：

1. 删除项目文件夹
2. （可选）删除配置和日志文件夹：
   ```
   C:\Users\<用户名>\.autovoicetype\
   ```

## 下一步

程序运行正常后，可以：

1. 查看完整的用户手册（待编写）
2. 自定义配置项（编辑 config.json）
3. 等待后续任务完成，获得完整的 UI 界面和自动输入功能

## 获取帮助

- 查看项目文档：`docs/PROJECT_PLAN.md`
- 查看日志文件：`~\.autovoicetype\logs\`
- 提交问题报告（待提供仓库地址）

---

**文档版本**: v1.0  
**更新日期**: 2025-12-28

