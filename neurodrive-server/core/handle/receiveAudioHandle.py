from core.handle.sendAudioHandle import send_stt_message
from core.handle.intentHandler import handle_user_intent, check_exact_match, extract_rule_cmds, process_commands
from core.utils.output_counter import check_device_output_limit
from core.handle.abortHandle import handleAbortMessage
import time
import asyncio
import json
from core.handle.sendAudioHandle import SentenceType, send_stt_message, send_tts_message, sendAudio
from core.utils.util import opus_datas_to_wav_bytes
from core.utils.util import audio_to_data
import uuid

TAG = __name__


async def handleAudioMessage(conn, audio):
    # 当前片段是否有人说话
    have_voice = conn.vad.is_vad(conn, audio)
    # print("debug have_voice: ", have_voice, conn.just_woken_up, flush=True)
    
    if hasattr(conn, 'control_cmd_active') and conn.control_cmd_active:
        if time.monotonic() < getattr(conn, 'control_cmd_timeout', 0):
            conn.asr_audio.clear()
            return
        else:
            conn.control_cmd_active = False
    
    # 如果设备刚刚被唤醒，短暂忽略VAD检测
    # if have_voice and hasattr(conn, "just_woken_up") and conn.just_woken_up:
    #     have_voice = False
    #     conn.asr_audio.clear()
    #     conn.just_woken_up = False
    #     # 设置一个短暂延迟后恢复VAD检测
    #     # if not hasattr(conn, "vad_resume_task") or conn.vad_resume_task.done():
    #     #     conn.vad_resume_task = asyncio.create_task(resume_vad_detection(conn))
    #     # print("return===>", flush=True)
    #     return

    #群聊音频转发：如果设备在群聊中且有声音，转发音频给群组其他成员
    # if hasattr(conn, 'current_group_id') and conn.current_group_id:
    #     # print("debug have_voice: ", have_voice,  conn.just_woken_up if hasattr(conn, "just_woken_up") else "false", flush=True)
    #     if have_voice:
    #         print("debug have_voice: ", have_voice,  conn.just_woken_up if hasattr(conn, "just_woken_up") else "false", flush=True)
    #         await forward_audio_to_group(conn, audio)
    #     return

    #esp32客户端正在说话，就会被打断，清空已输入的音频
    # if have_voice:
    #     if conn.client_is_speaking:
    #         await handleAbortMessage(conn)

    #设备长时间空闲检测，用于say goodbye ===> 暂不检查
    # await no_voice_close_connect(conn, have_voice)

    if have_voice:
       print("====> handleAudioMessage has_voice: ", have_voice, conn.asr_audio_queue.qsize(), conn.client_have_voice, len(conn.asr_audio), conn.client_voice_stop, flush=True)
       conn.last_activity_time = time.time() * 1000
    else:
       stop_duration = time.time() * 1000 - conn.last_activity_time
       if conn.client_have_voice and not conn.client_voice_stop and stop_duration >= 300:
           conn.client_voice_stop = True
    

    # 控制指令语音窗口：在控制指令激活期间，丢弃 ASR 音频并提前返回
    # if hasattr(conn, 'control_cmd_active') and conn.control_cmd_active:
    #     if time.monotonic() < getattr(conn, 'control_cmd_timeout', 0):
    #         conn.asr_audio.clear()
    #         return
    #     else:
    #         conn.control_cmd_active = False

    # 接收音频
    await conn.asr.receive_audio(conn, audio, have_voice)


async def resume_vad_detection(conn):
    # 等待2秒后恢复VAD检测
    await asyncio.sleep(1)
    conn.just_woken_up = False


