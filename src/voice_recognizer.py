"""
语音识别模块
负责音频采集和实时语音识别，集成阿里云DashScope API
"""
import logging
import queue
import threading
import time
from typing import Callable, Optional

import dashscope
import numpy as np
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
        self.connection_ready = threading.Event()  # WebSocket连接就绪标志
        
        logger.debug("语音识别回调处理器初始化完成")
    
    def on_open(self) -> None:
        """WebSocket连接建立时的回调"""
        try:
            logger.info("语音识别WebSocket连接已建立")
            
            # 注意：音频流已经在 start_recording() 中提前打开
            # 这里只需要设置连接就绪标志
            self.connection_ready.set()
            logger.info("WebSocket连接已就绪，可以开始发送音频数据")
        except Exception as e:
            logger.error(f"WebSocket连接建立时出错: {e}", exc_info=True)
            raise
    
    def on_close(self) -> None:
        """WebSocket连接关闭时的回调"""
        try:
            logger.info("语音识别WebSocket连接已关闭")
            
            # 注意：音频流由 VoiceRecognizer 统一管理，这里不需要关闭
            # 只需要重置连接状态标志
            self.connection_ready.clear()
            logger.debug("WebSocket连接状态标志已重置")
        except Exception as e:
            logger.error(f"WebSocket连接关闭时出错: {e}", exc_info=True)
    
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
        
        # 音频缓冲相关
        self.audio_buffer: Optional[queue.Queue] = None  # 音频数据缓冲区
        self.audio_mic: Optional[pyaudio.PyAudio] = None  # 提前打开的音频设备
        self.audio_stream: Optional[pyaudio.Stream] = None  # 提前打开的音频流
        self._record_thread: Optional[threading.Thread] = None  # 录音线程
        
        # 缓冲区大小限制：保存最近约2秒的音频数据
        # 假设采样率16000，chunk_size 3200，每chunk约0.2秒，2秒约10个chunk
        sample_rate = audio_config.get('sample_rate', 16000)
        chunk_size = audio_config.get('chunk_size', 3200)
        buffer_duration_seconds = 2.0  # 缓冲区保存2秒音频
        self.max_buffer_size = int(sample_rate * buffer_duration_seconds / chunk_size)
        
        # 配置DashScope
        dashscope.api_key = self.api_key
        dashscope.base_websocket_api_url = api_config.get(
            'base_websocket_url', 
            'wss://dashscope.aliyuncs.com/api-ws/v1/inference'
        )
        
        logger.info("语音识别器初始化完成")
        logger.debug(f"音频缓冲区最大容量: {self.max_buffer_size} 个chunk (约{buffer_duration_seconds}秒)")
    
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
        立即打开音频流并开始录音到缓冲区，确保不丢失任何音频数据
        
        Returns:
            bool: 是否成功启动
        """
        if self.is_recording:
            logger.warning("录音已经在进行中")
            return False
        
        try:
            start_time = time.time()
            logger.info("开始录音和识别")
            
            # 1. 立即创建音频缓冲区
            self.audio_buffer = queue.Queue(maxsize=self.max_buffer_size)
            logger.debug(f"音频缓冲区已创建，最大容量: {self.max_buffer_size} 个chunk")
            
            # 2. 立即打开音频流并开始录音到缓冲区
            try:
                logger.info("立即打开音频流，开始录音...")
                self.audio_mic = pyaudio.PyAudio()
                self.audio_stream = self.audio_mic.open(
                    format=pyaudio.paInt16,
                    channels=self.audio_config['channels'],
                    rate=self.audio_config['sample_rate'],
                    input=True,
                    frames_per_buffer=self.audio_config['chunk_size']
                )
                audio_stream_open_time = time.time()
                logger.info(f"音频流已立即打开 (耗时: {(audio_stream_open_time - start_time) * 1000:.2f}ms)")
            except Exception as e:
                logger.error(f"打开音频流失败: {e}", exc_info=True)
                self.audio_buffer = None
                return False
            
            # 3. 启动录音线程，持续录音到缓冲区
            self.is_recording = True
            self._record_thread = threading.Thread(target=self._record_audio_to_buffer, daemon=True)
            self._record_thread.start()
            record_thread_start_time = time.time()
            logger.info(f"录音线程已启动 (耗时: {(record_thread_start_time - start_time) * 1000:.2f}ms)")
            
            # 4. 创建回调处理器
            self.callback = VoiceRecognitionCallback(
                audio_config=self.audio_config,
                result_callback=self.result_callback
            )
            # 将提前打开的音频流传递给回调处理器
            self.callback.mic = self.audio_mic
            self.callback.stream = self.audio_stream
            
            # 5. 创建识别对象
            self.recognition = Recognition(
                model=self.api_config.get('model', 'fun-asr-realtime'),
                format=self.audio_config['format'],
                sample_rate=self.audio_config['sample_rate'],
                semantic_punctuation_enabled=self.api_config.get('semantic_punctuation_enabled', False),
                callback=self.callback
            )
            
            # 6. 启动识别（异步建立WebSocket连接）
            recognition_start_time = time.time()
            self.recognition.start()
            logger.info(f"识别服务已启动 (耗时: {(recognition_start_time - start_time) * 1000:.2f}ms)")
            
            # 7. 在独立线程中发送音频数据（会先发送缓冲区数据）
            self._audio_thread = threading.Thread(target=self._send_audio_stream, daemon=True)
            self._audio_thread.start()
            
            total_time = (time.time() - start_time) * 1000
            logger.info(f"录音和识别已启动 (总耗时: {total_time:.2f}ms)")
            logger.info("音频流已立即开始录音，不会丢失任何音频数据")
            return True
        except Exception as e:
            logger.error(f"启动录音和识别失败: {e}", exc_info=True)
            self.is_recording = False
            # 清理资源
            self._cleanup_audio_resources()
            return False
    
    def _amplify_audio(self, audio_data: bytes) -> bytes:
        """
        放大音频音量两倍
        
        Args:
            audio_data: 原始音频数据（16位整数格式）
            
        Returns:
            bytes: 放大后的音频数据
        """
        try:
            logger.debug(f"开始处理音频数据，原始数据长度: {len(audio_data)} 字节")
            
            # 将bytes转换为numpy数组（16位整数）
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            original_max = np.max(np.abs(audio_array))
            logger.debug(f"原始音频数据最大值: {original_max}")
            
            # 放大两倍
            amplified_array = audio_array * 2
            
            # 处理溢出：16位整数范围是-32768到32767
            # 使用np.clip限制在有效范围内
            amplified_array = np.clip(amplified_array, -32768, 32767).astype(np.int16)
            
            clipped_count = np.sum((amplified_array == 32767) | (amplified_array == -32768))
            if clipped_count > 0:
                logger.debug(f"音频放大后发生溢出裁剪，裁剪样本数: {clipped_count}")
            
            amplified_max = np.max(np.abs(amplified_array))
            logger.debug(f"放大后音频数据最大值: {amplified_max}")
            
            # 转换回bytes
            amplified_data = amplified_array.tobytes()
            logger.debug(f"音频放大处理完成，输出数据长度: {len(amplified_data)} 字节")
            
            return amplified_data
        except Exception as e:
            logger.error(f"音频放大处理失败: {e}", exc_info=True)
            # 处理失败时返回原始数据，避免中断录音流程
            logger.warning("音频放大处理失败，使用原始音频数据")
            return audio_data
    
    def _record_audio_to_buffer(self) -> None:
        """
        在独立线程中持续录音到缓冲区
        确保在WebSocket连接建立之前就开始录音，不丢失任何音频
        """
        try:
            logger.debug("录音线程已启动，开始持续录音到缓冲区")
            
            while self.is_recording and self.audio_stream:
                try:
                    # 检查状态
                    if not self.is_recording:
                        break
                    
                    # 从麦克风读取音频数据
                    audio_data = self.audio_stream.read(
                        self.audio_config['chunk_size'],
                        exception_on_overflow=False
                    )
                    
                    # 将音频数据放入缓冲区（如果缓冲区已满，会丢弃最旧的数据）
                    try:
                        if self.audio_buffer.full():
                            # 缓冲区已满，丢弃最旧的数据
                            try:
                                self.audio_buffer.get_nowait()
                                logger.debug("音频缓冲区已满，丢弃最旧的数据")
                            except queue.Empty:
                                pass
                        
                        self.audio_buffer.put_nowait(audio_data)
                        logger.debug(f"音频数据已存入缓冲区，当前缓冲区大小: {self.audio_buffer.qsize()}")
                    except queue.Full:
                        logger.warning("音频缓冲区已满，无法存入新数据")
                    
                except Exception as e:
                    if self.is_recording:
                        logger.error(f"录音到缓冲区时出错: {e}", exc_info=True)
                    else:
                        logger.debug(f"录音到缓冲区时出错（可能因停止录音）: {e}")
                    break
            
            logger.debug("录音线程已结束")
        except Exception as e:
            logger.error(f"录音线程异常: {e}", exc_info=True)
    
    def _send_audio_stream(self) -> None:
        """
        在独立线程中发送音频流到识别服务
        先等待WebSocket连接建立，然后先发送缓冲区中的所有音频数据，再继续发送实时音频
        """
        try:
            logger.debug("音频流发送线程已启动")
            logger.info("音频音量放大功能已启用（放大倍数: 2倍）")
            
            # 等待WebSocket连接建立
            if self.callback:
                logger.info("等待WebSocket连接建立...")
                wait_start_time = time.time()
                connection_ready = self.callback.connection_ready.wait(timeout=5.0)
                wait_time = (time.time() - wait_start_time) * 1000
                
                if not connection_ready:
                    logger.error("等待WebSocket连接建立超时（5秒）")
                    return
                
                logger.info(f"WebSocket连接已建立 (等待耗时: {wait_time:.2f}ms)")
            else:
                logger.error("回调处理器未初始化")
                return
            
            # 检查识别对象是否已准备好
            if not self.recognition:
                logger.error("识别对象未初始化")
                return
            
            # 第一阶段：先发送缓冲区中的所有音频数据
            if self.audio_buffer:
                buffer_size = self.audio_buffer.qsize()
                if buffer_size > 0:
                    logger.info(f"开始发送缓冲区中的音频数据，共 {buffer_size} 个chunk")
                    buffer_send_start_time = time.time()
                    
                    sent_count = 0
                    while not self.audio_buffer.empty() and self.is_recording:
                        try:
                            # 从缓冲区获取音频数据
                            audio_data = self.audio_buffer.get_nowait()
                            
                            # 检查状态
                            if not self.is_recording or not self.recognition:
                                break
                            
                            # 在发送到接口前进行音量放大处理
                            amplified_audio_data = self._amplify_audio(audio_data)
                            
                            # 发送到识别服务
                            self.recognition.send_audio_frame(amplified_audio_data)
                            sent_count += 1
                            logger.debug(f"已发送缓冲区音频数据 {sent_count}/{buffer_size}")
                            
                        except queue.Empty:
                            break
                        except InvalidParameter as e:
                            if "Speech recognition has stopped" in str(e):
                                logger.debug("识别已停止，停止发送缓冲区数据")
                            else:
                                logger.warning(f"发送缓冲区音频数据时参数错误: {e}")
                            break
                        except Exception as e:
                            logger.error(f"发送缓冲区音频数据时出错: {e}", exc_info=True)
                            break
                    
                    buffer_send_time = (time.time() - buffer_send_start_time) * 1000
                    logger.info(f"缓冲区音频数据发送完成，共发送 {sent_count} 个chunk (耗时: {buffer_send_time:.2f}ms)")
                else:
                    logger.debug("缓冲区为空，无需发送缓存数据")
            
            # 第二阶段：继续从缓冲区读取并发送实时音频数据
            # 注意：录音线程会持续将音频数据存入缓冲区，这里从缓冲区读取即可
            # 这样可以避免两个线程同时从同一个音频流读取数据
            logger.info("开始从缓冲区读取并发送实时音频数据")
            realtime_count = 0
            
            while self.is_recording and self.audio_buffer is not None:
                try:
                    # 检查状态
                    if not self.is_recording or not self.recognition:
                        break
                    
                    # 从缓冲区获取音频数据（阻塞等待，最多等待100ms）
                    try:
                        audio_data = self.audio_buffer.get(timeout=0.1)
                    except queue.Empty:
                        # 缓冲区暂时为空，继续等待
                        continue
                    
                    # 检查状态
                    if not self.is_recording or not self.recognition:
                        break
                    
                    # 在发送到接口前进行音量放大处理
                    amplified_audio_data = self._amplify_audio(audio_data)
                    
                    # 发送到识别服务
                    self.recognition.send_audio_frame(amplified_audio_data)
                    realtime_count += 1
                    
                    if realtime_count % 10 == 0:  # 每10个chunk记录一次
                        logger.debug(f"已发送实时音频数据 {realtime_count} 个chunk")
                    
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
            
            logger.info(f"实时音频数据发送完成，共发送 {realtime_count} 个chunk")
            logger.debug("音频流发送线程已结束")
        except Exception as e:
            logger.error(f"音频流发送线程异常: {e}", exc_info=True)
    
    def _cleanup_audio_resources(self) -> None:
        """清理音频资源"""
        try:
            # 关闭音频流
            if self.audio_stream:
                try:
                    self.audio_stream.stop_stream()
                    self.audio_stream.close()
                    logger.debug("提前打开的音频流已关闭")
                except Exception as e:
                    logger.debug(f"关闭音频流时出错: {e}")
                self.audio_stream = None
            
            # 释放音频设备
            if self.audio_mic:
                try:
                    self.audio_mic.terminate()
                    logger.debug("提前打开的音频设备已释放")
                except Exception as e:
                    logger.debug(f"释放音频设备时出错: {e}")
                self.audio_mic = None
            
            # 清空缓冲区
            if self.audio_buffer:
                while not self.audio_buffer.empty():
                    try:
                        self.audio_buffer.get_nowait()
                    except queue.Empty:
                        break
                self.audio_buffer = None
                logger.debug("音频缓冲区已清空")
        except Exception as e:
            logger.error(f"清理音频资源时出错: {e}", exc_info=True)
    
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
            
            # 等待录音线程结束
            if self._record_thread and self._record_thread.is_alive():
                logger.debug("等待录音线程结束...")
                self._record_thread.join(timeout=1)
            
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
            
            # 等待音频发送线程结束
            if hasattr(self, '_audio_thread') and self._audio_thread.is_alive():
                logger.debug("等待音频发送线程结束...")
                self._audio_thread.join(timeout=2)
            
            # 清理音频资源
            self._cleanup_audio_resources()
            
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

