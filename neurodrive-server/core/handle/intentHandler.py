import json
import asyncio
import uuid
import json
from core.handle.sendAudioHandle import send_stt_message, send_tts_message
from core.handle.helloHandle import checkWakeupWords
from core.utils.util import remove_punctuation_and_length
from core.providers.tts.dto.dto import ContentType
from core.utils.dialogue import Message
from plugins_func.register import Action, ActionResponse
from core.providers.tts.dto.dto import TTSMessageDTO, SentenceType
from core.utils.user_wakeup_words import user_wakeup_words_manager
from plugins_func.functions.create_group import handle_create_group_async
from core.handle.abortHandle import handleAbortMessage
import re

TAG = __name__

import difflib

def _normalize_text(t: str) -> str:
    if not isinstance(t, str):
        return ''
    t = t.strip()
    replacements = {
        '打開': '打开', '开启': '打开', '开开': '打开',
        '關': '关', '關閉': '关闭', '关上': '关闭', '關上': '关闭', '关关': '关闭',
        '車': '车', '燈': '灯', '後備箱': '后备箱', '車窗': '车窗', '車門': '车门',
        '音量': '音量', '聲音': '声音',
        '門': '门', '窗戶': '窗户',
        '雙閃': '双闪', '應急燈': '应急灯', '緊急燈': '紧急灯',
        '霧燈': '雾灯', '示寬燈': '示宽灯', '位置燈': '位置灯',
        '駐車燈': '停车灯', '後': '后', '前排': '前', '後排': '后',
        '主駕': '主驾', '副駕': '副驾'
    }
    for k, v in replacements.items():
        t = t.replace(k, v)
    return t

def _is_negated(text: str, keyword: str) -> bool:
    idx = text.find(keyword)
    if idx == -1:
        return False
    window = text[max(0, idx - 4): idx + len(keyword)]
    negatives = ['不', '不要', '别', '别开', '取消', '先不', '先不要', '先别', '暂时不要', '暂时别']
    return any(n in window for n in negatives)

def _fuzzy_contains(text: str, keyword: str, threshold: float = 0.85) -> bool:
    t = _normalize_text(text.lower())
    k = _normalize_text(keyword.lower())
    if k in t:
        return not _is_negated(t, k)
    sm = difflib.SequenceMatcher(None, t, k)
    match = sm.find_longest_match(0, len(t), 0, len(k))
    if match.size == 0:
        return False
    score = match.size / len(k) if len(k) > 0 else 0.0
    if score < threshold:
        return False
    start = match.a
    end = start + match.size
    window = t[max(0, start - 4): end]
    negatives = ['不', '不要', '别', '别开', '取消', '先不', '先不要', '先别', '暂时不要', '暂时别']
    return not any(n in window for n in negatives)

