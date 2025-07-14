#!/usr/bin/env python3
"""
Test script: lightweight video analysis + Qwen advice generation
"""
import os
import sys
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("DASHSCOPE_API_KEY")

from PIL import Image
sys.path.append(os.path.join(os.path.dirname(__file__), 'modules'))
from modules.vision_model import VisionModel
from modules.advice_generator import AdviceGenerator

def summarize_frame_result(frame_result):
    # Generate summary suitable for Qwen
    obs = frame_result.get('obstacles', [])
    if not obs:
        return "No obstacles detected, environment is relatively safe."
    parts = []
    for o in obs:
        parts.append(f"{o.get('type', 'unknown')} at {o.get('direction', 'unknown')}, distance {o.get('distance', 'unknown')}, risk level {o.get('severity', 'unknown')}")
    return "; ".join(parts)

def main():
    # 1. 初始化模型
    vision = VisionModel(device="cpu")
    advice_gen = AdviceGenerator(api_key=api_key)
    
    # 2. 读取帧
    assets_dir = "ai_walker/assets"
    frame_files = [os.path.join(assets_dir, f) for f in os.listdir(assets_dir) if f.endswith('.jpg')]
    frame_files.sort(key=lambda x: int(x.split('_')[-1].split('.')[0]))
    test_frames = frame_files[:5]
    
    # 3. 分析帧
    summaries = []
    for path in test_frames:
        result = vision.analyze_single_image(path)
        summary = summarize_frame_result(result)
        summaries.append(summary)
        print(f"Frame {os.path.basename(path)} summary: {summary}")
    
    # 4. Generate advice using Qwen
    advice = advice_gen.generate_advice(summaries)
    print("\n=== Qwen Advice ===")
    print(advice['advice_text'])

if __name__ == "__main__":
    main() 