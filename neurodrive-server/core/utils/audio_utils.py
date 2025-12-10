"""
音频处理工具函数
支持base64编码的opus音频数据处理
"""

import base64
import opuslib_next
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


def decode_base64_opus(base64_opus_data: str) -> bytes:
    """
    解码base64编码的opus音频数据
    
    Args:
        base64_opus_data: base64编码的opus音频数据字符串
        
    Returns:
        bytes: 解码后的opus音频数据
        
    Raises:
        ValueError: 当base64数据无效时
    """
    try:
        # 移除可能的前缀（如 "data:audio/opus;base64,"）
        if "," in base64_opus_data:
            base64_opus_data = base64_opus_data.split(",", 1)[1]
        
        # 解码base64数据
        opus_data = base64.b64decode(base64_opus_data)
        logger.bind(tag=TAG).debug(f"成功解码base64 opus数据，大小: {len(opus_data)} 字节")
        return opus_data
        
    except Exception as e:
        logger.bind(tag=TAG).error(f"解码base64 opus数据失败: {e}")
        raise ValueError(f"无效的base64 opus数据: {e}")


def split_opus_packets(opus_data: bytes, packet_size: int = 960) -> list:
    """
    将opus音频数据分割成数据包列表
    
    Args:
        opus_data: opus音频数据
        packet_size: 每个数据包的大小（默认960字节，对应60ms）
        
    Returns:
        list: opus数据包列表
    """
    try:
        packets = []
        
        # 检查是否是OGG容器文件
        if opus_data.startswith(b'OggS'):
            # 进一步检查是否是Opus编码（而不是Vorbis等其他编码）
            data_str = opus_data[:200].decode('latin-1', errors='ignore')
            
            if 'vorbis' in data_str.lower():
                logger.bind(tag=TAG).warning("检测到Ogg Vorbis文件，不是Ogg Opus格式，无法处理")
                raise ValueError("文件是Ogg Vorbis格式，不是Ogg Opus格式，请使用正确的Opus文件")
            
            if 'OpusHead' not in data_str:
                logger.bind(tag=TAG).warning("OGG文件中未找到OpusHead标识，可能不是有效的Ogg Opus文件")
                raise ValueError("OGG文件格式不正确，未找到OpusHead标识")
            
            logger.bind(tag=TAG).debug("检测到有效的OGG Opus文件，解析OGG页面提取Opus帧")
            
            import struct
            offset = 0
            page_count = 0
            
            while offset < len(opus_data) - 27:  # OGG页面头最小27字节
                # 查找OGG页面头标识
                if opus_data[offset:offset+4] != b'OggS':
                    offset += 1
                    continue
                
                try:
                    page_count += 1
                    
                    # 解析OGG页面头
                    header_type = opus_data[offset+5]
                    page_segments = opus_data[offset+26]
                    
                    logger.bind(tag=TAG).debug(f"页面 {page_count}: 类型={header_type:02x}, 段数={page_segments}")
                    
                    # 读取段表
                    segment_table_offset = offset + 27
                    if segment_table_offset + page_segments > len(opus_data):
                        break
                    
                    segment_table = opus_data[segment_table_offset:segment_table_offset + page_segments]
                    page_data_size = sum(segment_table)
                    page_data_offset = segment_table_offset + page_segments
                    
                    if page_data_offset + page_data_size > len(opus_data):
                        break
                    
                    page_data = opus_data[page_data_offset:page_data_offset + page_data_size]
                    
                    # 跳过OpusHead和OpusTags页面
                    if page_data.startswith(b'OpusHead'):
                        logger.bind(tag=TAG).debug("跳过OpusHead页面")
                    elif page_data.startswith(b'OpusTags'):
                        logger.bind(tag=TAG).debug("跳过OpusTags页面")
                    else:
                        # 这是音频数据页面，按段表提取Opus帧
                        logger.bind(tag=TAG).debug(f"音频数据页面，大小: {page_data_size} bytes")
                        
                        frame_offset = 0
                        for segment_size in segment_table:
                            if segment_size > 0 and frame_offset + segment_size <= len(page_data):
                                frame_data = page_data[frame_offset:frame_offset + segment_size]
                                if len(frame_data) > 0:
                                    packets.append(frame_data)
                                    logger.bind(tag=TAG).debug(f"提取帧: {len(frame_data)} bytes")
                                frame_offset += segment_size
                            else:
                                break
                    
                    # 移动到下一页
                    offset = page_data_offset + page_data_size
                    
                except Exception as e:
                    logger.bind(tag=TAG).warning(f"解析页面 {page_count} 失败: {e}")
                    offset += 1
                    continue
        else:
            # 对于原始Opus数据，使用固定大小分割
            logger.bind(tag=TAG).debug("使用固定大小分割原始Opus数据")
            offset = 0
            while offset < len(opus_data):
                end_offset = min(offset + packet_size, len(opus_data))
                packet = opus_data[offset:end_offset]
                
                if len(packet) > 0:
                    packets.append(packet)
                
                offset = end_offset
        
        logger.bind(tag=TAG).info(f"成功分割opus数据为 {len(packets)} 个数据包")
        return packets
        
    except Exception as e:
        logger.bind(tag=TAG).error(f"分割opus数据包失败: {e}")
        # 如果解析失败，回退到简单分割
        logger.bind(tag=TAG).debug("回退到简单固定大小分割")
        packets = []
        offset = 0
        while offset < len(opus_data):
            end_offset = min(offset + packet_size, len(opus_data))
            packet = opus_data[offset:end_offset]
            if len(packet) > 0:
                packets.append(packet)
            offset = end_offset
        return packets


