"""
Base recognizer interface
Defines the contract for all speech recognition providers
"""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Optional, Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class RecognitionConfig:
    """Configuration for speech recognition"""
    # Audio configuration
    sample_rate: int = 16000
    channels: int = 1
    chunk_size: int = 3200
    audio_format: str = "pcm"

    # Recognition configuration
    semantic_punctuation_enabled: bool = False
    timeout: int = 30

    # Provider-specific configuration
    provider_config: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate configuration after initialization"""
        if self.sample_rate not in [8000, 16000, 44100, 48000]:
            logger.warning(f"Unusual sample rate: {self.sample_rate}, standard values are 8000, 16000, 44100, 48000")

        if self.channels not in [1, 2]:
            raise ValueError(f"Invalid channels: {self.channels}, must be 1 or 2")

        if self.chunk_size <= 0:
            raise ValueError(f"Invalid chunk_size: {self.chunk_size}, must be positive")

        logger.debug(f"RecognitionConfig initialized: sample_rate={self.sample_rate}, channels={self.channels}, chunk_size={self.chunk_size}")


@dataclass
class RecognitionResult:
    """Result from speech recognition"""
    text: str
    is_final: bool = True
    confidence: float = 1.0
    metadata: Optional[Dict[str, Any]] = None

    def __str__(self):
        return f"RecognitionResult(text='{self.text}', is_final={self.is_final}, confidence={self.confidence})"


class BaseRecognizer(ABC):
    """
    Abstract base class for speech recognizers
    All provider implementations must inherit from this class
    """

    def __init__(self, config: RecognitionConfig):
        """
        Initialize recognizer

        Args:
            config: Recognition configuration
        """
        self.config = config
        self.is_recording = False
        self.result_callback: Optional[Callable[[RecognitionResult], None]] = None

        logger.info(f"Initializing {self.__class__.__name__} with config: {config}")

    def set_result_callback(self, callback: Callable[[RecognitionResult], None]) -> None:
        """
        Set callback for recognition results

        Args:
            callback: Function to call with recognition results
        """
        self.result_callback = callback
        logger.debug(f"Result callback set for {self.__class__.__name__}")

    @abstractmethod
    def start_recording(self) -> bool:
        """
        Start recording and recognition

        Returns:
            bool: True if started successfully, False otherwise
        """
        pass

    @abstractmethod
    def stop_recording(self) -> bool:
        """
        Stop recording and recognition

        Returns:
            bool: True if stopped successfully, False otherwise
        """
        pass

    @abstractmethod
    def is_currently_recording(self) -> bool:
        """
        Check if currently recording

        Returns:
            bool: True if recording, False otherwise
        """
        pass

    def _invoke_callback(self, result: RecognitionResult) -> None:
        """
        Invoke the result callback if set

        Args:
            result: Recognition result to pass to callback
        """
        if self.result_callback:
            try:
                logger.debug(f"Invoking result callback with: {result}")
                self.result_callback(result)
            except Exception as e:
                logger.error(f"Error in result callback: {e}", exc_info=True)
        else:
            logger.warning("Result callback not set, recognition result will be discarded")

    def cleanup(self) -> None:
        """
        Cleanup resources
        Override in subclasses if needed
        """
        logger.debug(f"Cleaning up {self.__class__.__name__}")
        pass
