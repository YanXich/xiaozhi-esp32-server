import time
import json
import random
import asyncio
from core.utils.dialogue import Message
from core.utils.util import audio_to_data
from core.handle.sendAudioHandle import sendAudioMessage, send_stt_message
from core.utils.util import remove_punctuation_and_length, opus_datas_to_wav_bytes
from core.providers.tts.dto.dto import ContentType, SentenceType
from core.providers.tools.device_mcp import (
    MCPClient,
    send_mcp_initialize_message,
    send_mcp_tools_list_request,
)
from core.utils.wakeup_word import WakeupWordsConfig
from core.utils.user_wakeup_words import user_wakeup_words_manager

TAG = __name__

WAKEUP_CONFIG = {
    "refresh_time": 5,
    "words": ["你好", "你好啊", "嘿，你好", "嗨"],
}

# 创建全局的唤醒词配置管理器
wakeup_words_config = WakeupWordsConfig()

# 用于防止并发调用wakeupWordsResponse的锁
_wakeup_response_lock = asyncio.Lock()


def update_ai_name_in_prompt(original_prompt, new_name):
    """
    更新系统提示词中的AI名字
    将原始prompt中的AI名字替换为新的唤醒词
    """
    import re
    
    # 常见的AI名字模式
    name_patterns = [
        r'你是小柚/小柚',
        r'你是小柚',
        r'你是小柚', 
        r'我是小柚',
        r'我是小柚',
        r'叫小柚',
        r'叫小柚',
        r'名字是小柚',
        r'名字是小柚'
    ]
    
    updated_prompt = original_prompt
    
    # 替换所有匹配的名字模式
    for pattern in name_patterns:
        if '小柚/小柚' in pattern:
            # 特殊处理小智/小志的情况
            updated_prompt = re.sub(pattern, f'你是{new_name}', updated_prompt)
        elif '小柚' in pattern:
            updated_prompt = re.sub(pattern, pattern.replace('小柚', new_name), updated_prompt)
        elif '小柚' in pattern:
            updated_prompt = re.sub(pattern, pattern.replace('小柚', new_name), updated_prompt)
    
    # 如果没有找到明确的名字模式，在开头添加名字声明
    if updated_prompt == original_prompt:
        updated_prompt = f"你的名字是{new_name}。\n\n{original_prompt}"
    
    return updated_prompt


async def handleHelloMessage(conn, msg_json):
    """处理hello消息"""
    audio_params = msg_json.get("audio_params")
    if audio_params:
        format = audio_params.get("format")
        conn.logger.bind(tag=TAG).info(f"客户端音频格式: {format}")
        conn.audio_format = format
        conn.welcome_msg["audio_params"] = audio_params
    features = msg_json.get("features")
    if features:
        conn.logger.bind(tag=TAG).info(f"客户端特性: {features}")
        conn.features = features
        if features.get("mcp"):
            conn.logger.bind(tag=TAG).info("客户端支持MCP")
            conn.mcp_client = MCPClient()
            # 发送初始化
            asyncio.create_task(send_mcp_initialize_message(conn))
            # 发送mcp消息，获取tools列表
            asyncio.create_task(send_mcp_tools_list_request(conn))

    await conn.websocket.send(json.dumps(conn.welcome_msg, separators=(",", ":")))


