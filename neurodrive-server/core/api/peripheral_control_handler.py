import json
import asyncio
import aiohttp
from aiohttp import web
from core.api.base_handler import BaseHandler

# 新增：缓存管理器，用于设备信息更新
from core.utils.cache.manager import cache_manager, CacheType

TAG = __name__


class PeripheralControlHandler(BaseHandler):
    def __init__(self, config: dict, websocket_server=None):
        super().__init__(config)
        self.websocket_server = websocket_server
        # 用于等待硬件回复的字典（类级共享），格式: {device_id: {request_id: asyncio.Event}}
        # 说明：HTTP 请求处理与 WebSocket 回复处理各自实例化了本类，
        # 如果使用实例级字典会导致无法跨实例匹配，从而出现已收到设备回复但接口仍提示超时的情况。
        # 因此这里改为类级共享，并在实例上引用同一对象，确保跨实例共享等待队列。
        if not hasattr(PeripheralControlHandler, "_shared_pending_requests"):
            PeripheralControlHandler._shared_pending_requests = {}
        self.pending_requests = PeripheralControlHandler._shared_pending_requests

    async def handle_post(self, request):
        """处理POST请求 - 外设控制（音量控制和麦克风控制）"""
        try:
            # 解析请求数据
            data = await request.json()
            action = data.get("action")
            
            if action == "volume":
                return await self._handle_volume_control(request, data)
            elif action == "microphone":
                return await self._handle_microphone_control(request, data)
            elif action == "volume_status":
                return await self._handle_volume_status(request, data)
            elif action == "device_reply":
                return await self._handle_device_reply(request, data)
            else:
                response = web.Response(
                    text=json.dumps({"success": False, "message": f"不支持的操作: {action}"}),
                    content_type="application/json",
                    status=400
                )
                self._add_cors_headers(response)
                return response

        except json.JSONDecodeError:
            response = web.Response(
                text=json.dumps({"success": False, "message": "无效的JSON格式"}),
                content_type="application/json",
                status=400
            )
            self._add_cors_headers(response)
            return response
        except Exception as e:
            self.logger.error(f"处理POST请求时发生错误: {str(e)}")
            response = web.Response(
                text=json.dumps({"success": False, "message": f"处理请求失败: {str(e)}"}),
                content_type="application/json",
                status=500
            )
            self._add_cors_headers(response)
            return response

    async def _handle_volume_control(self, request, data):
        """处理音量控制请求"""
        try:
            # 验证必需参数
            device_id = data.get("device_id")
            value = data.get("value")
            
            if not device_id:
                response = web.Response(
                    text=json.dumps({"success": False, "message": "缺少device_id参数"}),
                    content_type="application/json",
                    status=400
                )
                self._add_cors_headers(response)
                return response
                
            if value is None:
                response = web.Response(
                    text=json.dumps({"success": False, "message": "缺少value参数"}),
                    content_type="application/json",
                    status=400
                )
                self._add_cors_headers(response)
                return response

            # 验证音量范围
            try:
                value = int(value)
                if value < 0 or value > 100:
                    response = web.Response(
                        text=json.dumps({"success": False, "message": "音量值必须在0-100之间"}),
                        content_type="application/json",
                        status=400
                    )
                    self._add_cors_headers(response)
                    return response
            except (ValueError, TypeError):
                response = web.Response(
                    text=json.dumps({"success": False, "message": "音量值必须是数字"}),
                    content_type="application/json",
                    status=400
                )
                self._add_cors_headers(response)
                return response

            # 验证WebSocket服务器
            if not self.websocket_server or not hasattr(self.websocket_server, "active_connections"):
                response = web.Response(
                    text=json.dumps({"success": False, "message": "WebSocket服务器未初始化"}),
                    content_type="application/json",
                    status=500
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
                    text=json.dumps({"success": False, "message": f"设备 {device_id} 未在线"}),
                    content_type="application/json",
                    status=404
                )
                self._add_cors_headers(response)
                return response

            # 生成请求ID用于跟踪
            import uuid
            request_id = str(uuid.uuid4())
            
            # 构造发送给设备的消息 - 使用新的JSON格式
            device_message = {
                "type": "peripheral",
                "action": "volume_set",
                "value": value,
                "request_id": request_id,
                "timestamp": asyncio.get_event_loop().time()
            }

            # 创建等待事件
            if device_id not in self.pending_requests:
                self.pending_requests[device_id] = {}
            
            wait_event = asyncio.Event()
            self.pending_requests[device_id][request_id] = {
                "event": wait_event,
                "type": "volume",
                "value": value
            }

            # 发送消息给设备
            try:
                await target_connection.websocket.send(json.dumps(device_message))
                self.logger.info(f"已向设备 {device_id} 发送音量调节请求: {value}, request_id: {request_id}")
                
                # 等待硬件回复，最多等待5秒
                try:
                    await asyncio.wait_for(wait_event.wait(), timeout=5.0)
                    
                    # 检查缓存中的最新值
                    cache_key = f"device_info:{device_id}"
                    cached_info = cache_manager.get(CacheType.DEVICE_INFO, cache_key) or {}
                    current_volume = cached_info.get("volume", value)
                    
                    response = web.Response(
                        text=json.dumps({
                            "success": True, 
                            "message": f"音量调节成功",
                            "data": {
                                "device_id": device_id,
                                "value": current_volume,
                                "status": "已确认"
                            }
                        }),
                        content_type="application/json"
                    )
                    self._add_cors_headers(response)
                    return response
                    
                except asyncio.TimeoutError:
                    # 超时，返回发送成功但未确认的状态
                    response = web.Response(
                        text=json.dumps({
                            "success": True, 
                            "message": f"音量调节请求已发送给设备 {device_id}，等待确认超时",
                            "data": {
                                "device_id": device_id,
                                "value": value,
                                "status": "已发送"
                            }
                        }),
                        content_type="application/json"
                    )
                    self._add_cors_headers(response)
                    return response
                finally:
                    # 清理等待事件
                    if device_id in self.pending_requests and request_id in self.pending_requests[device_id]:
                        del self.pending_requests[device_id][request_id]
                
            except Exception as e:
                self.logger.error(f"发送消息给设备 {device_id} 失败: {str(e)}")
                response = web.Response(
                    text=json.dumps({"success": False, "message": f"发送消息给设备失败: {str(e)}"}),
                    content_type="application/json",
                    status=500
                )
                self._add_cors_headers(response)
                return response

        except Exception as e:
            self.logger.error(f"处理音量设置请求时发生错误: {str(e)}")
            response = web.Response(
                text=json.dumps({"success": False, "message": f"处理请求失败: {str(e)}"}),
                content_type="application/json",
                status=500
            )
            self._add_cors_headers(response)
            return response

    async def _handle_microphone_control(self, request, data):
        """处理麦克风控制请求"""
        try:
            # 验证必需参数
            device_id = data.get("device_id")
            value = data.get("value")
            
            if not device_id:
                response = web.Response(
                    text=json.dumps({"success": False, "message": "缺少device_id参数"}),
                    content_type="application/json",
                    status=400
                )
                self._add_cors_headers(response)
                return response
                
            if value is None:
                response = web.Response(
                    text=json.dumps({"success": False, "message": "缺少value参数"}),
                    content_type="application/json",
                    status=400
                )
                self._add_cors_headers(response)
                return response

            # 验证麦克风参数（0或1）
            try:
                value = int(value)
                if value not in [0, 1]:
                    response = web.Response(
                        text=json.dumps({"success": False, "message": "麦克风参数必须是0（关闭）或1（开启）"}),
                        content_type="application/json",
                        status=400
                    )
                    self._add_cors_headers(response)
                    return response
            except (ValueError, TypeError):
                response = web.Response(
                    text=json.dumps({"success": False, "message": "麦克风参数必须是数字"}),
                    content_type="application/json",
                    status=400
                )
                self._add_cors_headers(response)
                return response

            # 验证WebSocket服务器
            if not self.websocket_server or not hasattr(self.websocket_server, "active_connections"):
                response = web.Response(
                    text=json.dumps({"success": False, "message": "WebSocket服务器未初始化"}),
                    content_type="application/json",
                    status=500
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
                    text=json.dumps({"success": False, "message": f"设备 {device_id} 未在线"}),
                    content_type="application/json",
                    status=404
                )
                self._add_cors_headers(response)
                return response

            # 生成请求ID用于跟踪
            import uuid
            request_id = str(uuid.uuid4())
            
            # 构造发送给设备的消息
            device_message = {
                "type": "peripheral",
                "action": "mic",
                "value": value,
                "request_id": request_id,
                "timestamp": asyncio.get_event_loop().time()
            }

            # 创建等待事件
            if device_id not in self.pending_requests:
                self.pending_requests[device_id] = {}
            
            wait_event = asyncio.Event()
            self.pending_requests[device_id][request_id] = {
                "event": wait_event,
                "type": "microphone",
                "value": value
            }

            # 发送消息给设备
            try:
                await target_connection.websocket.send(json.dumps(device_message))
                self.logger.info(f"已向设备 {device_id} 发送麦克风控制请求: {value}, request_id: {request_id}")
                
                # 等待硬件回复，最多等待5秒
                try:
                    await asyncio.wait_for(wait_event.wait(), timeout=5.0)
                    
                    # 检查缓存中的最新值
                    cache_key = f"device_info:{device_id}"
                    cached_info = cache_manager.get(CacheType.DEVICE_INFO, cache_key) or {}
                    # 统一使用缓存键"microphone"（设备回复处理处已写入该键）
                    current_mic = cached_info.get("microphone", value)
                    
                    response = web.Response(
                        text=json.dumps({
                            "success": True, 
                            "message": f"麦克风控制成功",
                            "data": {
                                "device_id": device_id,
                                "value": current_mic,
                                "status": "开启" if current_mic == 1 else "关闭"
                            }
                        }),
                        content_type="application/json"
                    )
                    self._add_cors_headers(response)
                    return response
                    
                except asyncio.TimeoutError:
                    # 超时，返回发送成功但未确认的状态
                    response = web.Response(
                        text=json.dumps({
                            "success": True, 
                            "message": f"麦克风控制请求已发送给设备 {device_id}，等待确认超时",
                            "data": {
                                "device_id": device_id,
                                "value": value,
                                "status": "开启" if value == 1 else "关闭"
                            }
                        }),
                        content_type="application/json"
                    )
                    self._add_cors_headers(response)
                    return response
                finally:
                    # 清理等待事件
                    if device_id in self.pending_requests and request_id in self.pending_requests[device_id]:
                        del self.pending_requests[device_id][request_id]
                
            except Exception as e:
                self.logger.error(f"发送消息给设备 {device_id} 失败: {str(e)}")
                response = web.Response(
                    text=json.dumps({"success": False, "message": f"发送消息给设备失败: {str(e)}"}),
                    content_type="application/json",
                    status=500
                )
                self._add_cors_headers(response)
                return response

        except Exception as e:
            self.logger.error(f"处理麦克风控制请求时发生错误: {str(e)}")
            response = web.Response(
                text=json.dumps({"success": False, "message": f"处理请求失败: {str(e)}"}),
                content_type="application/json",
                status=500
            )
            self._add_cors_headers(response)
            return response

    async def _handle_volume_status(self, request, data):
        """处理设备发送的音量状态更新"""
        try:
            # 验证必需参数
            device_id = data.get("device_id")
            current_volume = data.get("current_volume")
            
            if not device_id:
                response = web.Response(
                    text=json.dumps({"success": False, "message": "缺少device_id参数"}),
                    content_type="application/json",
                    status=400
                )
                self._add_cors_headers(response)
                return response
                
            if current_volume is None:
                response = web.Response(
                    text=json.dumps({"success": False, "message": "缺少current_volume参数"}),
                    content_type="application/json",
                    status=400
                )
                self._add_cors_headers(response)
                return response

            # 调用APP回传接口
            await self._send_volume_callback(device_id, current_volume)

            # 构造要转发给APP的消息
            app_message = {
                "type": "volume_status",
                "device_id": device_id,
                "current_volume": current_volume,
                "timestamp": asyncio.get_event_loop().time(),
                "status": data.get("status", "success"),
                "message": data.get("message", "音量状态更新")
            }

            # 记录日志
            self.logger.info(f"收到设备 {device_id} 的音量状态更新: {current_volume}")
            
            response = web.Response(
                text=json.dumps({
                    "success": True, 
                    "message": "音量状态已接收",
                    "data": app_message
                }),
                content_type="application/json"
            )
            self._add_cors_headers(response)
            return response

        except Exception as e:
            self.logger.error(f"处理音量状态更新时发生错误: {str(e)}")
            response = web.Response(
                text=json.dumps({"success": False, "message": f"处理状态更新失败: {str(e)}"}),
                content_type="application/json",
                status=500
            )
            self._add_cors_headers(response)
            return response

    async def _handle_device_reply(self, request, data):
        """处理设备回传的消息"""
        try:
            # 验证必需参数
            device_id = data.get("device_id")
            message_type = data.get("type")
            content = data.get("content")
            value = data.get("value")
            
            if not device_id:
                response = web.Response(
                    text=json.dumps({"success": False, "message": "缺少device_id参数"}),
                    content_type="application/json",
                    status=400
                )
                self._add_cors_headers(response)
                return response
                
            if message_type != "reply":
                response = web.Response(
                    text=json.dumps({"success": False, "message": "消息类型必须为reply"}),
                    content_type="application/json",
                    status=400
                )
                self._add_cors_headers(response)
                return response
                
            if not content:
                response = web.Response(
                    text=json.dumps({"success": False, "message": "缺少content参数"}),
                    content_type="application/json",
                    status=400
                )
                self._add_cors_headers(response)
                return response
                
            if value is None:
                response = web.Response(
                    text=json.dumps({"success": False, "message": "缺少value参数"}),
                    content_type="application/json",
                    status=400
                )
                self._add_cors_headers(response)
                return response

            self.logger.info(f"收到设备 {device_id} 的回传消息: type={message_type}, content={content}, value={value}")

            # 根据content类型调用对应的回调方法
            if content == "volume":
                await self._send_volume_callback(device_id, value)
                response = web.Response(
                    text=json.dumps({"success": True, "message": "音量回调已处理"}),
                    content_type="application/json",
                    status=200
                )
            elif content == "microphone":
                await self._send_microphone_callback(device_id, value)
                response = web.Response(
                    text=json.dumps({"success": True, "message": "麦克风回调已处理"}),
                    content_type="application/json",
                    status=200
                )
            else:
                response = web.Response(
                    text=json.dumps({"success": False, "message": f"不支持的content类型: {content}"}),
                    content_type="application/json",
                    status=400
                )
                
            self._add_cors_headers(response)
            return response

        except Exception as e:
            self.logger.error(f"处理设备回传消息时发生错误: {str(e)}")
            response = web.Response(
                text=json.dumps({"success": False, "message": f"处理设备回传消息失败: {str(e)}"}),
                content_type="application/json",
                status=500
            )
            self._add_cors_headers(response)
            return response

    async def _send_volume_callback(self, device_id, volume):
        """向APP回传音量信息"""
        try:
            callback_url = "https://test.neurodrive.cn/api/car/setVolumeCallback"
            callback_data = {
                "mac": device_id,  # 使用device_id作为mac地址
                "volume": volume
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(callback_url, json=callback_data) as response:
                    if response.status == 200:
                        self.logger.info(f"成功向APP回传音量信息: device_id={device_id}, volume={volume}")
                    else:
                        self.logger.warning(f"向APP回传音量信息失败: status={response.status}, device_id={device_id}")
                        
        except Exception as e:
            self.logger.error(f"向APP回传音量信息时发生错误: {str(e)}")

    async def _send_microphone_callback(self, device_id, microphone_status):
        """向APP回传麦克风状态信息"""
        try:
            callback_url = "https://test.neurodrive.cn/api/car/setMicrophoneCallback"
            callback_data = {
                "mac": device_id,  # 使用device_id作为mac地址
                "microphone_status": microphone_status
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(callback_url, json=callback_data) as response:
                    if response.status == 200:
                        self.logger.info(f"成功向APP回传麦克风状态信息: device_id={device_id}, microphone_status={microphone_status}")
                    else:
                        self.logger.warning(f"向APP回传麦克风状态信息失败: status={response.status}, device_id={device_id}")
                        
        except Exception as e:
            self.logger.error(f"向APP回传麦克风状态信息时发生错误: {str(e)}")

    async def handle_get(self, request):
        """处理GET请求 - 获取设备当前音量状态"""
        try:
            device_id = request.query.get("device_id")
            
            if not device_id:
                response = web.Response(
                    text=json.dumps({"success": False, "message": "缺少device_id参数"}),
                    content_type="application/json",
                    status=400
                )
                self._add_cors_headers(response)
                return response

            # 验证WebSocket服务器
            if not self.websocket_server or not hasattr(self.websocket_server, "active_connections"):
                response = web.Response(
                    text=json.dumps({"success": False, "message": "WebSocket服务器未初始化"}),
                    content_type="application/json",
                    status=500
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
                    text=json.dumps({"success": False, "message": f"设备 {device_id} 未在线"}),
                    content_type="application/json",
                    status=404
                )
                self._add_cors_headers(response)
                return response

            # 构造查询音量状态的消息 - 使用新的JSON格式
            query_message = {
                "type": "peripheral",
                "action": "get_volume",
                "value": None,
                "timestamp": asyncio.get_event_loop().time()
            }

            # 发送查询请求给设备
            try:
                await target_connection.websocket.send(json.dumps(query_message))
                self.logger.info(f"已向设备 {device_id} 发送音量查询请求")
                
                response = web.Response(
                    text=json.dumps({
                        "success": True, 
                        "message": f"音量查询请求已发送给设备 {device_id}",
                        "data": {
                            "device_id": device_id,
                            "action": "get_volume"
                        }
                    }),
                    content_type="application/json"
                )
                self._add_cors_headers(response)
                return response
                
            except Exception as e:
                self.logger.error(f"发送查询请求给设备 {device_id} 失败: {str(e)}")
                response = web.Response(
                    text=json.dumps({"success": False, "message": f"发送查询请求失败: {str(e)}"}),
                    content_type="application/json",
                    status=500
                )
                self._add_cors_headers(response)
                return response

        except Exception as e:
            self.logger.error(f"处理音量查询请求时发生错误: {str(e)}")
            response = web.Response(
                text=json.dumps({"success": False, "message": f"处理查询请求失败: {str(e)}"}),
                content_type="application/json",
                status=500
            )
            self._add_cors_headers(response)
            return response

    async def handle_options(self, request):
        """处理OPTIONS请求 - CORS预检"""
        response = web.Response(
            text="",
            content_type="application/json"
        )
        self._add_cors_headers(response)
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        return response

    async def handle_device_reply_message(self, device_id, message_data):
        """处理从WebSocket收到的设备回复消息
        
        Args:
            device_id: 设备ID
            message_data: 消息数据，格式为 {type: "reply", content: "volume"/"microphone", value: 值}
        """
        try:
            message_type = message_data.get("type")
            content = message_data.get("content")
            value = message_data.get("value")
            
            # 验证消息格式
            if message_type != "reply":
                self.logger.warning(f"收到非reply类型的消息: {message_type}")
                return False
                
            if not content:
                self.logger.warning(f"收到的消息缺少content字段")
                return False
                
            if value is None:
                self.logger.warning(f"收到的消息缺少value字段")
                return False

            # 规范化数值
            normalized_value = value
            try:
                normalized_value = int(value)
            except (ValueError, TypeError):
                pass
            # 支持mic和microphone两种格式
            if content in ["microphone", "mic"] and isinstance(normalized_value, int):
                if normalized_value not in [0, 1]:
                    self.logger.warning(f"麦克风值不在[0,1]: {normalized_value}")
                    normalized_value = None

            self.logger.info(f"收到设备 {device_id} 的回复消息: type={message_type}, content={content}, value={value}")

            # 更新设备信息缓存
            try:
                cache_key = f"device_info:{device_id}"
                current = cache_manager.get(CacheType.DEVICE_INFO, cache_key) or {}
                if content == "volume" and normalized_value is not None:
                    current["volume"] = normalized_value
                elif content in ["microphone", "mic"] and normalized_value is not None:
                    current["microphone"] = normalized_value
                current["updated_at"] = int(asyncio.get_event_loop().time())
                cache_manager.set(CacheType.DEVICE_INFO, cache_key, current, ttl=None)
                self.logger.info(f"设备 {device_id} 缓存已更新: {current}")
            except Exception as e:
                self.logger.error(f"更新设备缓存失败: {str(e)}")

            # 检查是否有等待的请求，并触发事件
            # 由于硬件回复中没有request_id，我们使用设备ID和内容类型来匹配
            self.logger.info(f"检查等待请求，device_id: {device_id}, content: {content}")
            self.logger.info(f"当前pending_requests: {list(self.pending_requests.keys())}")
            
            if device_id in self.pending_requests:
                device_requests = self.pending_requests[device_id]
                self.logger.info(f"找到设备 {device_id} 的等待请求: {list(device_requests.keys())}")
                
                # 查找匹配的等待请求（按内容类型）
                # 需要同时匹配mic和microphone类型
                for request_id, request_info in list(device_requests.items()):
                    request_type = request_info.get("type")
                    self.logger.info(f"检查请求 {request_id}: request_type={request_type}, content={content}")
                    
                    # 如果硬件回复mic，匹配microphone类型的请求；如果硬件回复microphone，也匹配microphone类型的请求
                    if (content == "mic" and request_type == "microphone") or (content == request_type):
                        event = request_info.get("event")
                        if event:
                            event.set()
                            self.logger.info(f"触发等待事件，device_id: {device_id}, content: {content}, request_id: {request_id}")
                        else:
                            self.logger.warning(f"等待事件为空，request_id: {request_id}")
                        break
                    else:
                        self.logger.info(f"类型不匹配: content={content}, request_type={request_type}")
                else:
                    self.logger.warning(f"没有找到匹配的等待请求，device_id: {device_id}, content: {content}")
            else:
                self.logger.warning(f"设备 {device_id} 没有等待的请求")

            # 根据content类型调用对应的回调方法
            if content == "volume":
                await self._send_volume_callback(device_id, normalized_value if normalized_value is not None else value)
                self.logger.info(f"已处理设备 {device_id} 的音量回调: {value}")
                return True
            elif content in ["microphone", "mic"]:
                await self._send_microphone_callback(device_id, normalized_value if normalized_value is not None else value)
                self.logger.info(f"已处理设备 {device_id} 的麦克风回调: {value}")
                return True
            else:
                self.logger.warning(f"不支持的content类型: {content}")
                return False

        except Exception as e:
            self.logger.error(f"处理设备 {device_id} 回复消息时发生错误: {str(e)}")
            return False