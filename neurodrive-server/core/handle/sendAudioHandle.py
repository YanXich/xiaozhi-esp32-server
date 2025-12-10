import json
import asyncio
import time
from core.providers.tts.dto.dto import SentenceType
from core.utils.util import get_string_no_punctuation_or_emoji, analyze_emotion
from loguru import logger

TAG = __name__

emoji_map = {
    "neutral": "😶",
    "happy": "🙂",
    "laughing": "😆",
    "funny": "😂",
    "sad": "😔",
    "angry": "😠",
    "crying": "😭",
    "loving": "😍",
    "embarrassed": "😳",
    "surprised": "😲",
    "shocked": "😱",
    "thinking": "🤔",
    "winking": "😉",
    "cool": "😎",
    "relaxed": "😌",
    "delicious": "🤤",
    "kissy": "😘",
    "confident": "😏",
    "sleepy": "😴",
    "silly": "😜",
    "confused": "🙄",
}


async def sendAudioMessage(conn, sentenceType, audios, text):
    # 发送句子开始消息
    conn.logger.bind(tag=TAG).info(f"发送音频消息: {sentenceType}, {text}")
    """
    if text is not None:
        emotion = analyze_emotion(text)
        emoji = emoji_map.get(emotion, "🙂")  # 默认使用笑脸
        await conn.websocket.send(
            json.dumps(
                {
                    "type": "llm",
                    "text": emoji,
                    "emotion": emotion,
                    "session_id": conn.session_id,
                }
            )
        )
    """
    pre_buffer = False
    if conn.tts.tts_audio_first_sentence and text is not None:
        conn.logger.bind(tag=TAG).info(f"发送第一段语音: {text}")
        conn.tts.tts_audio_first_sentence = False
        pre_buffer = True

    st = time.time() 
    text = ""
    await send_tts_message(conn, "sentence_start", text)
    # print("sending audio time 1: ", time.time() - st, sentenceType, conn.llm_finish_task, flush=True)

    await sendAudio(conn, audios, pre_buffer)
    # print("sending audio time 2: ", time.time() - st, len(audios), flush=True)

    await send_tts_message(conn, "sentence_end", text)
    # print("sending audio time 3: ", time.time() - st, flush=True)

    # 发送结束消息（如果是最后一个文本）
    if conn.llm_finish_task and sentenceType == SentenceType.LAST:
        # #清空音频缓冲流
        # conn.asr_audio.clear()
        # #清空ASR音频队列
        # while not conn.asr_audio_queue.empty():
        #     try:
        #         conn.asr_audio_queue.get_nowait()
        #     except asyncio.QueueEmpty:
        #         break
        # #重置VAD状态
        # conn.reset_vad_states()
        # conn.logger.bind(tag=TAG).info(f"已清空音频缓冲队列，切换到说话状态")
        await send_tts_message(conn, "stop", None)
        conn.client_is_speaking = False
        if conn.close_after_chat:
            print("close conn after chat... ", time.time()-st, flush=True)
            await conn.close()


# 播放音频
async def sendAudio(conn, audios, pre_buffer=True):
    if audios is None or len(audios) == 0:
        return
    # 流控参数优化
    frame_duration = 60  # 帧时长（毫秒），匹配 Opus 编码
    start_time = time.perf_counter()
    play_position = 0

    # 仅当第一句话时执行预缓冲
    if pre_buffer:
        pre_buffer_frames = min(3, len(audios))
        for i in range(pre_buffer_frames):
            await conn.websocket.send(audios[i])
        remaining_audios = audios[pre_buffer_frames:]
    else:
        remaining_audios = audios

    # 播放剩余音频帧
    for opus_packet in remaining_audios:
        if conn.client_abort:
            print("client abort while sending audio", flush=True)
            break

        # 重置没有声音的状态
        conn.last_activity_time = time.time() * 1000

        # 计算预期发送时间
        expected_time = start_time + (play_position / 1000)
        current_time = time.perf_counter()
        delay = expected_time - current_time
        if delay > 0:
            await asyncio.sleep(delay)

        await conn.websocket.send(opus_packet)

        play_position += frame_duration


async def send_tts_message(conn, state, text=None):
    """发送 TTS 状态消息"""
    message = {"type": "tts", "state": state, "session_id": conn.session_id}
    if text is not None:
        message["text"] = text

    if state == "start":
        conn.set_state_assistant_speaking()
    elif state in ("stop", "abort"):
        conn.set_state_idle()

    await conn.websocket.send(json.dumps(message,separators=(",", ":")))


async def send_stt_message(conn, text):
    conn.client_is_speaking = True
    conn.set_state_user_speaking()
    await send_tts_message(conn, "start")
