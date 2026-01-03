"""
Doubao (ByteDance) speech recognition protocol implementation
Ported from official example code
"""
import asyncio
import gzip
import json
import logging
import struct
import uuid
from dataclasses import dataclass
from enum import IntEnum
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# Constants
DEFAULT_SAMPLE_RATE = 16000


class ProtocolVersion(IntEnum):
    """Protocol version"""
    V1 = 0b0001


class MessageType(IntEnum):
    """Message type"""
    CLIENT_FULL_REQUEST = 0b0001
    CLIENT_AUDIO_ONLY_REQUEST = 0b0010
    SERVER_FULL_RESPONSE = 0b1001
    SERVER_ERROR_RESPONSE = 0b1111


class MessageTypeSpecificFlags(IntEnum):
    """Message type specific flags"""
    NO_SEQUENCE = 0b0000
    POS_SEQUENCE = 0b0001
    NEG_SEQUENCE = 0b0010
    NEG_WITH_SEQUENCE = 0b0011


class SerializationType(IntEnum):
    """Serialization type"""
    NO_SERIALIZATION = 0b0000
    JSON = 0b0001


class CompressionType(IntEnum):
    """Compression type"""
    NO_COMPRESSION = 0b0000
    GZIP = 0b0001


class CommonUtils:
    """Common utility functions"""

    @staticmethod
    def gzip_compress(data: bytes) -> bytes:
        """
        Compress data using gzip

        Args:
            data: Data to compress

        Returns:
            bytes: Compressed data
        """
        try:
            compressed = gzip.compress(data)
            if len(data) > 0:
                ratio = len(compressed) / len(data)
                logger.debug(f"Compressed {len(data)} bytes to {len(compressed)} bytes (ratio: {ratio:.2%})")
            else:
                logger.debug(f"Compressed empty data, result: {len(compressed)} bytes")
            return compressed
        except Exception as e:
            logger.error(f"Failed to compress data: {e}", exc_info=True)
            raise

    @staticmethod
    def gzip_decompress(data: bytes) -> bytes:
        """
        Decompress gzip data

        Args:
            data: Compressed data

        Returns:
            bytes: Decompressed data
        """
        try:
            decompressed = gzip.decompress(data)
            logger.debug(f"Decompressed {len(data)} bytes to {len(decompressed)} bytes")
            return decompressed
        except Exception as e:
            logger.error(f"Failed to decompress data: {e}", exc_info=True)
            raise


@dataclass
class AsrRequestHeader:
    """ASR request header"""
    message_type: int = MessageType.CLIENT_FULL_REQUEST
    message_type_specific_flags: int = MessageTypeSpecificFlags.POS_SEQUENCE
    serialization_type: int = SerializationType.JSON
    compression_type: int = CompressionType.GZIP
    reserved_data: bytes = bytes([0x00])

    def with_message_type(self, message_type: int) -> 'AsrRequestHeader':
        """Set message type"""
        self.message_type = message_type
        return self

    def with_message_type_specific_flags(self, flags: int) -> 'AsrRequestHeader':
        """Set message type specific flags"""
        self.message_type_specific_flags = flags
        return self

    def with_serialization_type(self, serialization_type: int) -> 'AsrRequestHeader':
        """Set serialization type"""
        self.serialization_type = serialization_type
        return self

    def with_compression_type(self, compression_type: int) -> 'AsrRequestHeader':
        """Set compression type"""
        self.compression_type = compression_type
        return self

    def to_bytes(self) -> bytes:
        """
        Convert header to bytes

        Returns:
            bytes: Header bytes
        """
        header = bytearray()
        header.append((ProtocolVersion.V1 << 4) | 1)
        header.append((self.message_type << 4) | self.message_type_specific_flags)
        header.append((self.serialization_type << 4) | self.compression_type)
        header.extend(self.reserved_data)
        return bytes(header)

    @staticmethod
    def default_header() -> 'AsrRequestHeader':
        """Create default header"""
        return AsrRequestHeader()


