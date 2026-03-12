#!/bin/bash
# AI视频生成工作流 - 快速启动脚本
# 用法: ./quickstart.sh [episode_number]

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 默认值
EPISODE=${1:-1}
CONFIG_FILE="./config/ep${EPISODE}.yaml"

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║           AI视频生成工作流 - 快速启动                      ║"
echo "║                                                            ║"
echo "║  4卡并行 · 华人角色 · 专业后期 · 一键生成                  ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# 检查环境
echo -e "${YELLOW}▶ 检查环境...${NC}"

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python3 未安装${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python3 已安装${NC}"

# 检查CUDA
if ! command -v nvidia-smi &> /dev/null; then
    echo -e "${RED}✗ NVIDIA驱动未安装${NC}"
    exit 1
fi

GPU_COUNT=$(nvidia-smi --query-gpu=name --format=csv,noheader | wc -l)
echo -e "${GREEN}✓ 检测到 ${GPU_COUNT} 张GPU${NC}"

# 检查LTX模型
if [ ! -f "/data/LTX-2.3/ltx-2.3-22b-distilled.safetensors" ]; then
    echo -e "${RED}✗ LTX模型未找到${NC}"
    exit 1
fi
echo -e "${GREEN}✓ LTX模型已就绪${NC}"

# 检查配置文件
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${YELLOW}! 配置文件不存在: $CONFIG_FILE${NC}"
    echo -e "${YELLOW}  使用默认配置...${NC}"
    CONFIG_FILE="./config/workflow.yaml"
    
    if [ ! -f "$CONFIG_FILE" ]; then
        echo -e "${RED}✗ 默认配置也不存在${NC}"
        exit 1
    fi
fi
echo -e "${GREEN}✓ 配置文件: $CONFIG_FILE${NC}"

# 创建必要目录
mkdir -p ./logs ./output ./assets/audio ./assets/fonts

echo ""
echo -e "${YELLOW}▶ 开始生成第 ${EPISODE} 集...${NC}"
echo ""

# 运行工作流
python3 run_workflow.py --config "$CONFIG_FILE"

# 检查结果
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}"
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                    ✓ 生成完成！                            ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    OUTPUT_DIR="./output/ep${EPISODE}/final"
    if [ -d "$OUTPUT_DIR" ]; then
        echo -e "${BLUE}输出文件:${NC}"
        ls -lh "$OUTPUT_DIR"/*.mp4 2>/dev/null || true
    fi
else
    echo ""
    echo -e "${RED}"
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                    ✗ 生成失败                              ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo -e "${YELLOW}查看日志: tail -f ./logs/*.log${NC}"
    exit 1
fi
