#!/usr/bin/env python3
"""
AI视频生成脚本 - 4卡并行版
这是可复用的工作流模板
"""

import os
import sys
import yaml
import json
import subprocess
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('./logs/generation.log')
    ]
)
logger = logging.getLogger(__name__)


class VideoGenerator:
    """视频生成器 - 管理4卡并行生成"""
    
    def __init__(self, config_path: str):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.output_dir = Path(self.config['project']['output_dir'])
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # LTX模型路径
        self.model_path = self.config['generation']['model']['checkpoint']
        self.upsampler_path = self.config['generation']['model']['upsampler']
        self.gemma_root = self.config['generation']['model']['gemma_root']
        
        logger.info(f"初始化视频生成器: {self.config['project']['name']}")
    
    def build_prompt(self, scene: dict, characters: dict) -> str:
        """构建优化的提示词"""
        # 使用场景定义的基础提示词
        base_prompt = scene['prompt'].strip()
        
        # 添加质量增强词
        quality_suffix = (
            "Chinese short drama aesthetic, professional cinematography, "
            "stable composition, high quality, 4K resolution"
        )
        
        # 添加风格控制
        style_words = {
            "末日动作": "action-packed, dynamic movement, intense",
            "恐怖惊悚": "horror atmosphere, dramatic lighting, suspense",
            "阴暗戏剧": "dark moody lighting, dramatic tension",
            "希望明亮": "bright hopeful lighting, emotional"
        }
        
        style = scene.get('style', '')
        if style in style_words:
            base_prompt += f", {style_words[style]}"
        
        full_prompt = f"{base_prompt}, {quality_suffix}"
        return full_prompt
    
    def generate_scene(self, scene_id: str, gpu_id: int) -> dict:
        """在指定GPU上生成单个场景"""
        scene = next(s for s in self.config['scenes'] if s['id'] == scene_id)
        
        # 构建输出路径
        output_path = self.output_dir / f"{scene_id}_{scene['title']}.mp4"
        
        # 构建提示词
        prompt = self.build_prompt(scene, self.config['characters'])
        
        # 计算种子
        seed = self.config['generation']['params']['seed_base'] + int(scene_id[-1])
        
        # 使用LTX虚拟环境的Python
        ltx_python = '/home/admin/hf_models/LTX-2/.venv/bin/python'
        
        # 构建命令
        cmd = [
            ltx_python, '-m', 'ltx_pipelines.distilled',
            '--distilled-checkpoint-path', self.model_path,
            '--spatial-upsampler-path', self.upsampler_path,
            '--gemma-root', self.gemma_root,
            '--prompt', prompt,
            '--seed', str(seed),
            '--height', str(self.config['generation']['params']['resolution']['height']),
            '--width', str(self.config['generation']['params']['resolution']['width']),
            '--num-frames', str(self.config['generation']['params']['frames_per_scene']),
            '--frame-rate', str(self.config['generation']['params']['fps']),
            '--output-path', str(output_path),
            '--quantization', self.config['generation']['params']['quantization']
        ]
        
        # 设置环境变量
        env = os.environ.copy()
        env['CUDA_VISIBLE_DEVICES'] = str(gpu_id)
        env['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True,max_split_size_mb:512'
        
        logger.info(f"[GPU {gpu_id}] 开始生成 {scene_id}: {scene['title']}")
        logger.info(f"[GPU {gpu_id}] 提示词: {prompt[:100]}...")
        
        # 执行生成
        start_time = datetime.now()
        
        try:
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=900  # 15分钟超时
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            
            if result.returncode == 0 and output_path.exists():
                file_size = output_path.stat().st_size / (1024 * 1024)
                logger.info(f"[GPU {gpu_id}] ✓ {scene_id} 完成! 耗时: {duration:.1f}s, 大小: {file_size:.1f}MB")
                return {
                    'scene_id': scene_id,
                    'status': 'success',
                    'output': str(output_path),
                    'duration': duration,
                    'size_mb': file_size
                }
            else:
                logger.error(f"[GPU {gpu_id}] ✗ {scene_id} 失败: {result.stderr[:500]}")
                return {
                    'scene_id': scene_id,
                    'status': 'failed',
                    'error': result.stderr[:1000]
                }
                
        except subprocess.TimeoutExpired:
            logger.error(f"[GPU {gpu_id}] ✗ {scene_id} 超时!")
            return {
                'scene_id': scene_id,
                'status': 'timeout',
                'error': 'Generation timeout after 15 minutes'
            }
        except Exception as e:
            logger.error(f"[GPU {gpu_id}] ✗ {scene_id} 异常: {str(e)}")
            return {
                'scene_id': scene_id,
                'status': 'error',
                'error': str(e)
            }
    
    def run_parallel(self):
        """并行运行4卡生成"""
        scenes = self.config['scenes']
        gpu_mapping = self.config['generation']['parallel']['gpu_mapping']
        
        logger.info("=" * 60)
        logger.info(f"开始4卡并行生成: {self.config['project']['name']}")
        logger.info(f"共 {len(scenes)} 个场景")
        logger.info("=" * 60)
        
        # 创建任务列表
        tasks = []
        for scene in scenes:
            scene_id = scene['id']
            gpu_id = gpu_mapping.get(scene_id, 0)
            tasks.append((scene_id, gpu_id))
        
        # 并行执行
        results = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_scene = {
                executor.submit(self.generate_scene, scene_id, gpu_id): (scene_id, gpu_id)
                for scene_id, gpu_id in tasks
            }
            
            for future in as_completed(future_to_scene):
                scene_id, gpu_id = future_to_scene[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"[GPU {gpu_id}] {scene_id} 执行异常: {e}")
                    results.append({
                        'scene_id': scene_id,
                        'status': 'error',
                        'error': str(e)
                    })
        
        # 汇总结果
        logger.info("=" * 60)
        logger.info("生成结果汇总:")
        success_count = sum(1 for r in results if r.get('status') == 'success')
        logger.info(f"成功: {success_count}/{len(scenes)}")
        
        for r in results:
            status_icon = "✓" if r.get('status') == 'success' else "✗"
            logger.info(f"  {status_icon} {r['scene_id']}: {r.get('status')}")
        
        # 保存结果报告
        report_path = self.output_dir / 'generation_report.json'
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"报告已保存: {report_path}")
        
        return results


def main():
    parser = argparse.ArgumentParser(description='AI视频生成工作流 - 4卡并行版')
    parser.add_argument('--config', '-c', default='./config/workflow.yaml',
                       help='配置文件路径')
    parser.add_argument('--scene', '-s', type=str,
                       help='只生成指定场景 (scene1/scene2/scene3/scene4)')
    parser.add_argument('--gpu', '-g', type=int, default=0,
                       help='指定GPU ID (0-3)')
    
    args = parser.parse_args()
    
    generator = VideoGenerator(args.config)
    
    if args.scene:
        # 单场景生成模式
        result = generator.generate_scene(args.scene, args.gpu)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        # 完整并行生成模式
        results = generator.run_parallel()
        sys.exit(0 if all(r.get('status') == 'success' for r in results) else 1)


if __name__ == '__main__':
    main()