async def startToChat(conn, text):
    if hasattr(conn, 'current_group_id') and conn.current_group_id:
        # 检查是否为退出群聊的指令
        exit_group_keywords = ["退出群聊", "离开群聊", "退出", "离开", "结束群聊"]
        text_lower = text.lower().strip()
        is_exit_command = any(keyword in text_lower for keyword in exit_group_keywords)
        
        if is_exit_command:
            # 处理退出群聊指令
            conn.logger.bind(tag=TAG).info(f"群聊模式下检测到退出指令: {text}")
            # 清除群聊状态
            conn.current_group_id = None
            # 发送确认消息
            from core.handle.intentHandler import speak_txt
            speak_txt(conn, "您已退出群聊")
            return
        else:
            # 其他指令在群聊模式下跳过处理
            conn.logger.bind(tag=TAG).info(f"群聊模式下跳过文本处理: {text[:50]}...")
            return
    
    # 检查输入是否是JSON格式（包含说话人信息）
    speaker_name = None
    actual_text = text
    
    try:
        # 尝试解析JSON格式的输入
        if text.strip().startswith('{') and text.strip().endswith('}'):
            data = json.loads(text)
            if 'speaker' in data and 'content' in data:
                speaker_name = data['speaker']
                actual_text = data['content']
                conn.logger.bind(tag=TAG).info(f"解析到说话人信息: {speaker_name}")
                
                # 直接使用JSON格式的文本，不解析
                actual_text = text
    except (json.JSONDecodeError, KeyError):
        # 如果解析失败，继续使用原始文本
        pass
    
    # 保存说话人信息到连接对象
    if speaker_name:
        conn.current_speaker = speaker_name
    else:
        conn.current_speaker = None

    if conn.need_bind:
        await check_bind_device(conn)
        return

    # 如果当日的输出字数大于限定的字数
    if conn.max_output_size > 0:
        if check_device_output_limit(
            conn.headers.get("device-id"), conn.max_output_size
        ):
            await max_out_size(conn)
            return
    # if conn.client_is_speaking:
    #     await handleAbortMessage(conn)

    # 首先进行意图分析，使用实际文本内容
    chat_id = str(uuid.uuid4())
    conn.intent_chat_id[chat_id] = 1
    intent_task = asyncio.create_task(handle_user_intent(conn, actual_text))
    chat_task = asyncio.create_task(conn.submit_chat_async(actual_text, chat_id))

    def _intent_done(task):
        try:
            handled = task.result()
        except Exception:
            handled = False
        conn.intent_chat_id[chat_id] = 2 if handled else 3
        print("====>intent_handled: ", handled, chat_id, flush=True)

    intent_task.add_done_callback(_intent_done)
    return

    
    # 等待意图处理完成
    # intent_handled = await intent_task
    
    # if intent_handled: # 识别到意图
    #     conn.finished_chats.append(chat_id)
    #     print("意图已处理，正在终止chat任务...")
    # else:
    #     # 等待chat完成并获取结果
    #     chat_result = await asyncio.wrap_future(chat_future)
    #     print(chat_result)

    # if intent_handled:
    #     # 如果意图已被处理，不再进行聊天
    #     return

    # # 意图未被处理，继续常规聊天流程，使用实际文本内容
    # await send_stt_message(conn, actual_text)
    # conn.executor.submit(conn.chat, actual_text)





async def no_voice_close_connect(conn, have_voice):
    if have_voice:
        conn.last_activity_time = time.time() * 1000
        return
    # 只有在已经初始化过时间戳的情况下才进行超时检查
    if conn.last_activity_time > 0.0:
        no_voice_time = time.time() * 1000 - conn.last_activity_time
        close_connection_no_voice_time = int(
            conn.config.get("close_connection_no_voice_time", 120000)
        )
        if (
            not conn.close_after_chat
            and no_voice_time > 1000 * close_connection_no_voice_time
        ):
            conn.close_after_chat = True
            conn.client_abort = False
            end_prompt = conn.config.get("end_prompt", {})
            if end_prompt and end_prompt.get("enable", True) is False:
                conn.logger.bind(tag=TAG).info("结束对话，无需发送结束提示语")
                await conn.close()
                return
            prompt = end_prompt.get("prompt")
            if not prompt:
                prompt = "请你以```时间过得真快```未来头，用富有感情、依依不舍的话来结束这场对话吧。！"
            await startToChat(conn, prompt)


async def max_out_size(conn):
    text = "不好意思，我现在有点事情要忙，明天这个时候我们再聊，约好了哦！明天不见不散，拜拜！"
    await send_stt_message(conn, text)
    file_path = "config/assets/max_output_size.wav"
    opus_packets, _ = audio_to_data(file_path)
    conn.tts.tts_audio_queue.put((SentenceType.LAST, opus_packets, text))
    conn.close_after_chat = True


