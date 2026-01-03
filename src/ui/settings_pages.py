"""
配置页面模块
包含各个配置页面的实现
"""
import logging
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QComboBox,
    QCheckBox, QSpinBox, QDoubleSpinBox, QGroupBox,
    QTextEdit, QMessageBox, QScrollArea
)

logger = logging.getLogger(__name__)


class BasePage(QWidget):
    """配置页面基类"""
    
    # 配置变更信号
    config_changed = pyqtSignal(str, object)  # (key_path, value)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignTop)
        self.layout.setSpacing(20)
        self.layout.setContentsMargins(30, 30, 30, 30)
        
        logger.debug(f"初始化配置页面: {self.__class__.__name__}")
    
    def add_title(self, title: str, description: str = "") -> None:
        """
        添加页面标题和描述
        
        Args:
            title: 页面标题
            description: 页面描述
        """
        title_label = QLabel(title)
        title_label.setObjectName("PageTitle")
        self.layout.addWidget(title_label)
        
        if description:
            desc_label = QLabel(description)
            desc_label.setObjectName("PageDescription")
            desc_label.setWordWrap(True)
            self.layout.addWidget(desc_label)
    
    def create_group(self, title: str) -> QGroupBox:
        """
        创建一个配置组
        
        Args:
            title: 组标题
            
        Returns:
            QGroupBox: 组容器
        """
        group = QGroupBox(title)
        group_layout = QFormLayout()
        group_layout.setSpacing(15)
        group_layout.setContentsMargins(20, 25, 20, 20)
        group.setLayout(group_layout)
        
        self.layout.addWidget(group)
        return group
    
    def emit_config_change(self, key_path: str, value: object) -> None:
        """
        发射配置变更信号
        
        Args:
            key_path: 配置路径
            value: 配置值
        """
        logger.debug(f"配置变更: {key_path} = {value}")
        self.config_changed.emit(key_path, value)


