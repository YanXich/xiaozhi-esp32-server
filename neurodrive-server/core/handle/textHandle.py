import json
from core.handle.abortHandle import handleAbortMessage
from core.handle.helloHandle import handleHelloMessage
from core.providers.tools.device_mcp import handle_mcp_message
from core.utils.util import remove_punctuation_and_length, filter_sensitive_info
from core.handle.receiveAudioHandle import startToChat, handleAudioMessage
from core.handle.sendAudioHandle import send_stt_message, send_tts_message
from core.providers.tools.device_iot import handleIotDescriptors, handleIotStatus
from core.handle.reportHandle import enqueue_asr_report
from core.handle.intentHandler import handle_user_intent, handle_group_invitation_reply, process_wakeup
from core.api.peripheral_control_handler import PeripheralControlHandler
import asyncio
import time

# 新增：缓存管理器导入，用于设备状态缓存
from core.utils.cache.manager import cache_manager, CacheType

TAG = __name__


async def handleTextMessage(conn, message):
    """处理文本消息"""
    try:
        msg_json = json.loads(message)
        if isinstance(msg_json, int):
            conn.logger.bind(tag=TAG).info(f"收到文本消息：{message}")
            await conn.websocket.send(message)
            return
        if msg_json["type"] == "hello":
            conn.logger.bind(tag=TAG).info(f"收到hello消息：{message}")
            await handleHelloMessage(conn, msg_json)
        elif msg_json["type"] == "abort":
            conn.logger.bind(tag=TAG).info(f"收到abort消息：{message}")

            #清空音频缓冲流
            conn.asr_audio.clear()
            #清空ASR音频队列
            while not conn.asr_audio_queue.empty():
                try:
                    conn.asr_audio_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
            #重置VAD状态
            conn.reset_vad_states()

            if "reason" in msg_json and (msg_json["reason"] == "abort_asr_start" or msg_json["reason"] == "abort_asr_stop"):
                conn.abort_asr_start = time.monotonic()

            
            await handleAbortMessage(conn)
        elif msg_json["type"] == "cmd": 
            conn.logger.bind(tag=TAG).info(f"收到控制指令cmd消息：{message}")
            # payload = msg_json.get("payload")
            # if payload != 0:
            #     conn.asr_audio.clear()
            #     while not conn.asr_audio_queue.empty():
            #         try:
            #             conn.asr_audio_queue.get_nowait()
            #         except asyncio.QueueEmpty:
            #             break
            #     conn.reset_vad_states()
            #     conn.abort_asr_start = time.monotonic()
            #     conn.control_cmd_active = True
            #     conn.control_cmd_timeout = time.monotonic() + 0.5

        elif msg_json["type"] == "wake": # 唤醒
            # await process_wakeup(conn)
            conn.just_woken_up = True if not conn.session_awakened else False
            conn.session_awakened = True
            conn.logger.bind(tag=TAG).info(f"收到wake消息：{message}, just_woken_up={conn.just_woken_up}, session_awakened={conn.session_awakened}")

        elif msg_json["type"] == "listen":
            conn.logger.bind(tag=TAG).info(f"收到listen消息：{message}")
            if "mode" in msg_json:
                conn.client_listen_mode = msg_json["mode"]
                conn.logger.bind(tag=TAG).debug(
                    f"客户端拾音模式：{conn.client_listen_mode}"
                )
            if msg_json["state"] == "start":
                conn.client_have_voice = True
                conn.client_voice_stop = False
                conn.set_state_user_speaking()
                print("", flush=True)
            elif msg_json["state"] == "stop":
                conn.client_have_voice = True
                conn.client_voice_stop = True
                conn.set_state_thinking()
                print("stop state from esp32... voice stop true", flush=True)
                if len(conn.asr_audio) > 0:
                    await handleAudioMessage(conn, b"")
            elif msg_json["state"] == "detect":
                conn.client_have_voice = False
                conn.asr_audio.clear()
                conn.set_state_idle()
                print(msg_json)
                if "text" in msg_json:
                    original_text = msg_json["text"]  # 保留原始文本
                    
                    # # 首先进行意图分析，包括唤醒词检查
                    # print("ready gogo...", flush=True)
                    # intent_handled = await handle_user_intent(conn, original_text)
                    # print("intent_handled===>", intent_handled, flush=True)
                    # if intent_handled:
                    #     # 如果意图已被处理（包括唤醒词处理），不再进行后续处理
                    #     return
                    
                    # 意图未被处理，继续常规聊天流程
                    # 上报纯文字数据（复用ASR上报功能，但不提供音频数据）
                    enqueue_asr_report(conn, original_text, [])
                    # 需要LLM对文字内容进行答复
                    await startToChat(conn, original_text)
        elif msg_json["type"] == "iot":
            conn.logger.bind(tag=TAG).info(f"收到iot消息：{message}")
            if "descriptors" in msg_json:
                asyncio.create_task(handleIotDescriptors(conn, msg_json["descriptors"]))
            if "states" in msg_json:
                asyncio.create_task(handleIotStatus(conn, msg_json["states"]))
        elif msg_json["type"] == "mcp":
            conn.logger.bind(tag=TAG).info(f"收到mcp消息：{message[:100]}")
            if "payload" in msg_json:
                asyncio.create_task(
                    handle_mcp_message(conn, conn.mcp_client, msg_json["payload"])
                )
         # 新增：设备首次连接或状态上报（例如：{type:"status", volume: 数值, microphone: 0/1}）
        elif msg_json.get("type") == "status" or ("volume" in msg_json and "microphone" in msg_json):
            try:
                device_id = conn.device_id if hasattr(conn, 'device_id') else "unknown"
                volume = msg_json.get("volume")
                microphone = msg_json.get("microphone")
                # 基本校验
                if volume is not None:
                    try:
                        volume = int(volume)
                    except (ValueError, TypeError):
                        conn.logger.bind(tag=TAG).warning(f"状态上报的volume不是有效整数: {volume}")
                        volume = None
                if microphone is not None:
                    try:
                        microphone = int(microphone)
                        if microphone not in [0,1]:
                            conn.logger.bind(tag=TAG).warning(f"状态上报的microphone不在[0,1]: {microphone}")
                            microphone = None
                    except (ValueError, TypeError):
                        conn.logger.bind(tag=TAG).warning(f"状态上报的microphone不是有效整数: {microphone}")
                        microphone = None
                # 读取旧缓存并更新
                cache_key = f"device_info:{device_id}"
                current = cache_manager.get(CacheType.DEVICE_INFO, cache_key) or {}
                if volume is not None:
                    current["volume"] = volume
                if microphone is not None:
                    current["microphone"] = microphone
                current["updated_at"] = int(time.time())
                cache_manager.set(CacheType.DEVICE_INFO, cache_key, current, ttl=None)
                conn.logger.bind(tag=TAG).info(f"已缓存设备 {device_id} 状态: {current}")
            except Exception as e:
                conn.logger.bind(tag=TAG).error(f"缓存设备状态失败: {str(e)}")
                       
        elif msg_json["type"] == "reply":
            conn.logger.bind(tag=TAG).info(f"收到设备回复消息：{message}")
            # 处理设备回复消息，格式: {type: "reply", content: "volume"/"microphone", value: <value>}
            try:
                # 创建PeripheralControlHandler实例，传递config和websocket_server参数
                handler = PeripheralControlHandler(conn.config, conn.server)
                # 添加设备ID到消息中（从连接获取）
                device_id = conn.device_id if hasattr(conn, 'device_id') else "unknown"
                # 调用设备回复处理方法
                await handler.handle_device_reply_message(device_id, msg_json)
            except Exception as e:
                conn.logger.bind(tag=TAG).error(f"处理设备回复消息失败: {str(e)}")
                
        elif msg_json["type"] == "group": 
            action = msg_json["action"]
            # if conn.client_is_speaking: 
            #     await handleAbortMessage(conn)
            await handle_group_invitation_reply(conn, action)

        elif msg_json["type"] == "server":
            # 记录日志时过滤敏感信息
            conn.logger.bind(tag=TAG).info(
                f"收到服务器消息：{filter_sensitive_info(msg_json)}"
            )
            # 如果配置是从API读取的，则需要验证secret
            if not conn.read_config_from_api:
                return
            # 获取post请求的secret
            post_secret = msg_json.get("content", {}).get("secret", "")
            secret = conn.config["manager-api"].get("secret", "")
            # 如果secret不匹配，则返回
            if post_secret != secret:
                await conn.websocket.send(
                    json.dumps(
                        {
                            "type": "server",
                            "status": "error",
                            "message": "服务器密钥验证失败",
                        }
                    )
                )
                return
            # 动态更新配置
            if msg_json["action"] == "update_config":
                try:
                    # 更新WebSocketServer的配置
                    if not conn.server:
                        await conn.websocket.send(
                            json.dumps(
                                {
                                    "type": "server",
                                    "status": "error",
                                    "message": "无法获取服务器实例",
                                    "content": {"action": "update_config"},
                                }
                            )
                        )
                        return

                    if not await conn.server.update_config():
                        await conn.websocket.send(
                            json.dumps(
                                {
                                    "type": "server",
                                    "status": "error",
                                    "message": "更新服务器配置失败",
                                    "content": {"action": "update_config"},
                                }
                            )
                        )
                        return

                    # 发送成功响应
                    await conn.websocket.send(
                        json.dumps(
                            {
                                "type": "server",
                                "status": "success",
                                "message": "配置更新成功",
                                "content": {"action": "update_config"},
                            }
                        )
                    )
                except Exception as e:
                    conn.logger.bind(tag=TAG).error(f"更新配置失败: {str(e)}")
                    await conn.websocket.send(
                        json.dumps(
                            {
                                "type": "server",
                                "status": "error",
                                "message": f"更新配置失败: {str(e)}",
                                "content": {"action": "update_config"},
                            }
                        )
                    )
            # 重启服务器
            elif msg_json["action"] == "restart":
                await conn.handle_restart(msg_json)
        else:
            conn.logger.bind(tag=TAG).error(f"收到未知类型消息：{message}, {msg_json['type']}")
    except json.JSONDecodeError:
        await conn.websocket.send(message)