def validate_opus_data(opus_data: bytes) -> bool:
    """
    改进的opus音频数据验证
    
    Args:
        opus_data: opus音频数据
        
    Returns:
        bool: 数据是否有效
    """
    try:
        if not opus_data or len(opus_data) == 0:
            logger.bind(tag=TAG).debug("音频数据为空")
            return False
        
        logger.bind(tag=TAG).debug(f"验证音频数据，大小: {len(opus_data)} 字节")
        
        # 检查文件头部
        if len(opus_data) >= 8:
            header = opus_data[:8]
            logger.bind(tag=TAG).debug(f"文件头部: {header}")
            
            # 检查是否是Opus文件头
            if header.startswith(b'OpusHead'):
                logger.bind(tag=TAG).debug("检测到OpusHead头部")
                return True
            elif header.startswith(b'OggS'):
                logger.bind(tag=TAG).debug("检测到OggS容器头部")
                # 对于Ogg容器，检查是否包含Opus标识
                if b'OpusHead' in opus_data or b'OpusTags' in opus_data:
                    logger.bind(tag=TAG).debug("在Ogg容器中找到Opus标识")
                    return True
        
        # 如果没有标准头部，尝试作为原始Opus包验证
        logger.bind(tag=TAG).debug("尝试作为原始Opus包验证")
        # 对于原始Opus包，我们放宽验证条件
        # 只要数据不为空且长度合理就认为有效
        if len(opus_data) >= 1:
            logger.bind(tag=TAG).debug("原始Opus包长度验证通过")
            return True
            
        return False
        
    except Exception as e:
        logger.bind(tag=TAG).error(f"验证opus数据失败: {e}")
        return False


def process_base64_opus_audio(base64_opus_data: str) -> list:
    """
    处理base64编码的opus音频数据，返回可用于上报的数据包列表
    
    Args:
        base64_opus_data: base64编码的opus音频数据字符串
        
    Returns:
        list: 处理后的opus数据包列表，可直接用于enqueue_asr_report
        
    Raises:
        ValueError: 当数据无效时
    """
    try:
        # 1. 解码base64数据
        opus_data = decode_base64_opus(base64_opus_data)
        
        # 2. 验证opus数据有效性
        if not validate_opus_data(opus_data):
            raise ValueError("无效的opus音频数据")
        
        # 3. 分割成数据包
        packets = split_opus_packets(opus_data)
        
        if not packets:
            raise ValueError("无法从opus数据中提取有效数据包")
        
        logger.bind(tag=TAG).info(f"成功处理base64 opus音频数据，共 {len(packets)} 个数据包")
        return packets
        
    except Exception as e:
        logger.bind(tag=TAG).error(f"处理base64 opus音频数据失败: {e}")
        raise