cmd_keywords = {
    "wakeup": [["小宝小宝", "绿仔", "爵士"], "我在呢", "c1.p3", "唤醒指令"],
    "exit": (["退出", "再见", "拜拜", "结束对话"], "再见", "c1.p3", "唤醒指令"),
    #"agree": (["同意", "agree", "yes", "好的", "可以", "行", "ok", "加入"], "已成功加群", "c1.p3", "同意指令"),
    #"refuse": (["不同意", "拒绝", "no", "refuse", "不要", "不行", "不加入", "不参加"], "已拒绝加群", "c1.p3", "拒绝指令"),
    "exit_group": (["退群", "退出群", "解散群", "退出群聊"], "已经退出群聊", "c1.p3", "退群指令"),
    "open_windows": (["开窗","打开车窗","打开窗户","开所有车窗","打开所有车窗","开所有窗户","打开所有窗户"], "已经打开车窗", "c1.p3", "开车窗指令"),
    "close_windows": (["关窗","关闭车窗","关闭窗户","关所有车窗","关闭所有车窗","关上车窗","关所有窗户","关闭所有窗户"], "已经关闭车窗", "c1.p3", "关车窗指令"),
    "open_engine": (["启动发动机", "启动引擎", "开引擎", "开发动机"], "已经启动发动机", "c1.p3", "启动发动机指令"),
    "stop_engine": (["关闭发动机", "把发动机关了","熄火", "关引擎", "停车"], "已经关闭发动机", "c1.p3", "关闭发动机指令"),
    "open_trunk": (["打开后备箱", "开后备箱"], "已经打开后备箱", "c1.p3", "开后备箱指令"),
    "close_trunk": (["关闭后备箱", "关后备箱", "关上后备箱"], "已经关上后备箱", "c1.p3", "关后备箱指令"),
    "lock_door": (["锁门", "锁车门", "锁上所有车门", "把车门锁上", "车门上锁"], "车门已上锁", "c1.p3", "车门上锁指令"),
    "unlock_door": (["解锁","解锁车门","打开车门","开门" ,"把车门打开","打开所有车门","开所有车门"], "车门已解锁", "c1.p3", "解锁车门指令"),
    "light_on": (["开大灯", "开车灯", "打开车灯"], "已经打开车灯", "c1.p3", "开车灯指令"),
    "light_off": (["关大灯", "关车灯", "关闭车灯"], "已经关闭车灯", "c1.p3", "关车灯指令"),
    "open_EmergencyFlasher": (["开双闪","打开小双闪","打开双闪","应急灯","紧急灯","警示灯"], "已经打开双闪", "c1.p3", "双闪灯指令"),
    "close_EmergencyFlasher": (["关双闪","关闭双闪","关闭应急灯","关闭紧急灯","关闭警示灯"], "已经关闭双闪", "c1.p3", "双闪灯指令"),
    "open_RearFogLamp": (["开后雾灯","打开后雾灯","后雾灯"], "已经打开后雾灯", "c1.p3", "后雾灯指令"),
    "close_RearFogLamp": (["关后雾灯","关闭后雾灯"], "已经关闭后雾灯", "c1.p3", "后雾灯指令"),
    "open_StopLight": (["开停车灯","打开停车灯","示宽灯","位置灯"], "已经打开停车灯", "c1.p3", "停车灯指令"),
    "close_StopLight": (["关停车灯","关闭停车灯","关闭示宽灯","关闭位置灯"], "已经关闭停车灯", "c1.p3", "停车灯指令"),
    "open_LeftFrontWindow": (["打开主驾车窗","打开左前窗","开左前窗","打开驾驶位窗","开主驾窗"], "左前窗已打开", "c1.p3", "左前窗指令"),
    "close_LeftFrontWindow": (["关闭左前窗","关左前窗","关闭驾驶位窗","关主驾窗"], "左前窗已关闭", "c1.p3", "左前窗指令"),
    "open_RightFrontWindow": (["打开右前窗","开右前窗","打开副驾窗","开副驾驶窗"], "右前窗已打开", "c1.p3", "右前窗指令"),
    "close_RightFrontWindow": (["关闭右前窗","关右前窗","关闭副驾窗","关副驾驶窗"], "右前窗已关闭", "c1.p3", "右前窗指令"),
    "open_LeftRearWindow": (["打开左后窗","开左后窗","打开后排左窗","开后排左窗"], "左后窗已打开", "c1.p3", "左后窗指令"),
    "close_LeftRearWindow": (["关闭左后窗","关左后窗","关闭后排左窗","关后排左窗"], "左后窗已关闭", "c1.p3", "左后窗指令"),
    "open_RightRearWindow": (["打开右后窗","开右后窗","打开后排右窗","开后排右窗"], "右后窗已打开", "c1.p3", "右后窗指令"),
    "close_RightRearWindow": (["关闭右后窗","关右后窗","关闭后排右窗","关后排右窗"], "右后窗已关闭", "c1.p3", "右后窗指令"),
    "create_group": (["创建一个群", "拉个群", "创建群"], "", "c1.p3", "建群指令"),
    "volume_up": (["提高音量", "增大音量", "音量调高", "声音调大", "大声点", "音量增加", "声音太小了", "大一点", "再大点", "再大一些", "声音大一点", "调大一点", "调大一些"], "音量已提高", "c1.p3", "提高音量指令"),
    "volume_down": (["降低音量", "减小音量", "音量调低", "声音调小", "小声点", "音量减少", "声音太大了", "小一点", "再小点", "再小一些", "音量太高", "安静点", "小点声", "调小一点", "调小一些"], "音量已降低", "c1.p3", "降低音量指令"),
    "volume_set": (["音量设置", "音量调整","音量调到", "音量设为", "设置音量", "调节音量到"], "音量已设置", "c1.p3", "设置音量指令"),
}


     
cmd_codes = {
    "open_windows": 1,
    "close_windows": 2,
    "open_engine": 3,
    "stop_engine": 4,
    "open_trunk": 5,
    "close_trunk": 6,
    "unlock_door": 7,
    "lock_door": 8,
    "open_EmergencyFlasher":9,
    "close_EmergencyFlasher":10, 
    "light_on": 11,
    "light_off": 12,
    "open_RearFogLamp":13,
    "close_RearFogLamp":14,
    "open_StopLight":15,  
    "close_StopLight":16,  
    "open_LeftFrontWindow":17,
    "close_LeftFrontWindow":18,
    "open_RightFrontWindow":19,
    "close_RightFrontWindow":20,
    "open_LeftRearWindow":21,
    "close_LeftRearWindow":22,
    "open_RightRearWindow":23,
    "close_RightRearWindow":24,
}


intent_instructions = """
退出指令（exit）: ["退出", "再见", "拜拜", "闭嘴", "不想和你说话了", "结束对话"]
同意指令（agree）: ["同意", "agree", "yes", "好的", "可以", "行", "ok", "加入"]
拒绝指令（refuse）: ["不同意", "拒绝", "no", "refuse", "不要", "不行", "不加入", "不参加"]
退群指令（exit_group）: ["退群", "退出群", "解散群", "退出群聊"]
开车窗指令（open_windows）: ["开窗", "打开车窗", "打开窗户", "开所有车窗", "打开所有车窗", "开所有窗户", "打开所有窗户"]
关车窗指令（close_windows）: ["关窗", "关闭车窗", "关闭窗户", "关所有车窗", "关闭所有车窗", "关上车窗", "关所有窗户", "关闭所有窗户"]
启动发动机指令（open_engine）: ["启动发动机", "启动引擎", "开引擎", "开发动机"]
关闭发动机指令（stop_engine）: ["关闭发动机", "熄火", "关引擎", "停车"]
打开后备箱指令（open_trunk）: ["打开后备箱", "开后备箱"]
关闭后备箱指令（close_trunk）: ["关闭后备箱", "关后备箱", "关上后备箱"]
锁门指令（lock_door）: ["锁门", "锁车门", "锁上所有车门", "把车门锁上", "车门上锁"]
解锁门指令（unlock_door）: ["解锁", "开门", "解锁车门", "打开车门", "把车门打开", "打开所有车门", "开所有车门"]
开车灯指令（light_on）: ["开大灯", "开车灯", "打开车灯"]
关车灯指令（light_off）: ["关大灯", "关车灯", "关闭车灯"]
双闪打开指令（open_EmergencyFlasher）: ["开双闪", "打开双闪", "应急灯", "紧急灯", "警示灯"]
双闪关闭指令（close_EmergencyFlasher）: ["关双闪", "关闭双闪", "关闭应急灯", "关闭紧急灯", "关闭警示灯"]
后雾灯打开指令（open_RearFogLamp）: ["开后雾灯", "打开后雾灯", "后雾灯"]
后雾灯关闭指令（close_RearFogLamp）: ["关后雾灯", "关闭后雾灯"]
停车灯打开指令（open_StopLight）: ["开停车灯", "打开停车灯", "示宽灯", "位置灯"]
停车灯关闭指令（close_StopLight）: ["关停车灯", "关闭停车灯", "关闭示宽灯", "关闭位置灯"]
左前窗打开指令（open_LeftFrontWindow）: ["打开左前窗", "开左前窗", "打开驾驶位窗", "开主驾窗"]
左前窗关闭指令（close_LeftFrontWindow）: ["关闭左前窗", "关左前窗", "关闭驾驶位窗", "关主驾窗"]
右前窗打开指令（open_RightFrontWindow）: ["打开右前窗", "开右前窗", "打开副驾窗", "开副驾驶窗"]
右前窗关闭指令（close_RightFrontWindow）: ["关闭右前窗", "关右前窗", "关闭副驾窗", "关副驾驶窗"]
左后窗打开指令（open_LeftRearWindow）: ["打开左后窗", "开左后窗", "打开后排左窗", "开后排左窗"]
左后窗关闭指令（close_LeftRearWindow）: ["关闭左后窗", "关左后窗", "关闭后排左窗", "关后排左窗"]
右后窗打开指令（open_RightRearWindow）: ["打开右后窗", "开右后窗", "打开后排右窗", "开后排右窗"]
右后窗关闭指令（close_RightRearWindow）: ["关闭右后窗", "关右后窗", "关闭后排右窗", "关后排右窗"]
创建群聊指令（create_group）: ["创建一个群", "拉个群", "创建群"]
提高音量指令（volume_up）: ["提高音量", "增大音量", "音量调高", "声音调大", "大声点", "音量增加"]
降低音量指令（volume_down）: ["降低音量", "减小音量", "音量调低", "声音调小", "小声点", "音量减少"]
设置音量指令（volume_set）: ["音量设置", "音量调整", "音量调到", "音量设为", "设置音量", "调节音量到"]
"""

