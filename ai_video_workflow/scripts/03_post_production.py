#!/usr/bin/env python3
"""
后期制作脚本 - 字幕烧录 + 视频拼接 + 音效合成
使用MoviePy + FFmpeg
"""

import os
import sys
import yaml
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 尝试导入moviepy
try:
    from moviepy.editor import (
        VideoFileClip, AudioFileClip, CompositeAudioClip,
        concatenate_videoclips, CompositeVideoClip, TextClip
    )
    from moviepy.video.fx.all import fadein, fadeout
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False
    logger.warning("MoviePy未安装，将使用FFmpeg命令行模式")


class PostProduction:
    """后期制作处理器"""
    
    def __init__(self, config_path: str):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.project_dir = Path(self.config['project']['output_dir'])
        self.video_dir = self.project_dir
        self.audio_dir = self.project_dir / 'audio'
        self.final_output = self.project_dir / 'final'
        self.final_output.mkdir(exist_ok=True)
        
        self.subtitle_config = self.config.get('subtitles', {})
        self.post_config = self.config.get('post_processing', {})
        
        logger.info(f"初始化后期制作: {self.config['project']['name']}")
    
    def get_scene_videos(self) -> List[Path]:
        """获取所有场景视频文件"""
        scenes = self.config.get('scenes', [])
        video_files = []
        
        for scene in scenes:
            scene_id = scene['id']
            video_file = self.video_dir / f"{scene_id}_{scene['title']}.mp4"
            if video_file.exists():
                video_files.append({
                    'path': video_file,
                    'id': scene_id,
                    'title': scene['title'],
                    'style': scene.get('style', '')
                })
            else:
                logger.warning(f"视频文件不存在: {video_file}")
        
        return video_files
    
    def generate_subtitle_srt(self, scene_id: str, dialogues: List[dict]) -> Path:
        """生成SRT字幕文件"""
        srt_path = self.final_output / f"{scene_id}_subtitles.srt"
        
        with open(srt_path, 'w', encoding='utf-8') as f:
            for i, dialogue in enumerate(dialogues, 1):
                start_time = dialogue.get('time', 0)
                # 假设每句话持续3-5秒
                duration = 3 + len(dialogue['text']) / 5
                end_time = start_time + duration
                
                # 转换为SRT时间格式
                def to_srt_time(seconds):
                    hours = int(seconds // 3600)
                    minutes = int((seconds % 3600) // 60)
                    secs = int(seconds % 60)
                    ms = int((seconds % 1) * 1000)
                    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"
                
                f.write(f"{i}\n")
                f.write(f"{to_srt_time(start_time)} --> {to_srt_time(end_time)}\n")
                f.write(f"{dialogue['character']}: {dialogue['text']}\n\n")
        
        return srt_path
    
    def add_subtitles_ffmpeg(self, video_path: Path, srt_path: Path, 
                            output_path: Path) -> bool:
        """使用FFmpeg添加字幕"""
        # 字幕样式
        style = self.subtitle_config.get('style', {})
        font_size = style.get('size', 36)
        font_color = style.get('color', 'white')
        stroke_color = style.get('stroke_color', 'black')
        stroke_width = style.get('stroke_width', 2)
        
        # 构建FFmpeg命令
        cmd = [
            'ffmpeg', '-y',
            '-i', str(video_path),
            '-vf', (
                f"subtitles={srt_path}:force_style='"
                f"FontSize={font_size},"
                f"PrimaryColour=&H00FFFFFF,"
                f"OutlineColour=&H00000000,"
                f"Outline={stroke_width},"
                f"Alignment=2'"  # 底部居中
            ),
            '-c:a', 'copy',
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '18',
            str(output_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"FFmpeg字幕添加失败: {e}")
            return False
    
    def add_compliance_overlay(self, video_path: Path, output_path: Path) -> bool:
        """添加合规声明叠加层"""
        # 标题和警告文本
        title = self.config['project']['name']
        warning = "AI生成 本故事纯属虚构 仅供娱乐"
        
        cmd = [
            'ffmpeg', '-y',
            '-i', str(video_path),
            '-vf', (
                f"drawtext=text='{title}':fontsize=28:fontcolor=white:"
                f"x=(w-text_w)/2:y=20:box=1:boxcolor=black@0.5,"
                f"drawtext=text='{warning}':fontsize=20:fontcolor=yellow:"
                f"x=(w-text_w)/2:y=55:box=1:boxcolor=black@0.5"
            ),
            '-c:a', 'copy',
            '-c:v', 'libx264',
            str(output_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"叠加层添加失败: {e}")
            return False
    
    def concatenate_videos(self, video_files: List[dict], 
                          transition: str = "dissolve") -> Path:
        """拼接所有视频片段"""
        output_path = self.final_output / "concatenated.mp4"
        
        # 创建拼接列表文件
        list_file = self.final_output / "concat_list.txt"
        with open(list_file, 'w', encoding='utf-8') as f:
            for vf in video_files:
                # 使用绝对路径
                f.write(f"file '{vf['path'].absolute()}'\n")
        
        # 构建FFmpeg命令
        if transition == "cut":
            # 硬切
            cmd = [
                'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
                '-i', str(list_file),
                '-c', 'copy',
                str(output_path)
            ]
        else:
            # 使用转场效果
            inputs = []
            filter_parts = []
            
            for i, vf in enumerate(video_files):
                inputs.extend(['-i', str(vf['path'])])
            
            # 构建复杂过滤器（简单拼接）
            n = len(video_files)
            filter_complex = f"concat=n={n}:v=1:a=1[outv][outa]"
            
            cmd = [
                'ffmpeg', '-y',
                *inputs,
                '-filter_complex', filter_complex,
                '-map', '[outv]',
                '-map', '[outa]',
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '18',
                str(output_path)
            ]
        
        try:
            logger.info(f"拼接 {len(video_files)} 个视频片段...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            if result.returncode == 0:
                logger.info(f"✓ 拼接完成: {output_path}")
                return output_path
            else:
                logger.error(f"拼接失败: {result.stderr[:500]}")
                return None
        except Exception as e:
            logger.error(f"拼接异常: {e}")
            return None
    
    def final_export(self, video_path: Path, audio_path: Path = None) -> Path:
        """最终导出 - 添加所有元素"""
        final_path = self.final_output / f"{self.config['project']['name']}_final.mp4"
        
        # 获取输出配置
        output_config = self.post_config.get('output', {})
        width = output_config.get('resolution', {}).get('width', 1080)
        height = output_config.get('resolution', {}).get('height', 1920)
        bitrate = output_config.get('bitrate', '8000k')
        
        # 构建命令
        if audio_path and audio_path.exists():
            # 有独立音频轨道
            cmd = [
                'ffmpeg', '-y',
                '-i', str(video_path),
                '-i', str(audio_path),
                '-c:v', 'libx264',
                '-preset', 'slow',
                '-b:v', bitrate,
                '-vf', f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2',
                '-c:a', 'aac',
                '-b:a', '192k',
                '-ar', '48000',
                '-shortest',
                str(final_path)
            ]
        else:
            # 仅视频
            cmd = [
                'ffmpeg', '-y',
                '-i', str(video_path),
                '-c:v', 'libx264',
                '-preset', 'slow',
                '-b:v', bitrate,
                '-vf', f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2',
                '-c:a', 'copy',
                str(final_path)
            ]
        
        try:
            logger.info("最终导出中...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            if result.returncode == 0:
                file_size = final_path.stat().st_size / (1024 * 1024)
                logger.info(f"✓ 最终视频导出完成!")
                logger.info(f"  文件: {final_path}")
                logger.info(f"  大小: {file_size:.1f}MB")
                logger.info(f"  分辨率: {width}x{height}")
                return final_path
            else:
                logger.error(f"导出失败: {result.stderr[:500]}")
                return None
        except Exception as e:
            logger.error(f"导出异常: {e}")
            return None
    
    def run_full_pipeline(self):
        """运行完整的后期制作流程"""
        logger.info("=" * 60)
        logger.info("开始后期制作流程")
        logger.info("=" * 60)
        
        # 1. 获取所有场景视频
        video_files = self.get_scene_videos()
        if not video_files:
            logger.error("没有找到场景视频文件!")
            return False
        
        logger.info(f"找到 {len(video_files)} 个场景视频")
        
        # 2. 拼接视频
        transition = self.post_config.get('concat', {}).get('transition', 'cut')
        concatenated = self.concatenate_videos(video_files, transition)
        if not concatenated:
            return False
        
        # 3. 添加合规声明
        with_overlay = self.final_output / "with_overlay.mp4"
        if self.add_compliance_overlay(concatenated, with_overlay):
            logger.info("✓ 合规声明添加完成")
        else:
            logger.warning("合规声明添加失败，使用原始视频")
            with_overlay = concatenated
        
        # 4. 最终导出
        final_video = self.final_export(with_overlay)
        
        if final_video:
            logger.info("=" * 60)
            logger.info("✓ 后期制作完成!")
            logger.info(f"最终输出: {final_video}")
            logger.info("=" * 60)
            return True
        
        return False


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='后期制作')
    parser.add_argument('--config', '-c', default='./config/workflow.yaml')
    parser.add_argument('--skip-subtitles', action='store_true')
    
    args = parser.parse_args()
    
    processor = PostProduction(args.config)
    success = processor.run_full_pipeline()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
