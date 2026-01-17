"""
Doubao (ByteDance) speech recognizer implementation
Integrates Doubao ASR API with the application using async-to-sync bridge
"""
import asyncio
import logging
import queue
import threading
import time
from typing import Optional

import aiohttp
import numpy as np
import pyaudio

from .base_recognizer import BaseRecognizer, RecognitionConfig, RecognitionResult
from .doubao_protocol import RequestBuilder, ResponseParser, AsrResponse

logger = logging.getLogger(__name__)


class DoubaoRecognizer(BaseRecognizer):
    """Doubao (ByteDance) speech recognizer"""

    def __init__(self, config: RecognitionConfig, app_id: str, access_token: str):
        """
        Initialize Doubao recognizer

        Args:
            config: Recognition configuration
            app_id: Doubao app ID
            access_token: Doubao access token
        """
        super().__init__(config)

        if not app_id or not app_id.strip():
            raise ValueError("Doubao app ID is required")
        if not access_token or not access_token.strip():
            raise ValueError("Doubao access token is required")

        self.app_id = app_id
        self.access_token = access_token

        # Get provider config
        provider_config = config.provider_config or {}
        self.url = provider_config.get(
            'url',
            'wss://openspeech.bytedance.com/api/v3/sauc/bigmodel_async'
        )
        self.resource_id = provider_config.get(
            'resource_id',
            'volc.seedasr.sauc.duration'
        )
        self.segment_duration = provider_config.get('segment_duration', 200)  # ms

        # Audio buffer
        self.audio_buffer: Optional[queue.Queue] = None
        self.audio_mic: Optional[pyaudio.PyAudio] = None
        self.audio_stream: Optional[pyaudio.Stream] = None
        self._record_thread: Optional[threading.Thread] = None
        self._recognition_thread: Optional[threading.Thread] = None

        # Calculate buffer size (approximately 2 seconds)
        buffer_duration_seconds = 2.0
        self.max_buffer_size = int(
            config.sample_rate * buffer_duration_seconds / config.chunk_size
        )

        # Async event loop management
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None

        # Recognition state
        self.full_text = ""
        self._seq = 1
        self._ws_ready = threading.Event()  # Event to signal WebSocket is ready

        logger.info(
            f"Doubao recognizer initialized: url={self.url}, resource_id={self.resource_id}, "
            f"buffer_size={self.max_buffer_size} chunks (~{buffer_duration_seconds}s)"
        )

    def start_recording(self) -> bool:
        """Start recording and recognition"""
        if self.is_recording:
            logger.warning("Doubao recording already in progress")
            return False

        try:
            start_time = time.time()
            logger.info("Starting Doubao recording and recognition")

            # Create audio buffer
            self.audio_buffer = queue.Queue(maxsize=self.max_buffer_size)
            logger.debug(f"Audio buffer created, max size: {self.max_buffer_size} chunks")

            # Reset WebSocket ready event
            self._ws_ready.clear()

            # Mark as recording FIRST, before opening audio stream
            self.is_recording = True

            # Start recognition thread FIRST (to establish WebSocket connection in background)
            self._recognition_thread = threading.Thread(target=self._run_recognition_async, daemon=True)
            self._recognition_thread.start()
            recognition_thread_time = (time.time() - start_time) * 1000
            logger.info(f"Recognition thread started for Doubao (elapsed: {recognition_thread_time:.2f}ms)")

            # Wait for WebSocket connection to be ready before starting audio capture
            logger.info("Waiting for Doubao WebSocket connection to be ready...")
            wait_start = time.time()
            ws_ready = self._ws_ready.wait(timeout=5.0)
            wait_time = (time.time() - wait_start) * 1000

            if not ws_ready:
                logger.error("Doubao WebSocket connection timeout (5 seconds)")
                self.is_recording = False
                self.audio_buffer = None
                return False

            logger.info(f"Doubao WebSocket connection ready (wait time: {wait_time:.2f}ms)")

            # Open audio stream AFTER WebSocket is ready
            try:
                logger.info("Opening audio stream for Doubao...")
                self.audio_mic = pyaudio.PyAudio()
                self.audio_stream = self.audio_mic.open(
                    format=pyaudio.paInt16,
                    channels=self.config.channels,
                    rate=self.config.sample_rate,
                    input=True,
                    frames_per_buffer=self.config.chunk_size
                )
                audio_stream_time = (time.time() - start_time) * 1000
                logger.info(f"Audio stream opened for Doubao (elapsed: {audio_stream_time:.2f}ms)")
            except Exception as e:
                logger.error(f"Failed to open audio stream for Doubao: {e}", exc_info=True)
                self.is_recording = False
                self.audio_buffer = None
                return False

            # Add a small stabilization delay to ensure audio stream is fully ready
            logger.debug("Waiting for audio stream to stabilize (100ms)...")
            time.sleep(0.1)

            # Start recording thread
            self._record_thread = threading.Thread(target=self._record_audio_to_buffer, daemon=True)
            self._record_thread.start()
            record_time = (time.time() - start_time) * 1000
            logger.info(f"Recording thread started for Doubao (elapsed: {record_time:.2f}ms)")

            total_time = (time.time() - start_time) * 1000
            logger.info(f"Doubao recording and recognition started successfully (total: {total_time:.2f}ms)")
            return True

        except Exception as e:
            logger.error(f"Failed to start Doubao recording and recognition: {e}", exc_info=True)
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
            logger.debug("Doubao recording thread started, recording to buffer")

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

            logger.debug("Doubao recording thread ended")
        except Exception as e:
            logger.error(f"Doubao recording thread exception: {e}", exc_info=True)

    def _run_recognition_async(self) -> None:
        """Run async recognition in separate thread with its own event loop"""
        try:
            logger.info("Starting Doubao async recognition thread")

            # Create new event loop for this thread
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

            # Run recognition
            self._loop.run_until_complete(self._recognition_task())

            logger.info("Doubao async recognition thread ended")
        except Exception as e:
            logger.error(f"Doubao async recognition thread exception: {e}", exc_info=True)
        finally:
            if self._loop:
                self._loop.close()
                self._loop = None

    async def _recognition_task(self) -> None:
        """Async recognition task"""
        try:
            logger.info("Doubao recognition task started")

            # Create request builder
            request_builder = RequestBuilder(
                app_key=self.app_id,
                access_key=self.access_token,
                resource_id=self.resource_id
            )
            logger.info(f"Doubao RequestBuilder created - app_id: {self.app_id}, resource_id: {self.resource_id}")

            # Create session
            self._session = aiohttp.ClientSession()

            # Connect WebSocket
            headers = request_builder.new_auth_headers()
            logger.info(f"Connecting to Doubao WebSocket: {self.url}")
            logger.debug(f"WebSocket headers: {headers}")
            self._ws = await self._session.ws_connect(self.url, headers=headers)
            logger.info("Doubao WebSocket connection established")

            # Send full client request
            self._seq = 1
            full_request = RequestBuilder.new_full_client_request(
                self._seq,
                sample_rate=self.config.sample_rate
            )
            await self._ws.send_bytes(full_request)
            logger.info(f"Sent full client request to Doubao, seq={self._seq}, sample_rate={self.config.sample_rate}")

            # Receive initial response
            msg = await self._ws.receive()
            if msg.type == aiohttp.WSMsgType.BINARY:
                response = ResponseParser.parse_response(msg.data)
                logger.info(f"Received initial response from Doubao: {response}")
                if response.payload_msg:
                    logger.debug(f"Initial response payload: {response.payload_msg}")
                if response.code != 0:
                    logger.error(f"Initial response has error code: {response.code}, payload: {response.payload_msg}")
            else:
                logger.error(f"Unexpected message type from Doubao: {msg.type}")

            self._seq += 1

            # Signal that WebSocket is ready for audio streaming
            self._ws_ready.set()
            logger.info("Doubao WebSocket ready for audio streaming")

            # Start concurrent send/receive tasks
            send_task = asyncio.create_task(self._send_audio_task())
            recv_task = asyncio.create_task(self._receive_results_task())

            # Wait for both tasks
            await asyncio.gather(send_task, recv_task, return_exceptions=True)

            logger.info("Doubao recognition task completed")

        except Exception as e:
            logger.error(f"Doubao recognition task error: {e}", exc_info=True)
        finally:
            # Cleanup
            if self._ws and not self._ws.closed:
                await self._ws.close()
                logger.debug("Doubao WebSocket closed")
            if self._session and not self._session.closed:
                await self._session.close()
                logger.debug("Doubao session closed")

    async def _send_audio_task(self) -> None:
        """Send audio data to Doubao"""
        try:
            logger.info("Doubao audio sending task started")
            logger.info("Audio volume amplification enabled (2x amplification)")

            # WebSocket should already be ready at this point (set in _recognition_task)
            # Just verify it's still ready
            if not self._ws_ready.is_set():
                logger.warning("WebSocket not ready in audio task, this should not happen")
                await asyncio.sleep(0.1)  # Small fallback wait

            # Collect and send realtime audio chunks
            logger.info("Starting realtime audio streaming to Doubao")

            audio_to_send = []
            last_send_time = time.time()
            sent_count = 0

            while self.is_recording:
                try:
                    # Get audio from buffer (non-blocking with short timeout)
                    try:
                        chunk = self.audio_buffer.get(timeout=0.05)
                        audio_to_send.append(chunk)
                    except queue.Empty:
                        pass  # No new audio yet

                    # Calculate time since last send
                    current_time = time.time()
                    time_since_last_send = (current_time - last_send_time) * 1000  # ms

                    # Send audio when we have enough data OR enough time has passed
                    # Calculate expected chunk count for segment_duration
                    chunk_duration_ms = (self.config.chunk_size / self.config.sample_rate / self.config.channels / 2) * 1000
                    chunks_per_segment = max(1, int(self.segment_duration / chunk_duration_ms))

                    should_send = (
                        len(audio_to_send) >= chunks_per_segment or
                        (audio_to_send and time_since_last_send >= self.segment_duration)
                    )

                    if should_send:
                        # Combine chunks into segment
                        segment = b''.join(audio_to_send)
                        audio_to_send = []  # Clear the buffer

                        # Amplify audio
                        amplified_segment = self._amplify_audio(segment)

                        # Send to Doubao
                        is_last = False  # Will send last flag when stopping
                        audio_request = RequestBuilder.new_audio_only_request(
                            self._seq,
                            amplified_segment,
                            is_last=is_last
                        )
                        await self._ws.send_bytes(audio_request)
                        sent_count += 1
                        logger.info(f"Sent audio segment #{sent_count} to Doubao, seq={self._seq}, size={len(segment)} bytes")

                        self._seq += 1
                        last_send_time = current_time

                    # Small delay to prevent busy loop
                    await asyncio.sleep(0.01)

                except Exception as e:
                    if self.is_recording:
                        logger.error(f"Error sending audio to Doubao: {e}", exc_info=True)
                    break

            # Send final chunk with last flag
            if audio_to_send:
                segment = b''.join(audio_to_send)
                amplified_segment = self._amplify_audio(segment)
                audio_request = RequestBuilder.new_audio_only_request(
                    self._seq,
                    amplified_segment,
                    is_last=True
                )
                await self._ws.send_bytes(audio_request)
                logger.info(f"Sent final audio segment to Doubao with last flag, seq={self._seq}, size={len(segment)} bytes")
            else:
                # Send empty last packet if no pending audio
                audio_request = RequestBuilder.new_audio_only_request(
                    self._seq,
                    b'',
                    is_last=True
                )
                await self._ws.send_bytes(audio_request)
                logger.info(f"Sent empty final packet to Doubao with last flag, seq={self._seq}")

            logger.info(f"Doubao audio sending task completed, total segments sent: {sent_count}")

        except Exception as e:
            logger.error(f"Doubao audio sending task error: {e}", exc_info=True)

    async def _receive_results_task(self) -> None:
        """Receive recognition results from Doubao"""
        try:
            logger.info("Doubao results receiving task started")

            async for msg in self._ws:
                if msg.type == aiohttp.WSMsgType.BINARY:
                    response = ResponseParser.parse_response(msg.data)
                    logger.debug(f"Received Doubao response: {response}")

                    # Check for errors first
                    if response.code != 0:
                        error_msg = f"Doubao returned error code: {response.code}"
                        if response.payload_msg:
                            error_msg += f", message: {response.payload_msg}"
                        logger.error(error_msg)
                        # Continue to check if there's still useful data

                    # Process result
                    if response.payload_msg and 'result' in response.payload_msg:
                        result_data = response.payload_msg['result']
                        if 'text' in result_data:
                            text = result_data['text']
                            logger.info(f"Doubao recognized text: {text}")
                            self.full_text = text

                    # Check if last package
                    if response.is_last_package:
                        logger.info("Received last package from Doubao")

                        # Invoke callback with final result (even if there was an error)
                        if self.full_text:
                            result = RecognitionResult(
                                text=self.full_text,
                                is_final=True,
                                confidence=1.0,
                                metadata={'provider': 'doubao'}
                            )
                            self._invoke_callback(result)
                        else:
                            logger.warning("Doubao recognition completed but no text was recognized")

                        self.full_text = ""
                        break

                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"Doubao WebSocket error: {msg.data}")
                    break
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    logger.info("Doubao WebSocket connection closed by server")
                    break

            logger.info("Doubao results receiving task completed")

        except Exception as e:
            logger.error(f"Doubao results receiving task error: {e}", exc_info=True)

    def _cleanup_audio_resources(self) -> None:
        """Cleanup audio resources"""
        try:
            # Close audio stream
            if self.audio_stream:
                try:
                    self.audio_stream.stop_stream()
                    self.audio_stream.close()
                    logger.debug("Doubao audio stream closed")
                except Exception as e:
                    logger.debug(f"Error closing Doubao audio stream: {e}")
                self.audio_stream = None

            # Release audio device
            if self.audio_mic:
                try:
                    self.audio_mic.terminate()
                    logger.debug("Doubao audio device released")
                except Exception as e:
                    logger.debug(f"Error releasing Doubao audio device: {e}")
                self.audio_mic = None

            # Clear buffer
            if self.audio_buffer:
                while not self.audio_buffer.empty():
                    try:
                        self.audio_buffer.get_nowait()
                    except queue.Empty:
                        break
                self.audio_buffer = None
                logger.debug("Doubao audio buffer cleared")
        except Exception as e:
            logger.error(f"Error cleaning up Doubao audio resources: {e}", exc_info=True)

    def stop_recording(self) -> bool:
        """Stop recording and recognition"""
        if not self.is_recording:
            logger.warning("Doubao recording not in progress")
            return False

        try:
            logger.info("Stopping Doubao recording and recognition")

            # Mark as stopped
            self.is_recording = False

            # Wait for recording thread
            if self._record_thread and self._record_thread.is_alive():
                logger.debug("Waiting for Doubao recording thread to end...")
                self._record_thread.join(timeout=1)

            # Wait for recognition thread
            if self._recognition_thread and self._recognition_thread.is_alive():
                logger.debug("Waiting for Doubao recognition thread to end...")
                self._recognition_thread.join(timeout=3)

            # Cleanup audio resources
            self._cleanup_audio_resources()

            logger.info("Doubao recording and recognition stopped")
            return True
        except Exception as e:
            logger.error(f"Failed to stop Doubao recording and recognition: {e}", exc_info=True)
            return False

    def is_currently_recording(self) -> bool:
        """Check if currently recording"""
        return self.is_recording

    def cleanup(self) -> None:
        """Cleanup resources"""
        logger.debug("Cleaning up Doubao recognizer")
        if self.is_recording:
            self.stop_recording()
        super().cleanup()
