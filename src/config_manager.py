"""
配置管理模块
负责加载、保存和验证应用程序配置
"""
import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ConfigManager:
    """配置管理器类，负责处理应用配置的读写和验证"""
    
    # 默认配置
    DEFAULT_CONFIG = {
        "api": {
            "dashscope_api_key": "",
            "base_websocket_url": "wss://dashscope.aliyuncs.com/api-ws/v1/inference",
            "model": "qwen3-asr-flash-realtime"
        },
        "audio": {
            "sample_rate": 16000,
            "channels": 1,
            "chunk_size": 3200,
            "format": "pcm"
        },
        "hotkey": {
            "trigger_key": "ctrl_r",  # Right Ctrl key
            "description": "Right Control Key"
        },
        "input": {
            "preferred_method": "clipboard",  # clipboard, win32, pyautogui
            "input_delay": 0.05,              # 字符间延迟（秒）
            "paste_delay": 0.1,               # 粘贴前后延迟（秒）
            "restore_clipboard": True,        # 是否恢复剪贴板
            "max_input_length": 10000         # 最大输入长度限制
        },
        "general": {
            "auto_start": False,
            "language": "zh-CN",
            "log_level": "INFO"
        },
        "recognition": {
            "semantic_punctuation_enabled": False,
            "timeout": 30
        }
    }
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_dir: 配置文件目录，默认为用户目录下的.autovoicetype
        """
        if config_dir is None:
            self.config_dir = Path.home() / ".autovoicetype"
        else:
            self.config_dir = Path(config_dir)
        
        self.config_file = self.config_dir / "config.json"
        self.config = {}
        
        # 确保配置目录存在
        self._ensure_config_dir()
        
        # 加载配置
        self.load_config()
        
        logger.info(f"配置管理器初始化完成，配置文件路径: {self.config_file}")
    
    def _ensure_config_dir(self) -> None:
        """确保配置目录存在"""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"配置目录已创建或已存在: {self.config_dir}")
        except Exception as e:
            logger.error(f"创建配置目录失败: {e}")
            raise
    
    def load_config(self) -> dict:
        """
        加载配置文件，如果文件不存在则创建默认配置
        
        Returns:
            dict: 配置字典
        """
        if not self.config_file.exists():
            logger.info("配置文件不存在，创建默认配置")
            self.config = self.DEFAULT_CONFIG.copy()
            self.save_config()
        else:
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                logger.info("配置文件加载成功")
                
                # 合并默认配置（处理新增配置项）
                self._merge_default_config()
            except json.JSONDecodeError as e:
                logger.error(f"配置文件格式错误: {e}，将使用默认配置")
                self.config = self.DEFAULT_CONFIG.copy()
                self.save_config()
            except Exception as e:
                logger.error(f"加载配置文件失败: {e}")
                raise
        
        return self.config
    
    def _merge_default_config(self) -> None:
        """将默认配置与当前配置合并，补充缺失的配置项"""
        def merge_dict(default: dict, current: dict) -> dict:
            """递归合并字典"""
            for key, value in default.items():
                if key not in current:
                    current[key] = value
                    logger.debug(f"添加缺失的配置项: {key}")
                elif isinstance(value, dict) and isinstance(current[key], dict):
                    merge_dict(value, current[key])
            return current
        
        self.config = merge_dict(self.DEFAULT_CONFIG.copy(), self.config)
    
    def save_config(self) -> bool:
        """
        保存配置到文件
        
        Returns:
            bool: 是否保存成功
        """
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            logger.info("配置文件保存成功")
            return True
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            return False
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置项，支持点号分隔的路径
        
        Args:
            key_path: 配置路径，如 "api.dashscope_api_key"
            default: 默认值
            
        Returns:
            Any: 配置值
        """
        keys = key_path.split('.')
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            logger.debug(f"配置项 {key_path} 不存在，返回默认值: {default}")
            return default
    
    def set(self, key_path: str, value: Any) -> bool:
        """
        设置配置项，支持点号分隔的路径
        
        Args:
            key_path: 配置路径，如 "api.dashscope_api_key"
            value: 配置值
            
        Returns:
            bool: 是否设置成功
        """
        keys = key_path.split('.')
        config = self.config
        
        try:
            # 遍历到倒数第二个键
            for key in keys[:-1]:
                if key not in config:
                    config[key] = {}
                config = config[key]
            
            # 设置最后一个键的值
            config[keys[-1]] = value
            logger.debug(f"配置项 {key_path} 已设置为: {value}")
            return True
        except Exception as e:
            logger.error(f"设置配置项 {key_path} 失败: {e}")
            return False
    
    def validate_api_key(self) -> bool:
        """
        验证API密钥是否已配置且非空
        
        Returns:
            bool: API密钥是否有效
        """
        api_key = self.get("api.dashscope_api_key", "")
        is_valid = bool(api_key and api_key.strip())
        
        if is_valid:
            logger.info("API密钥验证通过")
        else:
            logger.warning("API密钥未配置或为空")
        
        return is_valid
    
    def is_first_run(self) -> bool:
        """
        检查是否是首次运行
        
        Returns:
            bool: 是否首次运行
        """
        # 如果API密钥未配置，认为是首次运行
        return not self.validate_api_key()
    
    def get_api_key(self) -> str:
        """
        获取DashScope API密钥
        
        Returns:
            str: API密钥
        """
        return self.get("api.dashscope_api_key", "")
    
    def get_audio_config(self) -> dict:
        """
        获取音频配置
        
        Returns:
            dict: 音频配置字典
        """
        return {
            "sample_rate": self.get("audio.sample_rate", 16000),
            "channels": self.get("audio.channels", 1),
            "chunk_size": self.get("audio.chunk_size", 3200),
            "format": self.get("audio.format", "pcm")
        }
    
    def get_log_level(self) -> str:
        """
        获取日志级别
        
        Returns:
            str: 日志级别
        """
        return self.get("general.log_level", "INFO")
    
    def get_input_config(self) -> dict:
        """
        获取文本输入配置
        
        Returns:
            dict: 输入配置字典
        """
        return {
            "preferred_method": self.get("input.preferred_method", "clipboard"),
            "input_delay": self.get("input.input_delay", 0.05),
            "paste_delay": self.get("input.paste_delay", 0.1),
            "restore_clipboard": self.get("input.restore_clipboard", True),
            "max_input_length": self.get("input.max_input_length", 10000)
        }
    
    def get_api_config(self) -> dict:
        """
        获取API配置
        
        Returns:
            dict: API配置字典
        """
        model = self.get("api.model", "qwen3-asr-flash-realtime")
        logger.debug(f"获取API配置，模型: {model}")
        return {
            "dashscope_api_key": self.get("api.dashscope_api_key", ""),
            "base_websocket_url": self.get(
                "api.base_websocket_url",
                "wss://dashscope.aliyuncs.com/api-ws/v1/inference"
            ),
            "model": model
        }