class BasicSettingsPage(BasePage):
    """基础设置页面"""
    
    # API验证信号
    api_validation_requested = pyqtSignal(str)  # api_key
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.add_title("基础设置", "配置应用的基本参数和API密钥")

        # 提供商选择
        self._create_provider_section()

        # API设置
        self._create_api_section()

        # 通用设置
        self._create_general_section()

        logger.info("基础设置页面初始化完成")
    
    def _create_provider_section(self) -> None:
        """创建提供商选择区域"""
        group = self.create_group("语音识别提供商")
        form_layout = group.layout()

        # 提供商选择
        provider_label = QLabel("选择提供商:")
        provider_label.setObjectName("FieldLabel")

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["Alibaba DashScope", "ByteDance Doubao"])
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)

        form_layout.addRow(provider_label, self.provider_combo)

        # 提示文本
        self.provider_desc = QLabel("选择要使用的语音识别服务提供商")
        self.provider_desc.setObjectName("HelpLabel")
        self.provider_desc.setWordWrap(True)
        form_layout.addRow("", self.provider_desc)

    def _create_api_section(self) -> None:
        """创建API设置区域（支持多个提供商）"""
        # DashScope设置组
        self.dashscope_group = self.create_group("DashScope API 设置")
        dashscope_layout = self.dashscope_group.layout()

        # DashScope API密钥输入
        dashscope_key_label = QLabel("API 密钥:")
        dashscope_key_label.setObjectName("FieldLabel")

        dashscope_key_layout = QHBoxLayout()
        self.dashscope_api_key_input = QLineEdit()
        self.dashscope_api_key_input.setPlaceholderText("请输入DashScope API密钥")
        self.dashscope_api_key_input.setEchoMode(QLineEdit.Password)
        self.dashscope_api_key_input.textChanged.connect(
            lambda text: self.emit_config_change("api.dashscope_api_key", text)
        )

        # 显示/隐藏按钮
        self.dashscope_toggle_btn = QPushButton("显示")
        self.dashscope_toggle_btn.setFixedWidth(60)
        self.dashscope_toggle_btn.clicked.connect(self._toggle_dashscope_key_visibility)

        dashscope_key_layout.addWidget(self.dashscope_api_key_input)
        dashscope_key_layout.addWidget(self.dashscope_toggle_btn)

        dashscope_layout.addRow(dashscope_key_label, dashscope_key_layout)

        # DashScope帮助文本
        dashscope_help_label = QLabel(
            "请前往 <a href='https://dashscope.aliyun.com'>阿里云DashScope控制台</a> 获取API密钥"
        )
        dashscope_help_label.setObjectName("HelpLabel")
        dashscope_help_label.setOpenExternalLinks(True)
        dashscope_layout.addRow("", dashscope_help_label)

        # DashScope模型
        dashscope_model_label = QLabel("识别模型:")
        dashscope_model_label.setObjectName("FieldLabel")

        self.dashscope_model_input = QLineEdit()
        self.dashscope_model_input.setPlaceholderText("请输入模型名称，例如: qwen3-asr-flash-realtime")
        self.dashscope_model_input.textChanged.connect(
            lambda text: self.emit_config_change("api.dashscope_model", text)
        )

        dashscope_layout.addRow(dashscope_model_label, self.dashscope_model_input)

        # Doubao设置组
        self.doubao_group = self.create_group("Doubao API 设置")
        doubao_layout = self.doubao_group.layout()

        # Doubao APP ID
        doubao_app_id_label = QLabel("APP ID:")
        doubao_app_id_label.setObjectName("FieldLabel")

        self.doubao_app_id_input = QLineEdit()
        self.doubao_app_id_input.setPlaceholderText("请输入Doubao APP ID")
        self.doubao_app_id_input.textChanged.connect(
            lambda text: self.emit_config_change("api.doubao_app_id", text)
        )

        doubao_layout.addRow(doubao_app_id_label, self.doubao_app_id_input)

        # Doubao Access Token
        doubao_token_label = QLabel("Access Token:")
        doubao_token_label.setObjectName("FieldLabel")

        doubao_token_layout = QHBoxLayout()
        self.doubao_access_token_input = QLineEdit()
        self.doubao_access_token_input.setPlaceholderText("请输入Doubao Access Token")
        self.doubao_access_token_input.setEchoMode(QLineEdit.Password)
        self.doubao_access_token_input.textChanged.connect(
            lambda text: self.emit_config_change("api.doubao_access_token", text)
        )

        # 显示/隐藏按钮
        self.doubao_toggle_btn = QPushButton("显示")
        self.doubao_toggle_btn.setFixedWidth(60)
        self.doubao_toggle_btn.clicked.connect(self._toggle_doubao_token_visibility)

        doubao_token_layout.addWidget(self.doubao_access_token_input)
        doubao_token_layout.addWidget(self.doubao_toggle_btn)

        doubao_layout.addRow(doubao_token_label, doubao_token_layout)

        # Doubao帮助文本
        doubao_help_label = QLabel(
            "请前往 <a href='https://console.volcengine.com/speech'>火山引擎语音控制台</a> 获取凭证"
        )
        doubao_help_label.setObjectName("HelpLabel")
        doubao_help_label.setOpenExternalLinks(True)
        doubao_layout.addRow("", doubao_help_label)
    
    def _create_general_section(self) -> None:
        """创建通用设置区域"""
        group = self.create_group("通用设置")
        form_layout = group.layout()
        
        # 语言选择
        lang_label = QLabel("界面语言:")
        lang_label.setObjectName("FieldLabel")
        
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["简体中文", "English"])
        self.lang_combo.setCurrentText("简体中文")
        self.lang_combo.currentTextChanged.connect(self._on_language_changed)
        
        form_layout.addRow(lang_label, self.lang_combo)
        
        # 日志级别
        log_level_label = QLabel("日志级别:")
        log_level_label.setObjectName("FieldLabel")
        
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.log_level_combo.currentTextChanged.connect(
            lambda text: self.emit_config_change("general.log_level", text)
        )
        
        form_layout.addRow(log_level_label, self.log_level_combo)
        
        # 开机自启动
        self.auto_start_check = QCheckBox("开机自动启动")
        self.auto_start_check.stateChanged.connect(
            lambda state: self.emit_config_change("general.auto_start", state == Qt.Checked)
        )
        
        form_layout.addRow("", self.auto_start_check)
    
    def _on_provider_changed(self, index: int) -> None:
        """提供商变更处理"""
        providers = ["dashscope", "doubao"]
        provider = providers[index]
        logger.info(f"提供商已变更: {provider}")
        self.emit_config_change("api.provider", provider)

        # 显示/隐藏对应的API设置组
        self.dashscope_group.setVisible(provider == "dashscope")
        self.doubao_group.setVisible(provider == "doubao")

    def _toggle_dashscope_key_visibility(self) -> None:
        """切换DashScope API密钥可见性"""
        if self.dashscope_api_key_input.echoMode() == QLineEdit.Password:
            self.dashscope_api_key_input.setEchoMode(QLineEdit.Normal)
            self.dashscope_toggle_btn.setText("隐藏")
        else:
            self.dashscope_api_key_input.setEchoMode(QLineEdit.Password)
            self.dashscope_toggle_btn.setText("显示")

    def _toggle_doubao_token_visibility(self) -> None:
        """切换Doubao Access Token可见性"""
        if self.doubao_access_token_input.echoMode() == QLineEdit.Password:
            self.doubao_access_token_input.setEchoMode(QLineEdit.Normal)
            self.doubao_toggle_btn.setText("隐藏")
        else:
            self.doubao_access_token_input.setEchoMode(QLineEdit.Password)
            self.doubao_toggle_btn.setText("显示")
    
    def _on_language_changed(self, language: str) -> None:
        """语言变更处理"""
        lang_code = "zh-CN" if language == "简体中文" else "en-US"
        self.emit_config_change("general.language", lang_code)
    
    def load_config(self, config: dict) -> None:
        """
        加载配置到界面

        Args:
            config: 配置字典
        """
        logger.debug("加载基础设置配置")

        # 提供商设置
        provider = config.get("api", {}).get("provider", "dashscope")
        provider_index = 0 if provider == "dashscope" else 1
        self.provider_combo.setCurrentIndex(provider_index)

        # DashScope API设置
        dashscope_api_key = config.get("api", {}).get("dashscope_api_key", "")
        self.dashscope_api_key_input.setText(dashscope_api_key)

        dashscope_model = config.get("api", {}).get("dashscope_model", "qwen3-asr-flash-realtime")
        self.dashscope_model_input.setText(dashscope_model)
        logger.debug(f"加载DashScope模型配置: {dashscope_model}")

        # Doubao API设置
        doubao_app_id = config.get("api", {}).get("doubao_app_id", "")
        self.doubao_app_id_input.setText(doubao_app_id)

        doubao_access_token = config.get("api", {}).get("doubao_access_token", "")
        self.doubao_access_token_input.setText(doubao_access_token)

        # 显示/隐藏对应的API设置组
        self.dashscope_group.setVisible(provider == "dashscope")
        self.doubao_group.setVisible(provider == "doubao")

        # 通用设置
        language = config.get("general", {}).get("language", "zh-CN")
        lang_text = "简体中文" if language == "zh-CN" else "English"
        self.lang_combo.setCurrentText(lang_text)

        log_level = config.get("general", {}).get("log_level", "INFO")
        self.log_level_combo.setCurrentText(log_level)

        auto_start = config.get("general", {}).get("auto_start", False)
        self.auto_start_check.setChecked(auto_start)