intent_system_prompt = """
任务描述：
请分析以下输入文本，并识别其背后的意图。仅从下面的预设指令中选择一个或多个英文代号作为输出。

任务场景:
语音控车场景，包含汽车控制、群聊创建/邀请。

预设指令及关键词：

{intent_instructions}

识别规则：

    只允许输出一个或多个指令英文代号（如 exit_group），不输出其他内容
    若不确定或无匹配，请输出“其他”
    否定表达（不/不要/别/取消/先不/先不要/先别/暂时不要/暂时别）出现且靠近动词时，判定为“其他”
    门窗区分：含“门/车门/开门/解锁车门”→ unlock_door；仅含“窗/车窗/窗户/开窗”→ open_windows/close_windows
    优先按关键词的明确匹配，不要凭相似词推断

输出示例：

输入文本：“小宝小宝，打开车灯。”
识别出的意图：light_on
输入文本:"拉个峨眉山旅游群吧"
识别出的意图：create_group(峨眉山旅游群)
输出文本：“小宝，打开双闪，大灯，后雾灯，启动发动机”
识别出的意图：open_EmergencyFlasher, light_on, open_RearFogLamp, open_engine

"""

intent_user_prompt = """
输入文本：

{input_text}

请识别是否包含指令意图，若有请输出指令代号，若无请输出“其他”。

识别出的意图:

"""


group_system_prompt = """
你是一个智能助手，用户需要给出一个群聊名称。请分析，用户输入的内容是否在提出群聊的名称。
若没有提及群聊名，请输出“默认群”。
若提及群聊名，请直接给个群聊名。

示例：

输入文本：“那就叫个吃火锅群吧”
群聊名：吃火锅群

"""

group_user_prompt = """
---
用户输入:
{input_text}
---
群聊名:
"""

async def process_exit(conn):
    await speak_txt_with_abort(conn, cmd_keywords["exit"][1])
    await conn.close()

async def process_wakeup(conn):
    conn.just_woken_up = True if not conn.session_awakened else False
    conn.session_awakened = True
    await speak_txt_with_abort(conn, cmd_keywords["wakeup"][1])

async def process_create_group(conn, cmd):
    split_list = cmd.split("(")
    group_name = ""
    if len(split_list) < 2:
        split_list = cmd.split("（")
    if len(split_list) > 1:
        group_name = split_list[1].replace(")", "").replace("）", "").replace(" ", "").strip()
    if group_name == "":
        # 叫对方说出群聊名称
        conn.wait_for_response = 1
        await speak_txt_with_abort(conn, "请给一个群聊名称")
        return
    
    conn.wait_for_response = 3
    conn.candidate_group_name = group_name
    await speak_txt_with_abort(conn, f"您将创建一个群聊， {group_name}。请说确认或拒绝。")


async def process_command(conn, ori_cmd, original_text=None):
    print("processing cmd: ", ori_cmd, flush=True)

    # 命令
    matches = re.findall(r'[a-zA-Z0-9_]+', ori_cmd)
    cmd = matches[0] if matches else ""

    if cmd == "exit":
        await process_exit(conn)
    elif cmd == "agree" or cmd == "refuse": # 在wait_for_response中处理
        # return await handle_group_invitation_reply(conn, cmd) 
        return False
    elif cmd == "exit_group":
        return await handle_group_invitation_reply(conn, cmd) 
    elif cmd == "create_group": 
        await process_create_group(conn, ori_cmd)
    elif cmd == "wakeup":
        await process_wakeup(conn)
    elif cmd == "volume_up":
        await process_volume_up(conn)
    elif cmd == "volume_down":
        await process_volume_down(conn)
    elif cmd == "volume_set":
        # 传入原始文本以便解析数值
        await process_volume_set(conn, original_text or ori_cmd)
    elif cmd in cmd_codes:
        try:
            ws_message = json.dumps({
                "type": "iot",
                "cmd": cmd_codes[cmd]
            }, separators=(",", ":"))
            await conn.websocket.send(ws_message)
            conn.logger.bind(tag=TAG).info(f"成功发送控制指令 {cmd}, {cmd_codes[cmd]} 到设备 {conn.device_id}")
        except Exception as e:
            conn.logger.bind(tag=TAG).warning(f"发送控制指令失败: {e}")
        # await speak_txt_with_abort(conn, cmd_keywords[cmd][1])
    else:
        return False
        
    return True

