import json
import time
from aiohttp import web
from core.api.base_handler import BaseHandler
from core.handle.receiveAudioHandle import startToChat
from core.handle.reportHandle import enqueue_asr_report
from core.utils.audio_utils import process_base64_audio

TAG = __name__


class TextMessageHandler(BaseHandler):
    def __init__(self, config: dict, websocket_server=None):
        super().__init__(config)
        self.websocket_server = websocket_server

    async def handle_post(self, request):
        """处理文字消息POST请求"""
        try:
            # 获取请求数据
            data = await request.json()
            self.logger.bind(tag=TAG).debug(f"文字消息请求数据: {data}")

            # 验证必要参数
            if not data.get("device_id"):
                response = web.Response(
                    text=json.dumps({"success": False, "message": "缺少设备ID"}),
                    content_type="application/json"
                )
                self._add_cors_headers(response)
                return response

            if not data.get("message"):
                response = web.Response(
                    text=json.dumps({"success": False, "message": "缺少消息内容"}),
                    content_type="application/json"
                )
                self._add_cors_headers(response)
                return response

            # 获取参数
            device_id = data.get("device_id")
            message = data.get("message")
            message_type = data.get("message_type", "text")  # 默认为文本类型
            timestamp = data.get("timestamp", int(time.time() * 1000))  # 如果没有提供时间戳，使用当前时间
            
            # 根据消息类型确定音频数据和显示消息
            if message_type == "audio":
                audio_data = message  # 音频类型时，message字段包含base64编码的opus音频数据
                display_message = "音频消息"  # 用于日志显示的消息内容
            else:
                audio_data = data.get("audio_data")  # 兼容旧格式：从audio_data字段获取音频数据
                display_message = message  # 文本消息直接显示内容

            self.logger.bind(tag=TAG).info(f"收到来自设备 {device_id} 的消息: {display_message}, 类型: {message_type}, 包含音频: {bool(audio_data)}")

            # 验证WebSocket服务器是否初始化
            if not self.websocket_server or not hasattr(self.websocket_server, "active_connections"):
                response = web.Response(
                    text=json.dumps({"success": False, "message": "WebSocket服务器未初始化"}),
                    content_type="application/json"
                )
                self._add_cors_headers(response)
                return response

            # 查找目标设备连接
            target_connection = None
            for conn in self.websocket_server.active_connections:
                if hasattr(conn, "device_id") and conn.device_id == device_id:
                    target_connection = conn
                    break

            if not target_connection:
                response = web.Response(
                    text=json.dumps({"success": False, "message": "设备未连接"}),
                    content_type="application/json"
                )
                self._add_cors_headers(response)
                return response

            # 处理消息（文字或音频）
            try:
                # 处理音频数据（如果提供）
                audio_packets = []
                audio_format = "opus"  # 默认格式
                if audio_data:
                    try:
                        # 处理音频数据
                        audio_packets, audio_format = process_base64_audio(audio_data)
                        self.logger.bind(tag=TAG).info(f"成功处理base64音频数据，共 {len(audio_packets)} 个数据包，格式: {audio_format}")
                    except ValueError as e:
                        self.logger.bind(tag=TAG).error(f"处理音频数据失败: {e}")
                        response = web.Response(
                            text=json.dumps({"success": False, "message": f"音频数据处理失败: {str(e)}"}),
                            content_type="application/json"
                        )
                        self._add_cors_headers(response)
                        return response
                
                # 确定要处理的文本消息
                if message_type == "audio":
                    # 对于音频消息，调用ASR进行语音识别
                    if audio_packets and self.websocket_server and hasattr(self.websocket_server, '_asr') and self.websocket_server._asr:
                        try:
                            # 生成会话ID用于ASR
                            session_id = f"{device_id}_{timestamp}"
                            
                            # 调用ASR进行语音识别
                            asr_result = await self.websocket_server._asr.speech_to_text(
                                audio_packets, session_id, audio_format
                            )
                            
                            # ASR返回的是一个元组 (text, speaker_name)
                            if asr_result and asr_result[0]:
                                text_message = asr_result[0]
                                self.logger.bind(tag=TAG).info(f"ASR识别结果: {text_message}")
                            else:
                                text_message = "语音识别失败，无法识别音频内容"
                                self.logger.bind(tag=TAG).warning("ASR识别失败或返回空结果")
                        except Exception as e:
                            text_message = "语音识别过程中发生错误"
                            self.logger.bind(tag=TAG).error(f"ASR识别过程中发生错误: {e}")
                    else:
                        text_message = "ASR服务不可用或音频数据为空"
                        self.logger.bind(tag=TAG).warning("ASR服务不可用或音频数据为空")
                else:
                    text_message = message
                
                # 上报数据（用于记录和统计）
                # 如果有音频数据，使用音频数据；否则使用空列表
                enqueue_asr_report(target_connection, text_message, audio_packets)
                
                # 调用LLM处理消息并生成TTS回复
                await startToChat(target_connection, text_message)
                
                message_type_desc = "音频消息" if audio_data else "文字消息"
                self.logger.bind(tag=TAG).info(f"{message_type_desc}已处理，设备 {device_id} 将播放LLM回复")
                
            except Exception as e:
                self.logger.bind(tag=TAG).error(f"处理文字消息失败: {e}")
                response = web.Response(
                    text=json.dumps({"success": False, "message": f"处理消息失败: {str(e)}"}),
                    content_type="application/json"
                )
                self._add_cors_headers(response)
                return response

            # 返回成功响应
            success_message = "音频消息发送成功" if message_type == "audio" else "文字消息发送成功"
            response_message = display_message if message_type == "audio" else message
            
            response = web.Response(
                text=json.dumps({
                    "success": True,
                    "message": success_message,
                    "data": {
                        "device_id": device_id,
                        "message": response_message,
                        "message_type": message_type,
                        "timestamp": timestamp,
                        "message_id": f"{device_id}_{timestamp}",  # 生成消息ID用于追踪
                        "audio_packets_count": len(audio_packets) if audio_packets else 0
                    }
                }),
                content_type="application/json"
            )
            self._add_cors_headers(response)
            return response

        except json.JSONDecodeError:
            self.logger.bind(tag=TAG).error("请求数据不是有效的JSON格式")
            response = web.Response(
                text=json.dumps({"success": False, "message": "请求数据格式错误"}),
                content_type="application/json"
            )
            self._add_cors_headers(response)
            return response

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"处理文字消息请求失败: {e}")
            response = web.Response(
                text=json.dumps({"success": False, "message": f"处理请求失败: {str(e)}"}),
                content_type="application/json"
            )
            self._add_cors_headers(response)
            return response

    async def handle_get(self, request):
        """处理GET请求，返回接口状态信息"""
        try:
            # 获取在线设备数量
            online_devices_count = 0
            if self.websocket_server and hasattr(self.websocket_server, "active_connections"):
                online_devices_count = len([
                    conn for conn in self.websocket_server.active_connections 
                    if hasattr(conn, "device_id") and conn.device_id
                ])

            response = web.Response(
                text=json.dumps({
                    "success": True,
                    "message": "文字消息接口运行正常",
                    "data": {
                        "endpoint": "/xiaozhi/message/text",
                        "methods": ["POST"],
                        "online_devices": online_devices_count,
                        "server_time": int(time.time() * 1000)
                    }
                }),
                content_type="application/json"
            )
            self._add_cors_headers(response)
            return response

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"处理GET请求失败: {e}")
            response = web.Response(
                text=json.dumps({"success": False, "message": f"处理请求失败: {str(e)}"}),
                content_type="application/json"
            )
            self._add_cors_headers(response)
            return response

    async def handle_options(self, request):
        """处理CORS预检请求"""
        response = web.Response()
        self._add_cors_headers(response)
        return response