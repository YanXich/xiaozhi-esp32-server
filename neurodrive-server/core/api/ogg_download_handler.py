import json
import time
from aiohttp import web
from core.utils.util import get_local_ip
from core.api.base_handler import BaseHandler
from pathlib import Path
import os
import asyncio
import uuid

# 检查ffmpeg-python，后续做到镜像里去
import subprocess
import sys
def check_and_install_package(package_name):
    try:
        # 检查包是否已安装
        subprocess.run([sys.executable, "-m", "pip", "show", package_name], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"'{package_name}' 已安装")
    except subprocess.CalledProcessError:
        print(f"'{package_name}' 未安装，正在安装...")
        # 安装包
        subprocess.run([sys.executable, "-m", "pip", "install", package_name], check=True)
        print(f"'{package_name}' 安装成功")
 
# 检查并安装 ffmpeg-python
check_and_install_package("ffmpeg-python")

import ffmpeg

TAG = __name__

"""
音频文件预下载
1. 语音回复的内容预制
"""

HANNUO_INTRO = """各位汉诺的师兄、师姐们，大家好。我是绿仔，接下来我为大家隆重介绍汉诺集团，汉诺集团起于CDN,但不止于发展CDN， CDN的技术作用原理是把互联网上的内容以就近原则很好的分发给全国各地的用户。中国CDN市场规模在2029年预计会增长到1400亿元的规模。汉诺集团集研发、生产、运营、营销为一体的AI物联网科技集团，通过CDN技术提升用户数字化体验，以及AI应用解决方案。搭建边缘云计算为赋能的产品。我们搭建AI产品线，包括AI智能音箱、AI车载机器人、AI眼镜、智能手环等，而智慧云盒、富氢水机、共享充电宝、智能酒柜、防霸凌设备等搭建了边缘云计算，集学、用、玩、行、娱为一体。

汉诺集团在CDN行业的核心优势涵盖三个方面，第一，国家工信部颁发的内容分发网络业务许可证，全国5600多家CDN企业中，只有1000家有这个证书。汉诺集团的经营范围是全国。

第二技术方面，汉诺集团通过CDN实现交付物联网、短视频、直播、AI智慧、游戏加速、电商等业务类型，做到万物互联，多场景完成整个技术和产业布局。

第三，汉诺集团的产业链业务优势，在上游端，派欧云、七牛云、白山云、爱偲云、网心云等签订了长期的CDN加速定向流量合作。中游生产端，自建智慧工厂——坐落于"一带一路"战略桥头堡成都蓉欧产业园，在产业园核心区域首期拥有超过3000㎡的智慧生产基地，年生产量可达300万台，下游运营端，拥有全国33个CDN数据中心和15万+CDN加速节点，当前储备带宽总量20T+。

汉诺集团集生产、研发、整体化营销、产品生命周期管理、严格的品控、专业品牌管理、资本运作为一体。值得您的信赖与支持。"""

