from plugins_func.register import register_function, ToolType, ActionResponse, Action
from config.logger import setup_logging
from core.handle.sendAudioHandle import send_tts_message, sendAudio
import json
import uuid
import os
import asyncio

TAG = __name__
logger = setup_logging()

create_group_function_desc = {
    "type": "function",
    "function": {
        "name": "create_group",
        "description": "当用户想要创建群聊、建群、邀请其他设备加入群聊时调用",
        "parameters": {
            "type": "object",
            "properties": {
                "group_name": {
                    "type": "string",
                    "description": "群聊名称，如果用户没有指定则使用默认名称"
                },
                "invitation_message": {
                    "type": "string",
                    "description": "邀请消息，向其他设备发送的邀请内容"
                }
            },
            "required": ["group_name"]
        }
    }
}

@register_function('create_group', create_group_function_desc, ToolType.SYSTEM_CTL)
def create_group(conn, group_name: str = "默认群聊", invitation_message: str = "邀请你加入群聊"):
    """创建群聊功能"""
    try:
        logger.bind(tag=TAG).info(f"开始创建群聊: {group_name}")
        
        # 检查事件循环状态
        if not conn.loop.is_running():
            logger.bind(tag=TAG).error("事件循环未运行，无法提交任务")
            return ActionResponse(
                action=Action.RESPONSE, 
                result="系统繁忙", 
                response="请稍后再试"
            )
        
        # 提交异步任务
        task = conn.loop.create_task(
            handle_create_group_async(conn, group_name, invitation_message)
        )
        
        # 非阻塞回调处理
        def handle_done(f):
            try:
                result = f.result()
                logger.bind(tag=TAG).info(f"群聊创建完成: {result}")
            except Exception as e:
                logger.bind(tag=TAG).error(f"群聊创建失败: {e}")
        
        task.add_done_callback(handle_done)
        
        return ActionResponse(
            action=Action.NONE, 
            result="群聊创建指令已接收", 
            response=f"群聊 '{group_name}' 创建成功，正在向在线设备发送邀请"
        )
        
    except Exception as e:
        logger.bind(tag=TAG).error(f"创建群聊错误: {e}")
        return ActionResponse(
            action=Action.RESPONSE, 
            result=str(e), 
            response="创建群聊时出错了"
        )

async def handle_create_group_async(conn, group_name: str, invitation_message: str):
    """异步处理群聊创建逻辑 - 单群聊模式"""
    
    # 获取当前设备ID
    current_device_id = conn.device_id
    # 初始化群聊信息
    if not hasattr(conn.server, 'active_groups'):
        conn.server.active_groups = {}
    conn.server.active_groups = {}

    # 检查是否已存在群聊（单群聊模式）
    # existing_group_id = None
    # existing_group_info = None
    
    # for group_id, group_info in conn.server.active_groups.items():
    #     # 找到第一个存在的群聊
    #     existing_group_id = group_id
    #     existing_group_info = group_info
    #     break
    
    # if existing_group_id:
    #     # 如果已存在群聊，直接加入
    #     logger.bind(tag=TAG).info(f"发现已存在群聊 {existing_group_id}，设备 {current_device_id} 直接加入")
        
    #     # 检查设备是否已在群聊中
    #     if current_device_id not in existing_group_info['members']:
    #         existing_group_info['members'].append(current_device_id)
    #         conn.current_group_id = existing_group_id
            
    #         # 发送确认消息
    #         confirmation_text = f"您已加入现有群聊 '{existing_group_info['group_name']}'，现在可以与群组成员进行语音通话了"
    #         await send_voice_invitation(conn, confirmation_text, conn)
            
    #         # 通知群组其他成员
    #         from core.handle.intentHandler import broadcast_to_group_members
    #         await broadcast_to_group_members(conn.server, existing_group_id, f"设备 {current_device_id} 已加入群聊", exclude_device=current_device_id)
            
    #         return f"已加入现有群聊 '{existing_group_info['group_name']}'"
    #     else:
    #         return f"您已在群聊 '{existing_group_info['group_name']}' 中"
    
    # 如果不存在群聊，创建新群聊
    group_id = str(uuid.uuid4().hex)
    
    # 获取所有在线设备（排除当前设备）
    online_devices = []
    for connection in conn.server.active_connections:
        if hasattr(connection, 'device_id') and connection.device_id != current_device_id:
            online_devices.append({
                'device_id': connection.device_id,
                'connection': connection
            })
    
    if not online_devices:
        logger.bind(tag=TAG).info("当前没有其他在线设备可以邀请")
        return "当前没有其他在线设备可以邀请"
    
    # 初始化群聊信息
    # if not hasattr(conn.server, 'active_groups'):
    #     conn.server.active_groups = {}
    
    conn.server.active_groups[group_id] = {
        'group_name': group_name,
        'creator': current_device_id,
        'members': [current_device_id],  # 创建者默认已经加入
        'pending_invitations': [], 
        'created_at': str(uuid.uuid4().hex)
    }
    
    # 不立即设置创建者的群聊ID，等待明确同意
    # conn.current_group_id = group_id
    
    # 生成语音邀请消息
    voice_invitation_text = f"您收到一个群聊邀请，群聊名称是{group_name}。请说同意或拒绝。"
    
    # 向所有在线设备发送邀请
    invitation_count = 0
    print("===> online_devices amount: ", len(online_devices), flush=True)
    for device in online_devices:
        if device['device_id'] == current_device_id:
            continue

        try:
            # 发送文本邀请消息
            invitation_data = {
                'type': 'group_invitation',
                'group_id': group_id,
                'group_name': group_name,
                'creator': current_device_id,
                'message': invitation_message,
                'timestamp': str(uuid.uuid4().hex)
            }
            
            # 发送文本邀请
            await device['connection'].websocket.send(json.dumps(invitation_data))
            device['connection'].candidate_group_id = group_id
            device['connection'].candidate_group_name = group_name
            device['connection'].wait_for_response = 2 # 建群后待其他设备响应是否同意
            
            # 发送语音邀请
            await send_voice_invitation(device['connection'], voice_invitation_text, conn)
            
            conn.server.active_groups[group_id]['pending_invitations'].append(device['device_id'])
            invitation_count += 1
            
            logger.bind(tag=TAG).info(f"已向设备 {device['device_id']} 发送群聊邀请（文本+语音）")
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"向设备 {device['device_id']} 发送邀请失败: {e}")
    
    # 向创建者也发送语音邀请提示 ===> 暂不需要
    # try:
    #     creator_voice_text = f"群聊{group_name}创建成功。您也需要确认加入此群聊，请说同意加入群聊，或者说不同意拒绝邀请。"
    #     await send_voice_invitation(conn, creator_voice_text, conn)
    #     logger.bind(tag=TAG).info(f"已向创建者发送群聊确认语音")
    # except Exception as e:
    #     logger.bind(tag=TAG).error(f"向创建者发送确认语音失败: {e}")
    
    result_message = f"群聊创建完成: 已向 {invitation_count} 个在线设备发送邀请（包含语音）"
    logger.bind(tag=TAG).info(result_message)

    conn.current_group_id = group_id
    conn.candidate_group_name = None
    conn.candidate_group_id = None

    await send_tts_message(conn, "candidate_group_id", group_id)
    return result_message

