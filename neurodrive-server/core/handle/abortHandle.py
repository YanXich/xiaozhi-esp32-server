import json

TAG = __name__


async def handleAbortMessage(conn):
    conn.logger.bind(tag=TAG).info("Abort message received")
    # 设置成打断状态，会自动打断llm、tts任务
    conn.client_abort = True
    conn.clear_queues()
    # 打断客户端说话状态
    await conn.websocket.send(
        json.dumps({"type": "tts", "state": "abort", "session_id": conn.session_id}, separators=(",", ":"))# 功能跟stop类似，客户端清空后续语音队列
    )
    conn.clearSpeakStatus()
    conn.set_state_idle()
    conn.logger.bind(tag=TAG).info("Abort message received-end")