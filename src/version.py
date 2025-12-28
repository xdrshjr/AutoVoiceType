"""
版本信息模块
集中管理应用程序的版本信息
"""
import datetime

# 版本号
__version__ = "1.0.0"

# 应用信息
APP_NAME = "AutoVoiceType"
APP_NAME_ZH = "智能语音输入法"
APP_DESCRIPTION = "一款专为Windows平台设计的智能语音输入工具"
APP_AUTHOR = "AutoVoiceType Team"
APP_COPYRIGHT = f"Copyright © 2025 {APP_AUTHOR}. All rights reserved."
APP_URL = "https://github.com/yourusername/AutoVoiceType"

# 构建信息
BUILD_DATE = datetime.datetime.now().strftime("%Y-%m-%d")
BUILD_YEAR = datetime.datetime.now().year

# 版本历史
VERSION_HISTORY = {
    "1.0.0": {
        "date": "2025-12-28",
        "changes": [
            "✅ 全局快捷键监听（右Ctrl键）",
            "✅ 实时语音识别（阿里云DashScope API）",
            "✅ 自动文本输入（三级降级策略）",
            "✅ 系统托盘应用",
            "✅ 录音动画提示",
            "✅ 配置管理界面",
            "✅ 首次运行向导",
            "✅ 开机自启动支持",
        ]
    }
}

def get_version_string() -> str:
    """
    获取完整的版本字符串
    
    Returns:
        str: 版本字符串，如 "AutoVoiceType v1.0.0"
    """
    return f"{APP_NAME} v{__version__}"

def get_full_info() -> str:
    """
    获取完整的应用信息
    
    Returns:
        str: 包含应用名称、版本、版权等信息的字符串
    """
    return (
        f"{APP_NAME} - {APP_NAME_ZH}\n"
        f"版本: {__version__}\n"
        f"构建日期: {BUILD_DATE}\n"
        f"{APP_COPYRIGHT}\n"
        f"网址: {APP_URL}"
    )

if __name__ == "__main__":
    print(get_full_info())

