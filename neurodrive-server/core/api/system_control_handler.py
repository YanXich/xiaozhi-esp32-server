import json
import asyncio
from aiohttp import web
from core.api.base_handler import BaseHandler

TAG = __name__


class SystemControlHandler(BaseHandler):
    def __init__(self, config: dict, websocket_server=None):
        super().__init__(config)
        self.websocket_server = websocket_server

    async def handle_post(self, request):
        """处理POST请求 - 系统控制（重启和删除ogg）"""
        try:
            # 解析请求数据
            data = await request.json()
            action = data.get("action")
            
            if action == "reboot":
                return await self._handle_reboot(request, data)
            elif action == "del_ogg":
                return await self._handle_del_ogg(request, data)
            elif action == "debug":
                return await self._handle_debug(request, data)
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

    async def _handle_reboot(self, request, data):
        """处理设备重启请求"""
        try:
            # 验证必需参数
            device_id = data.get("device_id")
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

            # 构造发送给设备的重启消息
            device_message = {
                "type": "system",
                "command": "reboot"
            }

            # 发送消息给设备
            try:
                await target_connection.websocket.send(json.dumps(device_message))
                self.logger.info(f"已向设备 {device_id} 发送重启请求")
                
                response = web.Response(
                    text=json.dumps({
                        "success": True, 
                        "message": f"重启请求已发送给设备 {device_id}",
                        "data": {
                            "device_id": device_id,
                            "command": "reboot"
                        }
                    }),
                    content_type="application/json"
                )
                self._add_cors_headers(response)
                return response
                
            except Exception as e:
                self.logger.error(f"发送重启消息给设备 {device_id} 失败: {str(e)}")
                response = web.Response(
                    text=json.dumps({"success": False, "message": f"发送消息给设备失败: {str(e)}"}),
                    content_type="application/json",
                    status=500
                )
                self._add_cors_headers(response)
                return response

        except Exception as e:
            self.logger.error(f"处理重启请求时发生错误: {str(e)}")
            response = web.Response(
                text=json.dumps({"success": False, "message": f"处理重启请求失败: {str(e)}"}),
                content_type="application/json",
                status=500
            )
            self._add_cors_headers(response)
            return response

    async def _handle_del_ogg(self, request, data):
        """处理删除ogg文件请求"""
        try:
            # 验证必需参数
            device_id = data.get("device_id")
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

            # 构造发送给设备的删除ogg消息
            device_message = {
                "type": "system",
                "command": "del_ogg"
            }

            # 发送消息给设备
            try:
                await target_connection.websocket.send(json.dumps(device_message))
                self.logger.info(f"已向设备 {device_id} 发送删除ogg请求")
                
                response = web.Response(
                    text=json.dumps({
                        "success": True, 
                        "message": f"删除ogg请求已发送给设备 {device_id}",
                        "data": {
                            "device_id": device_id,
                            "command": "del_ogg"
                        }
                    }),
                    content_type="application/json"
                )
                self._add_cors_headers(response)
                return response
                
            except Exception as e:
                self.logger.error(f"发送删除ogg消息给设备 {device_id} 失败: {str(e)}")
                response = web.Response(
                    text=json.dumps({"success": False, "message": f"发送消息给设备失败: {str(e)}"}),
                    content_type="application/json",
                    status=500
                )
                self._add_cors_headers(response)
                return response

        except Exception as e:
            self.logger.error(f"处理删除ogg请求时发生错误: {str(e)}")
            response = web.Response(
                text=json.dumps({"success": False, "message": f"处理删除ogg请求失败: {str(e)}"}),
                content_type="application/json",
                status=500
            )
            self._add_cors_headers(response)
            return response

    async def _handle_debug(self, request, data):
        """处理设备调整电阻请求"""
        try:
            device_id = data.get("device_id")
            if not device_id:
                response = web.Response(
                    text=json.dumps({"success": False, "message": "缺少device_id参数"}),
                    content_type="application/json",
                    status=400
                )
                self._add_cors_headers(response)
                return response

            if not self.websocket_server or not hasattr(self.websocket_server, "active_connections"):
                response = web.Response(
                    text=json.dumps({"success": False, "message": "WebSocket服务器未初始化"}),
                    content_type="application/json",
                    status=500
                )
                self._add_cors_headers(response)
                return response

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

            device_message = {
                "type": "system",
                "command": "debug"
            }

            try:
                await target_connection.websocket.send(json.dumps(device_message))
                self.logger.info(f"已向设备 {device_id} 发送调试请求")
                response = web.Response(
                    text=json.dumps({
                        "success": True,
                        "message": f"调试请求已发送给设备 {device_id}",
                        "data": {
                            "device_id": device_id,
                            "command": "debug"
                        }
                    }),
                    content_type="application/json"
                )
                self._add_cors_headers(response)
                return response
            except Exception as e:
                self.logger.error(f"发送调试消息给设备 {device_id} 失败: {str(e)}")
                response = web.Response(
                    text=json.dumps({"success": False, "message": f"发送消息给设备失败: {str(e)}"}),
                    content_type="application/json",
                    status=500
                )
                self._add_cors_headers(response)
                return response
        except Exception as e:
            self.logger.error(f"处理调试请求时发生错误: {str(e)}")
            response = web.Response(
                text=json.dumps({"success": False, "message": f"处理调试请求失败: {str(e)}"}),
                content_type="application/json",
                status=500
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
                    "message": "系统控制接口运行正常",
                    "data": {
                        "endpoint": "/xiaozhi/system/control",
                        "methods": ["POST", "GET"],
                        "supported_actions": ["reboot", "del_ogg", "debug"],
                        "online_devices": online_devices_count
                    }
                }),
                content_type="application/json"
            )
            self._add_cors_headers(response)
            return response

        except Exception as e:
            self.logger.error(f"处理GET请求失败: {str(e)}")
            response = web.Response(
                text=json.dumps({"success": False, "message": f"处理请求失败: {str(e)}"}),
                content_type="application/json",
                status=500
            )
            self._add_cors_headers(response)
            return response

    async def handle_options(self, request):
        """处理CORS预检请求"""
        response = web.Response()
        self._add_cors_headers(response)
        return response

    