import json
from aiohttp import web
from core.api.base_handler import BaseHandler

TAG = __name__


class ConnectionHandler(BaseHandler):
    def __init__(self, config: dict, websocket_server=None):
        super().__init__(config)
        self.websocket_server = websocket_server

    async def handle_post(self, request):
        """处理连接管理POST请求"""
        try:
            # 获取请求数据
            data = await request.json()
            self.logger.bind(tag=TAG).debug(f"连接管理请求数据: {data}")

            # 验证必要参数
            if not data.get("action"):
                return web.Response(
                    text=json.dumps({"success": False, "message": "缺少操作类型"}),
                    content_type="application/json"
                )

            action = data.get("action")
            device_id = data.get("device_id")

            if action == "disconnect":
                # 断开指定设备连接
                if not device_id:
                    return web.Response(
                        text=json.dumps({"success": False, "message": "缺少设备ID"}),
                        content_type="application/json"
                    )
                
                result = await self._disconnect_device(device_id)
                return web.Response(
                    text=json.dumps(result),
                    content_type="application/json"
                )
            
            elif action == "disconnect_all":
                # 断开所有连接
                result = await self._disconnect_all_devices()
                return web.Response(
                    text=json.dumps(result),
                    content_type="application/json"
                )
            
            elif action == "list":
                # 列出所有活跃连接
                result = await self._list_connections()
                return web.Response(
                    text=json.dumps(result),
                    content_type="application/json"
                )
            
            else:
                return web.Response(
                    text=json.dumps({"success": False, "message": "不支持的操作类型"}),
                    content_type="application/json"
                )

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"处理连接管理请求时出错: {e}")
            return web.Response(
                text=json.dumps({"success": False, "message": f"服务器错误: {str(e)}"}),
                content_type="application/json",
                status=500
            )

    async def _disconnect_device(self, device_id):
        """断开指定设备的连接"""
        try:
            if not self.websocket_server:
                return {"success": False, "message": "WebSocket服务器未初始化"}
            
            # 查找指定设备的连接
            target_handler = None
            for handler in self.websocket_server.active_connections:
                if hasattr(handler, 'device_id') and handler.device_id == device_id:
                    target_handler = handler
                    break
            
            if target_handler:
                # 主动关闭连接
                await target_handler.close()
                self.logger.bind(tag=TAG).info(f"已主动断开设备 {device_id} 的连接")
                return {"success": True, "message": f"设备 {device_id} 连接已断开"}
            else:
                return {"success": False, "message": f"未找到设备 {device_id} 的连接"}
        
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"断开设备连接时出错: {e}")
            return {"success": False, "message": f"断开连接失败: {str(e)}"}

    async def _disconnect_all_devices(self):
        """断开所有设备连接"""
        try:
            if not self.websocket_server:
                return {"success": False, "message": "WebSocket服务器未初始化"}
            
            # 获取所有活跃连接的副本
            handlers = list(self.websocket_server.active_connections)
            disconnected_count = 0
            
            for handler in handlers:
                try:
                    await handler.close()
                    disconnected_count += 1
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"断开连接时出错: {e}")
            
            self.logger.bind(tag=TAG).info(f"已断开 {disconnected_count} 个连接")
            return {"success": True, "message": f"已断开 {disconnected_count} 个连接"}
        
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"断开所有连接时出错: {e}")
            return {"success": False, "message": f"断开连接失败: {str(e)}"}

    async def _list_connections(self):
        """列出所有活跃连接"""
        try:
            if not self.websocket_server:
                return {"success": False, "message": "WebSocket服务器未初始化"}
            
            connections = []
            for handler in self.websocket_server.active_connections:
                connection_info = {
                    "device_id": getattr(handler, 'device_id', 'unknown'),
                    "client_id": getattr(handler, 'client_id', 'unknown'),
                    "connected_time": getattr(handler, 'connected_time', None),
                    "last_activity": getattr(handler, 'last_activity_time', None)
                }
                connections.append(connection_info)
            
            return {
                "success": True, 
                "message": f"当前有 {len(connections)} 个活跃连接",
                "connections": connections
            }
        
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"获取连接列表时出错: {e}")
            return {"success": False, "message": f"获取连接列表失败: {str(e)}"}

    async def handle_options(self, request):
        """处理OPTIONS请求（CORS预检）"""
        return web.Response(
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            }
        )