async def process_commands(conn, cmd_list, original_text=None):
    executed = False
    for c in cmd_list:
        if await process_command(conn, c, original_text or c):
            executed = True
    return executed

            
async def check_exact_match(conn, text, exclude_cmds=[]):
    try:
        device_id = conn.headers.get("device-id")
        effective = await user_wakeup_words_manager.get_effective_wakeup_words(device_id)
        if effective and isinstance(effective, list) and len(effective) > 0:
            cmd_keywords["wakeup"][0] = effective
        else:
            cmd_keywords["wakeup"][0] = ["小宝小宝","绿仔","爵士"]
    except Exception as e:
        conn.logger.bind(tag=TAG).warning(f"检查车载唤醒词失败: {e}")
        cmd_keywords["wakeup"][0] = ["小宝小宝","绿仔","爵士"]

    text_norm = _normalize_text(text)

    has_door = any(w in text_norm for w in ["车门", "门"])
    has_window = any(w in text_norm for w in ["车窗", "窗户", "窗"])
    has_open_kw = any(w in text_norm for w in ["打开", "开", "升", "升起", "升上", "抬起", "升高"]) and not any(w in text_norm for w in ["降", "降下", "下降", "落下", "降低"])
    has_close_kw = any(w in text_norm for w in ["关闭", "关", "降", "降下", "下降", "落下", "降低"]) and not any(w in text_norm for w in ["升", "升起", "升上", "抬起", "升高"])
    has_unlock = any(w in text_norm for w in ["解锁", "解鎖"])

    if any(w in text_norm for w in ["双闪", "应急灯", "紧急灯", "危险警示灯", "危险报警灯", "警示灯"]):
        if has_close_kw and not _is_negated(text_norm, "关"):
            return "close_EmergencyFlasher"
        if has_open_kw and not _is_negated(text_norm, "开"):
            return "open_EmergencyFlasher"

    has_front_fog = any(w in text_norm for w in ["前雾灯", "前雾"]) 
    has_rear_fog = any(w in text_norm for w in ["后雾灯", "后雾"]) 
    has_fog_generic = "雾灯" in text_norm
    if (has_rear_fog or (has_fog_generic and not has_front_fog)):
        if has_close_kw and not _is_negated(text_norm, "关"):
            return "close_RearFogLamp"
        if has_open_kw and not _is_negated(text_norm, "开"):
            return "open_RearFogLamp"

    if any(w in text_norm for w in ["停车灯", "示宽灯", "位置灯"]):
        if has_close_kw and not _is_negated(text_norm, "关"):
            return "close_StopLight"
        if has_open_kw and not _is_negated(text_norm, "开"):
            return "open_StopLight"

    if any(w in text_norm for w in ["车灯", "大灯"]) and not any(w in text_norm for w in ["双闪", "应急灯", "紧急灯", "危险警示灯", "危险报警灯", "停车灯", "示宽灯", "位置灯", "雾灯"]):
        if has_close_kw and not _is_negated(text_norm, "关"):
            return "light_off"
        if has_open_kw and not _is_negated(text_norm, "开"):
            return "light_on"

    if has_window:
        is_left = any(w in text_norm for w in ["左", "主驾", "驾驶位", "驾驶员"]) 
        is_right = any(w in text_norm for w in ["右", "副驾", "副驾驶"]) 
        is_front = any(w in text_norm for w in ["前", "前排", "驾驶位", "副驾", "主驾"]) 
        is_rear = any(w in text_norm for w in ["后", "后排", "后座"]) 
        has_open_alt = any(w in text_norm for w in ["降", "降下", "下降", "落下"]) 
        has_close_alt = any(w in text_norm for w in ["升", "升起", "升上", "抬起"]) 
        open_kw = (has_open_kw and not _is_negated(text_norm, "开")) or has_open_alt
        close_kw = (has_close_kw and not _is_negated(text_norm, "关")) or has_close_alt
        if open_kw and close_kw:
            if not any(w in text_norm for w in ["升","升起","升上","抬起"]):
                close_kw = False
        if is_left and is_front:
            if close_kw:
                return "close_LeftFrontWindow"
            if open_kw:
                return "open_LeftFrontWindow"
        if is_right and is_front:
            if close_kw:
                return "close_RightFrontWindow"
            if open_kw:
                return "open_RightFrontWindow"
        if is_left and is_rear:
            if close_kw:
                return "close_LeftRearWindow"
            if open_kw:
                return "open_LeftRearWindow"
        if is_right and is_rear:
            if close_kw:
                return "close_RightRearWindow"
            if open_kw:
                return "open_RightRearWindow"

    if has_door and has_unlock and not _is_negated(text_norm, "解锁"):
        return "unlock_door"
    if has_door and has_open_kw and not _is_negated(text_norm, "开"):
        return "unlock_door"
    # 若已匹配到具体左/右/前/后窗的条件，上面已返回具体窗命令；
    # 仅在没有任何具体方位信息时，才匹配全车窗开/关
    if has_window and not any(w in text_norm for w in ["左","右","前","后","主驾","副驾","驾驶位","副驾驶","前排","后排"]) and has_open_kw and not _is_negated(text_norm, "开"):
        return "open_windows"
    if has_window and not any(w in text_norm for w in ["左","右","前","后","主驾","副驾","驾驶位","副驾驶","前排","后排"]) and has_close_kw and not _is_negated(text_norm, "关"):
        return "close_windows"

    # 若文本包含“解锁”，优先匹配解锁车门，并避免误识别为上锁
    skip_lock = False
    if ("解锁" in text_norm) or ("解鎖" in text_norm):
        for kw in cmd_keywords.get("unlock_door", [[], "", "", ""])[0]:
            nkw = _normalize_text(kw)
            if nkw in text_norm and not _is_negated(text_norm, nkw):
                conn.logger.bind(tag=TAG).info("检测到意图命令: unlock_door")
                return "unlock_door"
        skip_lock = True

    for cmd, keywords in cmd_keywords.items():
        if cmd in exclude_cmds:
            continue
        if skip_lock and cmd == "lock_door":
            continue
        for kw in keywords[0]:
            nkw = _normalize_text(kw)
            if nkw in text_norm and not _is_negated(text_norm, nkw):
                conn.logger.bind(tag=TAG).info(f"检测到意图命令: {cmd}")
                return cmd

    for cmd, keywords in cmd_keywords.items():
        if cmd in exclude_cmds:
            continue
        if any(_fuzzy_contains(text_norm, kw) for kw in keywords[0]):
            conn.logger.bind(tag=TAG).info(f"检测到意图命令: {cmd}")
            return cmd
    return

