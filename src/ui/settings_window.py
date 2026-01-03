"""
设置窗口模块
提供用户友好的配置界面
"""
import logging
import sys
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QStackedWidget, QPushButton,
    QMessageBox, QListWidgetItem, QLabel, QDialog,
    QDialogButtonBox, QScrollArea, QFrame
)

from .settings_pages import (
    BasicSettingsPage,
    AudioSettingsPage,
    InputSettingsPage,
    AdvancedSettingsPage,
    AboutPage
)
from .icon_utils import get_app_icon, get_icon_path
from .windows_icon_utils import set_qt_window_icon_win32

logger = logging.getLogger(__name__)


class FirstRunWizard(QDialog):
    """首次运行向导"""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.setWindowTitle("欢迎使用 AutoVoiceType")
        self.setModal(True)
        self.setFixedSize(500, 300)
        
        # 设置窗口图标
        logger.debug("设置首次运行向导窗口图标")
        window_icon = get_app_icon()
        if not window_icon.isNull():
            self.setWindowIcon(window_icon)
            logger.debug("首次运行向导窗口图标设置成功")
        else:
            logger.warning("首次运行向导窗口图标设置失败")
        
        self._init_ui()
        
        logger.info("首次运行向导已打开")
    
    def showEvent(self, event) -> None:
        """
        窗口显示事件处理
        确保窗口图标在显示时被正确设置（包括Windows任务栏图标）
        
        Args:
            event: 显示事件
        """
        super().showEvent(event)
        
        # 在Windows上，使用Windows API强制设置任务栏图标
        if sys.platform == 'win32':
            icon_path = get_icon_path()
            if icon_path and icon_path.exists():
                logger.debug("尝试使用Windows API设置首次运行向导的任务栏图标")
                # 延迟一点时间，确保窗口已经完全显示
                QTimer.singleShot(100, lambda: set_qt_window_icon_win32(self, str(icon_path.resolve())))
    
    def _init_ui(self) -> None:
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # 欢迎标题
        title = QLabel("🎉 欢迎使用 AutoVoiceType")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #34a853;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 说明文字
        description = QLabel(
            "AutoVoiceType 是一款智能语音输入工具，\n"
            "通过按住【右Ctrl键】即可快速进行语音输入。\n\n"
            "使用前，您需要先配置 DashScope API 密钥。\n"
            "请点击下方按钮前往设置页面进行配置。"
        )
        description.setWordWrap(True)
        description.setStyleSheet("font-size: 13px; color: #555;")
        description.setAlignment(Qt.AlignCenter)
        layout.addWidget(description)
        
        # 链接
        link_label = QLabel(
            '获取API密钥: <a href="https://dashscope.aliyun.com">阿里云DashScope控制台</a>'
        )
        link_label.setOpenExternalLinks(True)
        link_label.setAlignment(Qt.AlignCenter)
        link_label.setStyleSheet("font-size: 12px; color: #888;")
        layout.addWidget(link_label)
        
        layout.addStretch()
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)


