# modules/vision_model.py
import os
import json
import torch
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from PIL import Image
import cv2
from transformers import pipeline
import requests
from io import BytesIO
from collections import defaultdict, deque
import time

class VisionModel:
    """
    Vision recognition module using lightweight Hugging Face models
    Uses open-source models for obstacle detection and navigation advice
    """
    
    def __init__(self, device: str = "auto"):
        """
        Initialize vision model
        
        Args:
            device: Device to use ('cpu', 'cuda', or 'auto')
        """
        self.device = "cuda" if torch.cuda.is_available() and device == "auto" else "cpu"
        print(f"Using device: {self.device}")
        
        # Initialize models
        self._load_models()
        
        # Video analysis settings
        self.frame_buffer_size = 10  # Number of frames to keep in memory
        self.frame_buffer = deque(maxlen=self.frame_buffer_size)
        self.temporal_analysis_window = 5  # Frames for temporal analysis
        
        # Define obstacle types and their categories
        self.obstacle_categories = {
            "stairs": ["stairs", "steps", "escalator"],
            "vehicle": ["car", "truck", "bus", "motorcycle", "bicycle"],
            "pedestrian": ["person", "people", "crowd"],
            "construction": ["construction", "barrier", "cone", "sign"],
            "road_hazard": ["pothole", "puddle", "debris", "hole"],
            "traffic": ["traffic_light", "stop_sign", "crosswalk"],
            "furniture": ["bench", "chair", "table", "fence"],
            "nature": ["tree", "bush", "plant", "rock"]
        }
        
        # Direction mapping
        self.direction_map = {
            "left": ["left", "left side", "to the left"],
            "right": ["right", "right side", "to the right"],
            "center": ["center", "middle", "ahead", "front"],
            "behind": ["behind", "back", "rear"]
        }
        
        # Safety advice templates
        self.safety_templates = {
            "high": [
                "⚠️ WARNING: {obstacle} detected {direction} at {distance}. Please STOP immediately and find an alternative route.",
                "🚨 DANGER: {obstacle} {direction} at {distance}. Do not proceed, seek assistance.",
                "⚠️ CRITICAL: {obstacle} blocking path {direction}. Stop and wait for guidance."
            ],
            "medium": [
                "⚠️ CAUTION: {obstacle} {direction} at {distance}. Proceed with extreme care.",
                "⚠️ ATTENTION: {obstacle} detected {direction}. Slow down and be careful.",
                "⚠️ WARNING: {obstacle} {direction} at {distance}. Exercise caution."
            ],
            "low": [
                "💡 NOTICE: {obstacle} {direction} at {distance}. Be aware and avoid if possible.",
                "💡 TIP: {obstacle} {direction} at {distance}. Proceed normally but stay alert.",
                "💡 INFO: {obstacle} {direction} at {distance}. No immediate danger."
            ]
        }
        
        # Navigation advice templates
        self.navigation_templates = {
            "avoid": "Avoid the {obstacle} by moving {direction}.",
            "wait": "Wait for the {obstacle} to clear before proceeding.",
            "find_alternative": "Look for an alternative route around the {obstacle}.",
            "proceed_carefully": "Proceed carefully past the {obstacle}.",
            "stop": "Stop and do not proceed due to {obstacle}."
        }
        
        # Video analysis templates
        self.video_advice_templates = {
            "trending_towards": "⚠️ You are moving towards {obstacle} - consider changing direction.",
            "approaching": "🚨 You are approaching {obstacle} - slow down and prepare to stop.",
            "moving_away": "✅ Good! You are moving away from {obstacle}.",
            "stable_obstacle": "⚠️ {obstacle} remains in your path - find alternative route.",
            "clear_path": "✅ Path ahead is clear - you can proceed safely.",
            "multiple_obstacles": "⚠️ Multiple obstacles detected - proceed with extreme caution."
        }
    
    def _load_models(self):
        """Load all required models"""
        try:
            print("Loading lightweight object detection model (YOLOs-tiny)...")
            self.object_detector = pipeline(
                "object-detection",
                model="hustvl/yolos-tiny",
                device=-1 if self.device == "cpu" else 0
            )
            print("Loading lightweight image classification model (MobileNetV2)...")
            self.image_classifier = pipeline(
                "image-classification",
                model="google/mobilenet_v2_1.0_224",
                device=-1 if self.device == "cpu" else 0
            )
            print("Lightweight models loaded successfully!")
        except Exception as e:
            print(f"Error loading lightweight models: {e}")
            self.object_detector = None
            self.image_classifier = None
    
    def analyze_single_image(self, image_path: str) -> Dict[str, Any]:
        """
        Analyze single image using HF models
        
        Args:
            image_path: Image path
            
        Returns:
            Analysis result dictionary
        """
        try:
            # Check if image exists
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image file does not exist: {image_path}")
            
            # Load and preprocess image
            image = Image.open(image_path).convert('RGB')
            
            # Perform object detection
            detection_results = self._detect_objects(image)
            
            # Perform image classification
            classification_results = self._classify_image(image)
            
            # Analyze scene and generate advice
            analysis_result = self._analyze_scene(detection_results, classification_results, image)
            
            return analysis_result
            
        except Exception as e:
            print(f"Error analyzing image: {e}")
            return {
                "error": str(e),
                "obstacles": [],
                "road_condition": "Analysis failed",
                "safety_advice": "Please proceed with caution",
                "navigation_info": ""
            }
    
    def _detect_objects(self, image: Image.Image) -> List[Dict[str, Any]]:
        """
        Detect objects in image
        
        Args:
            image: PIL Image
            
        Returns:
            List of detected objects
        """
        try:
            if self.object_detector is None:
                return []
            results = self.object_detector(image)
            
            # Process and filter results
            detected_objects = []
            for result in results:
                if result['score'] > 0.3:  # Confidence threshold
                    detected_objects.append({
                        'label': result['label'],
                        'confidence': result['score'],
                        'box': result['box'],
                        'position': self._analyze_position(result['box'], image.size)
                    })
            
            return detected_objects
            
        except Exception as e:
            print(f"Error in object detection: {e}")
            return []
    
    def _classify_image(self, image: Image.Image) -> List[Dict[str, Any]]:
        """
        Classify image content
        
        Args:
            image: PIL Image
            
        Returns:
            Classification results
        """
        try:
            if self.image_classifier is None:
                return []
            results = self.image_classifier(image)
            return results[:3]  # Top 3 classifications
            
        except Exception as e:
            print(f"Error in image classification: {e}")
            return []
    
    def _analyze_position(self, box: Dict[str, float], image_size: Tuple[int, int]) -> Dict[str, Any]:
        """
        Analyze object position relative to image
        
        Args:
            box: Bounding box coordinates
            image_size: Image dimensions (width, height)
            
        Returns:
            Position analysis
        """
        img_width, img_height = image_size
        x1, y1, x2, y2 = box['xmin'], box['ymin'], box['xmax'], box['ymax']
        
        # Calculate center point
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        
        # Determine horizontal position
        if center_x < img_width * 0.33:
            horizontal_pos = "left"
        elif center_x < img_width * 0.67:
            horizontal_pos = "center"
        else:
            horizontal_pos = "right"
        
        # Determine vertical position (distance)
        if center_y < img_height * 0.33:
            distance = "close"
        elif center_y < img_height * 0.67:
            distance = "medium"
        else:
            distance = "far"
        
        # Calculate actual distance estimate (rough approximation)
        # Assuming standard camera parameters
        distance_meters = self._estimate_distance(center_y, img_height)
        
        return {
            "horizontal": horizontal_pos,
            "vertical": "close" if center_y < img_height * 0.5 else "far",
            "distance_meters": distance_meters,
            "center_x": center_x,
            "center_y": center_y
        }
    
    def _estimate_distance(self, y_position: float, image_height: int) -> float:
        """
        Estimate distance based on vertical position
        
        Args:
            y_position: Y coordinate in image
            image_height: Image height
            
        Returns:
            Estimated distance in meters
        """
        # Simple distance estimation based on vertical position
        # Objects higher in image (lower y) are closer
        normalized_y = y_position / image_height
        
        if normalized_y < 0.3:
            return 1.0  # Very close
        elif normalized_y < 0.6:
            return 3.0  # Medium distance
        else:
            return 5.0  # Far away
    
    def _analyze_scene(self, detections: List[Dict], classifications: List[Dict], image: Image.Image) -> Dict[str, Any]:
        """
        Analyze scene and generate frame description
        
        Args:
            detections: Object detection results
            classifications: Image classification results
            image: Original image
            
        Returns:
            Frame description for advice generation
        """
        # Categorize detected objects
        obstacles = self._categorize_obstacles(detections)
        
        # Generate structured frame description
        frame_description = self.generate_frame_description(obstacles)
        
        # Add additional analysis info
        frame_description.update({
            "detection_count": len(detections),
            "classification_confidence": classifications[0]['score'] if classifications else 0.0,
            "road_condition": self._analyze_road_condition(classifications, detections)
        })
        
        return frame_description
    
    def _categorize_obstacles(self, detections: List[Dict]) -> List[Dict[str, Any]]:
        """
        Categorize detected objects as obstacles
        
        Args:
            detections: Object detection results
            
        Returns:
            List of categorized obstacles
        """
        obstacles = []
        
        for detection in detections:
            label = detection['label'].lower()
            position = detection['position']
            
            # Determine obstacle type
            obstacle_type = self._classify_obstacle_type(label)
            
            # Determine severity
            severity = self._determine_severity(obstacle_type, position['distance_meters'])
            
            # Determine direction
            direction = self._determine_direction(position['horizontal'])
            
            obstacle = {
                "type": obstacle_type,
                "original_label": detection['label'],
                "distance": f"{position['distance_meters']:.1f} meters",
                "direction": direction,
                "severity": severity,
                "confidence": detection['confidence'],
                "description": self._generate_obstacle_description(obstacle_type, direction, position['distance_meters'])
            }
            
            obstacles.append(obstacle)
        
        return obstacles
    
    def _classify_obstacle_type(self, label: str) -> str:
        """
        Classify detected object as obstacle type
        
        Args:
            label: Detected object label
            
        Returns:
            Obstacle type
        """
        label_lower = label.lower()
        
        for category, keywords in self.obstacle_categories.items():
            if any(keyword in label_lower for keyword in keywords):
                return category
        
        return "unknown"
    
    def _determine_severity(self, obstacle_type: str, distance: float) -> str:
        """
        Determine obstacle severity based on type and distance
        
        Args:
            obstacle_type: Type of obstacle
            distance: Distance in meters
            
        Returns:
            Severity level
        """
        # High severity obstacles
        high_severity = ["stairs", "construction", "road_hazard"]
        if obstacle_type in high_severity and distance < 3.0:
            return "high"
        
        # Medium severity obstacles
        medium_severity = ["vehicle", "traffic"]
        if obstacle_type in medium_severity and distance < 5.0:
            return "medium"
        
        # Low severity or far away
        return "low"
    
    def _determine_direction(self, horizontal_pos: str) -> str:
        """
        Determine direction based on horizontal position
        
        Args:
            horizontal_pos: Horizontal position
            
        Returns:
            Direction description
        """
        direction_map = {
            "left": "to your left",
            "center": "ahead of you",
            "right": "to your right"
        }
        return direction_map.get(horizontal_pos, "ahead of you")
    
    def _generate_obstacle_description(self, obstacle_type: str, direction: str, distance: float) -> str:
        """
        Generate detailed obstacle description
        
        Args:
            obstacle_type: Type of obstacle
            direction: Direction
            distance: Distance in meters
            
        Returns:
            Description string
        """
        descriptions = {
            "stairs": f"Stairs {direction} at {distance:.1f} meters",
            "vehicle": f"Vehicle {direction} at {distance:.1f} meters",
            "pedestrian": f"Person {direction} at {distance:.1f} meters",
            "construction": f"Construction barrier {direction} at {distance:.1f} meters",
            "road_hazard": f"Road hazard {direction} at {distance:.1f} meters",
            "traffic": f"Traffic signal {direction} at {distance:.1f} meters",
            "furniture": f"Street furniture {direction} at {distance:.1f} meters",
            "nature": f"Natural obstacle {direction} at {distance:.1f} meters"
        }
        
        return descriptions.get(obstacle_type, f"Object {direction} at {distance:.1f} meters")
    
    def _analyze_road_condition(self, classifications: List[Dict], detections: List[Dict]) -> str:
        """
        Analyze overall road condition
        
        Args:
            classifications: Image classification results
            detections: Object detection results
            
        Returns:
            Road condition description
        """
        # Count different types of obstacles
        obstacle_counts = {}
        for detection in detections:
            obstacle_type = self._classify_obstacle_type(detection['label'])
            obstacle_counts[obstacle_type] = obstacle_counts.get(obstacle_type, 0) + 1
        
        # Determine road condition based on obstacles
        if not obstacle_counts:
            return "Clear path ahead, road condition is good"
        
        # Check for major obstacles
        if obstacle_counts.get("construction", 0) > 0:
            return "Construction area detected, proceed with caution"
        elif obstacle_counts.get("stairs", 0) > 0:
            return "Stairs detected, look for accessible route"
        elif obstacle_counts.get("vehicle", 0) > 0:
            return "Vehicles detected, be aware of traffic"
        else:
            return "Minor obstacles detected, proceed with normal caution"
    
    def generate_frame_description(self, obstacles: List[Dict]) -> Dict[str, Any]:
        """
        Generate structured frame description for advice generation
        
        Args:
            obstacles: List of detected obstacles
            
        Returns:
            Structured description dictionary
        """
        if not obstacles:
            return {
                "scene_summary": "Clear path ahead",
                "obstacles": [],
                "risk_level": "low",
                "primary_obstacle": None,
                "spatial_info": {
                    "left_obstacles": [],
                    "right_obstacles": [],
                    "center_obstacles": [],
                    "closest_obstacle": None
                },
                "environment_context": "Safe walking environment"
            }
        
        # Group obstacles by direction
        left_obstacles = [obs for obs in obstacles if "left" in obs.get("direction", "")]
        right_obstacles = [obs for obs in obstacles if "right" in obs.get("direction", "")]
        center_obstacles = [obs for obs in obstacles if "ahead" in obs.get("direction", "")]
        
        # Find closest obstacle
        closest_obstacle = min(obstacles, key=lambda x: float(x.get("distance", "5.0").split()[0]))
        
        # Determine overall risk level
        risk_levels = [obs.get("severity", "low") for obs in obstacles]
        if "high" in risk_levels:
            overall_risk = "high"
        elif "medium" in risk_levels:
            overall_risk = "medium"
        else:
            overall_risk = "low"
        
        # Generate scene summary
        if center_obstacles:
            scene_summary = f"Obstacles detected ahead: {', '.join([obs['type'] for obs in center_obstacles])}"
        elif left_obstacles and right_obstacles:
            scene_summary = f"Obstacles on both sides: {len(left_obstacles)} on left, {len(right_obstacles)} on right"
        elif left_obstacles:
            scene_summary = f"Obstacles on left side: {', '.join([obs['type'] for obs in left_obstacles])}"
        elif right_obstacles:
            scene_summary = f"Obstacles on right side: {', '.join([obs['type'] for obs in right_obstacles])}"
        else:
            scene_summary = "Minor obstacles detected"
        
        # Environment context
        if overall_risk == "high":
            environment_context = "High-risk environment requiring immediate attention"
        elif overall_risk == "medium":
            environment_context = "Moderate-risk environment requiring caution"
        else:
            environment_context = "Low-risk environment, proceed normally"
        
        return {
            "scene_summary": scene_summary,
            "obstacles": obstacles,
            "risk_level": overall_risk,
            "primary_obstacle": closest_obstacle,
            "spatial_info": {
                "left_obstacles": left_obstacles,
                "right_obstacles": right_obstacles,
                "center_obstacles": center_obstacles,
                "closest_obstacle": closest_obstacle
            },
            "environment_context": environment_context
        }
    
    def _severity_to_score(self, severity: str) -> int:
        """
        Convert severity to numerical score
        
        Args:
            severity: Severity level
            
        Returns:
            Numerical score
        """
        severity_map = {"high": 3, "medium": 2, "low": 1}
        return severity_map.get(severity, 1)
    
    def analyze_image_sequence(self, image_paths: List[str], max_images: int = 5) -> Dict[str, Any]:
        """
        Analyze image sequence for more stable results
        
        Args:
            image_paths: List of image paths
            max_images: Maximum number of images to analyze
            
        Returns:
            Comprehensive analysis result
        """
        if not image_paths:
            return {"error": "No image paths provided"}
        
        # Limit number of images
        images_to_analyze = image_paths[:max_images]
        
        results = []
        for image_path in images_to_analyze:
            result = self.analyze_single_image(image_path)
            results.append(result)
        
        # Merge results
        return self._merge_analysis_results(results)
    
    def _merge_analysis_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge multiple analysis results
        
        Args:
            results: List of analysis results
            
        Returns:
            Merged result
        """
        if not results:
            return {"error": "No valid analysis results"}
        
        # Collect all obstacles
        all_obstacles = []
        for result in results:
            if "obstacles" in result and isinstance(result["obstacles"], list):
                all_obstacles.extend(result["obstacles"])
        
        # Merge obstacles by type and position
        merged_obstacles = self._merge_obstacles(all_obstacles)
        
        # Get latest road condition
        latest_result = results[-1]
        
        return {
            "obstacles": merged_obstacles,
            "road_condition": latest_result.get("road_condition", "Unknown road condition"),
            "safety_advice": latest_result.get("safety_advice", "Please proceed with caution"),
            "navigation_info": latest_result.get("navigation_info", ""),
            "analysis_count": len(results)
        }
    
    def _merge_obstacles(self, obstacles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Merge and deduplicate obstacles
        
        Args:
            obstacles: List of obstacles
            
        Returns:
            Merged obstacle list
        """
        if not obstacles:
            return []
        
        # Group by type and direction
        obstacle_groups = {}
        for obstacle in obstacles:
            key = f"{obstacle.get('type', 'unknown')}_{obstacle.get('direction', 'unknown')}"
            if key not in obstacle_groups:
                obstacle_groups[key] = []
            obstacle_groups[key].append(obstacle)
        
        # Merge groups
        merged_obstacles = []
        for group in obstacle_groups.values():
            if len(group) == 1:
                merged_obstacles.append(group[0])
            else:
                # Select most severe obstacle in group
                most_severe = max(group, key=lambda x: self._severity_to_score(x.get("severity", "low")))
                merged_obstacles.append(most_severe)
        
        return merged_obstacles
    
    def analyze_video_sequence(self, frame_paths: List[str], video_duration: float = None) -> Dict[str, Any]:
        """
        Analyze video sequence for comprehensive advice
        
        Args:
            frame_paths: List of frame paths in chronological order
            video_duration: Duration of video in seconds (optional)
            
        Returns:
            Comprehensive video analysis with advice
        """
        if not frame_paths:
            return {"error": "No frame paths provided"}
        
        print(f"Analyzing video sequence with {len(frame_paths)} frames...")
        
        # Analyze each frame
        frame_analyses = []
        for i, frame_path in enumerate(frame_paths):
            if os.path.exists(frame_path):
                print(f"Analyzing frame {i+1}/{len(frame_paths)}: {os.path.basename(frame_path)}")
                analysis = self.analyze_single_image(frame_path)
                analysis['frame_index'] = i
                analysis['timestamp'] = i * (video_duration / len(frame_paths) if video_duration else 1.0)
                frame_analyses.append(analysis)
        
        # Perform temporal analysis
        temporal_analysis = self._analyze_temporal_patterns(frame_analyses)
        
        # Generate video-level advice
        video_advice = self._generate_video_advice(frame_analyses, temporal_analysis)
        
        # Create comprehensive result
        result = {
            "video_summary": {
                "total_frames": len(frame_paths),
                "analyzed_frames": len(frame_analyses),
                "video_duration": video_duration,
                "average_risk_level": self._calculate_average_risk(frame_analyses)
            },
            "temporal_analysis": temporal_analysis,
            "frame_analyses": frame_analyses,
            "video_advice": video_advice,
            "key_obstacles": self._identify_key_obstacles(frame_analyses),
            "navigation_recommendations": self._generate_navigation_recommendations(frame_analyses, temporal_analysis)
        }
        
        return result
    
    def _analyze_temporal_patterns(self, frame_analyses: List[Dict]) -> Dict[str, Any]:
        """
        Analyze temporal patterns in video sequence
        
        Args:
            frame_analyses: List of frame analysis results
            
        Returns:
            Temporal analysis results
        """
        if len(frame_analyses) < 2:
            return {"error": "Insufficient frames for temporal analysis"}
        
        # Track obstacle movement patterns
        obstacle_tracks = defaultdict(list)
        risk_trends = []
        
        for analysis in frame_analyses:
            # Track obstacles over time
            for obstacle in analysis.get("obstacles", []):
                obstacle_tracks[obstacle.get("type", "unknown")].append({
                    "frame": analysis.get("frame_index", 0),
                    "timestamp": analysis.get("timestamp", 0),
                    "distance": float(obstacle.get("distance", "5.0").split()[0]),
                    "direction": obstacle.get("direction", "unknown"),
                    "severity": obstacle.get("severity", "low")
                })
            
            # Track risk level over time
            risk_level = self._calculate_frame_risk(analysis)
            risk_trends.append({
                "frame": analysis.get("frame_index", 0),
                "timestamp": analysis.get("timestamp", 0),
                "risk_level": risk_level
            })
        
        # Analyze movement patterns
        movement_patterns = self._analyze_obstacle_movement(obstacle_tracks)
        
        # Detect trends
        risk_trend = self._detect_risk_trend(risk_trends)
        
        return {
            "obstacle_tracks": dict(obstacle_tracks),
            "risk_trends": risk_trends,
            "movement_patterns": movement_patterns,
            "risk_trend": risk_trend,
            "temporal_summary": self._generate_temporal_summary(obstacle_tracks, risk_trend)
        }
    
    def _analyze_obstacle_movement(self, obstacle_tracks: Dict) -> Dict[str, Any]:
        """
        Analyze how obstacles move over time
        
        Args:
            obstacle_tracks: Obstacle tracking data
            
        Returns:
            Movement analysis
        """
        movement_patterns = {}
        
        for obstacle_type, track in obstacle_tracks.items():
            if len(track) < 2:
                continue
            
            # Calculate distance changes
            distances = [point["distance"] for point in track]
            distance_changes = [distances[i] - distances[i-1] for i in range(1, len(distances))]
            
            # Determine movement pattern
            avg_distance_change = sum(distance_changes) / len(distance_changes)
            
            if avg_distance_change < -0.5:  # Getting closer
                pattern = "approaching"
            elif avg_distance_change > 0.5:  # Moving away
                pattern = "moving_away"
            else:
                pattern = "stable"
            
            movement_patterns[obstacle_type] = {
                "pattern": pattern,
                "avg_distance_change": avg_distance_change,
                "initial_distance": distances[0],
                "final_distance": distances[-1],
                "track_length": len(track)
            }
        
        return movement_patterns
    
    def _detect_risk_trend(self, risk_trends: List[Dict]) -> str:
        """
        Detect overall risk trend
        
        Args:
            risk_trends: Risk level over time
            
        Returns:
            Risk trend description
        """
        if len(risk_trends) < 3:
            return "insufficient_data"
        
        # Convert risk levels to numbers
        risk_scores = []
        for trend in risk_trends:
            risk_level = trend.get("risk_level", "low")
            score = {"low": 1, "medium": 2, "high": 3}.get(risk_level, 1)
            risk_scores.append(score)
        
        # Calculate trend
        if len(risk_scores) >= 3:
            recent_avg = sum(risk_scores[-3:]) / 3
            earlier_avg = sum(risk_scores[:3]) / 3
            
            if recent_avg > earlier_avg + 0.5:
                return "increasing"
            elif recent_avg < earlier_avg - 0.5:
                return "decreasing"
            else:
                return "stable"
        
        return "stable"
    
    def _calculate_frame_risk(self, analysis: Dict) -> str:
        """
        Calculate risk level for a single frame
        
        Args:
            analysis: Frame analysis result
            
        Returns:
            Risk level
        """
        obstacles = analysis.get("obstacles", [])
        if not obstacles:
            return "low"
        
        # Calculate weighted risk based on severity and distance
        total_risk = 0
        for obstacle in obstacles:
            severity = obstacle.get("severity", "low")
            distance = float(obstacle.get("distance", "5.0").split()[0])
            
            severity_weight = {"low": 1, "medium": 2, "high": 3}.get(severity, 1)
            distance_weight = max(0, 5 - distance) / 5  # Closer = higher weight
            
            total_risk += severity_weight * distance_weight
        
        avg_risk = total_risk / len(obstacles)
        
        if avg_risk > 2.0:
            return "high"
        elif avg_risk > 1.0:
            return "medium"
        else:
            return "low"
    
    def _calculate_average_risk(self, frame_analyses: List[Dict]) -> str:
        """
        Calculate average risk level across all frames
        
        Args:
            frame_analyses: List of frame analyses
            
        Returns:
            Average risk level
        """
        risk_levels = []
        for analysis in frame_analyses:
            risk_level = self._calculate_frame_risk(analysis)
            risk_levels.append(risk_level)
        
        # Count risk levels
        risk_counts = {"low": 0, "medium": 0, "high": 0}
        for level in risk_levels:
            risk_counts[level] += 1
        
        # Determine dominant risk level
        total_frames = len(risk_levels)
        if risk_counts["high"] / total_frames > 0.3:
            return "high"
        elif risk_counts["medium"] / total_frames > 0.4:
            return "medium"
        else:
            return "low"
    
    def _generate_video_advice(self, frame_analyses: List[Dict], temporal_analysis: Dict) -> Dict[str, Any]:
        """
        Generate comprehensive video-level advice
        
        Args:
            frame_analyses: List of frame analyses
            temporal_analysis: Temporal analysis results
            
        Returns:
            Video-level advice
        """
        # Get key information
        movement_patterns = temporal_analysis.get("movement_patterns", {})
        risk_trend = temporal_analysis.get("risk_trend", "stable")
        average_risk = self._calculate_average_risk(frame_analyses)
        
        # Generate primary advice
        primary_advice = self._generate_primary_advice(movement_patterns, risk_trend, average_risk)
        
        # Generate specific recommendations
        specific_recommendations = self._generate_specific_recommendations(frame_analyses, movement_patterns)
        
        # Generate safety warnings
        safety_warnings = self._generate_safety_warnings(frame_analyses, temporal_analysis)
        
        return {
            "primary_advice": primary_advice,
            "specific_recommendations": specific_recommendations,
            "safety_warnings": safety_warnings,
            "overall_assessment": self._generate_overall_assessment(frame_analyses, temporal_analysis),
            "action_items": self._generate_action_items(frame_analyses, movement_patterns)
        }
    
    def _generate_primary_advice(self, movement_patterns: Dict, risk_trend: str, average_risk: str) -> str:
        """
        Generate primary advice based on video analysis
        
        Args:
            movement_patterns: Obstacle movement patterns
            risk_trend: Overall risk trend
            average_risk: Average risk level
            
        Returns:
            Primary advice string
        """
        # Check for approaching obstacles
        approaching_obstacles = [obs for obs, pattern in movement_patterns.items() 
                               if pattern.get("pattern") == "approaching"]
        
        if approaching_obstacles:
            obstacle_list = ", ".join(approaching_obstacles)
            return f"⚠️ You are approaching {obstacle_list}. Consider changing direction or slowing down."
        
        # Check risk trend
        if risk_trend == "increasing":
            return "⚠️ Risk level is increasing. Exercise extra caution and consider stopping."
        elif risk_trend == "decreasing":
            return "✅ Risk level is decreasing. You're moving to a safer area."
        
        # Check average risk
        if average_risk == "high":
            return "🚨 High-risk environment detected. Proceed with extreme caution or find alternative route."
        elif average_risk == "medium":
            return "⚠️ Moderate risk environment. Stay alert and proceed carefully."
        else:
            return "✅ Low-risk environment. You can proceed normally."
    
    def _generate_specific_recommendations(self, frame_analyses: List[Dict], movement_patterns: Dict) -> List[str]:
        """
        Generate specific recommendations
        
        Args:
            frame_analyses: List of frame analyses
            movement_patterns: Obstacle movement patterns
            
        Returns:
            List of specific recommendations
        """
        recommendations = []
        
        # Analyze each obstacle type
        for obstacle_type, pattern in movement_patterns.items():
            if pattern.get("pattern") == "approaching":
                recommendations.append(f"Slow down when approaching {obstacle_type}")
            elif pattern.get("pattern") == "stable":
                recommendations.append(f"Find alternative route around {obstacle_type}")
            elif pattern.get("pattern") == "moving_away":
                recommendations.append(f"Good! You're moving away from {obstacle_type}")
        
        # Add general recommendations
        if not recommendations:
            recommendations.append("Path appears clear - proceed normally")
        
        return recommendations
    
    def _generate_safety_warnings(self, frame_analyses: List[Dict], temporal_analysis: Dict) -> List[str]:
        """
        Generate safety warnings
        
        Args:
            frame_analyses: List of frame analyses
            temporal_analysis: Temporal analysis results
            
        Returns:
            List of safety warnings
        """
        warnings = []
        
        # Check for high-risk frames
        high_risk_frames = [frame for frame in frame_analyses 
                           if self._calculate_frame_risk(frame) == "high"]
        
        if high_risk_frames:
            warnings.append(f"⚠️ {len(high_risk_frames)} high-risk moments detected")
        
        # Check for multiple obstacles
        multi_obstacle_frames = [frame for frame in frame_analyses 
                                if len(frame.get("obstacles", [])) > 2]
        
        if multi_obstacle_frames:
            warnings.append(f"⚠️ Multiple obstacles detected in {len(multi_obstacle_frames)} frames")
        
        # Check risk trend
        risk_trend = temporal_analysis.get("risk_trend", "stable")
        if risk_trend == "increasing":
            warnings.append("⚠️ Risk level is trending upward - consider stopping")
        
        return warnings
    
    def _generate_overall_assessment(self, frame_analyses: List[Dict], temporal_analysis: Dict) -> str:
        """
        Generate overall assessment
        
        Args:
            frame_analyses: List of frame analyses
            temporal_analysis: Temporal analysis results
            
        Returns:
            Overall assessment string
        """
        total_frames = len(frame_analyses)
        clear_frames = len([frame for frame in frame_analyses 
                           if not frame.get("obstacles", [])])
        
        clear_percentage = (clear_frames / total_frames) * 100
        
        if clear_percentage > 80:
            return "✅ Overall safe path with mostly clear frames"
        elif clear_percentage > 50:
            return "⚠️ Moderate obstacles detected, proceed with caution"
        else:
            return "🚨 High obstacle density detected, consider alternative route"
    
    def _generate_action_items(self, frame_analyses: List[Dict], movement_patterns: Dict) -> List[str]:
        """
        Generate actionable items
        
        Args:
            frame_analyses: List of frame analyses
            movement_patterns: Obstacle movement patterns
            
        Returns:
            List of action items
        """
        actions = []
        
        # Immediate actions
        approaching_obstacles = [obs for obs, pattern in movement_patterns.items() 
                               if pattern.get("pattern") == "approaching"]
        
        if approaching_obstacles:
            actions.append("STOP and assess the situation")
            actions.append("Look for alternative routes")
        
        # General actions
        actions.append("Stay alert and scan your surroundings")
        actions.append("Use your mobility aid if available")
        actions.append("Ask for assistance if needed")
        
        return actions
    
    def _identify_key_obstacles(self, frame_analyses: List[Dict]) -> List[Dict]:
        """
        Identify the most important obstacles in the video
        
        Args:
            frame_analyses: List of frame analyses
            
        Returns:
            List of key obstacles
        """
        # Count obstacle occurrences
        obstacle_counts = defaultdict(int)
        obstacle_details = defaultdict(list)
        
        for analysis in frame_analyses:
            for obstacle in analysis.get("obstacles", []):
                obstacle_type = obstacle.get("type", "unknown")
                obstacle_counts[obstacle_type] += 1
                obstacle_details[obstacle_type].append(obstacle)
        
        # Find most frequent obstacles
        key_obstacles = []
        for obstacle_type, count in sorted(obstacle_counts.items(), key=lambda x: x[1], reverse=True):
            if count >= 2:  # Appears in at least 2 frames
                details = obstacle_details[obstacle_type]
                avg_distance = sum(float(obs.get("distance", "5.0").split()[0]) for obs in details) / len(details)
                
                key_obstacles.append({
                    "type": obstacle_type,
                    "frequency": count,
                    "average_distance": avg_distance,
                    "severity": max(obs.get("severity", "low") for obs in details),
                    "description": f"{obstacle_type} appears in {count} frames"
                })
        
        return key_obstacles[:5]  # Top 5 obstacles
    
    def _generate_navigation_recommendations(self, frame_analyses: List[Dict], temporal_analysis: Dict) -> List[str]:
        """
        Generate navigation recommendations
        
        Args:
            frame_analyses: List of frame analyses
            temporal_analysis: Temporal analysis results
            
        Returns:
            List of navigation recommendations
        """
        recommendations = []
        
        # Analyze movement patterns
        movement_patterns = temporal_analysis.get("movement_patterns", {})
        
        for obstacle_type, pattern in movement_patterns.items():
            if pattern.get("pattern") == "approaching":
                recommendations.append(f"Change direction to avoid {obstacle_type}")
            elif pattern.get("pattern") == "stable":
                recommendations.append(f"Look for alternative route around {obstacle_type}")
        
        # Add general recommendations
        if not recommendations:
            recommendations.append("Continue on current path")
        
        recommendations.append("Stay in well-lit areas")
        recommendations.append("Use pedestrian crossings when available")
        
        return recommendations
    
    def _generate_temporal_summary(self, obstacle_tracks: Dict, risk_trend: str) -> str:
        """
        Generate temporal summary
        
        Args:
            obstacle_tracks: Obstacle tracking data
            risk_trend: Risk trend
            
        Returns:
            Temporal summary string
        """
        total_obstacles = len(obstacle_tracks)
        
        if total_obstacles == 0:
            return "Clear path throughout the video"
        
        summary_parts = [f"Detected {total_obstacles} types of obstacles"]
        
        if risk_trend == "increasing":
            summary_parts.append("Risk level is increasing")
        elif risk_trend == "decreasing":
            summary_parts.append("Risk level is decreasing")
        else:
            summary_parts.append("Risk level is stable")
        
        return ". ".join(summary_parts)
    
    def test_with_sample_images(self, assets_dir: str = "ai_walker/assets") -> None:
        """
        Test with images in assets directory
        
        Args:
            assets_dir: Assets directory path
        """
        print("Starting vision model test...")
        
        # Get all image files
        image_files = []
        for file in os.listdir(assets_dir):
            if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                image_files.append(os.path.join(assets_dir, file))
        
        if not image_files:
            print("No image files found in assets directory")
            return
        
        # Sort files by frame number
        image_files.sort(key=lambda x: int(x.split('_')[-1].split('.')[0]))
        
        # Select first few images for testing
        test_images = image_files[:10]  # Test with more frames
        print(f"Test images: {len(test_images)} frames")
        
        # Test video sequence analysis
        print("\n=== Testing Video Sequence Analysis ===")
        video_result = self.analyze_video_sequence(test_images, video_duration=30.0)
        
        print("Video Analysis Result:")
        print(json.dumps(video_result, ensure_ascii=False, indent=2))
        
        # Test individual frame analysis
        print("\n=== Testing Individual Frame Analysis ===")
        for i, image_path in enumerate(test_images[:3]):  # Test first 3 frames
            print(f"\n--- Frame {i+1}: {os.path.basename(image_path)} ---")
            
            result = self.analyze_single_image(image_path)
            
            print("Frame analysis:")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            
            # Generate frame description
            frame_desc = self.generate_frame_description(result.get("obstacles", []))
            print(f"\nStructured frame description:")
            print(json.dumps(frame_desc, ensure_ascii=False, indent=2))
            print("-" * 50)


if __name__ == "__main__":
    # Test code
    print("Testing Vision Model...")
    
    # Create vision model instance
    vision_model = VisionModel()
    
    # Test video sequence analysis
    print("\nTesting video sequence analysis...")
    vision_model.test_with_sample_images() 