async def extract_rule_cmds(conn, text):
    try:
        text_norm = _normalize_text(text)
        matches = []
        has_open_kw = any(w in text_norm for w in ["打开","开"]) and not any(w in text_norm for w in ["降","降下","下降","落下","降低"])
        has_close_kw = any(w in text_norm for w in ["关闭","关"]) and not any(w in text_norm for w in ["升","升起","升上","抬起","升高"])
        if has_open_kw and has_close_kw and ("打开" in text_norm) and not any(w in text_norm for w in ["升","升起","升上","抬起"]):
            has_close_kw = False
        for cmd, keywords in cmd_keywords.items():
            for kw in keywords[0]:
                if _fuzzy_contains(text_norm, kw):
                    if cmd.startswith("close_") and not has_close_kw:
                        continue
                    if cmd.startswith("open_") and not has_open_kw and cmd not in ("unlock_door",):
                        continue
                    if cmd not in matches:
                        matches.append(cmd)
                    break
        directional = {
            "open_LeftFrontWindow","close_LeftFrontWindow",
            "open_RightFrontWindow","close_RightFrontWindow",
            "open_LeftRearWindow","close_LeftRearWindow",
            "open_RightRearWindow","close_RightRearWindow",
        }
        if any(d in matches for d in directional):
            matches = [m for m in matches if m not in ("open_windows","close_windows")]
        for seg in re.split(r'[，,、;；。\.]+', text):
            c = await check_exact_match(conn, seg)
            if c and c not in matches:
                matches.append(c)
        return matches
    except Exception:
        return []


async def analyze_intent_with_llm(conn, text): # TODO 还是用func可能更靠谱
    """使用LLM分析用户意图"""
    print("analyze_intent_with_llm text: ", text)
    model_info = getattr(conn.llm, "model_name", str(conn.llm.__class__.__name__))
    print("analyze_intent_with_llm model: ", model_info)
    
    cmd_ori = conn.llm.response_no_stream(
        intent_system_prompt.format(intent_instructions=intent_instructions), 
        intent_user_prompt.format(input_text=text),
        max_tokens=20
    )
    matches = re.findall(r'([a-zA-Z0-9_]+(?:\([^)]+\))?)', cmd_ori)
    cmds = []
    for m in matches:
        mm = re.match(r'([a-zA-Z0-9_]+)', m)
        name = mm.group(1) if mm else None
        if name and name in cmd_keywords.keys() and m not in cmds:
            cmds.append(m)
    if cmds:
        return cmds
    return

async def create_group_by_name(conn, text):
    """解析群聊名称"""
    group_name = conn.llm.response_no_stream(
        group_system_prompt, 
        group_user_prompt.format(input_text=text),
        max_tokens=30
    )

    if group_name != "默认群":
        conn.logger.bind(tag=TAG).info(f"用户输入群聊名称: {group_name}")
        # 建群
        task = conn.loop.create_task(
            handle_create_group_async(conn, group_name, "邀请你加入群聊")
        )
        def handle_done(f):
            try:
                result = f.result()
                conn.logger.bind(tag=TAG).info(f"群聊创建完成: {result}")
            except Exception as e:
                conn.logger.bind(tag=TAG).error(f"群聊创建失败: {e}")
        task.add_done_callback(handle_done)
        conn.wait_for_response = 0

        return True

    else:
        await speak_txt_with_abort(conn, "能将群聊名称描述更清晰点吗？")
        return False
        

async def create_group_by_confirm(conn, text):
    """解析群聊名称"""
    if not conn.candidate_group_name:
        return await create_group_by_name(conn, text)
    
    agree_texts = ["确认", "同意", "agree", "yes", "好的", "可以", "行", "ok", "加入"]
    refuse_texts = ["放弃", "不同意", "拒绝", "no", "refuse", "不要", "不行", "不加入", "不参加"]
    if text.lower() in agree_texts:
        # 建群
        task = conn.loop.create_task(
            handle_create_group_async(conn, conn.candidate_group_name, "邀请你加入群聊")
        )

        def handle_done(f):
            try:
                result = f.result()
                conn.logger.bind(tag=TAG).info(f"群聊创建完成: {result}")
            except Exception as e:
                conn.logger.bind(tag=TAG).error(f"群聊创建失败: {e}")

        task.add_done_callback(handle_done)
        conn.wait_for_response = 0
    elif text.lower() in refuse_texts:
        conn.wait_for_response = 0
        await speak_txt_with_abort(conn, f"您放弃创建群聊，{conn.candidate_group_name}")
    else:
        # print("请回复同意或不同意", text, agree_texts, flush=True)
        # await speak_txt_with_abort(conn, "请回复同意或不同意")
        await speak_txt_with_abort(conn, "您收到一个群聊邀请,请回复同意或拒绝")

