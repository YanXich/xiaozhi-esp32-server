#!/usr/bin/env python3
import sys
from pathlib import Path
import ffmpeg


def convert_mp3_to_ogg(input_file: Path, output_file: Path) -> bool:
    try:
        print(f"正在转换: {input_file} -> {output_file}")
        (
            ffmpeg
            .input(str(input_file))
            .output(
                str(output_file),
                acodec='opus',        # 正确的编码器名称
                audio_bitrate='16k',  # 码率与handler一致
                ac=1,                 # 单声道
                ar=48000,             # opus编码器支持的采样率
                strict=-2             # 允许实验性编码器
            )
            .run(overwrite_output=True)
        )
        print(f"转换成功: {output_file}")
        return True
    except ffmpeg.Error as e:
        print(f"转换失败 {input_file}: ffmpeg error\n{e}")
        return False
    except Exception as e:
        print(f"转换失败 {input_file}: {e}")
        return False


def main():
    # 基础目录：传参优先，否则使用脚本所在目录
    base_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).parent.resolve()
    print(f"工作目录: {base_dir}")
    if not base_dir.exists():
        print("错误: 目录不存在")
        sys.exit(1)

    mp3_files = sorted(base_dir.glob("*.mp3"))
    if not mp3_files:
        print("未找到MP3文件。目录列表:")
        for p in sorted(base_dir.iterdir()):
            print(" -", p.name)
        sys.exit(0)

    success, failed = 0, 0
    for mp3 in mp3_files:
        ogg = mp3.with_suffix(".ogg")
        # 如果已存在且非空则跳过
        if ogg.exists() and ogg.stat().st_size > 0:
            print(f"已存在且非空，跳过: {ogg}")
            success += 1
            continue

        if convert_mp3_to_ogg(mp3, ogg):
            success += 1
        else:
            failed += 1

    print("\n转换完成!")
    print(f"成功: {success} 个文件")
    print(f"失败: {failed} 个文件")

    print("\n生成的OGG文件:")
    for ogg in sorted(base_dir.glob("*.ogg")):
        print(f"  - {ogg.name}")


if __name__ == "__main__":
    main()