class SettingsWindow(QMainWindow):
    """设置窗口主类"""
    
    # 信号定义
    config_saved = pyqtSignal()  # 配置已保存
    
    def __init__(self, config_manager, parent: Optional[QWidget] = None):
        """
        初始化设置窗口
        
        Args:
            config_manager: 配置管理器实例
            parent: 父窗口
        """
        super().__init__(parent)
        
        self.config_manager = config_manager
        self.pages = {}
        self.pending_changes = {}  # 待保存的配置变更
        
        logger.info("初始化设置窗口")
        
        # 设置窗口属性
        self.setWindowTitle("AutoVoiceType - 设置")
        self.setMinimumSize(900, 600)
        self.resize(900, 600)
        
        # 设置窗口图标
        logger.info("设置设置窗口图标")
        window_icon = get_app_icon()
        if not window_icon.isNull():
            self.setWindowIcon(window_icon)
            logger.info("设置窗口图标设置成功")
            
            # 验证图标是否真的设置成功
            actual_icon = self.windowIcon()
            if actual_icon.isNull():
                logger.warning("警告：设置窗口图标设置后验证失败，可能未生效")
            else:
                available_sizes = actual_icon.availableSizes()
                if available_sizes:
                    logger.debug(f"设置窗口图标验证成功，可用尺寸: {[f'{s.width()}x{s.height()}' for s in available_sizes]}")
        else:
            logger.error("设置窗口图标设置失败，Windows任务栏可能显示默认图标")
        
        # 加载样式表
        self._load_stylesheet()
        
        # 初始化UI
        self._init_ui()
        
        # 加载配置
        self._load_all_config()
        
        logger.info("设置窗口初始化完成")
    
    def _load_stylesheet(self) -> None:
        """加载样式表"""
        logger.debug("开始加载样式表")
        
        # 确定资源文件路径
        # 在打包后的环境中，使用 sys._MEIPASS 获取临时解压目录
        # 在开发环境中，使用相对路径
        if getattr(sys, 'frozen', False):
            # 打包后的环境（exe）
            base_path = Path(sys._MEIPASS)
            qss_file = base_path / "assets" / "styles.qss"
            logger.debug(f"检测到打包环境，基础路径: {base_path}")
        else:
            # 开发环境（直接运行main.py）
            base_path = Path(__file__).parent.parent.parent
            qss_file = base_path / "assets" / "styles.qss"
            logger.debug(f"检测到开发环境，基础路径: {base_path}")
        
        logger.debug(f"样式表文件路径: {qss_file}")
        logger.debug(f"样式表文件是否存在: {qss_file.exists()}")
        
        if qss_file.exists():
            try:
                with open(qss_file, 'r', encoding='utf-8') as f:
                    stylesheet = f.read()
                    self.setStyleSheet(stylesheet)
                logger.info(f"样式表加载成功: {qss_file}")
                logger.debug(f"样式表内容长度: {len(stylesheet)} 字符")
            except Exception as e:
                logger.error(f"加载样式表失败: {e}", exc_info=True)
        else:
            logger.warning(f"样式表文件不存在: {qss_file}")
            # 尝试其他可能的路径
            alternative_paths = [
                Path(__file__).parent.parent.parent / "assets" / "styles.qss",
                Path.cwd() / "assets" / "styles.qss",
            ]
            if getattr(sys, 'frozen', False):
                # 打包环境：尝试 exe 所在目录
                exe_dir = Path(sys.executable).parent
                alternative_paths.append(exe_dir / "assets" / "styles.qss")
                alternative_paths.append(exe_dir / "_internal" / "assets" / "styles.qss")
            
            for alt_path in alternative_paths:
                logger.debug(f"尝试备用路径: {alt_path}")
                if alt_path.exists():
                    try:
                        with open(alt_path, 'r', encoding='utf-8') as f:
                            stylesheet = f.read()
                            self.setStyleSheet(stylesheet)
                        logger.info(f"样式表从备用路径加载成功: {alt_path}")
                        return
                    except Exception as e:
                        logger.warning(f"从备用路径加载样式表失败: {alt_path}, 错误: {e}")
            
            logger.error("所有样式表路径尝试均失败，界面将使用默认样式")
    
    def _init_ui(self) -> None:
        """初始化UI组件"""
        # 中央窗口
        central_widget = QWidget()
        central_widget.setObjectName("SettingsWindow")
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 左侧导航栏 (10%)
        self.sidebar = self._create_sidebar()
        main_layout.addWidget(self.sidebar, 1)
        
        # 右侧内容区 (90%)
        right_widget = QWidget()
        right_widget.setObjectName("ContentArea")
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(0)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建滚动区域包装页面容器
        scroll_area = QScrollArea()
        scroll_area.setObjectName("PageScrollArea")
        scroll_area.setWidgetResizable(True)  # 允许内容自适应大小
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # 禁用横向滚动
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)  # 需要时显示纵向滚动
        scroll_area.setFrameShape(QFrame.NoFrame)  # 无边框
        
        # 页面容器
        self.page_stack = QStackedWidget()
        self.page_stack.setObjectName("PageContainer")
        scroll_area.setWidget(self.page_stack)
        
        right_layout.addWidget(scroll_area, 1)
        
        # 底部按钮栏
        button_bar = self._create_button_bar()
        right_layout.addWidget(button_bar)
        
        logger.debug("滚动区域已创建并配置")
        
        main_layout.addWidget(right_widget, 9)
        
        # 创建所有页面
        self._create_pages()
        
        # 默认选中第一项（在页面创建完成后）
        self.nav_list.setCurrentRow(0)
        
        logger.debug("UI组件初始化完成")
    
    def _create_sidebar(self) -> QWidget:
        """创建左侧导航栏"""
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(140)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 导航列表
        self.nav_list = QListWidget()
        self.nav_list.setObjectName("SidebarList")
        self.nav_list.setSpacing(2)
        
        # 导航项
        nav_items = [
            ("⚙️  基础设置", "基础设置"),
            ("🎤  音频设置", "音频设置"),
            ("⌨️  输入设置", "输入设置"),
            ("🔧  高级设置", "高级设置"),
            ("ℹ️  关于", "关于")
        ]
        
        for display_text, page_name in nav_items:
            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, page_name)
            self.nav_list.addItem(item)
        
        # 连接信号
        self.nav_list.currentRowChanged.connect(self._on_nav_changed)
        
        layout.addWidget(self.nav_list)
        
        logger.debug("侧边栏创建完成")
        return sidebar
    
    def _create_button_bar(self) -> QWidget:
        """创建底部按钮栏"""
        button_bar = QWidget()
        button_bar.setStyleSheet("background-color: #f5f5f5; border-top: 1px solid #e0e0e0;")
        button_bar.setFixedHeight(60)
        
        layout = QHBoxLayout(button_bar)
        layout.setContentsMargins(20, 10, 20, 10)
        
        # 状态标签
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666;")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        # 取消按钮
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(80)
        cancel_btn.clicked.connect(self.close)
        layout.addWidget(cancel_btn)
        
        # 应用按钮
        apply_btn = QPushButton("应用")
        apply_btn.setFixedWidth(80)
        apply_btn.clicked.connect(self._apply_changes)
        layout.addWidget(apply_btn)
        
        # 保存按钮
        save_btn = QPushButton("保存")
        save_btn.setObjectName("PrimaryButton")
        save_btn.setFixedWidth(80)
        save_btn.clicked.connect(self._save_and_close)
        layout.addWidget(save_btn)
        
        logger.debug("按钮栏创建完成")
        return button_bar
    
    def _create_pages(self) -> None:
        """创建所有配置页面"""
        # 基础设置页
        basic_page = BasicSettingsPage()
        basic_page.config_changed.connect(self._on_config_changed)
        basic_page.api_validation_requested.connect(self._validate_api_key)
        self.pages["基础设置"] = basic_page
        self.page_stack.addWidget(basic_page)
        
        # 音频设置页
        audio_page = AudioSettingsPage()
        audio_page.config_changed.connect(self._on_config_changed)
        self.pages["音频设置"] = audio_page
        self.page_stack.addWidget(audio_page)
        
        # 输入设置页
        input_page = InputSettingsPage()
        input_page.config_changed.connect(self._on_config_changed)
        self.pages["输入设置"] = input_page
        self.page_stack.addWidget(input_page)
        
        # 高级设置页
        advanced_page = AdvancedSettingsPage()
        advanced_page.config_changed.connect(self._on_config_changed)
        self.pages["高级设置"] = advanced_page
        self.page_stack.addWidget(advanced_page)
        
        # 关于页
        about_page = AboutPage()
        self.pages["关于"] = about_page
        self.page_stack.addWidget(about_page)
        
        logger.info(f"创建了 {len(self.pages)} 个配置页面")
    
    def _on_nav_changed(self, index: int) -> None:
        """
        导航切换处理
        
        Args:
            index: 导航项索引
        """
        if index < 0:
            return
        
        # 检查 page_stack 是否已初始化
        if not hasattr(self, 'page_stack') or self.page_stack is None:
            return
        
        item = self.nav_list.item(index)
        if item is None:
            return
        
        page_name = item.data(Qt.UserRole)
        
        self.page_stack.setCurrentIndex(index)
        logger.debug(f"切换到页面: {page_name}")
    
    def _on_config_changed(self, key_path: str, value: object) -> None:
        """
        配置变更处理
        
        Args:
            key_path: 配置路径
            value: 配置值
        """
        # 处理特殊命令
        if key_path == "__reset__":
            self._reset_all_config()
            return
        
        # 记录待保存的变更
        self.pending_changes[key_path] = value
        
        # 根据配置项类型记录不同级别的日志
        if key_path == "api.model":
            logger.info(f"模型配置已变更: {value}")
        else:
            logger.debug(f"配置变更: {key_path} = {value}")
        
        # 更新状态标签
        self.status_label.setText(f"有 {len(self.pending_changes)} 项配置待保存")
    
    def _validate_api_key(self, api_key: str) -> None:
        """
        验证API密钥
        
        Args:
            api_key: API密钥
        """
        logger.info("开始验证API密钥")
        
        # 简单验证：检查格式
        if not api_key or len(api_key) < 10:
            QMessageBox.warning(
                self,
                "验证失败",
                "API密钥格式无效，请检查后重试"
            )
            logger.warning("API密钥格式无效")
            return
        
        # 实际应用中，这里应该调用API进行真实验证
        # 目前仅做格式检查
        
        QMessageBox.information(
            self,
            "验证成功",
            "API密钥格式正确！\n\n"
            "注意：实际可用性需要在使用时验证。"
        )
        logger.info("API密钥验证通过")
    
    def _apply_changes(self) -> None:
        """应用配置变更（不关闭窗口）"""
        if not self.pending_changes:
            QMessageBox.information(self, "提示", "没有需要保存的配置")
            return
        
        changes_count = len(self.pending_changes)
        logger.info(f"应用 {changes_count} 项配置变更")
        
        # 应用所有变更到配置管理器
        for key_path, value in self.pending_changes.items():
            success = self.config_manager.set(key_path, value)
            if success:
                if key_path == "api.model":
                    logger.info(f"模型配置已保存: {value}")
                else:
                    logger.debug(f"配置项已保存: {key_path} = {value}")
            else:
                logger.error(f"保存配置项失败: {key_path} = {value}")
        
        # 保存配置文件
        if self.config_manager.save_config():
            self.status_label.setText("✓ 配置已保存")
            self.pending_changes.clear()
            
            # 发射信号
            self.config_saved.emit()
            
            # 2秒后清除状态文本
            QTimer.singleShot(2000, lambda: self.status_label.setText(""))
            
            logger.info(f"配置保存成功，共保存 {changes_count} 项配置")
            QMessageBox.information(self, "成功", "配置已保存并应用")
        else:
            logger.error("配置保存失败")
            QMessageBox.critical(self, "错误", "配置保存失败，请检查文件权限")
    
    def _save_and_close(self) -> None:
        """保存配置并关闭窗口"""
        if self.pending_changes:
            self._apply_changes()
        
        self.close()
    
    def _reset_all_config(self) -> None:
        """重置所有配置"""
        logger.warning("重置所有配置")
        
        # 使用默认配置
        self.config_manager.config = self.config_manager.DEFAULT_CONFIG.copy()
        
        # 保存配置
        if self.config_manager.save_config():
            # 重新加载到界面
            self._load_all_config()
            
            # 清除待保存变更
            self.pending_changes.clear()
            self.status_label.setText("✓ 配置已重置")
            
            QTimer.singleShot(2000, lambda: self.status_label.setText(""))
            
            logger.info("配置重置成功")
            QMessageBox.information(self, "成功", "所有配置已重置为默认值")
        else:
            logger.error("配置重置失败")
            QMessageBox.critical(self, "错误", "配置重置失败")
    
    def _load_all_config(self) -> None:
        """加载所有配置到页面"""
        logger.info("加载配置到所有页面")
        
        config = self.config_manager.config
        
        for page_name, page in self.pages.items():
            if hasattr(page, 'load_config'):
                page.load_config(config)
                logger.debug(f"配置已加载到页面: {page_name}")
    
    def show_first_run_wizard(self) -> bool:
        """
        显示首次运行向导
        
        Returns:
            bool: 用户是否确认继续
        """
        wizard = FirstRunWizard(self)
        result = wizard.exec_()
        
        return result == QDialog.Accepted
    
    def showEvent(self, event) -> None:
        """
        窗口显示事件处理
        确保窗口图标在显示时被正确设置
        
        Args:
            event: 显示事件
        """
        # 确保窗口图标已设置（Windows任务栏可能需要）
        if self.windowIcon().isNull():
            logger.warning("检测到窗口图标为空，尝试重新设置")
            window_icon = get_app_icon()
            if not window_icon.isNull():
                self.setWindowIcon(window_icon)
                logger.info("窗口图标已重新设置")
            else:
                logger.error("无法重新设置窗口图标，图标文件可能不存在或损坏")
        
        # 在Windows上，使用Windows API强制设置任务栏图标
        # 这可以确保任务栏显示正确的图标，即使exe文件本身没有图标
        if sys.platform == 'win32':
            icon_path = get_icon_path()
            if icon_path and icon_path.exists():
                logger.info("尝试使用Windows API设置任务栏图标")
                # 延迟一点时间，确保窗口已经完全显示
                QTimer.singleShot(100, lambda: self._set_win32_icon(str(icon_path.resolve())))
        
        super().showEvent(event)
    
    def _set_win32_icon(self, icon_path: str) -> None:
        """
        使用Windows API设置窗口图标
        
        Args:
            icon_path: 图标文件路径
        """
        try:
            success = set_qt_window_icon_win32(self, icon_path)
            if success:
                logger.info("Windows API图标设置成功")
            else:
                logger.debug("Windows API图标设置失败，将使用PyQt5默认图标")
        except Exception as e:
            logger.error(f"设置Windows API图标时发生异常: {e}", exc_info=True)
    
    def closeEvent(self, event) -> None:
        """
        关闭事件处理
        
        Args:
            event: 关闭事件
        """
        # 检查是否有未保存的变更
        if self.pending_changes:
            reply = QMessageBox.question(
                self,
                "确认关闭",
                "有未保存的配置变更，确定要关闭吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                event.ignore()
                return
        
        logger.info("设置窗口关闭")
        event.accept()