async def join_group_by_confirm(conn, text):
    """确认加群与否"""
    agree_texts = ["同意", "agree", "yes", "好的", "可以", "行", "ok", "加入"]
    refuse_texts = ["不同意", "拒绝", "no", "refuse", "不要", "不行", "不加入", "不参加"]
    if text.lower() in agree_texts:
        conn.wait_for_response = 0
        return await handle_group_invitation_reply(conn, "agree")

    elif text.lower() in refuse_texts:
        conn.wait_for_response = 0
        return await handle_group_invitation_reply(conn, "refuse")

    else:
        await speak_txt_with_abort(conn, "您收到一个群聊邀请,请回复同意或拒绝")
        return False

async def handle_user_intent(conn, text):
    print(111, conn.wait_for_response, flush=True)
    _, filtered_text = remove_punctuation_and_length(text)

    # 检查是否有待回复的指令
    if conn.wait_for_response == 1: # 期望群主回复群聊名称
        return await create_group_by_name(conn, filtered_text)

    if conn.wait_for_response == 2: # 期望其他设备回复是否加群
        return await join_group_by_confirm(conn, filtered_text) 

    if conn.wait_for_response == 3: # 期望群主回复确认或放弃,例如是否建群
        await create_group_by_confirm(conn, filtered_text) 
        return True
        
    print(222, flush=True)
    text_norm = _normalize_text(filtered_text)
    cmds = []
    for seg in re.split(r'[，,、;；。\\.]+', filtered_text):
        c = await check_exact_match(conn, seg)
        if c is not None and c not in cmds:
            cmds.append(c)
    cmds = await extract_rule_cmds(conn, filtered_text)
    if not cmds:
        control_terms = ("车窗","窗户","窗","车灯","灯","后备箱","发动机","引擎","车门","门","双闪","应急灯","紧急灯","雾灯","停车灯","音量","声音","冷","热","吵","安静")
        if any(term in text_norm for term in control_terms):
            llm_cmds = await analyze_intent_with_llm(conn, filtered_text)
            if llm_cmds:
                cmds = [c for c in llm_cmds if c not in cmds]
    if cmds:
        await process_commands(conn, cmds, filtered_text)
        return True
    
    print(333, cmds if cmds else None, flush=True)
    # 未唤醒不做任何处理,改为未唤醒也可以正常处理聊天任务，因为会错误理解未唤醒
    if not conn.session_awakened: 
        print("------------------------current session not awakened",flush=True)
        return False
    
    print(444, cmds if cmds else None, flush=True)
    if await check_hanuo_intent(conn, text):
        return True
    text_norm2 = _normalize_text(text)
    return False


def speak_txt(conn, text):
    conn.tts.tts_text_queue.put(
        TTSMessageDTO(
            sentence_id=conn.sentence_id,
            sentence_type=SentenceType.FIRST,
            content_type=ContentType.ACTION,
        )
    )
    conn.tts.tts_one_sentence(conn, ContentType.TEXT, content_detail=text)
    conn.tts.tts_text_queue.put(
        TTSMessageDTO(
            sentence_id=conn.sentence_id,
            sentence_type=SentenceType.LAST,
            content_type=ContentType.ACTION,
        )
    )
    conn.dialogue.put(Message(role="assistant", content=text))

async def speak_txt_with_abort(conn, text):
    await handleAbortMessage(conn) #通常是优先级最高的语音信息， 打断客户端说话
    await send_stt_message(conn, "start")
    conn.llm_finish_task = True
    print("speak_txt_with_abort, conn.llm_finish_task:", text, conn.llm_finish_task, flush=True)
    speak_txt(conn, text)

async def process_volume_up(conn):
    """处理音量提高指令"""
    try:
        # 构造音量控制消息
        ws_message = json.dumps({
            "type": "peripheral",
            "action": "volume_up",
            "value": 10,  # 默认提高10个单位
            "timestamp": asyncio.get_event_loop().time()
        }, separators=(",", ":"))
        
        await conn.websocket.send(ws_message)
        conn.logger.bind(tag=TAG).info(f"成功发送音量提高指令到设备 {conn.device_id}")
        await speak_txt_with_abort(conn, cmd_keywords["volume_up"][1])
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"发送音量提高指令失败: {e}")
        await speak_txt_with_abort(conn, "音量调节失败，请稍后再试")

async def process_volume_down(conn):
    """处理音量降低指令"""
    try:
        # 构造音量控制消息
        ws_message = json.dumps({
            "type": "peripheral",
            "action": "volume_down",
            "value": 10,  # 默认降低10个单位
            "timestamp": asyncio.get_event_loop().time()
        }, separators=(",", ":"))
        
        await conn.websocket.send(ws_message)
        conn.logger.bind(tag=TAG).info(f"成功发送音量降低指令到设备 {conn.device_id}")
        await speak_txt_with_abort(conn, cmd_keywords["volume_down"][1])
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"发送音量降低指令失败: {e}")
        await speak_txt_with_abort(conn, "音量调节失败，请稍后再试")

