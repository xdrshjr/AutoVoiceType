"""
DashScope (Alibaba Cloud) speech recognizer implementation
"""
import logging
import queue
import threading
import time
from typing import Optional

import dashscope
import numpy as np
import pyaudio
from dashscope.audio.asr import Recognition, RecognitionCallback, RecognitionResult as DashScopeResult
from dashscope.common.error import InvalidParameter

from .base_recognizer import BaseRecognizer, RecognitionConfig, RecognitionResult

logger = logging.getLogger(__name__)


class DashScopeRecognitionCallback(RecognitionCallback):
    """DashScope recognition callback handler"""

    def __init__(self, audio_config: dict, recognizer: 'DashScopeRecognizer'):
        """
        Initialize callback handler

        Args:
            audio_config: Audio configuration dictionary
            recognizer: Reference to parent recognizer
        """
        super().__init__()
        self.audio_config = audio_config
        self.recognizer = recognizer
        self.mic: Optional[pyaudio.PyAudio] = None
        self.stream: Optional[pyaudio.Stream] = None
        self.full_text = ""
        self.connection_ready = threading.Event()

        logger.debug("DashScope recognition callback handler initialized")

    def on_open(self) -> None:
        """WebSocket connection opened callback"""
        try:
            logger.info("DashScope WebSocket connection established")
            self.connection_ready.set()
            logger.info("DashScope WebSocket connection ready for audio streaming")
        except Exception as e:
            logger.error(f"Error in DashScope on_open: {e}", exc_info=True)
            raise

    def on_close(self) -> None:
        """WebSocket connection closed callback"""
        try:
            logger.info("DashScope WebSocket connection closed")
            self.connection_ready.clear()
            logger.debug("DashScope WebSocket connection state reset")
        except Exception as e:
            logger.error(f"Error in DashScope on_close: {e}", exc_info=True)

    def on_complete(self) -> None:
        """Recognition complete callback"""
        logger.info("DashScope recognition completed")

        if self.full_text:
            try:
                result = RecognitionResult(
                    text=self.full_text,
                    is_final=True,
                    confidence=1.0,
                    metadata={'provider': 'dashscope'}
                )
                self.recognizer._invoke_callback(result)
                logger.debug(f"Final DashScope recognition text: {self.full_text}")
            except Exception as e:
                logger.error(f"Error invoking callback in DashScope on_complete: {e}", exc_info=True)

        self.full_text = ""

    def on_error(self, message) -> None:
        """Recognition error callback"""
        logger.error(f"DashScope recognition error - Request ID: {message.request_id}, Error: {message.message}")

        try:
            if self.stream and hasattr(self.stream, 'is_active') and self.stream.is_active():
                self.stream.stop_stream()
                self.stream.close()
        except Exception as e:
            logger.error(f"Error cleaning up resources in DashScope on_error: {e}", exc_info=True)

    def on_event(self, result: DashScopeResult) -> None:
        """
        Recognition result event callback

        Args:
            result: DashScope recognition result
        """
        try:
            sentence = result.get_sentence()

            if 'text' in sentence:
                text = sentence['text']
                logger.debug(f"DashScope recognized text fragment: {text}")

                self.full_text = text

                if DashScopeResult.is_sentence_end(sentence):
                    logger.info(
                        f"DashScope sentence end - Request ID: {result.get_request_id()}, "
                        f"Usage: {result.get_usage(sentence)}"
                    )
        except Exception as e:
            logger.error(f"Error processing DashScope recognition result: {e}", exc_info=True)


