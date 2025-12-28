"""
AutoVoiceType - 智能语音输入法
主程序入口
"""
import logging
import sys
import time
from pathlib import Path

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

from config_manager import ConfigManager
from hotkey_manager import HotkeyManager
from voice_recognizer import VoiceRecognizer
from text_simulator import TextSimulator
from ui import TrayApp, RecordingWidget, AutoStartManager, SettingsWindow

# 配置日志
def setup_logging(log_level: str = "INFO") -> None:
    """
    配置日志系统
    
    Args:
        log_level: 日志级别
    """
    # 创建日志目录
    log_dir = Path.home() / ".autovoicetype" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 日志文件路径
    log_file = log_dir / f"autovoicetype_{time.strftime('%Y%m%d')}.log"
    
    # 配置日志格式
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # 获取日志级别
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # 配置根日志记录器
    logging.basicConfig(
        level=numeric_level,
        format=log_format,
        datefmt=date_format,
        handlers=[
            # 文件处理器
            logging.FileHandler(log_file, encoding='utf-8'),
            # 控制台处理器
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"日志系统已初始化，日志级别: {log_level}")
    logger.info(f"日志文件路径: {log_file}")


class AutoVoiceTypeApp:
    """AutoVoiceType应用主类"""
    
    def __init__(self, qt_app: QApplication):
        """
        初始化应用
        
        Args:
            qt_app: Qt应用实例
        """
        self.qt_app = qt_app
        self.config_manager: ConfigManager = None
        self.hotkey_manager: HotkeyManager = None
        self.voice_recognizer: VoiceRecognizer = None
        self.text_simulator: TextSimulator = None
        self.tray_app: TrayApp = None
        self.recording_widget: RecordingWidget = None
        self.auto_start_manager: AutoStartManager = None
        self.settings_window: SettingsWindow = None
        self.logger = logging.getLogger(__name__)
        
        self.logger.info("=" * 60)
        self.logger.info("AutoVoiceType 应用启动")
        self.logger.info("=" * 60)
    
    def initialize(self) -> bool:
        """
        初始化所有模块
        
        Returns:
            bool: 是否初始化成功
        """
        try:
            # 1. 初始化配置管理器
            self.logger.info("正在初始化配置管理器...")
            self.config_manager = ConfigManager()
            
            # 配置日志级别
            log_level = self.config_manager.get_log_level()
            logging.getLogger().setLevel(getattr(logging, log_level.upper(), logging.INFO))
            self.logger.info(f"日志级别已更新为: {log_level}")
            
            # 2. 检查是否首次运行
            if self.config_manager.is_first_run():
                self.logger.warning("检测到首次运行，将显示配置向导")
                
                # 初始化设置窗口（首次运行）
                self.settings_window = SettingsWindow(self.config_manager)
                
                # 显示首次运行向导
                wizard_accepted = self.settings_window.show_first_run_wizard()
                
                if wizard_accepted:
                    # 显示设置窗口让用户配置
                    self.settings_window.show()
                    self.logger.info("首次运行：已打开设置窗口")
                else:
                    self.logger.info("用户取消首次配置")
                    return False
                
                # 等待用户配置完成
                # 注意：此时配置可能还未完成，但窗口已打开
                # 用户需要手动配置并保存后，再次启动应用
                return False
            
            # 3. 验证API密钥
            if not self.config_manager.validate_api_key():
                self.logger.error("API密钥未配置或无效")
                return False
            
            # 4. 初始化语音识别器
            self.logger.info("正在初始化语音识别器...")
            api_key = self.config_manager.get_api_key()
            audio_config = self.config_manager.get_audio_config()
            api_config = {
                'base_websocket_url': self.config_manager.get('api.base_websocket_url'),
                'model': self.config_manager.get('api.model'),
                'semantic_punctuation_enabled': self.config_manager.get('recognition.semantic_punctuation_enabled')
            }
            
            self.voice_recognizer = VoiceRecognizer(
                api_key=api_key,
                audio_config=audio_config,
                api_config=api_config
            )
            
            # 设置识别结果回调
            self.voice_recognizer.set_result_callback(self.on_recognition_result)
            
            # 5. 初始化快捷键管理器
            self.logger.info("正在初始化快捷键管理器...")
            self.hotkey_manager = HotkeyManager()
            
            # 设置快捷键回调
            self.hotkey_manager.set_callbacks(
                on_press=self.on_hotkey_press,
                on_release=self.on_hotkey_release
            )
            
            # 6. 初始化文本输入模拟器
            self.logger.info("正在初始化文本输入模拟器...")
            input_config = self.config_manager.get_input_config()
            self.text_simulator = TextSimulator(config=input_config)
            
            # 测试输入方法可用性
            test_results = self.text_simulator.test_input_methods()
            self.logger.debug(f"输入方法测试结果: {test_results}")
            
            # 7. 初始化录音动画窗口
            self.logger.info("正在初始化录音动画窗口...")
            self.recording_widget = RecordingWidget()
            
            # 8. 初始化系统托盘
            self.logger.info("正在初始化系统托盘...")
            self.tray_app = TrayApp(self.qt_app)
            
            # 设置托盘回调
            self.tray_app.set_callbacks(
                on_settings=self.on_settings_requested,
                on_quit=self.on_quit_requested
            )
            
            # 显示托盘图标
            self.tray_app.show()
            
            # 9. 初始化设置窗口（但不显示）
            self.logger.info("正在初始化设置窗口...")
            self.settings_window = SettingsWindow(self.config_manager)
            self.settings_window.config_saved.connect(self._on_config_saved)
            
            # 10. 初始化自动启动管理器
            self.logger.info("正在初始化自动启动管理器...")
            self.auto_start_manager = AutoStartManager()
            
            # 检查自动启动配置
            auto_start_enabled = self.config_manager.get('general.auto_start', False)
            if auto_start_enabled:
                current_status = self.auto_start_manager.is_enabled()
                if not current_status:
                    self.logger.info("配置中启用了自动启动，正在设置...")
                    if self.auto_start_manager.enable():
                        self.logger.info("自动启动已成功设置")
                    else:
                        self.logger.warning("自动启动设置失败")
            
            self.logger.info("所有模块初始化完成")
            
            # 显示启动成功通知
            if self.tray_app:
                self.tray_app.show_message(
                    "启动成功",
                    "AutoVoiceType已就绪，按住右Ctrl键开始语音输入",
                    self.tray_app.tray_icon.Information
                )
            
            return True
        except Exception as e:
            self.logger.error(f"初始化失败: {e}", exc_info=True)
            return False
    
    def on_hotkey_press(self) -> None:
        """快捷键按下回调 - 开始录音"""
        self.logger.info(">>> 检测到右Ctrl键按下，开始录音...")
        
        # 显示录音动画
        if self.recording_widget:
            self.recording_widget.show_recording()
        
        # 启动录音
        if not self.voice_recognizer.start_recording():
            self.logger.error("启动录音失败")
            
            # 隐藏动画
            if self.recording_widget:
                self.recording_widget.hide_recording()
            
            # 显示错误通知
            if self.tray_app:
                self.tray_app.show_message(
                    "录音失败",
                    "无法启动录音，请检查麦克风设置",
                    self.tray_app.tray_icon.Warning
                )
    
    def on_hotkey_release(self) -> None:
        """快捷键释放回调 - 停止录音"""
        self.logger.info("<<< 检测到右Ctrl键释放，停止录音...")
        
        # 停止录音
        if not self.voice_recognizer.stop_recording():
            self.logger.error("停止录音失败")
            
            # 显示错误通知
            if self.tray_app:
                self.tray_app.show_message(
                    "停止录音失败",
                    "无法正常停止录音",
                    self.tray_app.tray_icon.Warning
                )
        
        # 隐藏录音动画
        if self.recording_widget:
            self.recording_widget.hide_recording()
    
    def on_recognition_result(self, text: str) -> None:
        """
        识别结果回调
        
        Args:
            text: 识别出的文本
        """
        self.logger.info(f"收到识别结果，文本长度: {len(text)} 字符")
        self.logger.debug(f"识别结果内容: {text}")
        
        # 检查文本长度
        max_length = self.config_manager.get('input.max_input_length', 10000)
        if len(text) > max_length:
            self.logger.warning(
                f"识别文本长度({len(text)})超过最大限制({max_length})，将被截断"
            )
            text = text[:max_length]
            self.logger.debug(f"截断后文本长度: {len(text)} 字符")
        
        # 自动输入到当前活动窗口
        if self.text_simulator:
            self.logger.info("开始自动输入文本到当前窗口...")
            
            # 获取活动窗口信息
            window_info = self.text_simulator.get_active_window_info()
            if window_info:
                window_title = window_info.get('title', 'Unknown')
                self.logger.info(f"目标窗口: {window_title}")
                self.logger.debug(f"窗口详细信息: {window_info}")
            
            # 执行输入
            success = self.text_simulator.input_text(text)
            
            if success:
                self.logger.info(f"文本输入成功，已输入 {len(text)} 字符到目标窗口")
                # 成功时不显示通知，仅记录日志
            else:
                self.logger.error("文本输入失败，无法将识别结果输入到当前窗口")
                
                # 显示失败通知
                if self.tray_app:
                    self.tray_app.show_message(
                        "输入失败",
                        "无法输入文本到当前窗口",
                        self.tray_app.tray_icon.Warning
                    )
        else:
            self.logger.warning("文本输入模拟器未初始化，无法输入识别结果")
    
    def on_settings_requested(self) -> None:
        """设置请求回调"""
        self.logger.info("设置功能被请求")
        
        # 显示设置窗口
        if self.settings_window:
            self.settings_window.show()
            self.settings_window.activateWindow()  # 激活窗口
            self.logger.info("设置窗口已打开")
        else:
            self.logger.error("设置窗口未初始化")
            if self.tray_app:
                self.tray_app.show_message(
                    "错误",
                    "设置窗口未正确初始化",
                    self.tray_app.tray_icon.Warning
                )
    
    def on_quit_requested(self) -> None:
        """退出请求回调"""
        self.logger.info("退出请求被触发")
        self.cleanup()
    
    def _on_config_saved(self) -> None:
        """配置保存后的回调"""
        self.logger.info("配置已保存，重新加载配置")
        
        # 重新加载配置
        self.config_manager.load_config()
        
        # 更新日志级别
        log_level = self.config_manager.get_log_level()
        logging.getLogger().setLevel(getattr(logging, log_level.upper(), logging.INFO))
        self.logger.info(f"日志级别已更新为: {log_level}")
        
        # 显示通知
        if self.tray_app:
            self.tray_app.show_message(
                "配置已更新",
                "新配置将在下次操作时生效",
                self.tray_app.tray_icon.Information
            )
    
    def run(self) -> None:
        """运行应用主循环"""
        try:
            # 启动快捷键监听
            if not self.hotkey_manager.start_listening():
                self.logger.error("启动快捷键监听失败")
                return
            
            self.logger.info("应用已就绪，等待快捷键触发...")
            print("\n" + "=" * 60)
            print("🚀 AutoVoiceType 已启动")
            print("=" * 60)
            print("📌 按住【右Ctrl键】开始语音输入")
            print("📌 释放【右Ctrl键】结束输入")
            print("📌 右键点击托盘图标可打开设置或退出")
            print("=" * 60 + "\n")
            
            # 使用Qt事件循环
            self.qt_app.exec_()
        except Exception as e:
            self.logger.error(f"应用运行时出错: {e}", exc_info=True)
        finally:
            self.cleanup()
    
    def cleanup(self) -> None:
        """清理资源"""
        self.logger.info("正在清理资源...")
        
        try:
            # 停止快捷键监听
            if self.hotkey_manager:
                self.hotkey_manager.stop_listening()
            
            # 停止录音（如果正在进行）
            if self.voice_recognizer and self.voice_recognizer.is_currently_recording():
                self.voice_recognizer.stop_recording()
            
            self.logger.info("资源清理完成")
        except Exception as e:
            self.logger.error(f"清理资源时出错: {e}", exc_info=True)
        
        self.logger.info("=" * 60)
        self.logger.info("AutoVoiceType 应用已退出")
        self.logger.info("=" * 60)


def main():
    """主函数"""
    # 设置日志（使用默认级别，后续会根据配置更新）
    setup_logging()
    
    # 创建Qt应用实例
    qt_app = QApplication(sys.argv)
    qt_app.setQuitOnLastWindowClosed(False)  # 关闭窗口不退出应用
    
    # 创建应用实例
    app = AutoVoiceTypeApp(qt_app)
    
    # 初始化
    if not app.initialize():
        print("\n⚠️ 应用初始化未完成")
        print(f"📁 配置文件位置: {Path.home() / '.autovoicetype' / 'config.json'}")
        print("\n请配置 DashScope API 密钥后重新启动应用")
        
        # 如果是首次运行，Qt事件循环已经在运行（设置窗口已打开）
        # 需要等待用户配置完成
        if app.config_manager.is_first_run() and app.settings_window:
            print("\n💡 设置窗口已打开，请配置后重新启动应用\n")
            qt_app.exec_()
        
        sys.exit(0)
    
    # 运行应用
    app.run()


if __name__ == "__main__":
    main()

