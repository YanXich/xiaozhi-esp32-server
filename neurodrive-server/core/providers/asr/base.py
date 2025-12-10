import os
import wave
import uuid
import queue
import asyncio
import traceback
import threading
import opuslib_next
import json
import io
import time
import concurrent.futures
from abc import ABC, abstractmethod
from config.logger import setup_logging
from typing import Optional, Tuple, List, Dict, Any
from core.handle.receiveAudioHandle import startToChat, forward_audio_to_group
from core.handle.reportHandle import enqueue_asr_report
from core.utils.util import remove_punctuation_and_length, is_chinese_english_only
from core.handle.receiveAudioHandle import handleAudioMessage

TAG = __name__
logger = setup_logging()


class ASRProviderBase(ABC):
    def __init__(self):
        pass

    # 打开音频通道
    async def open_audio_channels(self, conn):
        conn.asr_priority_thread = threading.Thread(
            target=self.asr_text_priority_thread, args=(conn,), daemon=True
        )
        conn.asr_priority_thread.start()

    # 有序处理ASR音频
    def asr_text_priority_thread(self, conn):
        while not conn.stop_event.is_set():
            try:
                message = conn.asr_audio_queue.get(timeout=1)
                future = asyncio.run_coroutine_threadsafe(
                    handleAudioMessage(conn, message),
                    conn.loop,
                )
                future.result()
            except queue.Empty:
                continue
            except Exception as e:
                logger.bind(tag=TAG).error(
                    f"处理ASR文本失败: {str(e)}, 类型: {type(e).__name__}, 堆栈: {traceback.format_exc()}"
                )
                continue

    # 接收音频
    async def receive_audio(self, conn, audio, audio_have_voice):
        if conn.client_listen_mode == "auto" or conn.client_listen_mode == "realtime":
            have_voice = audio_have_voice
        else:
            have_voice = conn.client_have_voice
        
        conn.asr_audio.append(audio)
        if len(conn.asr_audio) == 1:
            conn.first_asr_audio_time = time.monotonic()
        if not have_voice and not conn.client_have_voice:
            #print("reduce asr_audio....", flush=True)
            conn.asr_audio = conn.asr_audio[-10:]
            return

        if conn.client_voice_stop:
            asr_audio_task = conn.asr_audio.copy()
            conn.asr_audio.clear()
            conn.reset_vad_states()

            print("audio tasks length: ", len(asr_audio_task), flush=True)

            if len(asr_audio_task) >= 5:
                await self.handle_voice_stop(conn, asr_audio_task)
            else:
                self.stop_ws_connection()

    # 处理语音停止
    async def handle_voice_stop(self, conn, asr_audio_task: List[bytes]):
        """并行处理ASR和声纹识别"""
        try:
            if not hasattr(conn, 'abort_asr_start'):
                conn.abort_asr_start = -1

            # 群聊模式下不进行ASR处理
            print("check current_group_id attr:", hasattr(conn, 'current_group_id'))
            if hasattr(conn, 'current_group_id'):
                print("conn.current_group_id===> ", conn.current_group_id, flush=True)
                
            if hasattr(conn, 'current_group_id') and conn.current_group_id:
                logger.bind(tag=TAG).info("群聊模式下跳过ASR处理")
                await forward_audio_to_group(conn, asr_audio_task)
                return

            if conn.first_asr_audio_time >= 0 and conn.abort_asr_start >= 0 and conn.first_asr_audio_time < conn.abort_asr_start:
                print("abort asr 1",  conn.first_asr_audio_time, conn.abort_asr_start)
                return
            
            total_start_time = time.monotonic()
            
            # 准备音频数据
            if conn.audio_format == "pcm":
                pcm_data = asr_audio_task
            else:
                pcm_data = self.decode_opus(asr_audio_task)
            
            combined_pcm_data = b"".join(pcm_data)
            
            # 预先准备WAV数据
            wav_data = None
            # 使用连接的声纹识别提供者
            if conn.voiceprint_provider and combined_pcm_data:
                wav_data = self._pcm_to_wav(combined_pcm_data)
            
            # 定义ASR任务
            def run_asr():
                start_time = time.monotonic()
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        result = loop.run_until_complete(
                            self.speech_to_text(asr_audio_task, conn.session_id, conn.audio_format)
                        )
                        end_time = time.monotonic()
                        logger.bind(tag=TAG).info(f"ASR耗时: {end_time - start_time:.3f}s")
                        return result
                    finally:
                        loop.close()
                except Exception as e:
                    end_time = time.monotonic()
                    logger.bind(tag=TAG).error(f"ASR失败: {e}")
                    return ("", None)
            
            # 定义声纹识别任务
            def run_voiceprint():
                if not wav_data:
                    return None
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        # 使用连接的声纹识别提供者
                        result = loop.run_until_complete(
                            conn.voiceprint_provider.identify_speaker(wav_data, conn.session_id)
                        )
                        return result
                    finally:
                        loop.close()
                except Exception as e:
                    logger.bind(tag=TAG).error(f"声纹识别失败: {e}")
                    return None
            
            # 使用线程池执行器并行运行
            parallel_start_time = time.monotonic()
            if conn.first_asr_audio_time >= 0 and conn.abort_asr_start >= 0 and conn.first_asr_audio_time < conn.abort_asr_start:
                print("abort asr 2",  conn.first_asr_audio_time, conn.abort_asr_start)
                return

            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as thread_executor:
                asr_future = thread_executor.submit(run_asr)
                
                if conn.voiceprint_provider and wav_data:
                    voiceprint_future = thread_executor.submit(run_voiceprint)
                    
                    # 等待两个线程都完成
                    asr_result = asr_future.result(timeout=15)
                    voiceprint_result = voiceprint_future.result(timeout=15)
                    
                    results = {"asr": asr_result, "voiceprint": voiceprint_result}
                else:
                    asr_result = asr_future.result(timeout=15)
                    results = {"asr": asr_result, "voiceprint": None}

            # 处理结果
            raw_text, file_path = results.get("asr", ("", None))
            speaker_name = results.get("voiceprint", None)
            
            # 记录识别结果
            if raw_text:
                logger.bind(tag=TAG).info(f"识别文本: {raw_text}")
            if speaker_name:
                logger.bind(tag=TAG).info(f"识别说话人: {speaker_name}")

            # 性能监控
            total_time = time.monotonic() - total_start_time
            logger.bind(tag=TAG).info(f"总处理耗时: {total_time:.3f}s")
            
            # 检查文本长度
            text_len, filtered_text = remove_punctuation_and_length(raw_text)

            # 短文本只能是中英文
            if text_len and text_len < 3:
                if not is_chinese_english_only(filtered_text):
                    raw_text = ""

            self.stop_ws_connection()
            
            # 增强的噪音和无效文本过滤
            if raw_text and not self._is_noise_or_invalid_text(filtered_text, combined_pcm_data) and text_len > 0:
                # 构建包含说话人信息的JSON字符串
                enhanced_text = self._build_enhanced_text(raw_text, speaker_name)
                
                # 使用自定义模块进行上报
                await startToChat(conn, enhanced_text)
                enqueue_asr_report(conn, enhanced_text, asr_audio_task)
            else:
                if raw_text:
                    logger.bind(tag=TAG).info(f"过滤噪音或无效文本: {raw_text}")
                self.stop_ws_connection()
                
        except Exception as e:
            import traceback
            logger.bind(tag=TAG).error(f"处理语音停止失败: {e}, {traceback.format_exc()}")
            logger.bind(tag=TAG).debug(f"异常详情: {traceback.format_exc()}")

    def _is_noise_or_invalid_text(self, text: str, audio_data: bytes) -> bool:
        """检测是否为噪音或无效文本"""
        if not text or len(text.strip()) == 0:
            return True
        
        # 过滤过短的文本（可能是噪音） 
        if len(text.strip()) < 2:
            return True
        
        # 检查韩语字符（更严格的检测）
        korean_chars = 0
        total_chars = 0
        for char in text:
            if char.isspace() or char in '.,!?;:':
                continue
            total_chars += 1
            # 韩语字符Unicode范围
            if (0x1100 <= ord(char) <= 0x11FF or   # 韩语字母
                0x3130 <= ord(char) <= 0x318F or   # 韩语兼容字母
                0xAC00 <= ord(char) <= 0xD7AF):    # 韩语音节
                korean_chars += 1
        
        # 如果韩语字符占比超过50%，认为是误识别
        if total_chars > 0 and korean_chars / total_chars > 0.5:
            return True
        
        # 检查日语字符
        japanese_chars = 0
        for char in text:
            if char.isspace() or char in '.,!?;:':
                continue
            # 日语字符Unicode范围
            if (0x3040 <= ord(char) <= 0x309F or   # 平假名
                0x30A0 <= ord(char) <= 0x30FF):    # 片假名
                japanese_chars += 1
        
        # 如果日语字符占比超过50%，认为是误识别
        if total_chars > 0 and japanese_chars / total_chars > 0.5:
            return True
        
        # 音频质量检测 - 检查是否为低质量音频（可能是噪音）
        if audio_data and len(audio_data) > 0:
            try:
                import numpy as np
                # 将音频数据转换为numpy数组进行分析
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                if len(audio_array) > 0:
                    # 计算音频的RMS值
                    rms = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))
                    # 计算零交叉率（噪音通常有高零交叉率）
                    zero_crossings = np.sum(np.diff(np.sign(audio_array)) != 0)
                    zero_crossing_rate = zero_crossings / len(audio_array)
                    
                    # 如果RMS很低且零交叉率很高，可能是噪音
                    if rms < 500 and zero_crossing_rate > 0.3:
                        logger.bind(tag=TAG).debug(f"检测到疑似噪音: RMS={rms:.2f}, ZCR={zero_crossing_rate:.3f}")
                        return True
            except Exception as e:
                logger.bind(tag=TAG).debug(f"音频质量检测失败: {e}")
        
        # 过滤纯符号或数字
        import re
        cleaned_text = re.sub(r'[.,:;!?\s]+', '', text)
        if not cleaned_text: # 数字是有可能的
            return True
        
        # 检查是否只包含符号
        if re.match(r'^[^\w\u4e00-\u9fff]+$', cleaned_text):
            return True
        
        # 检查重复字符模式（噪音常产生重复字符）
        # if len(set(text.replace(' ', ''))) <= 2 and len(text.strip()) > 3:
        #     return True
        
        return False
    
    def _build_enhanced_text(self, text: str, speaker_name: Optional[str]) -> str:
        """构建包含说话人信息的文本"""
        if speaker_name and speaker_name.strip():
            return json.dumps({
                "speaker": speaker_name,
                "content": text
            }, ensure_ascii=False)
        else:
            return text

    def _pcm_to_wav(self, pcm_data: bytes, sample_rate=16000, channels=1) -> bytes:
        """将PCM数据转换为WAV格式，并进行音频质量优化"""
        if len(pcm_data) == 0:
            logger.bind(tag=TAG).warning("PCM数据为空，无法转换WAV")
            return b""
        
        # 确保数据长度是偶数（16位音频）
        if len(pcm_data) % 2 != 0:
            pcm_data = pcm_data[:-1]
        
        try:
            import numpy as np
            
            # 转换为numpy数组进行处理
            audio_data = np.frombuffer(pcm_data, dtype=np.int16)
            
            # 音频质量检测（仅对较长音频进行处理，提高性能）
            if len(audio_data) < sample_rate * 0.2:  # 少于200ms的音频跳过处理
                logger.bind(tag=TAG).debug(f"音频片段过短: {len(audio_data)/sample_rate:.2f}s，跳过优化处理")
            else:
                # 简单降噪处理 - 仅对500ms以上的音频进行降噪
                if len(audio_data) > sample_rate * 0.5:
                    audio_data = self._apply_noise_reduction(audio_data)
                
                # 音频增强 - 标准化音量（简化处理）
                audio_data = self._normalize_audio(audio_data)
            
            # 创建WAV文件头
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(channels)      # 单声道
                wav_file.setsampwidth(2)      # 16位
                wav_file.setframerate(sample_rate)  # 16kHz采样率
                wav_file.writeframes(audio_data.tobytes())
            
            wav_buffer.seek(0)
            wav_data = wav_buffer.read()
            
            return wav_data
        except ImportError:
            logger.bind(tag=TAG).warning("numpy未安装，跳过音频优化")
            # 回退到原始方法
            wav_buffer = io.BytesIO()
            try:
                with wave.open(wav_buffer, 'wb') as wav_file:
                    wav_file.setnchannels(channels)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(sample_rate)
                    wav_file.writeframes(pcm_data)
                
                wav_buffer.seek(0)
                return wav_buffer.read()
            except Exception as e:
                logger.bind(tag=TAG).error(f"WAV转换失败: {e}")
                return b""
        except Exception as e:
            logger.bind(tag=TAG).error(f"WAV转换失败: {e}")
            return b""

    def _apply_noise_reduction(self, audio_data):
        """简单的降噪处理（优化版本）"""
        try:
            import numpy as np
            
            # 快速计算音频的RMS值
            audio_float = audio_data.astype(np.float32)
            rms = np.sqrt(np.mean(audio_float ** 2))
            
            # 设置噪音阈值（RMS的15%，减少过度处理）
            noise_threshold = rms * 0.15
            
            # 对低于阈值的信号进行轻微衰减
            mask = np.abs(audio_float) < noise_threshold
            audio_float[mask] *= 0.5  # 将噪音衰减到50%（减少失真）
            
            return np.clip(audio_float, -32767, 32767).astype(np.int16)
        except Exception as e:
            logger.bind(tag=TAG).debug(f"降噪处理失败: {str(e)}")
            return audio_data
    
    def _normalize_audio(self, audio_data):
        """音频标准化处理（简化版本）"""
        try:
            import numpy as np
            
            # 转换为浮点数进行处理
            audio_float = audio_data.astype(np.float32)
            
            # 快速计算最大绝对值
            max_val = np.max(np.abs(audio_float))
            
            if max_val > 0:
                # 简化的标准化处理（减少计算开销）
                target_max = 16000  # 降低目标最大值，减少过度处理
                if max_val < target_max * 0.2:  # 仅对音量过小的进行放大
                    scale_factor = min(target_max * 0.6 / max_val, 2.0)  # 最多放大2倍
                    audio_float *= scale_factor
                elif max_val > 25000:  # 仅对音量过大的进行压缩
                    audio_float *= target_max / max_val
            
            return np.clip(audio_float, -32767, 32767).astype(np.int16)
        except Exception as e:
            logger.bind(tag=TAG).debug(f"音频标准化失败: {str(e)}")
            return audio_data

    def stop_ws_connection(self):
        pass

    def save_audio_to_file(self, pcm_data: List[bytes], session_id: str) -> str:
        """PCM数据保存为WAV文件"""
        module_name = __name__.split(".")[-1]
        file_name = f"asr_{module_name}_{session_id}_{uuid.uuid4()}.wav"
        file_path = os.path.join(self.output_dir, file_name)

        with wave.open(file_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 2 bytes = 16-bit
            wf.setframerate(16000)
            wf.writeframes(b"".join(pcm_data))

        return file_path

    @abstractmethod
    async def speech_to_text(
        self, opus_data: List[bytes], session_id: str, audio_format="opus"
    ) -> Tuple[Optional[str], Optional[str]]:
        """将语音数据转换为文本"""
        pass

    @staticmethod
    def decode_opus(opus_data: List[bytes]) -> List[bytes]:
        """将Opus音频数据解码为PCM数据"""
        try:
            decoder = opuslib_next.Decoder(16000, 1)
            pcm_data = []
            buffer_size = 960  # 每次处理960个采样点 (60ms at 16kHz)
            
            for i, opus_packet in enumerate(opus_data):
                try:
                    if not opus_packet or len(opus_packet) == 0:
                        continue
                    
                    pcm_frame = decoder.decode(opus_packet, buffer_size)
                    if pcm_frame and len(pcm_frame) > 0:
                        pcm_data.append(pcm_frame)
                        
                except opuslib_next.OpusError as e:
                    logger.bind(tag=TAG).warning(f"Opus解码错误，跳过数据包 {i}: {e}")
                except Exception as e:
                    logger.bind(tag=TAG).error(f"音频处理错误，数据包 {i}: {e}")
            
            return pcm_data
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"音频解码过程发生错误: {e}")
            return []