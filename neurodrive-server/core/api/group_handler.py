import json
import uuid
from aiohttp import web
from core.api.base_handler import BaseHandler
from plugins_func.functions.create_group import handle_create_group_async

TAG = __name__


class GroupHandler(BaseHandler):
    def __init__(self, config: dict, websocket_server=None):
        super().__init__(config)
        self.websocket_server = websocket_server

    async def handle_post(self, request):
        """处理群聊相关POST请求"""
        try:
            # 获取请求数据
            data = await request.json()
            action = data.get("action", "create")
            self.logger.bind(tag=TAG).debug(f"群聊请求数据: {data}, 操作: {action}")

            # 验证必要参数
            if not data.get("device_id"):
                response = web.Response(
                    text=json.dumps({"success": False, "message": "缺少设备ID"}),
                    content_type="application/json"
                )
                self._add_cors_headers(response)
                return response

            # 根据操作类型分发处理
            if action == "create":
                return await self._handle_create_group(data)
            elif action == "join":
                return await self._handle_join_group(data)
            elif action == "leave":
                return await self._handle_leave_group(data)
            else:
                response = web.Response(
                    text=json.dumps({"success": False, "message": f"不支持的操作: {action}"}),
                    content_type="application/json"
                )
                self._add_cors_headers(response)
                return response

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"处理群聊请求失败: {e}")
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

    async def _handle_create_group(self, data):
        """处理创建群聊请求"""
        # 修正点：这里删除了多余的缩进（从8空格改为4空格）
        
        # 验证WebSocket服务器是否初始化
        if not self.websocket_server or not hasattr(self.websocket_server, "active_connections"):
            response = web.Response(
                text=json.dumps({"success": False, "message": "WebSocket服务器未初始化"}),
                content_type="application/json"
            )
            self._add_cors_headers(response)
            return response

        # 获取参数
        device_id = data.get("device_id")
        group_name = data.get("group_name", "默认群聊")
        invitation_message = data.get("invitation_message", "邀请你加入群聊")

        # 查找发起建群的设备连接
        creator_connection = None
        for conn in self.websocket_server.active_connections:
            if hasattr(conn, "device_id") and conn.device_id == device_id:
                creator_connection = conn
                break

        if not creator_connection:
            response = web.Response(
                text=json.dumps({"success": False, "message": "发起设备未连接"}),
                content_type="application/json"
            )
            self._add_cors_headers(response)
            return response

        # 检查是否有其他在线设备
        online_devices = []
        for conn in self.websocket_server.active_connections:
            if hasattr(conn, "device_id") and conn.device_id != device_id:
                online_devices.append(conn)

        if not online_devices:
            response = web.Response(
                text=json.dumps({
                    "success": False, 
                    "message": "当前没有其他在线设备可以邀请",
                    "data": {
                        "group_id": None,
                        "online_devices_count": 0
                    }
                }),
                content_type="application/json"
            )
            self._add_cors_headers(response)
            return response

        # 模拟连接对象的必要属性（为了兼容现有的建群函数）
        if not hasattr(creator_connection, 'loop'):
            import asyncio
            creator_connection.loop = asyncio.get_event_loop()
        
        if not hasattr(creator_connection, 'server'):
            creator_connection.server = self.websocket_server

        # 调用现有的建群逻辑
        try:
            result = await handle_create_group_async(creator_connection, group_name, invitation_message)
            
            # 获取创建的群聊ID
            group_id = getattr(creator_connection, 'current_group_id', None)
            
            response = web.Response(
                text=json.dumps({
                    "success": True, 
                    "message": "群聊创建成功",
                    "data": {
                        "group_id": group_id,
                        "group_name": group_name,
                        "creator_device_id": device_id,
                        "invitation_sent_to": len(online_devices),
                        "result": result
                    }
                }),
                content_type="application/json"
            )
            self._add_cors_headers(response)
            return response
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"建群异步处理失败: {e}")
            response = web.Response(
                text=json.dumps({"success": False, "message": f"建群处理失败: {str(e)}"}),
                content_type="application/json"
            )
            self._add_cors_headers(response)
        return response

    async def _handle_join_group(self, data):
        """处理加入群聊请求"""
        device_id = data.get("device_id")
        group_id = data.get("group_id")
        
        if not group_id:
            response = web.Response(
                text=json.dumps({"success": False, "message": "缺少群聊ID"}),
                content_type="application/json"
            )
            self._add_cors_headers(response)
            return response
        
        # 验证WebSocket服务器是否初始化
        if not self.websocket_server or not hasattr(self.websocket_server, "active_groups"):
            response = web.Response(
                text=json.dumps({"success": False, "message": "群聊服务未初始化"}),
                content_type="application/json"
            )
            self._add_cors_headers(response)
            return response
        
        # 检查群聊是否存在
        if group_id not in self.websocket_server.active_groups:
            response = web.Response(
                text=json.dumps({"success": False, "message": "群聊不存在"}),
                content_type="application/json"
            )
            self._add_cors_headers(response)
            return response
        
        # 查找设备连接
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
        
        # 加入群聊
        group_info = self.websocket_server.active_groups[group_id]
        if device_id not in group_info['members']:
            group_info['members'].append(device_id)
        
        # 设置设备的群聊ID
        target_connection.current_group_id = group_id
        
        # 发送确认消息
        from core.handle.intentHandler import speak_txt
        speak_txt(target_connection, f"您已加入群聊 '{group_info['group_name']}'")
        
        response = web.Response(
            text=json.dumps({
                "success": True, 
                "message": "成功加入群聊",
                "data": {
                    "group_id": group_id,
                    "group_name": group_info['group_name'],
                    "device_id": device_id
                }
            }),
            content_type="application/json"
        )
        self._add_cors_headers(response)
        return response
    
    async def _handle_leave_group(self, data):
        """处理退出群聊请求"""
        device_id = data.get("device_id")
        group_id = data.get("group_id")
        
        # 查找设备连接
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
        
        # 如果没有指定群聊ID，从当前群聊退出
        if not group_id:
            if hasattr(target_connection, 'current_group_id') and target_connection.current_group_id:
                group_id = target_connection.current_group_id
            else:
                response = web.Response(
                    text=json.dumps({"success": False, "message": "设备不在任何群聊中"}),
                    content_type="application/json"
                )
                self._add_cors_headers(response)
                return response
        
        # 清除群聊状态
        target_connection.current_group_id = None
        
        # 从群聊成员列表中移除
        if (hasattr(self.websocket_server, "active_groups") and 
            group_id in self.websocket_server.active_groups):
            group_info = self.websocket_server.active_groups[group_id]
            if device_id in group_info.get('members', []):
                group_info['members'].remove(device_id)
        
        # 发送确认消息
        from core.handle.intentHandler import speak_txt
        speak_txt(target_connection, "您已退出群聊")
        
        response = web.Response(
            text=json.dumps({
                "success": True, 
                "message": "成功退出群聊",
                "data": {
                    "group_id": group_id,
                    "device_id": device_id
                }
            }),
            content_type="application/json"
        )
        self._add_cors_headers(response)
        return response
    
    async def handle_get(self, request):
        """处理获取群聊列表GET请求"""
        try:
            # 验证WebSocket服务器是否初始化
            if not self.websocket_server or not hasattr(self.websocket_server, "active_groups"):
                response = web.Response(
                    text=json.dumps({"success": False, "message": "群聊服务未初始化"}),
                    content_type="application/json"
                )
                self._add_cors_headers(response)
                return response
            
            # 获取所有活跃群聊信息
            groups_info = []
            for group_id, group_data in self.websocket_server.active_groups.items():
                groups_info.append({
                    "group_id": group_id,
                    "group_name": group_data.get("group_name", "未命名群聊"),
                    "creator": group_data.get("creator", "未知"),
                    "members": group_data.get("members", []),
                    "member_count": len(group_data.get("members", [])),
                    "pending_invitations": group_data.get("pending_invitations", []),
                    "pending_count": len(group_data.get("pending_invitations", []))
                })
            
            response = web.Response(
                text=json.dumps({
                    "success": True,
                    "message": "获取群聊列表成功",
                    "data": {
                        "groups": groups_info,
                        "total_groups": len(groups_info)
                    }
                }),
                content_type="application/json"
            )
            self._add_cors_headers(response)
            return response
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"获取群聊列表失败: {e}")
            response = web.Response(
                text=json.dumps({"success": False, "message": f"获取群聊列表失败: {str(e)}"}),
                content_type="application/json"
            )
            self._add_cors_headers(response)
            return response

    async def handle_options(self, request):
        """处理OPTIONS请求，用于CORS预检"""
        response = web.Response()
        self._add_cors_headers(response)
        return response