class OggDownloadHandler(BaseHandler):
    def __init__(self, config: dict, websocket_server=None):
        super().__init__(config)
        self.tmp_dir = Path("./tmp_voice_files")
        os.makedirs(self.tmp_dir, exist_ok=True) 
        self.websocket_server = websocket_server
        self.file_string_map = {
            "wakeup.ogg": "我在呢！",
            "poke.ogg": "有人戳我",
            "open_window_ok.ogg": [
                "让风灌满整个车厢",
                "新鲜空气已注入",
                "开始呼吸啦",
                "让我们与风同行",
                "开窗大吉，今天也是元气满满的一天"
            ],
            "close_window_ok.ogg": [
                "车窗已关闭",
                "守护结界升起啦",
                "专属空间已建立",
                "安全区已确认",
                "这就让喧嚣被屏蔽"
            ],
            "lock_door_ok.ogg": [
                "车门已锁好",
                "已为您锁好车门",
                "放心吧您嘞，车门锁定完成",
                "锁好了，妥妥的",
                "车门已锁，请放心"
            ],
            "unlock_door_ok.ogg": [
                "车门已解锁",
                "芝麻开门，车门已开",
                "这就为你解除门禁",
                "随时可以开门",
                "好的，车门已可打开"
            ],
            "low_battery.ogg": [
                "电量低，请注意",
                "电量不足，请及时充电",
                "当前电量较低",
                "请尽快安排充电",
                "电量偏低，谨慎驾驶"
            ],
            "chatting_mode.ogg": [
                "群聊中，请先退出群聊",
                "当前处于群聊模式",
                "请结束群聊后再试",
                "群聊进行中，暂不执行",
                "请退出群聊以继续"
            ],
            "start_engine_ok.ogg": [
                "引擎在轰鸣，冒险的BGM响起来啦",
                "动力澎湃，准备出发",
                "座驾已激活",
                "咆哮吧，野兽",
                "力量已充满，随时可以出发"
            ],
            "stop_engine_ok.ogg": [
                "发动机已关闭",
                "好的，已熄火",
                "寂静回归",
                "心跳已平复",
                "节能模式启动"
            ],
            "open_trunk_ok.ogg": [
                "后备箱已打开",
                "载物模式启动",
                "空间任你用",
                "后备箱已开启，请取放物品",
                "请装载您的物品"
            ],
            "close_trunk_ok.ogg": [
                "后备箱已关闭",
                "货物已固定",
                "满载而归",
                "搞定，后备箱已合上",
                "后备箱已锁好"
            ],
            "light_on_ok.ogg": [
                "车灯已打开",
                "光芒万丈",
                "照亮你的前程",
                "好的，前灯已亮起",
                "让灯光点亮生活"
            ],
            "light_off_ok.ogg": "为了安全起见，你需要手动关闭车灯",
            "open_emergency_flasher_ok.ogg": "双闪已打开",
            "close_emergency_flasher_ok.ogg": "双闪已关闭",
            "open_rear_fog_lamp.ogg": "后雾灯已打开",
            "close_rear_fog_lamp.ogg": "后雾灯已关闭",
            "open_stop_light.ogg": "停车灯已打开",
            "close_stop_light.ogg": "为了安全起见，请手动关闭停车灯",
            "open_left_front_window.ogg": "左前窗已打开",
            "close_left_front_window.ogg": "左前窗已关闭",
            "open_right_front_window.ogg": "右前窗已打开",
            "close_right_front_window.ogg": "右前窗已关闭",
            "open_left_rear_window.ogg": "左后窗已打开",
            "close_left_rear_window.ogg": "左后窗已关闭",
            "open_right_rear_window.ogg": "右后窗已打开",
            "close_right_rear_window.ogg": "右后窗已关闭",
            "cmd_success.ogg": "指令操作成功",
            "hannuo_intro.ogg": HANNUO_INTRO
        }

    async def handle_get(self, request: web.Request) -> web.Response:
        """
        处理单个文件下载请求
        URL 示例: http://47.109.177.102:18003/xiaozhi/voice_files?file=low_battery.ogg
        """
        try:
            # TODO 自动清理历史文件

            output_path = ""

            # 获取设备信息
            client_conn = None
            device_id = request.headers.get("device-id", "")
            print("device_id: ", device_id, flush=True)

            if len(device_id) == 0:
                raise ValueError("Missing 'device_id' parameter")
            
            for conn in self.websocket_server.active_connections:
                print("check device id: ", conn.device_id, device_id, flush=True)
                if hasattr(conn, "device_id") and conn.device_id == device_id:
                    client_conn = conn
                    break
            if client_conn is None:
                raise ValueError("Failed to find client connection")


            requested = request.query.get('file')
            if not requested:
                raise ValueError("Missing 'file' parameter")
            requested_has_ext = requested.lower().endswith(".ogg")
            name_no_ext = os.path.splitext(requested)[0]
            idx_from_name = None
            base_candidate = name_no_ext
            if "_" in name_no_ext:
                maybe_base, maybe_idx = name_no_ext.rsplit("_", 1)
                if maybe_idx.isdigit():
                    idx_from_name = int(maybe_idx) + 1
                    base_candidate = maybe_base
            if f"{base_candidate}.ogg" in self.file_string_map:
                map_key = f"{base_candidate}.ogg"
            elif base_candidate in self.file_string_map:
                map_key = base_candidate
            else:
                raise ValueError(f"Unsupported 'file' parameter: {requested}")
            response_obj = self.file_string_map[map_key]
            base_name = os.path.splitext(map_key)[0]
            if isinstance(response_obj, (list, tuple)):
                index_str = request.query.get('index')
                ext_name = ".ogg"
                idx_int = None
                if index_str is not None:
                    try:
                        idx_int = int(index_str)
                    except Exception:
                        raise ValueError(f"Invalid 'index' parameter: {index_str}")
                elif idx_from_name is not None:
                    idx_int = idx_from_name
                elif requested_has_ext:
                    idx_int = 1
                if idx_int is not None:
                    if idx_int < 1 or idx_int > len(response_obj):
                        raise ValueError(f"Index out of range: {idx_int}")
                    text = response_obj[idx_int - 1]
                    tmp_file = client_conn.tts.generate_filename()
                    max_repeat_time = 5
                    while not os.path.exists(tmp_file) and max_repeat_time > 0:
                        try:
                            await client_conn.tts.text_to_speak(text, tmp_file)
                        except Exception as e:
                            print("text to speak error: ", e, flush=True)
                            if os.path.exists(tmp_file):
                                os.remove(tmp_file)
                            max_repeat_time -= 1
                    if max_repeat_time <= 0:
                        raise ValueError(f"语音生成失败: {text}")
                    output_file_name = f"{base_name}{ext_name}" if idx_int == 1 else f"{base_name}_{idx_int-1}{ext_name}"
                    output_path = "./tmp_voice_files/" + output_file_name
                    try:
                        print(f"正在转换==>: {tmp_file}")
                        (
                            ffmpeg
                            .input(tmp_file)
                            .output(output_path, acodec='libopus', audio_bitrate='16k', ac=1, ar=16000, frame_duration=60)
                            .run(overwrite_output=True)
                        )
                        print(f"转换成功: {output_file_name}\n")
                    except Exception as e:
                        raise ValueError(f"转换失败: {str(e)}\n")
                    finally:
                        if os.path.exists(tmp_file):
                            os.remove(tmp_file)
                    return web.FileResponse(
                        path=output_path,
                        headers={
                            "Content-Disposition": f"attachment; filename={output_file_name}"
                        }
                    )
                generated_ogg_paths = []
                for idx, text in enumerate(response_obj, start=1):
                    tmp_file = client_conn.tts.generate_filename()
                    max_repeat_time = 5
                    while not os.path.exists(tmp_file) and max_repeat_time > 0:
                        try:
                            await client_conn.tts.text_to_speak(text, tmp_file)
                        except Exception as e:
                            print("text to speak error: ", e, flush=True)
                            if os.path.exists(tmp_file):
                                os.remove(tmp_file)
                            max_repeat_time -= 1
                    if max_repeat_time <= 0:
                        raise ValueError(f"语音生成失败: {text}")
                    output_file_name = f"{base_name}{ext_name}" if idx == 1 else f"{base_name}_{idx-1}{ext_name}"
                    output_path = "./tmp_voice_files/" + output_file_name
                    try:
                        print(f"正在转换==>: {tmp_file}")
                        (
                            ffmpeg
                            .input(tmp_file)
                            .output(output_path, acodec='libopus', audio_bitrate='16k', ac=1, ar=16000, frame_duration=60)
                            .run(overwrite_output=True)
                        )
                        print(f"转换成功: {output_file_name}\n")
                        generated_ogg_paths.append(output_path)
                    except Exception as e:
                        raise ValueError(f"转换失败: {str(e)}\n")
                    finally:
                        if os.path.exists(tmp_file):
                            os.remove(tmp_file)
                boundary = f"ogg_{uuid.uuid4().hex}"
                body = bytearray()
                for ogg_path in generated_ogg_paths:
                    part_header = (
                        f"--{boundary}\r\n"
                        f"Content-Type: audio/ogg\r\n"
                        f"Content-Disposition: attachment; filename=\"{os.path.basename(ogg_path)}\"\r\n\r\n"
                    ).encode("utf-8")
                    body.extend(part_header)
                    with open(ogg_path, "rb") as f:
                        body.extend(f.read())
                    body.extend(b"\r\n")
                body.extend(f"--{boundary}--\r\n".encode("utf-8"))
                return web.Response(
                    body=bytes(body),
                    headers={
                        "Content-Type": f"multipart/mixed; boundary={boundary}"
                    }
                )
            else:
                response_str = response_obj
                print("response_str===>", response_str, flush=True)

            # tts生成音频文件
            tmp_file = client_conn.tts.generate_filename()
            max_repeat_time = 5
            while not os.path.exists(tmp_file) and max_repeat_time > 0:
                try:
                    await client_conn.tts.text_to_speak(response_str, tmp_file)
                except Exception as e:
                    print("text to speak error: ", e, flush=True)
                    if os.path.exists(tmp_file):
                        os.remove(tmp_file)
                    max_repeat_time -= 1

            if max_repeat_time > 0:
                print(
                    f"语音生成成功: {response_str}:{tmp_file}，重试{5 - max_repeat_time}次"
                )
            else:
                raise ValueError(f"语音生成失败: {response_str}，请检查网络或服务是否正常")

            # 音频文件转ogg
            # base_tmp_file, _ = os.path.splitext(tmp_file)  # 忽略原扩展名
            # ogg_file_path = base_tmp_file + ".ogg"  # 直接替换为 .ogg
            # output_path = (self.tmp_dir / file_name).resolve()
            # print("output_path===>", tmp_file, output_path, flush=True)
            # output_path = "test.ogg"
            output_file_name = f"{base_name}.ogg"
            output_path = "./tmp_voice_files/" + output_file_name
            try:
                print(f"正在转换==>: {tmp_file}")
                (
                    ffmpeg
                    .input(tmp_file)
                    .output(output_path, acodec='libopus', audio_bitrate='16k', ac=1, ar=16000, frame_duration=60)
                    .run(overwrite_output=True)
                )
                print(f"转换成功: {output_file_name}\n")
            except Exception as e:
                raise ValueError(f"转换失败: {str(e)}\n")
 
            print(output_path, flush=True)
            if os.path.exists(tmp_file):
                os.remove(tmp_file)

            return web.FileResponse(
                path=output_path,
                headers={
                    "Content-Disposition": f"attachment; filename={output_file_name}"
                }
            )
 
        except ValueError as ve:
            print(f"ValueError: {ve}", flush=True)
            return web.json_response({"error": str(ve)}, status=400)
        except FileNotFoundError:
            return web.json_response({"error": "File not found"}, status=404)
        except Exception as e:
            print(f"error: {e}", flush=True)
            return web.json_response({"error": "Internal server error"}, status=500)

        finally:
            # BUG: 可能先删除，然后再返回web.FileResponse
            # if os.path.exists(output_path):
            #     print("remove output path: ", output_path, flush=True)
            #     os.remove(output_path)
            pass
            