class RequestBuilder:
    """Build protocol requests"""

    def __init__(self, app_key: str, access_key: str, resource_id: str):
        """
        Initialize request builder

        Args:
            app_key: Application key
            access_key: Access token
            resource_id: Resource ID
        """
        self.app_key = app_key
        self.access_key = access_key
        self.resource_id = resource_id
        logger.debug(f"RequestBuilder initialized with resource_id: {resource_id}")

    def new_auth_headers(self) -> Dict[str, str]:
        """
        Create authentication headers

        Returns:
            Dict[str, str]: Authentication headers
        """
        reqid = str(uuid.uuid4())
        headers = {
            "X-Api-Resource-Id": self.resource_id,
            "X-Api-Request-Id": reqid,
            "X-Api-Access-Key": self.access_key,
            "X-Api-App-Key": self.app_key
        }
        logger.debug(f"Created auth headers with request ID: {reqid}")
        return headers

    @staticmethod
    def new_full_client_request(seq: int, sample_rate: int = DEFAULT_SAMPLE_RATE) -> bytes:
        """
        Create full client request

        Args:
            seq: Sequence number
            sample_rate: Audio sample rate

        Returns:
            bytes: Request bytes
        """
        header = AsrRequestHeader.default_header() \
            .with_message_type_specific_flags(MessageTypeSpecificFlags.POS_SEQUENCE)

        payload = {
            "user": {
                "uid": "autovoicetype_user"
            },
            "audio": {
                "format": "pcm",
                "codec": "raw",
                "rate": sample_rate,
                "bits": 16,
                "channel": 1
            },
            "request": {
                "model_name": "bigmodel",
                "enable_itn": True,
                "enable_punc": True,
                "enable_ddc": False,
                "show_utterances": False,
                "enable_nonstream": False
            }
        }

        payload_bytes = json.dumps(payload).encode('utf-8')
        compressed_payload = CommonUtils.gzip_compress(payload_bytes)
        payload_size = len(compressed_payload)

        request = bytearray()
        request.extend(header.to_bytes())
        request.extend(struct.pack('>i', seq))
        request.extend(struct.pack('>I', payload_size))
        request.extend(compressed_payload)

        logger.debug(f"Created full client request, seq={seq}, sample_rate={sample_rate}, payload_size={payload_size}")
        return bytes(request)

    @staticmethod
    def new_audio_only_request(seq: int, segment: bytes, is_last: bool = False, compress: bool = True) -> bytes:
        """
        Create audio only request

        Args:
            seq: Sequence number
            segment: Audio segment data
            is_last: Whether this is the last segment
            compress: Whether to compress the audio data (default True)

        Returns:
            bytes: Request bytes
        """
        header = AsrRequestHeader.default_header()
        if is_last:
            header.with_message_type_specific_flags(MessageTypeSpecificFlags.NEG_WITH_SEQUENCE)
            seq = -seq
        else:
            header.with_message_type_specific_flags(MessageTypeSpecificFlags.POS_SEQUENCE)
        header.with_message_type(MessageType.CLIENT_AUDIO_ONLY_REQUEST)

        # Optionally disable compression for audio data
        if not compress:
            header.with_compression_type(CompressionType.NO_COMPRESSION)

        request = bytearray()
        request.extend(header.to_bytes())
        request.extend(struct.pack('>i', seq))

        # Compress or not based on parameter
        if compress:
            compressed_segment = CommonUtils.gzip_compress(segment)
            request.extend(struct.pack('>I', len(compressed_segment)))
            request.extend(compressed_segment)
            logger.debug(f"Created audio only request with compression, seq={seq}, original_size={len(segment)}, compressed_size={len(compressed_segment)}, is_last={is_last}")
        else:
            request.extend(struct.pack('>I', len(segment)))
            request.extend(segment)
            logger.debug(f"Created audio only request without compression, seq={seq}, segment_size={len(segment)}, is_last={is_last}")

        return bytes(request)


@dataclass
class AsrResponse:
    """ASR response"""
    code: int = 0
    event: int = 0
    is_last_package: bool = False
    payload_sequence: int = 0
    payload_size: int = 0
    payload_msg: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "code": self.code,
            "event": self.event,
            "is_last_package": self.is_last_package,
            "payload_sequence": self.payload_sequence,
            "payload_size": self.payload_size,
            "payload_msg": self.payload_msg
        }

    def __str__(self):
        return f"AsrResponse(code={self.code}, is_last={self.is_last_package}, seq={self.payload_sequence})"


class ResponseParser:
    """Parse protocol responses"""

    @staticmethod
    def parse_response(msg: bytes) -> AsrResponse:
        """
        Parse response message

        Args:
            msg: Response message bytes

        Returns:
            AsrResponse: Parsed response
        """
        try:
            response = AsrResponse()

            if len(msg) < 4:
                logger.error(f"Response message too short: {len(msg)} bytes")
                return response

            header_size = msg[0] & 0x0f
            message_type = msg[1] >> 4
            message_type_specific_flags = msg[1] & 0x0f
            serialization_method = msg[2] >> 4
            message_compression = msg[2] & 0x0f

            payload = msg[header_size * 4:]

            # Parse message_type_specific_flags
            if message_type_specific_flags & 0x01:
                if len(payload) < 4:
                    logger.error("Payload too short for sequence number")
                    return response
                response.payload_sequence = struct.unpack('>i', payload[:4])[0]
                payload = payload[4:]

            if message_type_specific_flags & 0x02:
                response.is_last_package = True

            if message_type_specific_flags & 0x04:
                if len(payload) < 4:
                    logger.error("Payload too short for event")
                    return response
                response.event = struct.unpack('>i', payload[:4])[0]
                payload = payload[4:]

            # Parse message_type
            if message_type == MessageType.SERVER_FULL_RESPONSE:
                if len(payload) < 4:
                    logger.error("Payload too short for payload size")
                    return response
                response.payload_size = struct.unpack('>I', payload[:4])[0]
                payload = payload[4:]
            elif message_type == MessageType.SERVER_ERROR_RESPONSE:
                if len(payload) < 8:
                    logger.error("Payload too short for error response")
                    return response
                response.code = struct.unpack('>i', payload[:4])[0]
                response.payload_size = struct.unpack('>I', payload[4:8])[0]
                payload = payload[8:]

            if not payload:
                return response

            # Decompress
            if message_compression == CompressionType.GZIP:
                try:
                    payload = CommonUtils.gzip_decompress(payload)
                except Exception as e:
                    logger.error(f"Failed to decompress payload: {e}")
                    return response

            # Parse payload
            try:
                if serialization_method == SerializationType.JSON:
                    response.payload_msg = json.loads(payload.decode('utf-8'))
                    logger.debug(f"Parsed response: {response}")
            except Exception as e:
                logger.error(f"Failed to parse payload JSON: {e}")

            return response
        except Exception as e:
            logger.error(f"Error parsing response: {e}", exc_info=True)
            return AsrResponse()