async def check_bind_device(conn):
    if conn.bind_code:
        # 确保bind_code是6位数字
        if len(conn.bind_code) != 6:
            conn.logger.bind(tag=TAG).error(f"无效的绑定码格式: {conn.bind_code}")
            text = "绑定码格式错误，请检查配置。"
            await send_stt_message(conn, text)
            return

        text = f"请登录控制面板，输入{conn.bind_code}，绑定设备。"
        await send_stt_message(conn, text)

        # 播放提示音
        music_path = "config/assets/bind_code.wav"
        opus_packets, _ = audio_to_data(music_path)
        conn.tts.tts_audio_queue.put((SentenceType.FIRST, opus_packets, text))

        # 逐个播放数字
        for i in range(6):  # 确保只播放6位数字
            try:
                digit = conn.bind_code[i]
                num_path = f"config/assets/bind_code/{digit}.wav"
                num_packets, _ = audio_to_data(num_path)
                conn.tts.tts_audio_queue.put((SentenceType.MIDDLE, num_packets, None))
            except Exception as e:
                conn.logger.bind(tag=TAG).error(f"播放数字音频失败: {e}")
                continue
        conn.tts.tts_audio_queue.put((SentenceType.LAST, [], None))
    else:
        text = f"没有找到该设备的版本信息，请正确配置 OTA地址，然后重新编译固件。"
        await send_stt_message(conn, text)
        music_path = "config/assets/bind_not_found.wav"
        opus_packets, _ = audio_to_data(music_path)
        conn.tts.tts_audio_queue.put((SentenceType.LAST, opus_packets, text))


async def forward_audio_to_group(conn, audio):
    """
    将音频数据转发给群组中的其他成员
    """
    try:
        # TODO 测试代码记得关闭
        # wav_bytes = opus_datas_to_wav_bytes(audio, sample_rate=16000) 
        # with open("test_opus_to_wav.wav", "wb") as f:
        #     f.write(wav_bytes)

        # 检查服务器是否有active_groups属性
        if not hasattr(conn.server, 'active_groups'):
            print("forward_audio_to_group 111", flush=True)
            return
        
        group_id = conn.current_group_id
        if group_id not in conn.server.active_groups:
            print("forward_audio_to_group 222", flush=True)
            return
        
        group_info = conn.server.active_groups[group_id]
        sender_device_id = conn.device_id

        print("forward_audio_to_group", group_info['members'], flush=True)
        
        # 遍历群组成员，转发音频给除发送者外的其他成员
        for member_device_id in group_info['members']:
            if member_device_id == sender_device_id:
                continue  # 跳过发送者自己
            
            # 查找目标设备的连接
            target_conn = None
            for client_conn in conn.server.active_connections:
                if hasattr(client_conn, 'device_id') and client_conn.device_id == member_device_id:
                    target_conn = client_conn
                    break
            
            if target_conn and hasattr(target_conn, 'websocket'):
                # try:
                #     # 创建音频转发消息，包含发送者信息
                #     audio_message = {
                #         "type": "group_audio",
                #         "sender_device_id": sender_device_id,
                #         "group_id": group_id,
                #         "audio_data": audio.hex() if isinstance(audio, bytes) else audio
                #     }
                    
                #     # 发送音频数据给目标设备
                #     await target_conn.websocket.send(json.dumps(audio_message))
                # except Exception as e:
                #     if hasattr(conn, 'logger'):
                #         conn.logger.bind(tag=TAG).error(f"转发音频给设备 {member_device_id} 失败: {e}")
                #     else:
                #         print(f"转发音频给设备 {member_device_id} 失败: {e}")

                try:
                    target_conn.cient_is_listening = True

                    print("ready to send voice to device: ", target_conn.device_id, flush=True)
                    # await asyncio.wait_for(send_tts_message(target_conn, "start", None), timeout=5)
                    await asyncio.wait_for(sendAudio(target_conn, audio), timeout=30) # 直接发送 TODO
                    # await asyncio.wait_for(send_tts_message(target_conn, "stop"), timeout=5)

                except asyncio.TimeoutError:
                    print(f"Timeout sending to {target_conn.device_id}")
                except Exception as e:
                    print(f"Error sending to {target_conn.device_id}: {e}")

                target_conn.clearSpeakStatus()


        # print("forward_audio_to_group 444", flush=True)
    except Exception as e:
        if hasattr(conn, 'logger'):
            conn.logger.bind(tag=TAG).error(f"群聊音频转发失败: {e}")
        else:
            print(f"群聊音频转发失败: {e}")