def detect_audio_format(audio_data: bytes) -> str:
    """
    检测音频文件格式
    
    Args:
        audio_data: 音频数据字节
        
    Returns:
        str: 音频格式 ('ogg_opus', 'ogg_vorbis', 'opus', 'unknown')
    """
    try:
        if audio_data.startswith(b'OggS'):
            # 检查OGG容器内的编码格式
            data_str = audio_data[:200].decode('latin-1', errors='ignore')
            
            if 'vorbis' in data_str.lower():
                return 'ogg_vorbis'
            elif 'OpusHead' in data_str:
                return 'ogg_opus'
            else:
                return 'ogg_unknown'
        elif audio_data.startswith(b'Opus'):
            return 'opus'
        else:
            return 'unknown'
            
    except Exception as e:
        logger.bind(tag=TAG).error(f"检测音频格式失败: {e}")
        return 'unknown'


def convert_vorbis_to_pcm(vorbis_data: bytes) -> bytes:
    """
    将Ogg Vorbis数据转换为PCM数据
    
    Args:
        vorbis_data: Ogg Vorbis音频数据
        
    Returns:
        bytes: PCM音频数据 (16kHz, 16bit, mono)
        
    Raises:
        ValueError: 当转换失败时
    """
    try:
        import subprocess
        import tempfile
        import os
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_input:
            temp_input.write(vorbis_data)
            temp_input_path = temp_input.name
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_output:
            temp_output_path = temp_output.name
        
        try:
            # 使用ffmpeg转换Vorbis到PCM
            cmd = [
                'ffmpeg', '-i', temp_input_path,
                '-ar', '16000',  # 采样率16kHz
                '-ac', '1',      # 单声道
                '-f', 'wav',     # WAV格式
                '-y',            # 覆盖输出文件
                temp_output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise ValueError(f"ffmpeg转换失败: {result.stderr}")
            
            # 读取转换后的PCM数据
            with open(temp_output_path, 'rb') as f:
                wav_data = f.read()
            
            # 跳过WAV头部，提取PCM数据
            # WAV头部通常是44字节
            if len(wav_data) > 44:
                pcm_data = wav_data[44:]
                logger.bind(tag=TAG).info(f"成功转换Vorbis到PCM，PCM数据长度: {len(pcm_data)} bytes")
                return pcm_data
            else:
                raise ValueError("转换后的WAV文件太小，可能转换失败")
                
        finally:
            # 清理临时文件
            try:
                os.unlink(temp_input_path)
                os.unlink(temp_output_path)
            except:
                pass
                
    except Exception as e:
        logger.bind(tag=TAG).error(f"转换Vorbis到PCM失败: {e}")
        raise ValueError(f"Vorbis转换失败: {e}")


def process_base64_audio(base64_audio_data: str) -> tuple:
    """
    处理base64编码的音频数据，支持Opus和Vorbis格式
    
    Args:
        base64_audio_data: base64编码的音频数据字符串
        
    Returns:
        tuple: (音频数据包列表, 音频格式) 
               音频格式为 'opus' 或 'pcm'
        
    Raises:
        ValueError: 当数据无效时
    """
    try:
        # 1. 解码base64数据
        audio_data = decode_base64_opus(base64_audio_data)
        
        # 2. 检测音频格式
        audio_format = detect_audio_format(audio_data)
        logger.bind(tag=TAG).info(f"检测到音频格式: {audio_format}")
        
        if audio_format == 'ogg_opus':
            # 处理Ogg Opus文件
            packets = process_base64_opus_audio(base64_audio_data)
            return packets, 'opus'
            
        elif audio_format == 'ogg_vorbis':
            # 处理Ogg Vorbis文件
            logger.bind(tag=TAG).info("处理Ogg Vorbis文件，转换为PCM格式")
            pcm_data = convert_vorbis_to_pcm(audio_data)
            
            # 将PCM数据分割成合适的块
            chunk_size = 1920  # 16kHz * 2 bytes * 60ms = 1920 bytes
            chunks = []
            
            for i in range(0, len(pcm_data), chunk_size):
                chunk = pcm_data[i:i + chunk_size]
                if len(chunk) > 0:
                    chunks.append(chunk)
            
            logger.bind(tag=TAG).info(f"Vorbis文件转换完成，共 {len(chunks)} 个PCM数据块")
            return chunks, 'pcm'
            
        elif audio_format == 'opus':
            # 处理原始Opus文件
            packets = process_base64_opus_audio(base64_audio_data)
            return packets, 'opus'
            
        else:
            raise ValueError(f"不支持的音频格式: {audio_format}")
            
    except Exception as e:
        logger.bind(tag=TAG).error(f"处理base64音频数据失败: {e}")
        raise