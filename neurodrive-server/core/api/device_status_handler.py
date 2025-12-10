import json
from aiohttp import web
from core.api.base_handler import BaseHandler

# 新增：缓存管理器导入，用于读取设备音量与麦克风状态
from core.utils.cache.manager import cache_manager, CacheType

TAG = __name__


class DeviceStatusHandler(BaseHandler):
    def __init__(self, config: dict, websocket_server=None):
        super().__init__(config)
        self.websocket_server = websocket_server

    def _check_device_status(self, device_id):
        """检查特定设备的在线状态
        
        Args:
            device_id (str): 设备ID
            
        Returns:
            dict: 包含设备状态信息的字典
        """
        if not self.websocket_server or not hasattr(self.websocket_server, "active_connections"):
            return {"status": 0, "message": "WebSocket服务器未初始化"}
        
        # 查找指定设备
        for conn in self.websocket_server.active_connections:
            if hasattr(conn, "device_id") and conn.device_id == device_id:
                device_info = {
                    "status": 1,  # 在线
                    "device_id": conn.device_id,
                    "last_activity": getattr(conn, "last_activity_time", 0),
                    "client_ip": getattr(conn, "client_ip", "unknown")
                }
                
                # 如果有设备名称，也添加进去
                if hasattr(conn, "device_name") and conn.device_name:
                    device_info["device_name"] = conn.device_name
                
                
                # 从缓存读取音量与麦克风状态
                cache_key = f"device_info:{device_id}"
                cached = cache_manager.get(CacheType.DEVICE_INFO, cache_key)
                if cached is not None:
                    if "volume" in cached:
                        device_info["volume"] = cached["volume"]
                    if "microphone" in cached:
                        device_info["microphone"] = cached["microphone"]
                
                return device_info
        
        # 设备不在线
        return {"status": 0, "device_id": device_id, "message": "设备离线"}

    def _check_device_status_simple(self, device_id):
        """检查特定设备的在线状态（简化版本，仅返回status字段）
        
        Args:
            device_id (str): 设备ID
            
        Returns:
            dict: 只包含status字段的字典
        """
        if not self.websocket_server or not hasattr(self.websocket_server, "active_connections"):
            return {"status": 0}
        
        # 查找指定设备
        for conn in self.websocket_server.active_connections:
            if hasattr(conn, "device_id") and conn.device_id == device_id:
                # 简化返回：status + 缓存的volume/microphone（如果有）
                result = {"status": 1}
                cache_key = f"device_info:{device_id}"
                cached = cache_manager.get(CacheType.DEVICE_INFO, cache_key)
                if cached is not None:
                    if "volume" in cached:
                        result["volume"] = cached["volume"]
                    if "microphone" in cached:
                        result["microphone"] = cached["microphone"]
                return result
        
        # 设备不在线
        return {"status": 0}

    async def handle_get(self, request):
        """处理获取在线设备列表的GET请求，支持通过device_id查询特定设备状态"""
        try:
            # 检查是否有device_id查询参数
            device_id = request.query.get('device_id')
            
            if device_id:
                # 查询特定设备状态
                device_status = self._check_device_status(device_id)
                response = web.Response(
                    text=json.dumps({
                        "success": True,
                        "data": device_status
                    }),
                    content_type="application/json"
                )
                self._add_cors_headers(response)
                return response
            
            # 验证WebSocket服务器是否初始化
            if not self.websocket_server or not hasattr(self.websocket_server, "active_connections"):
                response = web.Response(
                    text=json.dumps({"success": False, "message": "WebSocket服务器未初始化"}),
                    content_type="application/json"
                )
                self._add_cors_headers(response)
                return response

            # 获取在线设备列表
            online_devices = []
            for conn in self.websocket_server.active_connections:
                if hasattr(conn, "device_id") and conn.device_id:
                    device_info = {
                        "device_id": conn.device_id,
                        "last_activity": getattr(conn, "last_activity_time", 0),
                        "client_ip": getattr(conn, "client_ip", "unknown")
                    }
                    
                    # 如果有设备名称，也添加进去
                    if hasattr(conn, "device_name") and conn.device_name:
                        device_info["device_name"] = conn.device_name
                    
                    # 从缓存读取音量与麦克风状态
                    cache_key = f"device_info:{conn.device_id}"
                    cached = cache_manager.get(CacheType.DEVICE_INFO, cache_key)
                    if cached is not None:
                        if "volume" in cached:
                            device_info["volume"] = cached["volume"]
                        if "microphone" in cached:
                            device_info["microphone"] = cached["microphone"]


                    online_devices.append(device_info)

            # 返回成功响应
            response = web.Response(
                text=json.dumps({
                    "success": True, 
                    "data": {
                        "total": len(online_devices),
                        "devices": online_devices
                    }
                }),
                content_type="application/json"
            )
            self._add_cors_headers(response)
            return response

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"处理获取在线设备请求失败: {e}")
            response = web.Response(
                text=json.dumps({"success": False, "message": f"处理请求失败: {str(e)}"}),
                content_type="application/json"
            )
            self._add_cors_headers(response)
            return response

    async def handle_post(self, request):
        """处理POST请求，通过device_id查询设备状态"""
        try:
            # 解析请求体
            try:
                request_data = await request.json()
            except json.JSONDecodeError:
                response = web.Response(
                    text=json.dumps({"success": False, "message": "无效的JSON格式"}),
                    content_type="application/json"
                )
                self._add_cors_headers(response)
                return response

            # 验证device_id参数
            device_id = request_data.get("device_id")
            if not device_id:
                response = web.Response(
                    text=json.dumps({"success": False, "message": "缺少device_id参数"}),
                    content_type="application/json"
                )
                self._add_cors_headers(response)
                return response

            # 查询设备状态（简化版本）
            device_status = self._check_device_status_simple(device_id)
            
            response = web.Response(
                text=json.dumps(device_status),
                content_type="application/json"
            )
            self._add_cors_headers(response)
            return response

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"处理POST设备状态查询请求失败: {e}")
            response = web.Response(
                text=json.dumps({"success": False, "message": f"处理请求失败: {str(e)}"}),
                content_type="application/json"
            )
            self._add_cors_headers(response)
            return response

    async def handle_options(self, request):
        """处理OPTIONS请求，用于CORS预检"""
        response = web.Response()
        self._add_cors_headers(response)
        return response