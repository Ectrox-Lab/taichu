# AI视频生成工作流模板

一套完整的、可复用的AI短剧视频生成工作流，基于LTX Video + 4卡并行 + 专业后期。

## ✨ 特性

- **4卡并行生成**：同时利用4张RTX 4090，6分钟生成2分钟视频
- **华人角色优化**：针对中国短剧市场优化的提示词模板
- **完整后期流程**：自动生成配音、字幕、音效、转场
- **合规声明**：自动添加AI生成声明和虚构声明
- **可复用模板**：一次配置，多集复用

## 📁 目录结构

```
ai_video_workflow/
├── config/
│   └── workflow.yaml          # 主配置文件
├── scripts/
│   ├── 01_generate_videos.py  # 4卡并行生成
│   ├── 02_generate_audio.py   # 中文配音
│   └── 03_post_production.py  # 后期制作
├── templates/
│   └── prompts/               # 提示词模板
├── assets/
│   ├── audio/                 # BGM、音效
│   ├── fonts/                 # 字幕字体
│   └── overlays/              # 叠加层素材
├── output/                    # 输出目录
├── logs/                      # 日志文件
└── run_workflow.py           # 主控脚本
```

## 🚀 快速开始

### 1. 环境准备

```bash
# 安装依赖
pip install pyyaml edge-tts moviepy

# 确保LTX Video已配置
ls /data/LTX-2.3/
# 应该包含: ltx-2.3-22b-distilled.safetensors 等
```

### 2. 运行工作流

```bash
cd /home/admin/ai_video_workflow

# 生成完整剧集
python run_workflow.py --episode 1

# 或使用自定义配置
python run_workflow.py --config ./config/my_drama.yaml
```

### 3. 查看输出

```bash
ls -la ./output/ep1/final/
# 包含:
#   - ep1_01_场景名.mp4    (各场景视频)
#   - concatenated.mp4      (拼接后的视频)
#   - final.mp4            (最终成品)
```

## 📝 配置说明

### 配置文件结构

```yaml
project:
  name: "末日重生第一集"      # 剧集名称
  episode: 1                   # 集数
  output_dir: "./output/ep1"   # 输出目录

generation:
  model:
    type: "distilled"          # 模型类型
    checkpoint: "/data/LTX-2.3/ltx-2.3-22b-distilled.safetensors"
  
  params:
    resolution:
      width: 768               # 生成分辨率
      height: 512
    fps: 24
    frames_per_scene: 721      # 30秒/场景
    quantization: "fp8-cast"   # FP8量化

characters:
  protagonist:
    name: "李明"
    desc: "20岁华人男性..."
    outfit_modern: "蓝白校服"

scenes:
  - id: "scene1"
    title: "末日开场"
    duration: 30
    style: "末日动作"
    prompt: |
      Chinese short drama style...

dialogues:
  scene1:
    - time: 2
      character: "母亲"
      text: "儿子，妈拼死送你去高考考场"
      emotion: "urgent"

tts:
  provider: "edge"
  voices:
    旁白:
      voice: "zh-CN-YunxiNeural"
```

### 场景风格词

| 风格 | 效果 |
|-----|------|
| 末日动作 | action-packed, dynamic movement |
| 恐怖惊悚 | horror atmosphere, dramatic lighting |
| 阴暗戏剧 | dark moody lighting, dramatic tension |
| 希望明亮 | bright hopeful lighting, emotional |

## 🎬 使用流程

### 创建新剧

```bash
# 1. 创建配置文件
python run_workflow.py --create-episode 2

# 2. 编辑配置文件
vim ./config/ep2.yaml
# 修改: 场景描述、对话、角色等

# 3. 生成
python run_workflow.py --episode 2
```

### 分步执行

```bash
# 只生成视频（4卡并行）
python run_workflow.py --episode 1 --skip-audio --skip-post

# 只生成配音
python run_workflow.py --episode 1 --skip-gen --skip-post

# 只做后期
python run_workflow.py --episode 1 --skip-gen --skip-audio
```

### 单场景调试

```bash
# 只生成场景1，使用GPU 0
python scripts/01_generate_videos.py --scene scene1 --gpu 0

# 只生成场景1的配音
python scripts/02_generate_audio.py --scene scene1
```

## 🔧 高级配置

### 自定义提示词模板

在 `scenes[].prompt` 中使用变量:

```yaml
prompt: |
  Chinese short drama style, {{ protagonist.desc }},
  wearing {{ protagonist.outfit_modern }},
  in {{ location }}, {{ mood }}
```

### 音效配置

```yaml
audio:
  sound_effects:
    scene1:
      - type: "engine"
        file: "boat_engine.mp3"
      - type: "water"
        file: "waves.mp3"
```

### 字幕样式

```yaml
subtitles:
  style:
    font: "NotoSansCJK-Bold.otf"
    size: 36
    color: "white"
    stroke_color: "black"
    stroke_width: 2
```

## 📊 性能指标

| 配置 | 时间 | 产出 |
|-----|------|------|
| 4卡并行 × 30秒 | ~6分钟 | 2分钟视频 |
| 单卡串行 × 30秒 | ~24分钟 | 2分钟视频 |
| 4卡并行 × 60秒 | ~12分钟 | 4分钟视频 |

## 🐛 故障排除

### OOM错误

```bash
# 降低分辨率
params:
  resolution:
    width: 512
    height: 384

# 或减少帧数
frames_per_scene: 481  # 20秒
```

### 生成失败

```bash
# 检查日志
tail -f ./logs/generation.log

# 单场景调试
python scripts/01_generate_videos.py --scene scene1 --gpu 0
```

### 字幕不显示

确保系统安装了中文字体:
```bash
# Ubuntu
sudo apt-get install fonts-noto-cjk
```

## 📝 提示词最佳实践

### 成功的提示词结构

```
Chinese short drama style,      # 风格声明
[角色描述],                      # 详细外貌+服装
[动作/姿态],                     # 动态描述
[环境场景],                      # 中国本土化环境
[灯光氛围],                      # 情绪照明
[质量指令]                       # 4K, cinematic
```

### 示例

```yaml
prompt: |
  Chinese short drama style, post-apocalyptic flooded city scene.
  A determined Chinese mother in her 40s with black hair tied back,
  wearing simple grey shirt, drives a speedboat through submerged
  Chinese city streets with typical Chinese buildings and signboards.
  Behind them, a giant Titanoboa snake emerges from the water.
  Her 20-year-old son in blue and white Chinese school uniform
  reads a Python programming book. Dramatic sunset golden hour lighting,
  waves splashing, cinematic action scene, 4K quality.
```

## 📄 许可证

本工作流模板仅供学习和研究使用。

生成的视频请遵守:
- 标注"AI生成"声明
- 标注"本故事纯属虚构"
- 遵守平台内容规范