async def send_voice_invitation(target_conn, voice_text, source_conn=None):
    """向目标设备发送语音邀请"""
    try:
        # 使用发起方的TTS实例生成语音（如果提供了source_conn）
        tts_instance = None
        if source_conn and hasattr(source_conn, 'tts') and source_conn.tts:
            tts_instance = source_conn.tts
            logger.bind(tag=TAG).info(f"使用发起方设备的TTS实例生成语音")
        elif hasattr(target_conn, 'tts') and target_conn.tts:
            tts_instance = target_conn.tts
            logger.bind(tag=TAG).info(f"使用目标设备的TTS实例生成语音")
        
        if tts_instance:
            # 创建临时文件路径
            tmp_file = tts_instance.generate_filename()
            
            try:
                # 直接使用异步方法生成语音文件
                await tts_instance.text_to_speak(voice_text, tmp_file)
                
                if os.path.exists(tmp_file):
                    # 处理音频文件并转换为指定格式
                    audio_data = tts_instance._process_audio_file(tmp_file)
                    
                    if audio_data:
                        # 发送TTS开始消息
                        await send_tts_message(target_conn, "start", voice_text)
                        
                        # 发送语音段开始消息
                        await send_tts_message(target_conn, "sentence_start", voice_text)
                        
                        # 发送音频数据
                        await sendAudio(target_conn, audio_data)
                        
                        # 发送语音段结束消息
                        await send_tts_message(target_conn, "sentence_end", voice_text)
                        
                        # 发送TTS结束消息
                        await send_tts_message(target_conn, "stop")
                        
                        logger.bind(tag=TAG).info(f"成功向设备 {target_conn.device_id} 发送语音邀请")
                    else:
                        logger.bind(tag=TAG).warning(f"设备 {target_conn.device_id} 音频处理失败")
                else:
                    logger.bind(tag=TAG).warning(f"设备 {target_conn.device_id} 语音文件生成失败")
            except Exception as e:
                logger.bind(tag=TAG).warning(f"设备 {target_conn.device_id} 语音生成失败: {e}")
                
                # 发送纯文本邀请作为备选
                await send_tts_message(target_conn, "start", voice_text)
                await send_tts_message(target_conn, "sentence_start", voice_text)
                await send_tts_message(target_conn, "sentence_end", voice_text)
                await send_tts_message(target_conn, "stop")
        else:
            logger.bind(tag=TAG).warning(f"没有可用的TTS实例")
            
    except Exception as e:
        logger.bind(tag=TAG).error(f"发送语音邀请失败: {e}")
