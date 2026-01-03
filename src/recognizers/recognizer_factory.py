"""
Recognizer factory
Creates appropriate recognizer instances based on provider configuration
"""
import logging
from typing import Dict, Any

from .base_recognizer import BaseRecognizer, RecognitionConfig
from .dashscope_recognizer import DashScopeRecognizer
from .doubao_recognizer import DoubaoRecognizer

logger = logging.getLogger(__name__)


class RecognizerFactory:
    """Factory for creating speech recognizer instances"""

    # Supported providers
    PROVIDER_DASHSCOPE = 'dashscope'
    PROVIDER_DOUBAO = 'doubao'

    SUPPORTED_PROVIDERS = [PROVIDER_DASHSCOPE, PROVIDER_DOUBAO]

    @staticmethod
    def create_recognizer(
        provider: str,
        config: RecognitionConfig,
        credentials: Dict[str, Any]
    ) -> BaseRecognizer:
        """
        Create a recognizer instance based on provider

        Args:
            provider: Provider name ('dashscope' or 'doubao')
            config: Recognition configuration
            credentials: Provider-specific credentials

        Returns:
            BaseRecognizer: Recognizer instance

        Raises:
            ValueError: If provider is not supported or credentials are invalid
        """
        provider = provider.lower().strip()

        if provider not in RecognizerFactory.SUPPORTED_PROVIDERS:
            raise ValueError(
                f"Unsupported provider: {provider}. "
                f"Supported providers: {', '.join(RecognizerFactory.SUPPORTED_PROVIDERS)}"
            )

        logger.info(f"Creating recognizer for provider: {provider}")

        if provider == RecognizerFactory.PROVIDER_DASHSCOPE:
            return RecognizerFactory._create_dashscope_recognizer(config, credentials)
        elif provider == RecognizerFactory.PROVIDER_DOUBAO:
            return RecognizerFactory._create_doubao_recognizer(config, credentials)
        else:
            raise ValueError(f"Unknown provider: {provider}")

    @staticmethod
    def _create_dashscope_recognizer(
        config: RecognitionConfig,
        credentials: Dict[str, Any]
    ) -> DashScopeRecognizer:
        """
        Create DashScope recognizer

        Args:
            config: Recognition configuration
            credentials: DashScope credentials

        Returns:
            DashScopeRecognizer: DashScope recognizer instance

        Raises:
            ValueError: If API key is missing
        """
        api_key = credentials.get('api_key', '')
        if not api_key or not api_key.strip():
            raise ValueError("DashScope API key is required")

        logger.info("Creating DashScope recognizer")
        logger.debug(f"DashScope config: {config}")

        return DashScopeRecognizer(config=config, api_key=api_key)

    @staticmethod
    def _create_doubao_recognizer(
        config: RecognitionConfig,
        credentials: Dict[str, Any]
    ) -> DoubaoRecognizer:
        """
        Create Doubao recognizer

        Args:
            config: Recognition configuration
            credentials: Doubao credentials

        Returns:
            DoubaoRecognizer: Doubao recognizer instance

        Raises:
            ValueError: If credentials are missing
        """
        app_id = credentials.get('app_id', '')
        access_token = credentials.get('access_token', '')

        if not app_id or not app_id.strip():
            raise ValueError("Doubao app ID is required")
        if not access_token or not access_token.strip():
            raise ValueError("Doubao access token is required")

        logger.info("Creating Doubao recognizer")
        logger.debug(f"Doubao config: {config}")

        return DoubaoRecognizer(
            config=config,
            app_id=app_id,
            access_token=access_token
        )

    @staticmethod
    def validate_credentials(provider: str, credentials: Dict[str, Any]) -> bool:
        """
        Validate credentials for a provider

        Args:
            provider: Provider name
            credentials: Credentials dictionary

        Returns:
            bool: True if valid, False otherwise
        """
        provider = provider.lower().strip()

        if provider not in RecognizerFactory.SUPPORTED_PROVIDERS:
            logger.warning(f"Cannot validate unknown provider: {provider}")
            return False

        try:
            if provider == RecognizerFactory.PROVIDER_DASHSCOPE:
                api_key = credentials.get('api_key', '')
                is_valid = bool(api_key and api_key.strip())
                if is_valid:
                    logger.debug("DashScope credentials valid")
                else:
                    logger.warning("DashScope API key missing or empty")
                return is_valid

            elif provider == RecognizerFactory.PROVIDER_DOUBAO:
                app_id = credentials.get('app_id', '')
                access_token = credentials.get('access_token', '')
                is_valid = bool(
                    app_id and app_id.strip() and
                    access_token and access_token.strip()
                )
                if is_valid:
                    logger.debug("Doubao credentials valid")
                else:
                    logger.warning("Doubao app ID or access token missing or empty")
                return is_valid

            else:
                logger.warning(f"Unknown provider for validation: {provider}")
                return False

        except Exception as e:
            logger.error(f"Error validating credentials for {provider}: {e}", exc_info=True)
            return False

    @staticmethod
    def get_provider_display_name(provider: str) -> str:
        """
        Get display name for provider

        Args:
            provider: Provider name

        Returns:
            str: Display name
        """
        display_names = {
            RecognizerFactory.PROVIDER_DASHSCOPE: 'Alibaba DashScope',
            RecognizerFactory.PROVIDER_DOUBAO: 'ByteDance Doubao'
        }
        return display_names.get(provider.lower(), provider)
