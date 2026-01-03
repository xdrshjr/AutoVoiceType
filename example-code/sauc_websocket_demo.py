import asyncio
import aiohttp
import json
import struct
import gzip
import uuid
import logging
from typing import Optional, List, Dict, Any, Tuple, AsyncGenerator
import subprocess

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('doubao_asr.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 常量定义
DEFAULT_SAMPLE_RATE = 16000


class ProtocolVersion:
    V1 = 0b0001


class MessageType:
    CLIENT_FULL_REQUEST = 0b0001
    CLIENT_AUDIO_ONLY_REQUEST = 0b0010
    SERVER_FULL_RESPONSE = 0b1001
    SERVER_ERROR_RESPONSE = 0b1111


class MessageTypeSpecificFlags:
    NO_SEQUENCE = 0b0000
    POS_SEQUENCE = 0b0001
    NEG_SEQUENCE = 0b0010
    NEG_WITH_SEQUENCE = 0b0011


class SerializationType:
    NO_SERIALIZATION = 0b0000
    JSON = 0b0001


class CompressionType:
    GZIP = 0b0001


class CommonUtils:
    @staticmethod
    def gzip_compress(data: bytes) -> bytes:
        return gzip.compress(data)

    @staticmethod
    def gzip_decompress(data: bytes) -> bytes:
        return gzip.decompress(data)

    @staticmethod
    def judge_wav(data: bytes) -> bool:
        if len(data) < 44:
            return False
        return data[:4] == b'RIFF' and data[8:12] == b'WAVE'

    @staticmethod
    def convert_wav_with_path(audio_path: str, sample_rate: int = DEFAULT_SAMPLE_RATE) -> bytes:
        try:
            cmd = [
                "ffmpeg", "-v", "quiet", "-y", "-i", audio_path,
                "-acodec", "pcm_s16le", "-ac", "1", "-ar", str(sample_rate),
                "-f", "wav", "-"
            ]
            result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg转换失败: {e.stderr.decode()}")
            raise RuntimeError(f"音频转换失败: {e.stderr.decode()}")

    @staticmethod
    def read_wav_info(data: bytes) -> Tuple[int, int, int, int, bytes]:
        if len(data) < 44:
            raise ValueError("无效的WAV文件: 文件太短")

        # 解析WAV头
        chunk_id = data[:4]
        if chunk_id != b'RIFF':
            raise ValueError("无效的WAV文件: 不是RIFF格式")

        format_ = data[8:12]
        if format_ != b'WAVE':
            raise ValueError("无效的WAV文件: 不是WAVE格式")

        # 解析fmt子块
        num_channels = struct.unpack('<H', data[22:24])[0]
        sample_rate = struct.unpack('<I', data[24:28])[0]
        bits_per_sample = struct.unpack('<H', data[34:36])[0]

        # 查找data子块
        pos = 36
        while pos < len(data) - 8:
            subchunk_id = data[pos:pos + 4]
            subchunk_size = struct.unpack('<I', data[pos + 4:pos + 8])[0]
            if subchunk_id == b'data':
                wave_data = data[pos + 8:pos + 8 + subchunk_size]
                return (
                    num_channels,
                    bits_per_sample // 8,
                    sample_rate,
                    subchunk_size // (num_channels * (bits_per_sample // 8)),
                    wave_data
                )
            pos += 8 + subchunk_size

        raise ValueError("无效的WAV文件: 没有找到data子块")


class AsrRequestHeader:
    def __init__(self):
        self.message_type = MessageType.CLIENT_FULL_REQUEST
        self.message_type_specific_flags = MessageTypeSpecificFlags.POS_SEQUENCE
        self.serialization_type = SerializationType.JSON
        self.compression_type = CompressionType.GZIP
        self.reserved_data = bytes([0x00])

    def with_message_type(self, message_type: int) -> 'AsrRequestHeader':
        self.message_type = message_type
        return self

    def with_message_type_specific_flags(self, flags: int) -> 'AsrRequestHeader':
        self.message_type_specific_flags = flags
        return self

    def with_serialization_type(self, serialization_type: int) -> 'AsrRequestHeader':
        self.serialization_type = serialization_type
        return self

    def with_compression_type(self, compression_type: int) -> 'AsrRequestHeader':
        self.compression_type = compression_type
        return self

    def to_bytes(self) -> bytes:
        header = bytearray()
        header.append((ProtocolVersion.V1 << 4) | 1)
        header.append((self.message_type << 4) | self.message_type_specific_flags)
        header.append((self.serialization_type << 4) | self.compression_type)
        header.extend(self.reserved_data)
        return bytes(header)

    @staticmethod
    def default_header() -> 'AsrRequestHeader':
        return AsrRequestHeader()


class RequestBuilder:
    def __init__(self, app_key: str, access_key: str, resource_id: str):
        self.app_key = app_key
        self.access_key = access_key
        self.resource_id = resource_id

    def new_auth_headers(self) -> Dict[str, str]:
        reqid = str(uuid.uuid4())
        return {
            "X-Api-Resource-Id": self.resource_id,
            "X-Api-Request-Id": reqid,
            "X-Api-Access-Key": self.access_key,
            "X-Api-App-Key": self.app_key
        }

    @staticmethod
    def new_full_client_request(seq: int) -> bytes:
        header = AsrRequestHeader.default_header() \
            .with_message_type_specific_flags(MessageTypeSpecificFlags.POS_SEQUENCE)

        payload = {
            "user": {
                "uid": "demo_uid"
            },
            "audio": {
                "format": "wav",
                "codec": "raw",
                "rate": 16000,
                "bits": 16,
                "channel": 1
            },
            "request": {
                "model_name": "bigmodel",
                "enable_itn": True,
                "enable_punc": True,
                "enable_ddc": False,
                "show_utterances": True,
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

        return bytes(request)

    @staticmethod
    def new_audio_only_request(seq: int, segment: bytes, is_last: bool = False) -> bytes:
        header = AsrRequestHeader.default_header()
        if is_last:
            header.with_message_type_specific_flags(MessageTypeSpecificFlags.NEG_WITH_SEQUENCE)
            seq = -seq
        else:
            header.with_message_type_specific_flags(MessageTypeSpecificFlags.POS_SEQUENCE)
        header.with_message_type(MessageType.CLIENT_AUDIO_ONLY_REQUEST)

        request = bytearray()
        request.extend(header.to_bytes())
        request.extend(struct.pack('>i', seq))

        compressed_segment = CommonUtils.gzip_compress(segment)
        request.extend(struct.pack('>I', len(compressed_segment)))
        request.extend(compressed_segment)

        return bytes(request)


class AsrResponse:
    def __init__(self):
        self.code = 0
        self.event = 0
        self.is_last_package = False
        self.payload_sequence = 0
        self.payload_size = 0
        self.payload_msg = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "event": self.event,
            "is_last_package": self.is_last_package,
            "payload_sequence": self.payload_sequence,
            "payload_size": self.payload_size,
            "payload_msg": self.payload_msg
        }


class ResponseParser:
    @staticmethod
    def parse_response(msg: bytes) -> AsrResponse:
        response = AsrResponse()

        header_size = msg[0] & 0x0f
        message_type = msg[1] >> 4
        message_type_specific_flags = msg[1] & 0x0f
        serialization_method = msg[2] >> 4
        message_compression = msg[2] & 0x0f

        payload = msg[header_size * 4:]

        # 解析message_type_specific_flags
        if message_type_specific_flags & 0x01:
            response.payload_sequence = struct.unpack('>i', payload[:4])[0]
            payload = payload[4:]
        if message_type_specific_flags & 0x02:
            response.is_last_package = True
        if message_type_specific_flags & 0x04:
            response.event = struct.unpack('>i', payload[:4])[0]
            payload = payload[4:]

        # 解析message_type
        if message_type == MessageType.SERVER_FULL_RESPONSE:
            response.payload_size = struct.unpack('>I', payload[:4])[0]
            payload = payload[4:]
        elif message_type == MessageType.SERVER_ERROR_RESPONSE:
            response.code = struct.unpack('>i', payload[:4])[0]
            response.payload_size = struct.unpack('>I', payload[4:8])[0]
            payload = payload[8:]

        if not payload:
            return response

        # 解压缩
        if message_compression == CompressionType.GZIP:
            try:
                payload = CommonUtils.gzip_decompress(payload)
            except Exception as e:
                logger.error(f"解压缩payload失败: {e}")
                return response

        # 解析payload
        try:
            if serialization_method == SerializationType.JSON:
                response.payload_msg = json.loads(payload.decode('utf-8'))
        except Exception as e:
            logger.error(f"解析payload失败: {e}")

        return response


class DouBaoAsrClient:
    def __init__(self, app_key: str, access_key: str, url: str,
                 resource_id: str = "volc.bigasr.sauc.duration",
                 segment_duration: int = 200):
        self.seq = 1
        self.url = url
        self.segment_duration = segment_duration
        self.conn = None
        self.session = None
        self.request_builder = RequestBuilder(app_key, access_key, resource_id)

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.conn and not self.conn.closed:
            await self.conn.close()
        if self.session and not self.session.closed:
            await self.session.close()

    async def read_audio_data(self, file_path: str) -> bytes:
        try:
            with open(file_path, 'rb') as f:
                content = f.read()

            if not CommonUtils.judge_wav(content):
                logger.info("转换音频为WAV格式...")
                content = CommonUtils.convert_wav_with_path(file_path, DEFAULT_SAMPLE_RATE)

            return content
        except Exception as e:
            logger.error(f"读取音频数据失败: {e}")
            raise

    def get_segment_size(self, content: bytes) -> int:
        try:
            channel_num, samp_width, frame_rate, _, _ = CommonUtils.read_wav_info(content)[:5]
            size_per_sec = channel_num * samp_width * frame_rate
            segment_size = size_per_sec * self.segment_duration // 1000
            return segment_size
        except Exception as e:
            logger.error(f"计算分段大小失败: {e}")
            raise

    async def create_connection(self) -> None:
        headers = self.request_builder.new_auth_headers()
        try:
            self.conn = await self.session.ws_connect(
                self.url,
                headers=headers
            )
            logger.info(f"成功连接到 {self.url}")
        except Exception as e:
            logger.error(f"连接WebSocket失败: {e}")
            raise

    async def send_full_client_request(self) -> None:
        request = RequestBuilder.new_full_client_request(self.seq)
        self.seq += 1
        try:
            await self.conn.send_bytes(request)
            logger.info(f"发送完整客户端请求，序列号: {self.seq - 1}")

            msg = await self.conn.receive()
            if msg.type == aiohttp.WSMsgType.BINARY:
                response = ResponseParser.parse_response(msg.data)
                logger.info(f"收到响应: {response.to_dict()}")
            else:
                logger.error(f"意外的消息类型: {msg.type}")
        except Exception as e:
            logger.error(f"发送完整客户端请求失败: {e}")
            raise

    async def send_messages(self, segment_size: int, content: bytes) -> AsyncGenerator[None, None]:
        audio_segments = self.split_audio(content, segment_size)
        total_segments = len(audio_segments)

        for i, segment in enumerate(audio_segments):
            is_last = (i == total_segments - 1)
            request = RequestBuilder.new_audio_only_request(
                self.seq,
                segment,
                is_last=is_last
            )
            await self.conn.send_bytes(request)
            logger.info(f"发送音频段，序列号: {self.seq} (最后一包: {is_last})")

            if not is_last:
                self.seq += 1

            await asyncio.sleep(self.segment_duration / 1000)
            yield

    async def recv_messages(self) -> AsyncGenerator[AsrResponse, None]:
        try:
            async for msg in self.conn:
                if msg.type == aiohttp.WSMsgType.BINARY:
                    response = ResponseParser.parse_response(msg.data)
                    yield response

                    if response.is_last_package or response.code != 0:
                        break
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket错误: {msg.data}")
                    break
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    logger.info("WebSocket连接已关闭")
                    break
        except Exception as e:
            logger.error(f"接收消息时出错: {e}")
            raise

    async def start_audio_stream(self, segment_size: int, content: bytes) -> AsyncGenerator[AsrResponse, None]:
        async def sender():
            async for _ in self.send_messages(segment_size, content):
                pass

        sender_task = asyncio.create_task(sender())

        try:
            async for response in self.recv_messages():
                yield response
        finally:
            sender_task.cancel()
            try:
                await sender_task
            except asyncio.CancelledError:
                pass

    @staticmethod
    def split_audio(data: bytes, segment_size: int) -> List[bytes]:
        if segment_size <= 0:
            return []

        segments = []
        for i in range(0, len(data), segment_size):
            end = i + segment_size
            if end > len(data):
                end = len(data)
            segments.append(data[i:end])
        return segments

    async def recognize(self, file_path: str) -> AsyncGenerator[AsrResponse, None]:
        """识别音频文件"""
        if not file_path:
            raise ValueError("文件路径为空")

        if not self.url:
            raise ValueError("URL为空")

        self.seq = 1

        try:
            # 1. 读取音频文件
            content = await self.read_audio_data(file_path)

            # 2. 计算分段大小
            segment_size = self.get_segment_size(content)

            # 3. 创建WebSocket连接
            await self.create_connection()

            # 4. 发送完整客户端请求
            await self.send_full_client_request()

            # 5. 启动音频流处理
            async for response in self.start_audio_stream(segment_size, content):
                yield response

        except Exception as e:
            logger.error(f"ASR执行错误: {e}")
            raise
        finally:
            if self.conn:
                await self.conn.close()


async def main():
    """
    豆包语音识别主函数

    API信息：
    - APP ID: 4269953601
    - Access Token: uAGE3iP8nJf3ewu-d6U1P6Jthv7i1DH7
    - Secret Key: Dfta36aYgcdqY-ylHoh9FQyqiERS5iTv
    """

    # ========== API配置 ==========
    APP_ID = "4269953601"
    ACCESS_TOKEN = "uAGE3iP8nJf3ewu-d6U1P6Jthv7i1DH7"
    SECRET_KEY = "Dfta36aYgcdqY-ylHoh9FQyqiERS5iTv"

    # 资源ID配置你好。
    # 豆包流式语音识别模型1.0 小时版
    RESOURCE_ID = "volc.seedasr.sauc.duration"

    # WebSocket URL配置
    # 双向流式模式（推荐）
    WS_URL = "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel_async"

    # 音频文件路径（请修改为您的音频文件路径）
    AUDIO_FILE = "./test_audio.wav"

    # 每个音频包的时长（毫秒），建议100-200ms
    SEGMENT_DURATION = 200

    # ========== 开始识别 ==========
    print("=" * 60)
    print("豆包语音识别服务")
    print("=" * 60)
    print(f"APP ID: {APP_ID}")
    print(f"资源ID: {RESOURCE_ID}")
    print(f"WebSocket URL: {WS_URL}")
    print(f"音频文件: {AUDIO_FILE}")
    print(f"分段时长: {SEGMENT_DURATION}ms")
    print("=" * 60)

    async with DouBaoAsrClient(
            app_key=APP_ID,
            access_key=ACCESS_TOKEN,
            url=WS_URL,
            resource_id=RESOURCE_ID,
            segment_duration=SEGMENT_DURATION
    ) as client:
        try:
            print("\n开始识别...")
            async for response in client.recognize(AUDIO_FILE):
                # 打印完整响应
                logger.info(f"收到识别结果:\n{json.dumps(response.to_dict(), indent=2, ensure_ascii=False)}")

                # 如果有识别文本，单独打印
                if response.payload_msg and 'result' in response.payload_msg:
                    result = response.payload_msg['result']
                    if 'text' in result:
                        print(f"\n识别文本: {result['text']}")

                    # 打印分句信息
                    if 'utterances' in result:
                        print("\n分句信息:")
                        for utt in result['utterances']:
                            print(f"  [{utt.get('start_time', 0)}ms - {utt.get('end_time', 0)}ms] "
                                  f"确定: {utt.get('definite', False)} - {utt.get('text', '')}")

                # 如果出错，打印错误信息
                if response.code != 0:
                    print(f"\n错误: 错误码 {response.code}")

        except Exception as e:
            logger.error(f"语音识别失败: {e}")
            print(f"\n识别失败: {e}")


if __name__ == "__main__":
    # 运行主函数
    asyncio.run(main())

    # 使用示例:
    # 1. 确保已安装依赖: pip install aiohttp
    # 2. 确保已安装ffmpeg（用于音频格式转换）
    # 3. 修改 AUDIO_FILE 为您的音频文件路径
    # 4. 运行: python douban_asr.py