async def checkWakeupWords(conn, text):
    enable_wakeup_words_response_cache = conn.config[
        "enable_wakeup_words_response_cache"
    ]

    if not enable_wakeup_words_response_cache or not conn.tts:
        return False

    _, filtered_text = remove_punctuation_and_length(text)
    
    # 获取设备ID
    device_id = conn.headers.get("device-id")
    
    # 获取车载设备唤醒词
    effective_wakeup_words = []
    if device_id:
        try:
            car_wakeup_words = await user_wakeup_words_manager.get_effective_wakeup_words(device_id)
            effective_wakeup_words = car_wakeup_words
            conn.logger.bind(tag=TAG).debug(f"设备 ID: {device_id} 的车载唤醒词: {effective_wakeup_words}")
        except Exception as e:
            conn.logger.bind(tag=TAG).warning(f"获取车载唤醒词失败: {e}")
    
    # 如果没有车载唤醒词，则不响应唤醒
    if not effective_wakeup_words:
        conn.logger.bind(tag=TAG).debug(f"没有找到车载唤醒词，不响应唤醒")
        return False
    
    # 检查是否匹配唤醒词
    conn.logger.bind(tag=TAG).info(f"唤醒词匹配检查 - 输入文本: '{text}', 过滤后: '{filtered_text}', 唤醒词列表: {effective_wakeup_words}")
    if filtered_text not in effective_wakeup_words:
        conn.logger.bind(tag=TAG).info(f"唤醒词匹配失败 - '{filtered_text}' 不在 {effective_wakeup_words} 中")
        return False

    conn.just_woken_up = True
    conn.session_awakened = True  # 设置会话为已唤醒状态
    conn.logger.bind(tag=TAG).info(f"唤醒成功 - 匹配到唤醒词: '{filtered_text}'")
    
    # 动态更新AI的名字为唤醒词
    try:
        original_prompt = conn.config["prompt"]
        # 将原始prompt中的名字替换为当前唤醒词
        updated_prompt = update_ai_name_in_prompt(original_prompt, filtered_text)
        conn.change_system_prompt(updated_prompt)
        conn.logger.bind(tag=TAG).info(f"已将AI名字更新为: '{filtered_text}'")
    except Exception as e:
        conn.logger.bind(tag=TAG).warning(f"更新AI名字失败: {e}")
    
    await send_stt_message(conn, text)

    # 获取当前音色
    voice = getattr(conn.tts, "voice", "default")
    if not voice:
        voice = "default"

    # 获取唤醒词回复配置
    response = wakeup_words_config.get_wakeup_response(voice)
    if not response or not response.get("file_path"):
        response = {
            "voice": "default",
            "file_path": "config/assets/wakeup_words.wav",
            "time": 0,
            "text": "哈啰啊，我是小智啦，声音好听的台湾女孩一枚，超开心认识你耶，最近在忙啥，别忘了给我来点有趣的料哦，我超爱听八卦的啦",
        }

    # 播放唤醒词回复
    conn.client_abort = False
    opus_packets, _ = audio_to_data(response.get("file_path"))

    conn.logger.bind(tag=TAG).info(f"播放唤醒词回复: {response.get('text')}")
    await sendAudioMessage(conn, SentenceType.FIRST, opus_packets, response.get("text"))
    await sendAudioMessage(conn, SentenceType.LAST, [], None)

    # 补充对话
    conn.dialogue.put(Message(role="assistant", content=response.get("text")))

    # 检查是否需要更新唤醒词回复
    if time.time() - response.get("time", 0) > WAKEUP_CONFIG["refresh_time"]:
        if not _wakeup_response_lock.locked():
            asyncio.create_task(wakeupWordsResponse(conn))
    return True


async def wakeupWordsResponse(conn):
    if not conn.tts or not conn.llm or not conn.llm.response_no_stream:
        return

    try:
        # 尝试获取锁，如果获取不到就返回
        if not await _wakeup_response_lock.acquire():
            return

        # 生成唤醒词回复
        wakeup_word = random.choice(WAKEUP_CONFIG["words"])
        question = (
            "此刻用户正在和你说```"
            + wakeup_word
            + "```。\n请你根据以上用户的内容进行20-30字回复。要符合系统设置的角色情感和态度，不要像机器人一样说话。\n"
            + "请勿对这条内容本身进行任何解释和回应，请勿返回表情符号，仅返回对用户的内容的回复。"
        )

        result = conn.llm.response_no_stream(conn.config["prompt"], question)
        if not result or len(result) == 0:
            return

        # 生成TTS音频
        tts_result = await asyncio.to_thread(conn.tts.to_tts, result)
        if not tts_result:
            return

        # 获取当前音色
        voice = getattr(conn.tts, "voice", "default")

        wav_bytes = opus_datas_to_wav_bytes(tts_result, sample_rate=16000)
        file_path = wakeup_words_config.generate_file_path(voice)
        with open(file_path, "wb") as f:
            f.write(wav_bytes)
        # 更新配置
        wakeup_words_config.update_wakeup_response(voice, file_path, result)
    finally:
        # 确保在任何情况下都释放锁
        if _wakeup_response_lock.locked():
            _wakeup_response_lock.release()
