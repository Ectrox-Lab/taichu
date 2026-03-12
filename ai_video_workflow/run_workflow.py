#!/usr/bin/env python3
"""
AI视频生成工作流 - 主控脚本
一键执行完整的短剧生成流程

用法:
  python run_workflow.py --episode 1          # 生成第一集
  python run_workflow.py --episode 2 --skip-gen  # 跳过生成，只做后期
  python run_workflow.py --config custom.yaml  # 使用自定义配置
"""

import os
import sys
import yaml
import json
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f'./logs/workflow_{datetime.now():%Y%m%d_%H%M%S}.log')
    ]
)
logger = logging.getLogger(__name__)


class WorkflowManager:
    """工作流管理器"""
    
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.project_name = self.config['project']['name']
        self.episode = self.config['project']['episode']
        
        # 脚本路径
        self.scripts_dir = Path(__file__).parent / 'scripts'
        
        logger.info("=" * 70)
        logger.info(f"🎬 AI视频生成工作流")
        logger.info(f"项目: {self.project_name}")
        logger.info(f"集数: 第{self.episode}集")
        logger.info("=" * 70)
    
    def run_step(self, step_name: str, script_name: str, args: list = None) -> bool:
        """执行单个步骤"""
        script_path = self.scripts_dir / script_name
        
        if not script_path.exists():
            logger.error(f"脚本不存在: {script_path}")
            return False
        
        cmd = ['python', str(script_path), '--config', str(self.config_path)]
        if args:
            cmd.extend(args)
        
        logger.info("")
        logger.info(f"▶ 步骤: {step_name}")
        logger.info(f"  命令: {' '.join(cmd)}")
        logger.info("-" * 70)
        
        start_time = datetime.now()
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=False,
                text=True,
                check=True
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"✓ {step_name} 完成 (耗时: {duration:.1f}s)")
            return True
            
        except subprocess.CalledProcessError as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"✗ {step_name} 失败 (耗时: {duration:.1f}s)")
            logger.error(f"  返回码: {e.returncode}")
            return False
        
        except Exception as e:
            logger.error(f"✗ {step_name} 异常: {e}")
            return False
    
    def run_full_workflow(self, skip_gen: bool = False, skip_audio: bool = False,
                         skip_post: bool = False) -> bool:
        """运行完整工作流"""
        results = {}
        
        # 步骤1: 视频生成 (4卡并行)
        if not skip_gen:
            results['generation'] = self.run_step(
                "视频生成 (4卡并行)",
                "01_generate_videos.py"
            )
            if not results['generation']:
                logger.error("视频生成失败，停止工作流")
                return False
        else:
            logger.info("⏭ 跳过视频生成")
            results['generation'] = True
        
        # 步骤2: 配音生成
        if not skip_audio:
            results['audio'] = self.run_step(
                "中文配音生成",
                "02_generate_audio.py"
            )
        else:
            logger.info("⏭ 跳过配音生成")
            results['audio'] = True
        
        # 步骤3: 后期制作
        if not skip_post:
            results['post'] = self.run_step(
                "后期制作 (字幕+拼接+导出)",
                "03_post_production.py"
            )
        else:
            logger.info("⏭ 跳过后期制作")
            results['post'] = True
        
        # 汇总
        logger.info("")
        logger.info("=" * 70)
        logger.info("工作流执行结果")
        logger.info("=" * 70)
        
        all_success = all(results.values())
        
        for step, success in results.items():
            status = "✓ 成功" if success else "✗ 失败"
            logger.info(f"  {step:15s} {status}")
        
        if all_success:
            logger.info("")
            logger.info("🎉 所有步骤完成!")
            logger.info(f"输出目录: {self.config['project']['output_dir']}")
        else:
            logger.error("")
            logger.error("❌ 工作流执行失败")
        
        logger.info("=" * 70)
        
        return all_success
    
    def create_episode_config(self, episode_num: int, template: dict = None) -> Path:
        """创建新集数的配置文件"""
        if template is None:
            template = self.config
        
        new_config = template.copy()
        new_config['project']['episode'] = episode_num
        new_config['project']['name'] = f"末日重生第{episode_num}集"
        new_config['project']['output_dir'] = f"./output/ep{episode_num}"
        
        # 根据集数调整场景（示例）
        # 这里可以根据模板自动生成新集数的场景
        
        output_path = Path(f'./config/ep{episode_num}.yaml')
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(new_config, f, allow_unicode=True, sort_keys=False)
        
        logger.info(f"已创建新集数配置: {output_path}")
        return output_path


