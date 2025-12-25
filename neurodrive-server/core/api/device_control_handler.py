import json
import asyncio
import aiohttp
from aiohttp import web
from core.api.base_handler import BaseHandler

TAG = __name__


class DeviceControlHandler(BaseHandler):
    def __init__(self, config: dict, websocket_server=None):
        super().__init__(config)
        self.websocket_server = websocket_server
        self.active_groups = {}
        if not hasattr(DeviceControlHandler, "_shared_pending_cmds"):
            DeviceControlHandler._shared_pending_cmds = {}
        self.pending_cmds = DeviceControlHandler._shared_pending_cmds
        if not hasattr(DeviceControlHandler, "_shared_device_status"):
            DeviceControlHandler._shared_device_status = {}
        self.device_status = DeviceControlHandler._shared_device_status

    async def handle_post(self, request):
        """处理设备控制POST请求"""
        try:
            # 获取请求数据
            data = await request.json()
            self.logger.bind(tag=TAG).debug(f"设备控制请求数据: {data}")

            # 验证必要参数
            if not data.get("device_id"):
                return web.Response(
                    text=json.dumps({"success": False, "message": "缺少设备ID"}),
                    content_type="application/json"
                )

            if not data.get("command"):
                return web.Response(
                    text=json.dumps({"success": False, "message": "缺少控制指令"}),
                    content_type="application/json"
                )

            # 获取设备ID和控制指令
            device_id = data.get("device_id")
            command = data.get("command")

            # 验证指令格式
            if not isinstance(command, int):
                return web.Response(
                    text=json.dumps({"success": False, "message": "控制指令必须是整数"}),
                    content_type="application/json"
                )
            print(f"处理设备控制请求: 设备ID={device_id}, 指令={command}")
            # 映射指令到设备操作
            device_name, method_name, parameters = self._map_command_to_operation(command)

            # 查找设备连接
            if not self.websocket_server or not hasattr(self.websocket_server, "active_connections"):
                print(f"WebSocket服务器未初始化")
                return web.Response(
                    text=json.dumps({"success": False, "message": "WebSocket服务器未初始化"}),
                    content_type="application/json"  
                )

            # 查找目标设备连接
            target_connection = None
            print(f"正在查找设备连接: {device_id}")
            for conn in self.websocket_server.active_connections:
                if conn.device_id == device_id:
                    target_connection = conn
                    print(f"找到设备连接: {conn.device_id}")
                    break

            if not target_connection:
                try:
                    if self.device_status.get(device_id) != 0:
                        self.device_status[device_id] = 0
                        await self._notify_app_online_status(device_id, 0)
                except Exception as _:
                    pass
                return web.Response(
                    text=json.dumps({"success": False, "message": "设备未连接"}),
                    content_type="application/json"
                )

            # 构建IoT控制命令
            command_data = {
                "name": device_name,
                "method": method_name,
            }

            if parameters:
                command_data["parameters"] = parameters

            ws_message = json.dumps({"type": "iot", "cmd": command})
            await target_connection.websocket.send(ws_message)
            self.logger.bind(tag=TAG).info(f"成功发送控制指令 {command} 到设备 {device_id}")
            if device_id not in self.pending_cmds:
                self.pending_cmds[device_id] = {}
            wait_event = asyncio.Event()
            self.pending_cmds[device_id][command] = wait_event
            try:
                await asyncio.wait_for(wait_event.wait(), timeout=5.0)
                try:
                    if self.device_status.get(device_id) != 1:
                        self.device_status[device_id] = 1
                        await self._notify_app_online_status(device_id, 1)
                except Exception as _:
                    pass
                return web.Response(
                    text=json.dumps({"success": True, "message": "设备已确认指令"}),
                    content_type="application/json"
                )
            except asyncio.TimeoutError:
                is_online = False
                for conn in self.websocket_server.active_connections:
                    if hasattr(conn, "device_id") and conn.device_id == device_id and hasattr(conn, "websocket") and conn.websocket:
                        try:
                            pong_waiter = await conn.websocket.ping()
                            await asyncio.wait_for(pong_waiter, timeout=1.0)
                            is_online = True
                        except Exception:
                            is_online = False
                        break
                status_msg = "设备在线但未确认指令" if is_online else "设备未在线"
                try:
                    new_status = 1 if is_online else 0
                    if self.device_status.get(device_id) != new_status:
                        self.device_status[device_id] = new_status
                        await self._notify_app_online_status(device_id, new_status)
                except Exception as _:
                    pass
                return web.Response(
                    text=json.dumps({"success": False, "message": status_msg}),
                    content_type="application/json"
                )
            finally:
                if device_id in self.pending_cmds and command in self.pending_cmds[device_id]:
                    del self.pending_cmds[device_id][command]

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"处理设备控制请求失败: {e}")
            return web.Response(
                text=json.dumps({"success": False, "message": f"处理请求失败: {str(e)}"}),
                content_type="application/json"
            )
        # finally:
        #     # 添加CORS头信息
        #     response = web.Response()
        #     self._add_cors_headers(response)
        #     return response

    def _map_command_to_operation(self, command):
        """将指令映射到设备操作"""
        # 默认设备名称
        device_name = "Car"
        method_name = ""
        parameters = {}

        # 根据指令映射到具体操作
        if command == 1:
            method_name = "openAllWindows"
        elif command == 2:
            method_name = "closeAllWindows"
        elif command == 3:
            method_name = "startEngine"
        elif command == 4:
            method_name = "stopEngine"
        elif command == 5:
            method_name = "openTrunk"
        elif command == 6:
            method_name = "closeTrunk"
        elif command == 7:
            method_name = "openSunroof"
        elif command == 8:
            method_name = "closeSunroof"
        elif command == 9:
            method_name = "UnlockCar"
        elif command == 10:
            method_name = "LockCar"
        else:
            # 未知指令，使用默认方法
            method_name = "unknownCommand"
            parameters = {"code": command}

        return device_name, method_name, parameters

    async def handle_options(self, request):
        """处理OPTIONS请求，用于CORS预检"""
        response = web.Response()
        self._add_cors_headers(response)
        return response

    async def _notify_app_online_status(self, device_mac: str, status: int):
        url = "https://api.neurodrive.cn/api/car/onlineStatusCallback"
        payload = {"device_mac": device_mac, "status": status}
        headers = {}
        cfg = self.config.get("manager-api", {}) if isinstance(self.config, dict) else {}
        token = cfg.get("secret")
        if token:
            headers["Authorization"] = "Bearer " + token
            headers["Accept"] = "application/json"
        timeout = aiohttp.ClientTimeout(total=3)
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.post(url, json=payload) as resp:
                await resp.text()
                self.logger.bind(tag=TAG).info(f"已回调在线状态: device_mac={device_mac}, status={status}, http_status={resp.status}")

    async def handle_group_response(self, device_id, response, group_id):
        """
        处理设备对建群邀请的回复
        """
        if group_id not in self.active_groups:
            return
            
        group_info = self.active_groups[group_id]
        
        if response.lower() in ["同意", "agree", "yes"]:
            group_info["members"].append(device_id)
            # 通知群组成员有新成员加入
            await self.broadcast_to_group(group_id, f"设备 {device_id} 已加入群聊")
        else:
            # 记录拒绝的设备
            group_info["declined"].append(device_id)
    
    async def broadcast_to_group(self, group_id, message):
        """
        向群组所有成员广播消息
        """
        if group_id not in self.active_groups:
            return
            
        group_info = self.active_groups[group_id]
        
        for member_device_id in group_info["members"]:
            # 找到对应的连接并发送消息
            if hasattr(conn, 'device_id') and conn.device_id == member_device_id:
                    try:
                        # 检查WebSocket连接状态
                        if hasattr(conn, 'websocket') and conn.websocket and not conn.websocket.closed:
                            tts_message = {
                                "type": "tts",
                                "state": "sentence_start",
                                "text": message,
                                "sentence_type": "normal",
                                "group_id": group_id
                            }
                            await conn.websocket.send(json.dumps(tts_message))
                            
                            # 发送结束状态
                            end_message = {
                                "type": "tts",
                                "state": "sentence_end",
                                "group_id": group_id
                            }
                            await conn.websocket.send(json.dumps(end_message))
                            
                            print(f"成功向设备 {member_device_id} 发送群聊消息: {message}")
                        else:
                            print(f"设备 {member_device_id} WebSocket连接已断开")
                            # 从群组中移除断开的设备
                            if member_device_id in group_info["members"]:
                                group_info["members"].remove(member_device_id)
                    except Exception as e:
                        print(f"向设备 {member_device_id} 发送群聊消息失败: {e}")
                    break
    