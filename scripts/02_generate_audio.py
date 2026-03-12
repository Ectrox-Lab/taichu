#!/usr/bin/env python3
"""
中文配音生成脚本 - 使用Edge-TTS
支持多角色配音、情感控制
"""

import os
import sys
import yaml
import json
import subprocess
import asyncio
import edge_tts
from pathlib import Path
from typing import Dict, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AudioGenerator:
    """音频生成器 - 管理TTS和音效"""
    
    # Edge-TTS 中文语音库
    VOICES = {
        "zh-CN-YunxiNeural": "男声-沉稳",      # 旁白、主角
        "zh-CN-YunjianNeural": "男声-年轻",    # 年轻角色
        "zh-CN-YunyeNeural": "男声-中年",      # 小叔
        "zh-CN-XiaoxiaoNeural": "女声-温柔",   # 母亲
        "zh-CN-XiaoyiNeural": "女声-老年",     # 奶奶
        "zh-CN-XiaochenNeural": "女声-活泼",   # 其他
    }
    
    def __init__(self, config_path: str):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.output_dir = Path(self.config['project']['output_dir']) / 'audio'
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"初始化音频生成器")
    
    async def generate_tts(self, text: str, voice: str, output_path: Path, 
                          rate: str = "+0%", pitch: str = "+0Hz") -> bool:
        """生成单个TTS音频"""
        try:
            communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
            await communicate.save(str(output_path))
            return True
        except Exception as e:
            logger.error(f"TTS生成失败: {e}")
            return False
    
    async def generate_scene_dialogues(self, scene_id: str) -> List[Path]:
        """生成场景的所有对话音频"""
        dialogues = self.config.get('dialogues', {}).get(scene_id, [])
        voice_config = self.config.get('tts', {}).get('voices', {})
        
        if not dialogues:
            logger.warning(f"场景 {scene_id} 没有对话配置")
            return []
        
        audio_files = []
        
        for i, dialogue in enumerate(dialogues):
            character = dialogue['character']
            text = dialogue['text']
            emotion = dialogue.get('emotion', 'neutral')
            
            # 获取角色语音配置
            char_voice = voice_config.get(character, {})
            voice = char_voice.get('voice', 'zh-CN-YunxiNeural')
            rate = char_voice.get('rate', '+0%')
            pitch = char_voice.get('pitch', '+0Hz')
            
            # 根据情感调整
            emotion_adjustments = {
                'urgent': ('+15%', '+10Hz'),
                'scared': ('+20%', '+20Hz'),
                'sinister': ('-10%', '-15Hz'),
                'mocking': ('-5%', '-5Hz'),
                'determined': ('+0%', '+5Hz'),
                'mysterious': ('-15%', '-20Hz'),
            }
            
            if emotion in emotion_adjustments:
                rate, pitch = emotion_adjustments[emotion]
            
            output_path = self.output_dir / f"{scene_id}_dialogue_{i:02d}_{character}.mp3"
            
            logger.info(f"[TTS] {scene_id} - {character}: {text[:30]}...")
            
            success = await self.generate_tts(text, voice, output_path, rate, pitch)
            if success:
                audio_files.append({
                    'file': output_path,
                    'time': dialogue.get('time', 0),
                    'character': character,
                    'text': text
                })
        
        return audio_files
    
    async def generate_all(self):
        """生成所有场景的音频"""
        scenes = self.config.get('scenes', [])
        
        all_audio = {}
        
        for scene in scenes:
            scene_id = scene['id']
            logger.info(f"\n处理场景音频: {scene_id}")
            
            audio_files = await self.generate_scene_dialogues(scene_id)
            all_audio[scene_id] = audio_files
            
            logger.info(f"  生成了 {len(audio_files)} 个音频片段")
        
        # 保存音频清单
        manifest_path = self.output_dir / 'audio_manifest.json'
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(all_audio, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\n✓ 音频清单已保存: {manifest_path}")
        return all_audio


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='中文配音生成')
    parser.add_argument('--config', '-c', default='./config/workflow.yaml')
    parser.add_argument('--scene', '-s', help='只生成指定场景')
    
    args = parser.parse_args()
    
    generator = AudioGenerator(args.config)
    
    if args.scene:
        # 单场景模式
        asyncio.run(generator.generate_scene_dialogues(args.scene))
    else:
        # 全部生成
        asyncio.run(generator.generate_all())


if __name__ == '__main__':
    main()
