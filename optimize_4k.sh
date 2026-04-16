#!/bin/bash

# 检查是否提供了输入文件
if [ -z "$1" ]; then
    echo "用法: $0 <输入视频文件>"
    echo "示例: $0 my_video.mp4"
    exit 1
fi

INPUT_FILE="$1"

# 检查文件是否存在
if [ ! -f "$INPUT_FILE" ]; then
    echo "错误: 找不到文件 '$INPUT_FILE'"
    exit 1
fi

# 检查是否安装了 ffmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "错误: 未安装 ffmpeg。请先安装它 (例如: sudo apt install ffmpeg)"
    exit 1
fi

# 提取文件名和扩展名
FILENAME=$(basename -- "$INPUT_FILE")
EXTENSION="${FILENAME##*.}"
BASENAME="${FILENAME%.*}"

# 提取目录路径
DIRNAME=$(dirname -- "$INPUT_FILE")

# 定义输出文件名
OUTPUT_FILE="${DIRNAME}/${BASENAME}_web_optimized.mp4"

echo "=================================================="
echo "开始优化视频，用于 Web 端流畅播放 (保持 4K, 降低码率, 开启 faststart)"
echo "输入文件: $INPUT_FILE"
echo "输出文件: $OUTPUT_FILE"
echo "=================================================="

# 执行 ffmpeg 优化命令
ffmpeg -i "$INPUT_FILE" \
  -c:v libx264 \
  -crf 28 \
  -preset fast \
  -pix_fmt yuv420p \
  -movflags +faststart \
  -c:a copy \
  "$OUTPUT_FILE"

echo "=================================================="
if [ $? -eq 0 ]; then
    echo "✅ 优化完成！文件已保存为: $OUTPUT_FILE"
    echo "你可以用这个优化后的视频替换原视频加载到服务中。"
else
    echo "❌ 优化过程中发生错误。"
fi
