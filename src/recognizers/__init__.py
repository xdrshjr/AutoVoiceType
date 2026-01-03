"""
Speech recognizer module
Provides abstraction layer for different speech recognition providers
"""
from .base_recognizer import BaseRecognizer, RecognitionConfig, RecognitionResult
from .recognizer_factory import RecognizerFactory

__all__ = [
    'BaseRecognizer',
    'RecognitionConfig',
    'RecognitionResult',
    'RecognizerFactory'
]