async def process_volume_set(conn, ori_cmd):
    """处理音量设置指令"""
    try:
        import re
        text_norm = _normalize_text(ori_cmd)
        numbers = re.findall(r'\d+', text_norm)
        volume = None
        if numbers:
            volume = int(numbers[0])
        else:
            zh_digits = {'零':0,'一':1,'二':2,'两':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9}
            def parse_zh_num(s: str):
                s = s.replace('百分之','')
                if '十' in s and len(s) >= 2:
                    parts = s.split('十')
                    tens = zh_digits.get(parts[0], 1) if parts[0] != '' else 1
                    ones = zh_digits.get(parts[1], 0) if len(parts) > 1 else 0
                    return tens * 10 + ones
                return zh_digits.get(s, None)
            m = re.search(r'(百分之)?[零一二两三四五六七八九十]+', text_norm)
            if m:
                volume = parse_zh_num(m.group(0))
        if volume is not None:
            volume = max(0, min(100, volume))
            ws_message = json.dumps({
                "type": "peripheral",
                "action": "volume_set",
                "value": volume,
                "timestamp": asyncio.get_event_loop().time()
            }, separators=(",", ":"))
            await conn.websocket.send(ws_message)
            conn.logger.bind(tag=TAG).info(f"成功发送音量设置指令到设备 {conn.device_id}: {volume}")
            await speak_txt_with_abort(conn, f"已将音量设置为{volume}")
        else:
            await speak_txt_with_abort(conn, "请说明要设置的音量数值，比如音量设置为50或百分之五十")
            
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"发送音量设置指令失败: {e}")
        await speak_txt_with_abort(conn, "音量调节失败，请稍后再试")

async def handle_group_invitation_reply(conn, cmd):
    """处理群聊邀请回复"""

    # # TODO 此处处理不太妥当，加群时需保持就一个群
    # group_id = None
    # for tmp_group_id, group_info in conn.server.active_groups.items():
    #     if conn.device_id in group_info.get("pending_invitations", []):
    #         group_id = tmp_group_id
    #         break

    if not conn.candidate_group_id:
        return False
            
    device_id = conn.device_id
    group_id = conn.candidate_group_id
    group_info = conn.server.active_groups[group_id]
    
    # 从待处理列表中移除
    if device_id in group_info['pending_invitations']:
        group_info['pending_invitations'].remove(device_id)

    # 如果同时包含同意和拒绝关键词，优先判断为拒绝（更安全）
    if cmd == "refuse":
        # 拒绝加入群聊
        if 'declined' not in group_info:
            group_info['declined'] = []
        if device_id not in group_info['declined']:
            group_info['declined'].append(device_id)
        
        # 发送确认消息
        confirmation_text = "您已拒绝加入群聊"
        await send_tts_message(conn, "candidate_group_id", "")
        await speak_txt_with_abort(conn, confirmation_text)
        conn.logger.bind(tag=TAG).info(f"设备 {device_id} 已拒绝群聊邀请 {group_id}")

    elif cmd == "agree":
        # 同意加入群聊
        if device_id not in group_info['members']:
            group_info['members'].append(device_id)
        
        # 设置设备的群聊ID
        conn.current_group_id = group_id
        conn.candidate_group_id = None
        conn.candidate_group_name = ""
        
        # 发送确认消息
        confirmation_text = f"您已成功加入群聊 '{group_info['group_name']}'，现在可以与群组成员进行语音通话了"
        await send_tts_message(conn, "candidate_group_id", group_id)
        await speak_txt_with_abort(conn, confirmation_text)
        

    elif cmd == "exit_group":
        # 退出群聊
        conn.current_group_id = None
        
        # 从群聊成员列表中移除
        if (hasattr(conn.server, "active_groups") and group_id in conn.server.active_groups):
            group_info = conn.server.active_groups[group_id]
            if device_id in group_info.get('members', []):
                group_info['members'].remove(device_id)

        await send_tts_message(conn, "candidate_group_id", "")
        await speak_txt_with_abort(conn, "您已退出群聊")

    elif cmd == "dismiss":
        print("暂不考虑解散群的实现", flush=True)
    
    else:
        return False
    
    conn.candidate_group_id = None
    conn.candidate_group_name = ""
    return True

async def broadcast_to_group_members(server, group_id, message, exclude_device=None):
    """向群组成员广播消息"""
    if not hasattr(server, 'active_groups') or group_id not in server.active_groups:
        return
    
    group_info = server.active_groups[group_id]
    
    for member_device_id in group_info['members']:
        if exclude_device and member_device_id == exclude_device:
            continue
            
        # 找到对应的连接并发送消息
        for conn in server.active_connections:
            if hasattr(conn, 'device_id') and conn.device_id == member_device_id:
                tts_message = {
                    "type": "tts",
                    "content": message,
                    "sentence_type": "normal"
                }
                try:
                    await conn.websocket.send(json.dumps(tts_message))
                except Exception as e:
                    # 使用任意连接的logger实例
                    if hasattr(conn, 'logger'):
                        conn.logger.bind(tag=TAG).error(f"向设备 {member_device_id} 发送消息失败: {e}")
                    else:
                        print(f"向设备 {member_device_id} 发送消息失败: {e}")
                break