def print_usage_examples():
    """打印使用示例"""
    examples = """
使用示例:
    
  1. 生成完整剧集:
     python run_workflow.py --episode 1
    
  2. 使用自定义配置:
     python run_workflow.py --config ./config/my_drama.yaml
    
  3. 跳过视频生成（只做后期）:
     python run_workflow.py --episode 1 --skip-gen
    
  4. 只生成视频（跳过后期）:
     python run_workflow.py --episode 1 --skip-post
    
  5. 创建新剧集模板:
     python run_workflow.py --create-episode 2
    
  6. 查看配置信息:
     python run_workflow.py --episode 1 --dry-run
"""
    print(examples)


def main():
    parser = argparse.ArgumentParser(
        description='AI视频生成工作流 - 一键生成短剧',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run_workflow.py --episode 1                    # 生成第1集
  python run_workflow.py --config custom.yaml          # 使用自定义配置
  python run_workflow.py --episode 1 --skip-gen        # 跳过生成只做后期
        """
    )
    
    parser.add_argument('--episode', '-e', type=int,
                       help='指定剧集编号 (1, 2, 3...)')
    parser.add_argument('--config', '-c', type=str,
                       help='配置文件路径')
    parser.add_argument('--skip-gen', action='store_true',
                       help='跳过视频生成')
    parser.add_argument('--skip-audio', action='store_true',
                       help='跳过配音生成')
    parser.add_argument('--skip-post', action='store_true',
                       help='跳过后期制作')
    parser.add_argument('--create-episode', type=int,
                       help='创建新集数的配置文件')
    parser.add_argument('--dry-run', action='store_true',
                       help='干运行（不实际执行）')
    parser.add_argument('--examples', action='store_true',
                       help='显示使用示例')
    
    args = parser.parse_args()
    
    if args.examples:
        print_usage_examples()
        return
    
    # 确定配置文件路径
    if args.config:
        config_path = args.config
    elif args.episode:
        config_path = f'./config/ep{args.episode}.yaml'
    else:
        config_path = './config/workflow.yaml'
    
    # 检查配置文件
    if not Path(config_path).exists():
        # 尝试使用默认模板
        if Path('./config/workflow.yaml').exists():
            logger.warning(f"配置文件不存在: {config_path}")
            logger.info("使用默认配置: ./config/workflow.yaml")
            config_path = './config/workflow.yaml'
        else:
            logger.error(f"配置文件不存在: {config_path}")
            logger.error("请创建配置文件或使用 --episode 参数")
            sys.exit(1)
    
    # 创建新集数
    if args.create_episode:
        manager = WorkflowManager(config_path)
        new_config = manager.create_episode_config(args.create_episode)
        logger.info(f"已创建第 {args.create_episode} 集配置文件")
        logger.info(f"请编辑配置文件: {new_config}")
        return
    
    # 干运行
    if args.dry_run:
        logger.info(f"干运行模式 - 读取配置: {config_path}")
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        logger.info(f"项目: {config['project']['name']}")
        logger.info(f"场景: {len(config.get('scenes', []))} 个")
        logger.info(f"角色: {len(config.get('characters', {}))} 个")
        return
    
    # 运行工作流
    try:
        manager = WorkflowManager(config_path)
        success = manager.run_full_workflow(
            skip_gen=args.skip_gen,
            skip_audio=args.skip_audio,
            skip_post=args.skip_post
        )
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"工作流异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
