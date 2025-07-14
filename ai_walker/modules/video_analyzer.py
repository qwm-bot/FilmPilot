# modules/video_analyzer.py
import os
import json
import cv2
import time
from typing import List, Dict, Any, Optional
from pathlib import Path
from collections import defaultdict
import numpy as np
from .vision_model import VisionModel

class VideoAnalyzer:
    """
    Video analysis module for processing video sequences
    Provides comprehensive analysis and advice for video-based navigation
    """
    
    def __init__(self, vision_model: VisionModel = None):
        """
        Initialize video analyzer
        
        Args:
            vision_model: Vision model instance (optional)
        """
        self.vision_model = vision_model or VisionModel()
        self.analysis_cache = {}
        
    def analyze_video_file(self, video_path: str, output_dir: str = "ai_walker/assets", 
                          frame_rate: int = 30, max_frames: int = 50) -> Dict[str, Any]:
        """
        Analyze video file and generate comprehensive advice
        
        Args:
            video_path: Path to video file
            output_dir: Directory to save extracted frames
            frame_rate: Frame extraction rate (every N frames)
            max_frames: Maximum number of frames to analyze
            
        Returns:
            Comprehensive video analysis result
        """
        print(f"Starting video analysis: {video_path}")
        
        # Extract frames from video
        frame_paths = self._extract_frames_from_video(video_path, output_dir, frame_rate, max_frames)
        
        if not frame_paths:
            return {"error": "Failed to extract frames from video"}
        
        print(f"Extracted {len(frame_paths)} frames for analysis")
        
        # Get video duration
        video_duration = self._get_video_duration(video_path)
        
        # Analyze video sequence (using lightweight models)
        analysis_result = self.vision_model.analyze_video_sequence(frame_paths, video_duration)
        
        # Add video metadata
        analysis_result["video_metadata"] = {
            "video_path": video_path,
            "frame_count": len(frame_paths),
            "extraction_rate": frame_rate,
            "duration_seconds": video_duration
        }
        
        return analysis_result
    
    def _extract_frames_from_video(self, video_path: str, output_dir: str, 
                                  frame_rate: int, max_frames: int) -> List[str]:
        """
        Extract frames from video file
        
        Args:
            video_path: Path to video file
            output_dir: Output directory for frames
            frame_rate: Extract every N frames
            max_frames: Maximum frames to extract
            
        Returns:
            List of frame file paths
        """
        if not os.path.exists(video_path):
            print(f"Video file not found: {video_path}")
            return []
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Open video
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"Failed to open video: {video_path}")
            return []
        
        frame_paths = []
        frame_count = 0
        extracted_count = 0
        
        print(f"Extracting frames (every {frame_rate} frames, max {max_frames})...")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_count % frame_rate == 0 and extracted_count < max_frames:
                # Save frame
                frame_filename = f"frame_{frame_count:04d}.jpg"
                frame_path = os.path.join(output_dir, frame_filename)
                
                # Compress and save
                cv2.imwrite(frame_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                
                if os.path.exists(frame_path):
                    frame_paths.append(frame_path)
                    extracted_count += 1
                    print(f"Extracted frame {extracted_count}/{max_frames}: {frame_filename}")
            
            frame_count += 1
        
        cap.release()
        print(f"Extraction complete: {len(frame_paths)} frames saved")
        
        return frame_paths
    
    def _get_video_duration(self, video_path: str) -> float:
        """
        Get video duration in seconds
        
        Args:
            video_path: Path to video file
            
        Returns:
            Duration in seconds
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return 0.0
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        cap.release()
        
        if fps > 0:
            return frame_count / fps
        else:
            return 0.0
    
    def generate_video_summary(self, analysis_result: Dict[str, Any]) -> str:
        """
        Generate human-readable video summary
        
        Args:
            analysis_result: Video analysis result
            
        Returns:
            Formatted summary string
        """
        if "error" in analysis_result:
            return f"Analysis failed: {analysis_result['error']}"
        
        video_advice = analysis_result.get("video_advice", {})
        video_summary = analysis_result.get("video_summary", {})
        key_obstacles = analysis_result.get("key_obstacles", [])
        
        summary_parts = []
        
        # Video overview
        summary_parts.append("=== VIDEO ANALYSIS SUMMARY ===")
        summary_parts.append(f"Total frames analyzed: {video_summary.get('analyzed_frames', 0)}")
        summary_parts.append(f"Video duration: {video_summary.get('video_duration', 0):.1f} seconds")
        summary_parts.append(f"Average risk level: {video_summary.get('average_risk_level', 'unknown')}")
        
        # Primary advice
        primary_advice = video_advice.get("primary_advice", "No specific advice available")
        summary_parts.append(f"\nPRIMARY ADVICE:")
        summary_parts.append(primary_advice)
        
        # Key obstacles
        if key_obstacles:
            summary_parts.append(f"\nKEY OBSTACLES DETECTED:")
            for obstacle in key_obstacles:
                summary_parts.append(f"- {obstacle['type']}: {obstacle['description']}")
        
        # Specific recommendations
        recommendations = video_advice.get("specific_recommendations", [])
        if recommendations:
            summary_parts.append(f"\nSPECIFIC RECOMMENDATIONS:")
            for rec in recommendations:
                summary_parts.append(f"- {rec}")
        
        # Safety warnings
        warnings = video_advice.get("safety_warnings", [])
        if warnings:
            summary_parts.append(f"\nSAFETY WARNINGS:")
            for warning in warnings:
                summary_parts.append(f"- {warning}")
        
        # Action items
        actions = video_advice.get("action_items", [])
        if actions:
            summary_parts.append(f"\nIMMEDIATE ACTIONS:")
            for action in actions:
                summary_parts.append(f"- {action}")
        
        # Overall assessment
        assessment = video_advice.get("overall_assessment", "Assessment not available")
        summary_parts.append(f"\nOVERALL ASSESSMENT:")
        summary_parts.append(assessment)
        
        return "\n".join(summary_parts)
    
    def save_analysis_report(self, analysis_result: Dict[str, Any], output_path: str) -> bool:
        """
        Save analysis result to JSON file
        
        Args:
            analysis_result: Analysis result
            output_path: Output file path
            
        Returns:
            Success status
        """
        try:
            # Create output directory
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Save detailed analysis
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(analysis_result, f, ensure_ascii=False, indent=2)
            
            # Generate and save summary
            summary = self.generate_video_summary(analysis_result)
            summary_path = output_path.replace('.json', '_summary.txt')
            
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(summary)
            
            print(f"Analysis report saved to: {output_path}")
            print(f"Summary saved to: {summary_path}")
            
            return True
            
        except Exception as e:
            print(f"Error saving analysis report: {e}")
            return False
    
    def analyze_video_with_advice(self, video_path: str, output_dir: str = "ai_walker/assets") -> Dict[str, Any]:
        """
        Complete video analysis with advice generation
        
        Args:
            video_path: Path to video file
            output_dir: Output directory for frames and reports
            
        Returns:
            Complete analysis with advice
        """
        print(f"Starting comprehensive video analysis: {video_path}")
        
        # Analyze video
        analysis_result = self.analyze_video_file(video_path, output_dir)
        
        if "error" in analysis_result:
            return analysis_result
        
        # Generate summary
        summary = self.generate_video_summary(analysis_result)
        analysis_result["human_readable_summary"] = summary
        
        # Save report
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        report_path = os.path.join(output_dir, f"{video_name}_analysis.json")
        self.save_analysis_report(analysis_result, report_path)
        
        return analysis_result
    
    def test_with_sample_video(self, video_path: str = "ai_walker/video_input/obstacle_input.mp4") -> None:
        """
        Test video analysis with sample video
        
        Args:
            video_path: Path to test video
        """
        print("Testing video analysis...")
        
        if not os.path.exists(video_path):
            print(f"Test video not found: {video_path}")
            return
        
        # Perform analysis
        result = self.analyze_video_with_advice(video_path)
        
        # Print summary
        if "human_readable_summary" in result:
            print("\n" + "="*60)
            print(result["human_readable_summary"])
            print("="*60)
        else:
            print("Analysis failed or incomplete")


if __name__ == "__main__":
    # Test video analyzer
    print("Testing Video Analyzer...")
    
    analyzer = VideoAnalyzer()
    analyzer.test_with_sample_video() 