async def check_hanuo_intent(conn, text):
    """
    检查是否为汉诺集团相关意图
    """
    # 汉诺集团相关关键词（包括谐音字）
    hanuo_keywords = [
        "汉诺", "汉诺集团", "韩诺", "韩诺集团", "汗诺", "汗诺集团",
        "寒诺", "寒诺集团", "翰诺", "翰诺集团", "瀚诺", "瀚诺集团",
        "汉若", "汉若集团", "韩若", "韩若集团"
    ]
    
    # 检查文本中是否包含汉诺集团相关关键词
    text_lower = text.lower()
    has_hanuo_keyword = any(keyword.lower() in text_lower for keyword in hanuo_keywords)
    
    if has_hanuo_keyword:
        # 检查是否是明确的介绍请求
        introduction_keywords = ["介绍", "是什么", "怎么样", "了解", "说说", "讲讲", "告诉我"]
        is_introduction_request = any(keyword in text_lower for keyword in introduction_keywords)
        
        if is_introduction_request:
            # 返回完整的汉诺集团介绍
            introduction_text = get_hanuo_full_introduction()
            await send_stt_message(conn, text)
            await speak_txt_with_abort(conn, introduction_text)
            conn.logger.bind(tag=TAG).info(f"识别到汉诺集团介绍请求: {text}")
            return True
        else:
            # 简单提及汉诺集团，给出简短回应
            simple_response = get_hanuo_simple_response()
            await send_stt_message(conn, text)
            await speak_txt_with_abort(conn, simple_response)
            conn.logger.bind(tag=TAG).info(f"识别到汉诺集团简单提及: {text}")
            return True
    
    # 检查CDN、AI物联网等相关技术词汇
    tech_keywords = [
        "CDN", "cdn", "内容分发网络", "边缘云计算", "AI物联网",
        "智能音箱", "车载机器人", "AI眼镜", "智能手环", "智慧云盒",
        "富氢水机", "共享充电宝", "智能酒柜", "防霸凌设备"
    ]
    
    has_tech_keyword = any(keyword.lower() in text_lower for keyword in tech_keywords)
    
    if has_tech_keyword:
        # 检查是否是明确的询问
        question_keywords = ["是什么", "怎么样", "介绍", "了解", "原理", "作用", "功能"]
        is_question = any(keyword in text_lower for keyword in question_keywords)
        
        if is_question:
            # 返回技术相关的汉诺集团介绍
            tech_response = get_hanuo_tech_response(text_lower)
            await send_stt_message(conn, text)
            await speak_txt_with_abort(conn, tech_response)
            conn.logger.bind(tag=TAG).info(f"识别到汉诺集团技术相关询问: {text}")
            return True
    
    return False


def get_hanuo_full_introduction():
    """
    返回完整的汉诺集团介绍
    """
    return """各位汉诺的师兄、师姐们，大家好。我是绿仔，接下来我为大家隆重介绍汉诺集团，汉诺集团起于CDN,但不止于发展CDN， CDN的技术作用原理是把互联网上的内容以就近原则很好的分发给全国各地的用户。中国CDN市场规模在2029年预计会增长到1400亿元的规模。汉诺集团集研发、生产、运营、营销一体化的AI物联网科技集团，通过CDN技术提升用户数字化体验，以及AI应用解决方案。搭建边缘云计算为赋能的产品。我们搭建AI产品线，包括AI智能音箱、AI车载机器人、AI眼镜、智能手环等，而智慧云盒、富氢水机、共享充电宝、智能酒柜、防霸凌设备等搭建了边缘云计算，集学、用、玩、行、娱为一体。

汉诺集团在CDN行业的核心优势涵盖三个方面，第一，国家工信工业颁发的内容分发网络业务许可证，全国5600多家CDN企业中，只有1000家有这个证书。汉诺集团的经营范围是全球。

第二技术方面，汉诺集团通过CDN实现交付物联网、短视频、直播、AI智慧、游戏加速、电商等业务类型，做到万物互联，多场景完成整个技术和产业布局。

第三，汉诺集团的产业链业务优势，在上游端，派欧云、七牛云、白山云、爱偲云、网心云等签订了长期的CDN加速定向流量合作。中游生产端，自建智慧工厂——坐落于"一带一路"战略桥头堡成都蓉欧产业园，在产业园核心区域首期拥有超过3000㎡的智慧生产基地，年生产量可达300万台，下游运营端，拥有全国33个CDN数据中心和15万+CDN加速节点，当前储备带宽总量20T+。

汉诺集团集生产、研发、整体化营销、产品生命周期管理、严格的品控、专业品牌管理、资本运作为一体。值得您的信赖与支持。"""


def get_hanuo_simple_response():
    """
    返回简短的汉诺集团回应
    """
    responses = [
        "汉诺集团是一家专注于CDN和AI物联网的科技集团，如果您想了解更多，可以说'介绍一下汉诺集团'。",
        "提到汉诺集团了呢，这是一家很有实力AI物联网科技公司，主要做CDN和智能设备。",
        "汉诺集团确实不错，他们在CDN技术和AI产品方面都很有优势。想了解详情可以让我详细介绍一下。"
    ]
    import random
    return random.choice(responses)


def get_hanuo_tech_response(text_lower):
    """
    根据技术关键词返回相应的汉诺集团技术介绍
    """
    if "cdn" in text_lower or "内容分发网络" in text_lower:
        return "CDN是内容分发网络的缩写，汉诺集团在这方面很有优势。CDN的技术作用原理是把互联网上的内容以就近原则很好的分发给全国各地的用户。汉诺集团拥有全国33个CDN数据中心和15万+CDN加速节点，当前储备带宽总量20T+。如果想了解汉诺集团的完整情况，可以说'介绍一下汉诺集团'。"
    elif "边缘云计算" in text_lower:
        return "边缘云计算是汉诺集团的核心技术之一。他们通过边缘云计算技术，搭建了智慧云盒、富氢水机、共享充电宝、智能酒柜、防霸凌设备等产品，集学、用、玩、行、娱为一体。想了解更多可以让我详细介绍汉诺集团。"
    elif any(keyword in text_lower for keyword in ["智能音箱", "车载机器人", "ai眼镜", "智能手环"]):
        return "这些都是汉诺集团AI产品线的重要组成部分。汉诺集团搭建了包括AI智能音箱、AI车载机器人、AI眼镜、智能手环等完整的AI产品线。如果想了解汉诺集团的完整布局，可以说'介绍一下汉诺集团'。"
    else:
        return "您提到的这个技术汉诺集团也有涉及。汉诺集团是一家集研发、生产、运营、营销一体化的AI物联网科技集团，在多个技术领域都有布局。想了解详情可以让我介绍一下汉诺集团。"