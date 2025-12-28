"""
语音识别模块
负责音频采集和实时语音识别，集成阿里云DashScope API
"""
import logging
import threading
import time
from typing import Callable, Optional

import dashscope
import pyaudio
from dashscope.audio.asr import Recognition, RecognitionCallback, RecognitionResult
from dashscope.common.error import InvalidParameter

logger = logging.getLogger(__name__)


class VoiceRecognitionCallback(RecognitionCallback):
    """语音识别回调处理类"""
    
    def __init__(self, audio_config: dict, result_callback: Optional[Callable] = None):
        """
        初始化回调处理器
        
        Args:
            audio_config: 音频配置字典
            result_callback: 识别结果回调函数
        """
        super().__init__()
        self.audio_config = audio_config
        self.result_callback = result_callback
        self.mic: Optional[pyaudio.PyAudio] = None
        self.stream: Optional[pyaudio.Stream] = None
        self.full_text = ""  # 累积的完整识别文本
        
        logger.debug("语音识别回调处理器初始化完成")
    
    def on_open(self) -> None:
        """WebSocket连接建立时的回调"""
        try:
            logger.info("语音识别WebSocket连接已建立")
            
            # 初始化音频设备
            self.mic = pyaudio.PyAudio()
            self.stream = self.mic.open(
                format=pyaudio.paInt16,
                channels=self.audio_config['channels'],
                rate=self.audio_config['sample_rate'],
                input=True,
                frames_per_buffer=self.audio_config['chunk_size']
            )
            
            logger.info("音频流已打开")
        except Exception as e:
            logger.error(f"打开音频流失败: {e}", exc_info=True)
            raise
    
    def on_close(self) -> None:
        """WebSocket连接关闭时的回调"""
        try:
            logger.info("语音识别WebSocket连接已关闭")
            
            # 清理音频资源
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
                logger.debug("音频流已关闭")
            
            if self.mic:
                self.mic.terminate()
                self.mic = None
                logger.debug("音频设备已释放")
        except Exception as e:
            logger.error(f"关闭音频流时出错: {e}", exc_info=True)
    
    def on_complete(self) -> None:
        """识别完成时的回调"""
        logger.info("语音识别已完成")
        
        # 如果有累积的文本，调用结果回调
        if self.full_text and self.result_callback:
            try:
                self.result_callback(self.full_text)
                logger.debug(f"最终识别文本: {self.full_text}")
            except Exception as e:
                logger.error(f"执行结果回调函数时出错: {e}", exc_info=True)
        
        # 重置累积文本
        self.full_text = ""
    
    def on_error(self, message) -> None:
        """识别错误时的回调"""
        logger.error(f"语音识别错误 - Request ID: {message.request_id}, 错误信息: {message.message}")
        
        # 清理资源
        try:
            if self.stream and hasattr(self.stream, 'is_active') and self.stream.is_active():
                self.stream.stop_stream()
                self.stream.close()
        except Exception as e:
            logger.error(f"错误处理中清理资源失败: {e}", exc_info=True)
    
    def on_event(self, result: RecognitionResult) -> None:
        """
        识别结果事件回调
        
        Args:
            result: 识别结果对象
        """
        try:
            sentence = result.get_sentence()
            
            if 'text' in sentence:
                text = sentence['text']
                logger.debug(f"识别到文本片段: {text}")
                
                # 累积文本
                self.full_text = text
                
                # 如果是句子结束标记
                if RecognitionResult.is_sentence_end(sentence):
                    logger.info(
                        f"句子结束 - Request ID: {result.get_request_id()}, "
                        f"使用情况: {result.get_usage(sentence)}"
                    )
        except Exception as e:
            logger.error(f"处理识别结果时出错: {e}", exc_info=True)