class DashScopeRecognizer(BaseRecognizer):
    """DashScope (Alibaba Cloud) speech recognizer"""

    def __init__(self, config: RecognitionConfig, api_key: str):
        """
        Initialize DashScope recognizer

        Args:
            config: Recognition configuration
            api_key: DashScope API key
        """
        super().__init__(config)

        if not api_key or not api_key.strip():
            raise ValueError("DashScope API key is required")

        self.api_key = api_key
        self.recognition: Optional[Recognition] = None
        self.callback: Optional[DashScopeRecognitionCallback] = None

        # Audio buffer
        self.audio_buffer: Optional[queue.Queue] = None
        self.audio_mic: Optional[pyaudio.PyAudio] = None
        self.audio_stream: Optional[pyaudio.Stream] = None
        self._record_thread: Optional[threading.Thread] = None
        self._audio_thread: Optional[threading.Thread] = None

        # Calculate buffer size (approximately 2 seconds)
        buffer_duration_seconds = 2.0
        self.max_buffer_size = int(
            config.sample_rate * buffer_duration_seconds / config.chunk_size
        )

        # Configure DashScope
        dashscope.api_key = self.api_key
        provider_config = config.provider_config or {}
        dashscope.base_websocket_api_url = provider_config.get(
            'base_websocket_url',
            'wss://dashscope.aliyuncs.com/api-ws/v1/inference'
        )

        logger.info(f"DashScope recognizer initialized, buffer size: {self.max_buffer_size} chunks (~{buffer_duration_seconds}s)")

    def start_recording(self) -> bool:
        """Start recording and recognition"""
        if self.is_recording:
            logger.warning("DashScope recording already in progress")
            return False

        try:
            start_time = time.time()
            logger.info("Starting DashScope recording and recognition")

            # Create audio buffer
            self.audio_buffer = queue.Queue(maxsize=self.max_buffer_size)
            logger.debug(f"Audio buffer created, max size: {self.max_buffer_size} chunks")

            # Create callback handler first (before opening audio stream)
            self.callback = DashScopeRecognitionCallback(
                audio_config={
                    'sample_rate': self.config.sample_rate,
                    'channels': self.config.channels,
                    'chunk_size': self.config.chunk_size,
                    'format': self.config.audio_format
                },
                recognizer=self
            )
            callback_time = (time.time() - start_time) * 1000
            logger.debug(f"Callback handler created (elapsed: {callback_time:.2f}ms)")

            # Create and start recognition object FIRST (establish WebSocket connection)
            provider_config = self.config.provider_config or {}
            model_name = provider_config.get('model', 'qwen3-asr-flash-realtime')
            logger.info(f"Using DashScope recognition model: {model_name}")

            self.recognition = Recognition(
                model=model_name,
                format=self.config.audio_format,
                sample_rate=self.config.sample_rate,
                semantic_punctuation_enabled=self.config.semantic_punctuation_enabled,
                callback=self.callback
            )
            logger.debug(
                f"DashScope recognition object created: model={model_name}, "
                f"format={self.config.audio_format}, sample_rate={self.config.sample_rate}"
            )

            # Start recognition to establish WebSocket connection
            recognition_start = time.time()
            self.recognition.start()
            logger.info(f"DashScope recognition service started (elapsed: {(recognition_start - start_time) * 1000:.2f}ms)")

            # Wait for WebSocket connection to be ready BEFORE starting audio capture
            logger.info("Waiting for DashScope WebSocket connection to be ready...")
            wait_start = time.time()
            connection_ready = self.callback.connection_ready.wait(timeout=5.0)
            wait_time = (time.time() - wait_start) * 1000

            if not connection_ready:
                logger.error("DashScope WebSocket connection timeout (5 seconds)")
                self._cleanup_audio_resources()
                return False

            logger.info(f"DashScope WebSocket connection ready (wait time: {wait_time:.2f}ms)")

            # Now that WebSocket is ready, open audio stream
            try:
                logger.info("Opening audio stream for DashScope...")
                self.audio_mic = pyaudio.PyAudio()
                self.audio_stream = self.audio_mic.open(
                    format=pyaudio.paInt16,
                    channels=self.config.channels,
                    rate=self.config.sample_rate,
                    input=True,
                    frames_per_buffer=self.config.chunk_size
                )
                audio_stream_time = (time.time() - start_time) * 1000
                logger.info(f"Audio stream opened for DashScope (elapsed: {audio_stream_time:.2f}ms)")
            except Exception as e:
                logger.error(f"Failed to open audio stream for DashScope: {e}", exc_info=True)
                self.audio_buffer = None
                if self.recognition:
                    self.recognition.stop()
                    self.recognition = None
                return False

            # Link audio resources to callback
            self.callback.mic = self.audio_mic
            self.callback.stream = self.audio_stream

            # Add a small stabilization delay to ensure audio stream is fully ready
            logger.debug("Waiting for audio stream to stabilize (100ms)...")
            time.sleep(0.1)

            # NOW start recording thread (audio capture begins here)
            self.is_recording = True
            self._record_thread = threading.Thread(target=self._record_audio_to_buffer, daemon=True)
            self._record_thread.start()
            record_time = (time.time() - start_time) * 1000
            logger.info(f"Recording thread started for DashScope (elapsed: {record_time:.2f}ms)")

            # Start audio streaming thread (this will send immediately since WebSocket is ready)
            self._audio_thread = threading.Thread(target=self._send_audio_stream, daemon=True)
            self._audio_thread.start()

            total_time = (time.time() - start_time) * 1000
            logger.info(f"DashScope recording and recognition started successfully (total: {total_time:.2f}ms)")
            return True

        except Exception as e:
            logger.error(f"Failed to start DashScope recording and recognition: {e}", exc_info=True)
            self.is_recording = False
            self._cleanup_audio_resources()
            return False

    def _amplify_audio(self, audio_data: bytes) -> bytes:
        """
        Amplify audio volume by 2x

        Args:
            audio_data: Raw audio data (16-bit integers)

        Returns:
            bytes: Amplified audio data
        """
        try:
            logger.debug(f"Amplifying audio data, original size: {len(audio_data)} bytes")

            # Convert bytes to numpy array (16-bit integers)
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            original_max = np.max(np.abs(audio_array))
            logger.debug(f"Original audio max value: {original_max}")

            # Amplify by 2x
            amplified_array = audio_array * 2

            # Handle overflow: 16-bit integer range is -32768 to 32767
            amplified_array = np.clip(amplified_array, -32768, 32767).astype(np.int16)

            clipped_count = np.sum((amplified_array == 32767) | (amplified_array == -32768))
            if clipped_count > 0:
                logger.debug(f"Audio clipping occurred, clipped samples: {clipped_count}")

            amplified_max = np.max(np.abs(amplified_array))
            logger.debug(f"Amplified audio max value: {amplified_max}")

            amplified_data = amplified_array.tobytes()
            logger.debug(f"Audio amplification complete, output size: {len(amplified_data)} bytes")

            return amplified_data
        except Exception as e:
            logger.error(f"Audio amplification failed: {e}", exc_info=True)
            logger.warning("Audio amplification failed, using original audio data")
            return audio_data

    def _record_audio_to_buffer(self) -> None:
        """Record audio to buffer in separate thread"""
        try:
            logger.debug("DashScope recording thread started, recording to buffer")

            while self.is_recording and self.audio_stream:
                try:
                    if not self.is_recording:
                        break

                    # Read audio data from microphone
                    audio_data = self.audio_stream.read(
                        self.config.chunk_size,
                        exception_on_overflow=False
                    )

                    # Put audio data into buffer
                    try:
                        # Use blocking put with timeout to avoid data loss
                        # If buffer is full, wait briefly for space to become available
                        self.audio_buffer.put(audio_data, timeout=0.5)
                        logger.debug(f"Audio data stored in buffer, current buffer size: {self.audio_buffer.qsize()}")
                    except queue.Full:
                        # This should rarely happen now that WebSocket is established first
                        logger.warning("Audio buffer full, cannot store new data - possible audio streaming lag")
                        # Don't discard the data - the stream consumer should be keeping up

                except Exception as e:
                    if self.is_recording:
                        logger.error(f"Error recording to buffer: {e}", exc_info=True)
                    else:
                        logger.debug(f"Error recording to buffer (likely due to stopping): {e}")
                    break

            logger.debug("DashScope recording thread ended")
        except Exception as e:
            logger.error(f"DashScope recording thread exception: {e}", exc_info=True)

    def _send_audio_stream(self) -> None:
        """Send audio stream to recognition service in separate thread"""
        try:
            logger.debug("DashScope audio streaming thread started")
            logger.info("Audio volume amplification enabled (2x amplification)")

            # Verify prerequisites
            if not self.callback:
                logger.error("Callback handler not initialized")
                return

            if not self.recognition:
                logger.error("Recognition object not initialized")
                return

            # WebSocket should already be connected (verified in start_recording)
            # Double-check connection is ready
            if not self.callback.connection_ready.is_set():
                logger.warning("WebSocket connection not ready, waiting...")
                connection_ready = self.callback.connection_ready.wait(timeout=2.0)
                if not connection_ready:
                    logger.error("WebSocket connection timeout in audio thread")
                    return

            logger.info("Starting realtime audio streaming to DashScope")

            # Send realtime audio data
            sent_count = 0

            while self.is_recording and self.audio_buffer is not None:
                try:
                    if not self.is_recording or not self.recognition:
                        break

                    # Get audio data from buffer (blocking, timeout 100ms)
                    try:
                        audio_data = self.audio_buffer.get(timeout=0.1)
                    except queue.Empty:
                        # Buffer temporarily empty, continue waiting
                        continue

                    if not self.is_recording or not self.recognition:
                        break

                    # Amplify audio before sending
                    amplified_audio_data = self._amplify_audio(audio_data)

                    # Send to recognition service
                    self.recognition.send_audio_frame(amplified_audio_data)
                    sent_count += 1

                    if sent_count % 10 == 0:  # Log every 10 chunks
                        logger.debug(f"Sent {sent_count} realtime audio chunks to DashScope")

                except InvalidParameter as e:
                    if "Speech recognition has stopped" in str(e):
                        logger.debug("DashScope recognition stopped, stopping audio send")
                    else:
                        logger.warning(f"Parameter error sending audio to DashScope: {e}")
                    break
                except Exception as e:
                    if self.is_recording:
                        logger.error(f"Error sending audio to DashScope: {e}", exc_info=True)
                    else:
                        logger.debug(f"Error sending audio (likely due to stopping): {e}")
                    break

            logger.info(f"Realtime audio sending complete, sent {sent_count} chunks to DashScope")
            logger.debug("DashScope audio streaming thread ended")
        except Exception as e:
            logger.error(f"DashScope audio streaming thread exception: {e}", exc_info=True)

    def _cleanup_audio_resources(self) -> None:
        """Cleanup audio resources"""
        try:
            # Close audio stream
            if self.audio_stream:
                try:
                    self.audio_stream.stop_stream()
                    self.audio_stream.close()
                    logger.debug("DashScope audio stream closed")
                except Exception as e:
                    logger.debug(f"Error closing DashScope audio stream: {e}")
                self.audio_stream = None

            # Release audio device
            if self.audio_mic:
                try:
                    self.audio_mic.terminate()
                    logger.debug("DashScope audio device released")
                except Exception as e:
                    logger.debug(f"Error releasing DashScope audio device: {e}")
                self.audio_mic = None

            # Clear buffer
            if self.audio_buffer:
                while not self.audio_buffer.empty():
                    try:
                        self.audio_buffer.get_nowait()
                    except queue.Empty:
                        break
                self.audio_buffer = None
                logger.debug("DashScope audio buffer cleared")
        except Exception as e:
            logger.error(f"Error cleaning up DashScope audio resources: {e}", exc_info=True)

    def stop_recording(self) -> bool:
        """Stop recording and recognition"""
        if not self.is_recording:
            logger.warning("DashScope recording not in progress")
            return False

        try:
            logger.info("Stopping DashScope recording and recognition")

            # Mark as stopped
            self.is_recording = False

            # Wait for recording thread
            if self._record_thread and self._record_thread.is_alive():
                logger.debug("Waiting for DashScope recording thread to end...")
                self._record_thread.join(timeout=1)

            # Stop recognition
            if self.recognition:
                self.recognition.stop()

                # Get performance metrics
                try:
                    request_id = self.recognition.get_last_request_id()
                    first_delay = self.recognition.get_first_package_delay()
                    last_delay = self.recognition.get_last_package_delay()

                    logger.info(
                        f"DashScope recognition metrics - Request ID: {request_id}, "
                        f"First package delay: {first_delay}ms, Last package delay: {last_delay}ms"
                    )
                except Exception as e:
                    logger.debug(f"Failed to get DashScope performance metrics: {e}")

                self.recognition = None

            # Wait for audio streaming thread
            if hasattr(self, '_audio_thread') and self._audio_thread.is_alive():
                logger.debug("Waiting for DashScope audio streaming thread to end...")
                self._audio_thread.join(timeout=2)

            # Cleanup audio resources
            self._cleanup_audio_resources()

            logger.info("DashScope recording and recognition stopped")
            return True
        except Exception as e:
            logger.error(f"Failed to stop DashScope recording and recognition: {e}", exc_info=True)
            return False

    def is_currently_recording(self) -> bool:
        """Check if currently recording"""
        return self.is_recording

    def cleanup(self) -> None:
        """Cleanup resources"""
        logger.debug("Cleaning up DashScope recognizer")
        if self.is_recording:
            self.stop_recording()
        super().cleanup()