class AudioSettingsPage(BasePage):
    """音频设置页面"""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.add_title("音频设置", "配置麦克风和音频采集参数")
        
        # 音频设备
        self._create_device_section()
        
        # 音频参数
        self._create_parameters_section()
        
        logger.info("音频设置页面初始化完成")
    
    def _create_device_section(self) -> None:
        """创建音频设备区域"""
        group = self.create_group("音频设备")
        form_layout = group.layout()
        
        # 麦克风选择
        mic_label = QLabel("麦克风:")
        mic_label.setObjectName("FieldLabel")
        
        mic_layout = QHBoxLayout()
        self.mic_combo = QComboBox()
        self.mic_combo.addItem("默认设备")
        
        # 刷新按钮
        refresh_btn = QPushButton("刷新")
        refresh_btn.setFixedWidth(60)
        refresh_btn.clicked.connect(self._refresh_audio_devices)
        
        mic_layout.addWidget(self.mic_combo, 1)
        mic_layout.addWidget(refresh_btn)
        
        form_layout.addRow(mic_label, mic_layout)
        
        # 自动加载音频设备
        self._refresh_audio_devices()
    
    def _create_parameters_section(self) -> None:
        """创建音频参数区域"""
        group = self.create_group("音频参数")
        form_layout = group.layout()
        
        # 采样率
        sample_rate_label = QLabel("采样率:")
        sample_rate_label.setObjectName("FieldLabel")
        
        self.sample_rate_combo = QComboBox()
        self.sample_rate_combo.addItems(["8000", "16000", "44100", "48000"])
        self.sample_rate_combo.setCurrentText("16000")
        self.sample_rate_combo.currentTextChanged.connect(
            lambda text: self.emit_config_change("audio.sample_rate", int(text))
        )
        
        form_layout.addRow(sample_rate_label, self.sample_rate_combo)
        
        # 声道数
        channels_label = QLabel("声道数:")
        channels_label.setObjectName("FieldLabel")
        
        self.channels_combo = QComboBox()
        self.channels_combo.addItems(["单声道 (1)", "立体声 (2)"])
        self.channels_combo.currentIndexChanged.connect(
            lambda idx: self.emit_config_change("audio.channels", idx + 1)
        )
        
        form_layout.addRow(channels_label, self.channels_combo)
        
        # 缓冲大小
        chunk_label = QLabel("缓冲大小:")
        chunk_label.setObjectName("FieldLabel")
        
        self.chunk_spin = QSpinBox()
        self.chunk_spin.setRange(1024, 8192)
        self.chunk_spin.setSingleStep(512)
        self.chunk_spin.setValue(3200)
        self.chunk_spin.setSuffix(" 字节")
        self.chunk_spin.valueChanged.connect(
            lambda val: self.emit_config_change("audio.chunk_size", val)
        )
        
        form_layout.addRow(chunk_label, self.chunk_spin)
        
        # 帮助文本
        help_label = QLabel("默认参数适用于大多数场景，通常无需修改")
        help_label.setObjectName("HelpLabel")
        form_layout.addRow("", help_label)
    
    def _refresh_audio_devices(self) -> None:
        """刷新音频设备列表"""
        logger.debug("刷新音频设备列表")
        
        self.mic_combo.clear()
        self.mic_combo.addItem("默认设备")
        
        try:
            import pyaudio
            p = pyaudio.PyAudio()
            
            for i in range(p.get_device_count()):
                device_info = p.get_device_info_by_index(i)
                if device_info.get('maxInputChannels', 0) > 0:
                    device_name = device_info.get('name', f'设备 {i}')
                    self.mic_combo.addItem(device_name)
            
            p.terminate()
            logger.info(f"找到 {self.mic_combo.count() - 1} 个音频输入设备")
        except Exception as e:
            logger.error(f"刷新音频设备失败: {e}")
            QMessageBox.warning(self, "错误", f"无法枚举音频设备:\n{e}")
    
    def load_config(self, config: dict) -> None:
        """
        加载配置到界面
        
        Args:
            config: 配置字典
        """
        logger.debug("加载音频设置配置")
        
        sample_rate = config.get("audio", {}).get("sample_rate", 16000)
        self.sample_rate_combo.setCurrentText(str(sample_rate))
        
        channels = config.get("audio", {}).get("channels", 1)
        self.channels_combo.setCurrentIndex(channels - 1)
        
        chunk_size = config.get("audio", {}).get("chunk_size", 3200)
        self.chunk_spin.setValue(chunk_size)


