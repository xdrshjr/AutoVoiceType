"""
系统托盘应用模块
提供系统托盘图标、菜单和应用控制功能
"""
import logging
import sys
from pathlib import Path
from typing import Optional, Callable

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt5.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QAction,
    QMessageBox
)

logger = logging.getLogger(__name__)


class TrayApp(QObject):
    """系统托盘应用类"""
    
    # 信号定义
    settings_requested = pyqtSignal()  # 打开设置信号
    quit_requested = pyqtSignal()      # 退出应用信号
    
    def __init__(self, app: QApplication):
        """
        初始化系统托盘应用
        
        Args:
            app: Qt应用实例
        """
        super().__init__()
        
        self.app = app
        self.tray_icon: Optional[QSystemTrayIcon] = None
        self.menu: Optional[QMenu] = None
        
        # 回调函数
        self._on_settings_callback: Optional[Callable] = None
        self._on_quit_callback: Optional[Callable] = None
        
        logger.info("初始化系统托盘应用")
        
        # 检查系统托盘支持
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.error("系统不支持系统托盘")
            QMessageBox.critical(
                None,
                "系统托盘不可用",
                "您的系统不支持系统托盘功能，程序将退出。"
            )
            sys.exit(1)
        
        # 初始化托盘图标
        self._init_tray_icon()
        
        logger.info("系统托盘应用初始化完成")
    
    def _init_tray_icon(self) -> None:
        """初始化托盘图标和菜单"""
        # 创建托盘图标
        self.tray_icon = QSystemTrayIcon(self.app)
        
        # 设置图标
        icon = self._create_default_icon()
        self.tray_icon.setIcon(icon)
        
        # 设置提示文本
        self.tray_icon.setToolTip("AutoVoiceType - 智能语音输入法")
        
        # 创建右键菜单
        self._create_context_menu()
        
        # 连接信号
        self.tray_icon.activated.connect(self._on_tray_icon_activated)
        
        logger.debug("托盘图标初始化完成")
    
    def _create_default_icon(self) -> QIcon:
        """
        创建默认图标
        如果没有图标文件，则生成一个简单的默认图标
        
        Returns:
            QIcon: 图标对象
        """
        # 尝试加载图标文件
        icon_paths = [
            Path(__file__).parent.parent.parent / "assets" / "icon.ico",
            Path(__file__).parent.parent.parent / "assets" / "icon.png",
        ]
        
        for icon_path in icon_paths:
            if icon_path.exists():
                logger.info(f"加载图标文件: {icon_path}")
                return QIcon(str(icon_path))
        
        # 如果没有图标文件，生成默认图标
        logger.warning("未找到图标文件，使用默认生成的图标")
        return self._generate_default_icon()
    
    def _generate_default_icon(self) -> QIcon:
        """
        生成默认图标（简单的圆形麦克风图标）
        
        Returns:
            QIcon: 生成的图标
        """
        # 创建32x32的像素图
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(0, 0, 0, 0))  # 透明背景
        
        # 绘制图标
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制圆形背景
        painter.setPen(QColor(52, 168, 83))  # 绿色边框
        painter.setBrush(QColor(52, 168, 83))
        painter.drawEllipse(2, 2, 28, 28)
        
        # 绘制麦克风符号（简化的M字母）
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(painter.font())
        font = painter.font()
        font.setPixelSize(20)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), 0x84, "M")  # AlignCenter | AlignVCenter
        
        painter.end()
        
        logger.debug("已生成默认图标")
        return QIcon(pixmap)
    
    def _create_context_menu(self) -> None:
        """创建右键菜单"""
        self.menu = QMenu()
        
        # 设置菜单
        settings_action = QAction("⚙️ 设置", self.menu)
        settings_action.triggered.connect(self._on_settings_clicked)
        self.menu.addAction(settings_action)
        
        # 分隔线
        self.menu.addSeparator()
        
        # 关于
        about_action = QAction("ℹ️ 关于", self.menu)
        about_action.triggered.connect(self._show_about_dialog)
        self.menu.addAction(about_action)
        
        # 分隔线
        self.menu.addSeparator()
        
        # 退出
        quit_action = QAction("❌ 退出", self.menu)
        quit_action.triggered.connect(self._on_quit_clicked)
        self.menu.addAction(quit_action)
        
        # 设置菜单到托盘图标
        self.tray_icon.setContextMenu(self.menu)
        
        logger.debug("右键菜单创建完成")
    
    def _on_tray_icon_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """
        托盘图标激活事件处理
        
        Args:
            reason: 激活原因
        """
        if reason == QSystemTrayIcon.DoubleClick:
            logger.info("托盘图标双击 - 打开设置")
            self._on_settings_clicked()
        elif reason == QSystemTrayIcon.Trigger:
            logger.debug("托盘图标单击")
        elif reason == QSystemTrayIcon.Context:
            logger.debug("托盘图标右键")
    
    def _on_settings_clicked(self) -> None:
        """设置菜单点击处理"""
        logger.info("设置菜单被点击")
        
        # 发射信号
        self.settings_requested.emit()
        
        # 调用回调
        if self._on_settings_callback:
            try:
                self._on_settings_callback()
            except Exception as e:
                logger.error(f"设置回调执行失败: {e}", exc_info=True)
    
    def _on_quit_clicked(self) -> None:
        """退出菜单点击处理"""
        logger.info("退出菜单被点击")
        
        # 确认对话框
        reply = QMessageBox.question(
            None,
            "确认退出",
            "确定要退出 AutoVoiceType 吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            logger.info("用户确认退出")
            
            # 发射信号
            self.quit_requested.emit()
            
            # 调用回调
            if self._on_quit_callback:
                try:
                    self._on_quit_callback()
                except Exception as e:
                    logger.error(f"退出回调执行失败: {e}", exc_info=True)
            
            # 隐藏托盘图标
            if self.tray_icon:
                self.tray_icon.hide()
            
            # 退出应用
            QApplication.quit()
        else:
            logger.debug("用户取消退出")
    
    def _show_about_dialog(self) -> None:
        """显示关于对话框"""
        logger.info("显示关于对话框")
        
        about_text = """
        <h2>AutoVoiceType</h2>
        <p><b>版本:</b> 1.0.0</p>
        <p><b>描述:</b> 智能语音输入法</p>
        <br>
        <p>一款专为Windows平台设计的轻量级语音输入工具，<br>
        通过全局快捷键实现"按住即说"的无缝语音输入体验。</p>
        <br>
        <p><b>使用方法:</b></p>
        <ul>
        <li>按住【右Ctrl键】开始语音输入</li>
        <li>释放【右Ctrl键】结束输入</li>
        <li>识别结果将自动输入到当前窗口</li>
        </ul>
        <br>
        <p>© 2025 AutoVoiceType. All rights reserved.</p>
        """
        
        msg_box = QMessageBox()
        msg_box.setWindowTitle("关于 AutoVoiceType")
        msg_box.setTextFormat(1)  # RichText
        msg_box.setText(about_text)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()
        
        logger.debug("关于对话框已关闭")
    
    def show(self) -> None:
        """显示托盘图标"""
        if self.tray_icon:
            self.tray_icon.show()
            logger.info("托盘图标已显示")
    
    def hide(self) -> None:
        """隐藏托盘图标"""
        if self.tray_icon:
            self.tray_icon.hide()
            logger.info("托盘图标已隐藏")
    
    def show_message(
        self,
        title: str,
        message: str,
        icon: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.Information,
        timeout: int = 3000
    ) -> None:
        """
        显示气泡通知
        
        Args:
            title: 通知标题
            message: 通知内容
            icon: 图标类型
            timeout: 显示时长（毫秒）
        """
        if self.tray_icon:
            self.tray_icon.showMessage(title, message, icon, timeout)
            logger.info(f"显示气泡通知: {title} - {message}")
    
    def set_tooltip(self, tooltip: str) -> None:
        """
        设置托盘图标提示文本
        
        Args:
            tooltip: 提示文本
        """
        if self.tray_icon:
            self.tray_icon.setToolTip(tooltip)
            logger.debug(f"托盘图标提示文本已更新: {tooltip}")
    
    def set_icon(self, icon: QIcon) -> None:
        """
        设置托盘图标
        
        Args:
            icon: 图标对象
        """
        if self.tray_icon:
            self.tray_icon.setIcon(icon)
            logger.debug("托盘图标已更新")
    
    def set_callbacks(
        self,
        on_settings: Optional[Callable] = None,
        on_quit: Optional[Callable] = None
    ) -> None:
        """
        设置回调函数
        
        Args:
            on_settings: 设置回调
            on_quit: 退出回调
        """
        self._on_settings_callback = on_settings
        self._on_quit_callback = on_quit
        logger.debug("回调函数已设置")
    
    def cleanup(self) -> None:
        """清理资源"""
        logger.info("清理系统托盘资源")
        
        if self.tray_icon:
            self.tray_icon.hide()
            self.tray_icon = None
        
        if self.menu:
            self.menu.clear()
            self.menu = None
        
        logger.debug("系统托盘资源清理完成")

