"""
语音识别模块（统一接口）
负责根据配置创建适当的语音识别器
"""
import logging
from typing import Callable, Optional

from recognizers import BaseRecognizer, RecognitionConfig, RecognitionResult, RecognizerFactory

logger = logging.getLogger(__name__)


class VoiceRecognizer:
    """
    语音识别器统一接口
    根据配置创建和管理实际的识别器实例
    """

    def __init__(self, api_config: dict, audio_config: dict):
        """
        初始化语音识别器

        Args:
            api_config: API配置字典
            audio_config: 音频配置字典
        """
        self.api_config = api_config
        self.audio_config = audio_config
        self.result_callback: Optional[Callable] = None
        self._recognizer: Optional[BaseRecognizer] = None

        # 创建识别器
        self._create_recognizer()

        logger.info("语音识别器统一接口初始化完成")

    def _create_recognizer(self) -> None:
        """根据配置创建识别器实例"""
        try:
            provider = self.api_config.get('provider', 'dashscope')
            logger.info(f"创建语音识别器，提供商: {provider}")

            # 构建RecognitionConfig
            recognition_config = RecognitionConfig(
                sample_rate=self.audio_config.get('sample_rate', 16000),
                channels=self.audio_config.get('channels', 1),
                chunk_size=self.audio_config.get('chunk_size', 3200),
                audio_format=self.audio_config.get('format', 'pcm'),
                semantic_punctuation_enabled=self.api_config.get('semantic_punctuation_enabled', False),
                timeout=self.api_config.get('timeout', 30),
                provider_config=self._build_provider_config(provider)
            )

            # 构建凭证
            credentials = self._build_credentials(provider)

            # 创建识别器
            self._recognizer = RecognizerFactory.create_recognizer(
                provider=provider,
                config=recognition_config,
                credentials=credentials
            )

            # 设置回调
            if self.result_callback:
                self._recognizer.set_result_callback(self._on_recognition_result)

            logger.info(f"语音识别器创建成功: {RecognizerFactory.get_provider_display_name(provider)}")

        except Exception as e:
            logger.error(f"创建语音识别器失败: {e}", exc_info=True)
            raise

    def _build_provider_config(self, provider: str) -> dict:
        """
        构建提供商特定配置

        Args:
            provider: 提供商名称

        Returns:
            dict: 提供商配置
        """
        if provider == 'dashscope':
            return {
                'model': self.api_config.get('dashscope_model', 'qwen3-asr-flash-realtime'),
                'base_websocket_url': self.api_config.get(
                    'dashscope_base_websocket_url',
                    'wss://dashscope.aliyuncs.com/api-ws/v1/inference'
                )
            }
        elif provider == 'doubao':
            return {
                'url': self.api_config.get(
                    'doubao_url',
                    'wss://openspeech.bytedance.com/api/v3/sauc/bigmodel_async'
                ),
                'resource_id': self.api_config.get(
                    'doubao_resource_id',
                    'volc.seedasr.sauc.duration'
                ),
                'segment_duration': self.api_config.get('doubao_segment_duration', 200)
            }
        else:
            return {}

    def _build_credentials(self, provider: str) -> dict:
        """
        构建提供商凭证

        Args:
            provider: 提供商名称

        Returns:
            dict: 凭证字典
        """
        if provider == 'dashscope':
            return {
                'api_key': self.api_config.get('dashscope_api_key', '')
            }
        elif provider == 'doubao':
            return {
                'app_id': self.api_config.get('doubao_app_id', ''),
                'access_token': self.api_config.get('doubao_access_token', '')
            }
        else:
            return {}

    def set_result_callback(self, callback: Callable) -> None:
        """
        设置识别结果回调函数

        Args:
            callback: 回调函数，接收识别文本作为参数
        """
        self.result_callback = callback
        if self._recognizer:
            self._recognizer.set_result_callback(self._on_recognition_result)
        logger.debug("识别结果回调函数已设置")

    def _on_recognition_result(self, result: RecognitionResult) -> None:
        """
        内部识别结果回调

        Args:
            result: 识别结果对象
        """
        if self.result_callback:
            try:
                # 提取文本并调用用户回调
                self.result_callback(result.text)
            except Exception as e:
                logger.error(f"执行用户回调函数时出错: {e}", exc_info=True)

    def start_recording(self) -> bool:
        """
        开始录音和识别

        Returns:
            bool: 是否成功启动
        """
        if not self._recognizer:
            logger.error("识别器未初始化")
            return False

        return self._recognizer.start_recording()

    def stop_recording(self) -> bool:
        """
        停止录音和识别

        Returns:
            bool: 是否成功停止
        """
        if not self._recognizer:
            logger.error("识别器未初始化")
            return False

        return self._recognizer.stop_recording()

    def is_currently_recording(self) -> bool:
        """
        检查是否正在录音

        Returns:
            bool: 是否正在录音
        """
        if not self._recognizer:
            return False

        return self._recognizer.is_currently_recording()

    def cleanup(self) -> None:
        """清理资源"""
        if self._recognizer:
            self._recognizer.cleanup()
            self._recognizer = None
        logger.debug("语音识别器已清理")