class InputSettingsPage(BasePage):
    """输入设置页面"""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.add_title("输入设置", "配置文本输入方式和参数")
        
        # 输入方法
        self._create_method_section()
        
        # 输入参数
        self._create_parameters_section()
        
        logger.info("输入设置页面初始化完成")
    
    def _create_method_section(self) -> None:
        """创建输入方法区域"""
        group = self.create_group("输入方法")
        form_layout = group.layout()
        
        # 首选方法
        method_label = QLabel("首选方法:")
        method_label.setObjectName("FieldLabel")
        
        self.method_combo = QComboBox()
        self.method_combo.addItems([
            "剪贴板方案 (推荐)",
            "Win32 API",
            "PyAutoGUI"
        ])
        self.method_combo.currentIndexChanged.connect(self._on_method_changed)
        
        form_layout.addRow(method_label, self.method_combo)
        
        # 方法说明
        self.method_desc = QLabel()
        self.method_desc.setObjectName("HelpLabel")
        self.method_desc.setWordWrap(True)
        form_layout.addRow("", self.method_desc)
        
        self._update_method_description(0)
    
    def _create_parameters_section(self) -> None:
        """创建输入参数区域"""
        group = self.create_group("输入参数")
        form_layout = group.layout()
        
        # 输入延迟
        input_delay_label = QLabel("字符延迟:")
        input_delay_label.setObjectName("FieldLabel")
        
        self.input_delay_spin = QDoubleSpinBox()
        self.input_delay_spin.setRange(0.01, 1.0)
        self.input_delay_spin.setSingleStep(0.01)
        self.input_delay_spin.setValue(0.05)
        self.input_delay_spin.setSuffix(" 秒")
        self.input_delay_spin.setDecimals(2)
        self.input_delay_spin.valueChanged.connect(
            lambda val: self.emit_config_change("input.input_delay", val)
        )
        
        form_layout.addRow(input_delay_label, self.input_delay_spin)
        
        # 粘贴延迟
        paste_delay_label = QLabel("粘贴延迟:")
        paste_delay_label.setObjectName("FieldLabel")
        
        self.paste_delay_spin = QDoubleSpinBox()
        self.paste_delay_spin.setRange(0.01, 1.0)
        self.paste_delay_spin.setSingleStep(0.01)
        self.paste_delay_spin.setValue(0.1)
        self.paste_delay_spin.setSuffix(" 秒")
        self.paste_delay_spin.setDecimals(2)
        self.paste_delay_spin.valueChanged.connect(
            lambda val: self.emit_config_change("input.paste_delay", val)
        )
        
        form_layout.addRow(paste_delay_label, self.paste_delay_spin)
        
        # 最大长度
        max_len_label = QLabel("最大长度:")
        max_len_label.setObjectName("FieldLabel")
        
        self.max_len_spin = QSpinBox()
        self.max_len_spin.setRange(100, 50000)
        self.max_len_spin.setSingleStep(1000)
        self.max_len_spin.setValue(10000)
        self.max_len_spin.setSuffix(" 字符")
        self.max_len_spin.valueChanged.connect(
            lambda val: self.emit_config_change("input.max_input_length", val)
        )
        
        form_layout.addRow(max_len_label, self.max_len_spin)
        
        # 恢复剪贴板
        self.restore_clipboard_check = QCheckBox("自动恢复剪贴板内容")
        self.restore_clipboard_check.setChecked(True)
        self.restore_clipboard_check.stateChanged.connect(
            lambda state: self.emit_config_change("input.restore_clipboard", state == Qt.Checked)
        )
        
        form_layout.addRow("", self.restore_clipboard_check)
    
    def _on_method_changed(self, index: int) -> None:
        """输入方法变更处理"""
        methods = ["clipboard", "win32", "pyautogui"]
        self.emit_config_change("input.preferred_method", methods[index])
        self._update_method_description(index)
    
    def _update_method_description(self, index: int) -> None:
        """更新方法说明"""
        descriptions = [
            "通过剪贴板粘贴文本，兼容性最好，推荐使用",
            "使用Windows API输入，适合英文输入，中文支持有限",
            "逐字符输入，速度较慢但兼容性极高"
        ]
        self.method_desc.setText(descriptions[index])
    
    def load_config(self, config: dict) -> None:
        """
        加载配置到界面
        
        Args:
            config: 配置字典
        """
        logger.debug("加载输入设置配置")
        
        method = config.get("input", {}).get("preferred_method", "clipboard")
        method_index = {"clipboard": 0, "win32": 1, "pyautogui": 2}.get(method, 0)
        self.method_combo.setCurrentIndex(method_index)
        
        input_delay = config.get("input", {}).get("input_delay", 0.05)
        self.input_delay_spin.setValue(input_delay)
        
        paste_delay = config.get("input", {}).get("paste_delay", 0.1)
        self.paste_delay_spin.setValue(paste_delay)
        
        max_length = config.get("input", {}).get("max_input_length", 10000)
        self.max_len_spin.setValue(max_length)
        
        restore_clipboard = config.get("input", {}).get("restore_clipboard", True)
        self.restore_clipboard_check.setChecked(restore_clipboard)


