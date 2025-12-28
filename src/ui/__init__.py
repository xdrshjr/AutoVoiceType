"""
UI模块
包含系统托盘、录音动画界面、设置窗口和自动启动管理
"""

from .tray_app import TrayApp
from .recording_widget import RecordingWidget
from .auto_start import AutoStartManager
from .settings_window import SettingsWindow

__all__ = ['TrayApp', 'RecordingWidget', 'AutoStartManager', 'SettingsWindow']

