"""
录音动画悬浮窗模块
显示语音识别状态的可视化反馈
"""
import logging
from typing import Optional

from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QRect, pyqtProperty
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QPalette
from PyQt5.QtWidgets import QWidget, QApplication, QLabel, QVBoxLayout

logger = logging.getLogger(__name__)


class RecordingWidget(QWidget):
    """录音动画悬浮窗，显示在屏幕底部中央"""
    
    # 窗口尺寸
    WIDGET_WIDTH = 300
    WIDGET_HEIGHT = 80
    MARGIN_BOTTOM = 50  # 距离屏幕底部的距离
    
    # 动画参数
    PULSE_MIN_SCALE = 0.95
    PULSE_MAX_SCALE = 1.05
    PULSE_DURATION = 1000  # 毫秒
    
    # 样式参数
    BG_COLOR = QColor(40, 40, 40, 230)  # 半透明深色背景
    TEXT_COLOR = QColor(255, 255, 255)  # 白色文字
    ACCENT_COLOR = QColor(52, 168, 83)  # 绿色强调色
    BORDER_RADIUS = 12
    
    def __init__(self, parent: Optional[QWidget] = None):
        """
        初始化录音动画窗口
        
        Args:
            parent: 父窗口
        """
        super().__init__(parent)
        
        self._scale = 1.0  # 缩放因子，用于脉动动画
        self._pulse_animation: Optional[QPropertyAnimation] = None
        self._wave_offset = 0  # 波形偏移量
        self._wave_timer: Optional[QTimer] = None
        
        logger.info("初始化录音动画窗口")
        
        # 初始化UI
        self._init_ui()
        
        # 初始化动画
        self._init_animation()
        
        logger.debug("录音动画窗口初始化完成")
    
    def _init_ui(self) -> None:
        """初始化UI组件"""
        # 窗口属性
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |      # 窗口置顶
            Qt.FramelessWindowHint |       # 无边框
            Qt.Tool |                       # 工具窗口（不在任务栏显示）
            Qt.WindowTransparentForInput   # 透明输入（不捕获鼠标事件）
        )
        
        # 设置透明背景
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)  # 显示时不激活
        
        # 设置窗口大小
        self.setFixedSize(self.WIDGET_WIDTH, self.WIDGET_HEIGHT)
        
        # 创建布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建文本标签
        self.label = QLabel("🎤 正在聆听...")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet(f"""
            QLabel {{
                color: {self.TEXT_COLOR.name()};
                font-size: 16px;
                font-weight: bold;
                background: transparent;
                padding: 5px;
            }}
        """)
        
        layout.addWidget(self.label)
        
        logger.debug("UI组件初始化完成")
    
    def _init_animation(self) -> None:
        """初始化动画效果"""
        # 脉动动画
        self._pulse_animation = QPropertyAnimation(self, b"scale")
        self._pulse_animation.setDuration(self.PULSE_DURATION)
        self._pulse_animation.setStartValue(self.PULSE_MIN_SCALE)
        self._pulse_animation.setEndValue(self.PULSE_MAX_SCALE)
        self._pulse_animation.setLoopCount(-1)  # 无限循环
        
        # 使用EaseInOutQuad缓动函数实现平滑动画
        from PyQt5.QtCore import QEasingCurve
        self._pulse_animation.setEasingCurve(QEasingCurve.InOutQuad)
        
        # 波形动画定时器
        self._wave_timer = QTimer(self)
        self._wave_timer.timeout.connect(self._update_wave)
        self._wave_timer.setInterval(50)  # 50ms更新一次，约20fps
        
        logger.debug("动画效果初始化完成")
    
    def _update_wave(self) -> None:
        """更新波形偏移量"""
        self._wave_offset = (self._wave_offset + 1) % 360
        self.update()  # 触发重绘
    
    def _position_at_bottom_center(self) -> None:
        """将窗口定位到屏幕底部中央"""
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        
        x = (screen_geometry.width() - self.WIDGET_WIDTH) // 2
        y = screen_geometry.height() - self.WIDGET_HEIGHT - self.MARGIN_BOTTOM
        
        self.move(x, y)
        logger.debug(f"窗口定位到: ({x}, {y})")
    
    def show_recording(self) -> None:
        """显示录音动画"""
        logger.info("显示录音动画")
        
        # 定位窗口
        self._position_at_bottom_center()
        
        # 显示窗口
        self.show()
        
        # 启动动画
        if self._pulse_animation:
            self._pulse_animation.start()
        
        if self._wave_timer:
            self._wave_timer.start()
        
        logger.debug("录音动画已启动")
    
    def hide_recording(self) -> None:
        """隐藏录音动画"""
        logger.info("隐藏录音动画")
        
        # 停止动画
        if self._pulse_animation:
            self._pulse_animation.stop()
        
        if self._wave_timer:
            self._wave_timer.stop()
        
        # 隐藏窗口
        self.hide()
        
        # 重置状态
        self._scale = 1.0
        self._wave_offset = 0
        
        logger.debug("录音动画已停止")
    
    def paintEvent(self, event) -> None:
        """
        绘制窗口内容
        
        Args:
            event: 绘制事件
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)  # 抗锯齿
        
        # 计算缩放后的矩形
        rect = self.rect()
        center_x = rect.width() / 2
        center_y = rect.height() / 2
        
        scaled_width = rect.width() * self._scale
        scaled_height = rect.height() * self._scale
        
        scaled_rect = QRect(
            int(center_x - scaled_width / 2),
            int(center_y - scaled_height / 2),
            int(scaled_width),
            int(scaled_height)
        )
        
        # 绘制圆角矩形背景
        painter.setPen(Qt.NoPen)
        painter.setBrush(self.BG_COLOR)
        painter.drawRoundedRect(scaled_rect, self.BORDER_RADIUS, self.BORDER_RADIUS)
        
        # 绘制波形效果（在矩形顶部）
        self._draw_wave(painter, scaled_rect)
        
        # 父类绘制（文本标签）
        super().paintEvent(event)
    
    def _draw_wave(self, painter: QPainter, rect: QRect) -> None:
        """
        绘制波形效果
        
        Args:
            painter: 绘图对象
            rect: 绘制矩形
        """
        import math
        
        painter.setPen(QPen(self.ACCENT_COLOR, 2))
        
        # 波形参数
        wave_height = 8
        wave_length = 30
        num_waves = rect.width() // wave_length + 2
        
        # 绘制波形
        points = []
        for i in range(num_waves):
            x = rect.left() + i * wave_length
            # 使用正弦函数计算y坐标
            y_offset = wave_height * math.sin(math.radians(self._wave_offset + i * 30))
            y = rect.top() + 15 + y_offset
            points.append((x, y))
        
        # 绘制连续曲线
        if len(points) > 1:
            for i in range(len(points) - 1):
                x1, y1 = points[i]
                x2, y2 = points[i + 1]
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))
    
    @pyqtProperty(float)
    def scale(self) -> float:
        """
        获取缩放因子（用于动画）
        
        Returns:
            float: 缩放因子
        """
        return self._scale
    
    @scale.setter
    def scale(self, value: float) -> None:
        """
        设置缩放因子（用于动画）
        
        Args:
            value: 缩放因子
        """
        self._scale = value
        self.update()  # 触发重绘
    
    def closeEvent(self, event) -> None:
        """
        关闭事件处理
        
        Args:
            event: 关闭事件
        """
        logger.info("录音动画窗口关闭")
        
        # 停止动画
        if self._pulse_animation:
            self._pulse_animation.stop()
        
        if self._wave_timer:
            self._wave_timer.stop()
        
        event.accept()