class AdvancedSettingsPage(BasePage):
    """高级设置页面"""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.add_title("高级设置", "配置高级功能和识别参数")
        
        # 识别设置
        self._create_recognition_section()
        
        # 配置文件
        self._create_config_section()
        
        logger.info("高级设置页面初始化完成")
    
    def _create_recognition_section(self) -> None:
        """创建识别设置区域"""
        group = self.create_group("识别设置")
        form_layout = group.layout()
        
        # 智能标点
        self.punctuation_check = QCheckBox("启用智能标点符号")
        self.punctuation_check.stateChanged.connect(
            lambda state: self.emit_config_change(
                "recognition.semantic_punctuation_enabled",
                state == Qt.Checked
            )
        )
        
        form_layout.addRow("", self.punctuation_check)
        
        # 超时时间
        timeout_label = QLabel("超时时间:")
        timeout_label.setObjectName("FieldLabel")
        
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 120)
        self.timeout_spin.setSingleStep(5)
        self.timeout_spin.setValue(30)
        self.timeout_spin.setSuffix(" 秒")
        self.timeout_spin.valueChanged.connect(
            lambda val: self.emit_config_change("recognition.timeout", val)
        )
        
        form_layout.addRow(timeout_label, self.timeout_spin)
    
    def _create_config_section(self) -> None:
        """创建配置文件区域"""
        group = self.create_group("配置文件")
        form_layout = group.layout()
        
        # 配置文件路径
        config_path_label = QLabel("配置路径:")
        config_path_label.setObjectName("FieldLabel")
        
        config_path = str(Path.home() / ".autovoicetype" / "config.json")
        self.config_path_display = QLabel(config_path)
        self.config_path_display.setWordWrap(True)
        self.config_path_display.setTextInteractionFlags(Qt.TextSelectableByMouse)
        
        form_layout.addRow(config_path_label, self.config_path_display)
        
        # 按钮组
        btn_layout = QHBoxLayout()
        
        open_config_btn = QPushButton("打开配置文件")
        open_config_btn.clicked.connect(self._open_config_file)
        
        open_folder_btn = QPushButton("打开配置目录")
        open_folder_btn.clicked.connect(self._open_config_folder)
        
        reset_btn = QPushButton("重置配置")
        reset_btn.setObjectName("DangerButton")
        reset_btn.clicked.connect(self._reset_config)
        
        btn_layout.addWidget(open_config_btn)
        btn_layout.addWidget(open_folder_btn)
        btn_layout.addWidget(reset_btn)
        btn_layout.addStretch()
        
        form_layout.addRow("", btn_layout)
    
    def _open_config_file(self) -> None:
        """打开配置文件"""
        import subprocess
        import platform
        
        config_file = Path.home() / ".autovoicetype" / "config.json"
        
        try:
            if platform.system() == "Windows":
                subprocess.Popen(["notepad.exe", str(config_file)])
            elif platform.system() == "Darwin":  # macOS
                subprocess.Popen(["open", "-e", str(config_file)])
            else:  # Linux
                subprocess.Popen(["xdg-open", str(config_file)])
            
            logger.info(f"已打开配置文件: {config_file}")
        except Exception as e:
            logger.error(f"打开配置文件失败: {e}")
            QMessageBox.warning(self, "错误", f"无法打开配置文件:\n{e}")
    
    def _open_config_folder(self) -> None:
        """打开配置目录"""
        import subprocess
        import platform
        
        config_dir = Path.home() / ".autovoicetype"
        
        try:
            if platform.system() == "Windows":
                subprocess.Popen(["explorer", str(config_dir)])
            elif platform.system() == "Darwin":  # macOS
                subprocess.Popen(["open", str(config_dir)])
            else:  # Linux
                subprocess.Popen(["xdg-open", str(config_dir)])
            
            logger.info(f"已打开配置目录: {config_dir}")
        except Exception as e:
            logger.error(f"打开配置目录失败: {e}")
            QMessageBox.warning(self, "错误", f"无法打开配置目录:\n{e}")
    
    def _reset_config(self) -> None:
        """重置配置"""
        reply = QMessageBox.question(
            self,
            "确认重置",
            "确定要重置所有配置为默认值吗？\n此操作无法撤销！",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            logger.warning("用户确认重置配置")
            # 发射信号通知主窗口
            self.emit_config_change("__reset__", True)
    
    def load_config(self, config: dict) -> None:
        """
        加载配置到界面
        
        Args:
            config: 配置字典
        """
        logger.debug("加载高级设置配置")
        
        punctuation = config.get("recognition", {}).get("semantic_punctuation_enabled", False)
        self.punctuation_check.setChecked(punctuation)
        
        timeout = config.get("recognition", {}).get("timeout", 30)
        self.timeout_spin.setValue(timeout)


class AboutPage(BasePage):
    """关于页面"""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.add_title("关于 AutoVoiceType", "智能语音输入法")
        
        # 版本信息
        self._create_version_section()
        
        # 使用说明
        self._create_usage_section()
        
        # 链接
        self._create_links_section()
        
        logger.info("关于页面初始化完成")
    
    def _create_version_section(self) -> None:
        """创建版本信息区域"""
        group = self.create_group("版本信息")
        form_layout = group.layout()
        
        version_label = QLabel("版本:")
        version_label.setObjectName("FieldLabel")
        version_value = QLabel("1.0.0")
        form_layout.addRow(version_label, version_value)
        
        build_label = QLabel("构建日期:")
        build_label.setObjectName("FieldLabel")
        build_value = QLabel("2025-12-28")
        form_layout.addRow(build_label, build_value)
        
        python_label = QLabel("Python 版本:")
        python_label.setObjectName("FieldLabel")
        import sys
        python_value = QLabel(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
        form_layout.addRow(python_label, python_value)
    
    def _create_usage_section(self) -> None:
        """创建使用说明区域"""
        group = self.create_group("使用说明")
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        
        usage_text = QTextEdit()
        usage_text.setReadOnly(True)
        usage_text.setMaximumHeight(150)
        usage_text.setPlainText(
            "1. 按住【右Ctrl键】开始语音输入\n"
            "2. 对着麦克风说话\n"
            "3. 释放【右Ctrl键】结束输入\n"
            "4. 识别结果将自动输入到当前窗口的光标位置\n\n"
            "提示：\n"
            "- 首次使用需要配置DashScope API密钥\n"
            "- 确保麦克风工作正常\n"
            "- 在安静环境下识别效果更好"
        )
        
        layout.addWidget(usage_text)
        group.setLayout(layout)
    
    def _create_links_section(self) -> None:
        """创建链接区域"""
        group = self.create_group("相关链接")
        form_layout = group.layout()
        
        dashscope_link = QLabel(
            '<a href="https://dashscope.aliyun.com">阿里云DashScope控制台</a>'
        )
        dashscope_link.setOpenExternalLinks(True)
        form_layout.addRow("API控制台:", dashscope_link)
        
        docs_link = QLabel(
            '<a href="https://help.aliyun.com/zh/dashscope/">DashScope 文档</a>'
        )
        docs_link.setOpenExternalLinks(True)
        form_layout.addRow("API文档:", docs_link)
        
        # 版权信息
        copyright_label = QLabel("© 2025 AutoVoiceType. All rights reserved.")
        copyright_label.setObjectName("HelpLabel")
        copyright_label.setAlignment(Qt.AlignCenter)
        self.layout.addStretch()
        self.layout.addWidget(copyright_label)
    
    def load_config(self, config: dict) -> None:
        """关于页面不需要加载配置"""
        pass