class VoiceRecognizer:
    """语音识别器类，管理录音和识别流程"""
    
    def __init__(self, api_key: str, audio_config: dict, api_config: dict):
        """
        初始化语音识别器
        
        Args:
            api_key: DashScope API密钥
            audio_config: 音频配置字典
            api_config: API配置字典
        """
        self.api_key = api_key
        self.audio_config = audio_config
        self.api_config = api_config
        
        self.recognition: Optional[Recognition] = None
        self.callback: Optional[VoiceRecognitionCallback] = None
        self.is_recording = False
        self.result_callback: Optional[Callable] = None
        
        # 配置DashScope
        dashscope.api_key = self.api_key
        dashscope.base_websocket_api_url = api_config.get(
            'base_websocket_url', 
            'wss://dashscope.aliyuncs.com/api-ws/v1/inference'
        )
        
        logger.info("语音识别器初始化完成")
    
    def set_result_callback(self, callback: Callable) -> None:
        """
        设置识别结果回调函数
        
        Args:
            callback: 回调函数，接收识别文本作为参数
        """
        self.result_callback = callback
        logger.debug("识别结果回调函数已设置")
    
    def start_recording(self) -> bool:
        """
        开始录音和识别
        
        Returns:
            bool: 是否成功启动
        """
        if self.is_recording:
            logger.warning("录音已经在进行中")
            return False
        
        try:
            logger.info("开始录音和识别")
            
            # 创建回调处理器
            self.callback = VoiceRecognitionCallback(
                audio_config=self.audio_config,
                result_callback=self.result_callback
            )
            
            # 创建识别对象
            self.recognition = Recognition(
                model=self.api_config.get('model', 'fun-asr-realtime'),
                format=self.audio_config['format'],
                sample_rate=self.audio_config['sample_rate'],
                semantic_punctuation_enabled=self.api_config.get('semantic_punctuation_enabled', False),
                callback=self.callback
            )
            
            # 启动识别
            self.recognition.start()
            self.is_recording = True
            
            # 在独立线程中发送音频数据
            self._audio_thread = threading.Thread(target=self._send_audio_stream, daemon=True)
            self._audio_thread.start()
            
            logger.info("录音和识别已启动")
            return True
        except Exception as e:
            logger.error(f"启动录音和识别失败: {e}", exc_info=True)
            self.is_recording = False
            return False
    
    def _send_audio_stream(self) -> None:
        """在独立线程中发送音频流到识别服务"""
        try:
            logger.debug("音频流发送线程已启动")
            
            while self.is_recording and self.callback and self.callback.stream:
                try:
                    # 再次检查状态，防止在读取音频数据期间状态发生变化
                    if not self.is_recording or not self.recognition:
                        break
                    
                    # 从麦克风读取音频数据
                    audio_data = self.callback.stream.read(
                        self.audio_config['chunk_size'],
                        exception_on_overflow=False
                    )
                    
                    # 发送前再次检查状态
                    if not self.is_recording or not self.recognition:
                        break
                    
                    # 发送到识别服务
                    self.recognition.send_audio_frame(audio_data)
                except InvalidParameter as e:
                    # 识别已停止，这是正常情况，不需要记录为错误
                    if "Speech recognition has stopped" in str(e):
                        logger.debug("识别已停止，停止发送音频数据")
                    else:
                        logger.warning(f"发送音频数据时参数错误: {e}")
                    break
                except Exception as e:
                    # 其他异常才记录为错误
                    if self.is_recording:
                        logger.error(f"发送音频数据时出错: {e}", exc_info=True)
                    else:
                        logger.debug(f"发送音频数据时出错（可能因停止识别）: {e}")
                    break
                
                # 短暂休眠，避免过于频繁
                time.sleep(0.01)
            
            logger.debug("音频流发送线程已结束")
        except Exception as e:
            logger.error(f"音频流发送线程异常: {e}", exc_info=True)
    
    def stop_recording(self) -> bool:
        """
        停止录音和识别
        
        Returns:
            bool: 是否成功停止
        """
        if not self.is_recording:
            logger.warning("录音未在进行中")
            return False
        
        try:
            logger.info("停止录音和识别")
            
            # 标记为停止状态
            self.is_recording = False
            
            # 停止识别
            if self.recognition:
                self.recognition.stop()
                
                # 获取性能指标
                try:
                    request_id = self.recognition.get_last_request_id()
                    first_delay = self.recognition.get_first_package_delay()
                    last_delay = self.recognition.get_last_package_delay()
                    
                    logger.info(
                        f"识别性能指标 - Request ID: {request_id}, "
                        f"首包延迟: {first_delay}ms, 尾包延迟: {last_delay}ms"
                    )
                except Exception as e:
                    logger.debug(f"获取性能指标失败: {e}")
                
                self.recognition = None
            
            # 等待音频线程结束
            if hasattr(self, '_audio_thread') and self._audio_thread.is_alive():
                self._audio_thread.join(timeout=2)
            
            logger.info("录音和识别已停止")
            return True
        except Exception as e:
            logger.error(f"停止录音和识别失败: {e}", exc_info=True)
            return False
    
    def is_currently_recording(self) -> bool:
        """
        检查是否正在录音
        
        Returns:
            bool: 是否正在录音
        """
        return self.is_recording

