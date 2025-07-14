# main.py
import os
import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add module path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.vision_model import VisionModel
from modules.langchain_chain import SmartWalkerChain
from modules.tts_output import Speaker
from modules.video_reader import extract_frames
from modules.advice_generator import AdviceGenerator

class SmartWalkerSystem:
    """
    Smart Walker System using Hugging Face models
    Integrates vision recognition, voice output, navigation and other functions
    """
    
    def __init__(self, device: str = "auto"):
        """
        Initialize smart walker system
        
        Args:
            device: Device to use ('cpu', 'cuda', or 'auto')
        """
        self.device = device
        
        # Initialize components
        self.vision_model = VisionModel(device=device)
        self.chain = SmartWalkerChain(device=device)
        self.speaker = Speaker()
        # Note: AdviceGenerator now requires api_key parameter
        # self.advice_generator = AdviceGenerator(api_key="YOUR_API_KEY")
        
        # System status
        self.is_running = False
        self.current_location = "Unknown location"
        self.destination = None
        self.analysis_history = []
        
        print("🤖 Smart Walker System initialized")
    
    def start_system(self):
        """
        Start system
        """
        self.is_running = True
        print("🚀 Smart Walker System started")
        self.speaker.speak("Smart Walker System started, beginning to serve you")
    
    def stop_system(self):
        """
        Stop system
        """
        self.is_running = False
        print("🛑 Smart Walker System stopped")
        self.speaker.speak("System stopped")
    
    def process_realtime_image(self, image_path: str, user_context: str = "") -> Dict[str, Any]:
        """
        Process real-time image
        
        Args:
            image_path: Image path
            user_context: User context
            
        Returns:
            Processing result
        """
        if not self.is_running:
            return {"error": "System not started"}
        
        try:
            print(f"📸 Processing image: {os.path.basename(image_path)}")
            
            # Analyze image with vision model
            vision_result = self.vision_model.analyze_single_image(image_path)
            
            # Note: AdviceGenerator interface has changed
            # advice_result = self.advice_generator.generate_advice([vision_result], user_context)
            # guidance_result = self.advice_generator.generate_directional_guidance(vision_result)
            advice_result = {"advice_text": "Advice generation requires API key configuration"}
            guidance_result = {"guidance": "Directional guidance requires API key configuration"}
            
            # Combine results
            result = {
                "vision_analysis": vision_result,
                "ai_advice": advice_result,
                "directional_guidance": guidance_result,
                "timestamp": time.time()
            }
            
            # Save to history
            self.analysis_history.append(result)
            
            # Voice broadcast
            if "ai_advice" in result and result["ai_advice"].get("advice_text"):
                self.speaker.speak(result["ai_advice"]["advice_text"])
            
            return result
            
        except Exception as e:
            error_msg = f"Error processing image: {e}"
            print(error_msg)
            self.speaker.speak("Processing failed, please retry")
            return {"error": error_msg}
    
    def process_video_frames(self, video_path: str, frame_rate: int = 30) -> List[Dict[str, Any]]:
        """
        Process video frames
        
        Args:
            video_path: Video path
            frame_rate: Frame extraction rate
            
        Returns:
            Processing result list
        """
        results = []
        
        try:
            print(f"🎬 Starting video processing: {video_path}")
            
            # Extract frames
            frame_paths = []
            for frame_path in extract_frames(video_path, frame_rate):
                frame_paths.append(frame_path)
            
            print(f"📊 Extracted {len(frame_paths)} frames")
            
            # Process each frame
            for i, frame_path in enumerate(frame_paths):
                print(f"Processing frame {i+1}/{len(frame_paths)}")
                
                result = self.process_realtime_image(
                    frame_path, 
                    f"Video frame {i+1}, user is walking with walker"
                )
                
                results.append(result)
                
                # Avoid too frequent processing
                time.sleep(1)
            
            return results
            
        except Exception as e:
            print(f"Error processing video: {e}")
            return [{"error": str(e)}]
    
    def set_navigation_destination(self, destination: str):
        """
        Set navigation destination
        
        Args:
            destination: Destination
        """
        self.destination = destination
        print(f"🗺️ Destination set: {destination}")
        self.speaker.speak(f"Destination set to {destination}")
    
    def get_navigation_advice(self, current_location: str) -> str:
        """
        Get navigation advice
        
        Args:
            current_location: Current location
            
        Returns:
            Navigation advice
        """
        if not self.destination:
            return "Please set destination first"
        
        # Get recent obstacle information
        recent_obstacles = []
        if self.analysis_history:
            latest_result = self.analysis_history[-1]
            if "vision_analysis" in latest_result:
                recent_obstacles = latest_result["vision_analysis"].get("obstacles", [])
        
        # Generate navigation advice
        navigation_advice = self.chain.generate_navigation_advice(
            current_location, 
            self.destination, 
            recent_obstacles
        )
        
        return navigation_advice
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get system status
        
        Returns:
            System status information
        """
        return {
            "is_running": self.is_running,
            "current_location": self.current_location,
            "destination": self.destination,
            "analysis_count": len(self.analysis_history),
            "last_analysis": self.analysis_history[-1] if self.analysis_history else None,
            "device": self.device
        }
    
    def save_analysis_history(self, output_path: str):
        """
        Save analysis history
        
        Args:
            output_path: Output file path
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.analysis_history, f, ensure_ascii=False, indent=2)
            print(f"Analysis history saved to: {output_path}")
        except Exception as e:
            print(f"Error saving analysis history: {e}")
    
    def test_with_assets(self, max_images: int = 5):
        """
        Test with images in assets directory
        
        Args:
            max_images: Maximum number of test images
        """
        print("🧪 Starting system test...")
        
        # Start system
        self.start_system()
        
        # Get test images
        assets_dir = "ai_walker/assets"
        image_files = []
        for file in os.listdir(assets_dir):
            if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                image_files.append(os.path.join(assets_dir, file))
        
        if not image_files:
            print("No image files found in assets directory")
            return
        
        # Select test images
        test_images = sorted(image_files)[:max_images]
        print(f"Number of test images: {len(test_images)}")
        
        # Process each image
        for i, image_path in enumerate(test_images):
            print(f"\n=== Test {i+1}/{len(test_images)}: {os.path.basename(image_path)} ===")
            
            result = self.process_realtime_image(
                image_path,
                f"Test image {i+1}, user is walking with walker"
            )
            
            print("Processing result:")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            
            # Wait before processing next image
            time.sleep(2)
        
        # Show system status
        status = self.get_system_status()
        print(f"\nSystem status: {json.dumps(status, ensure_ascii=False, indent=2)}")
        
        # Stop system
        self.stop_system()
        
        print("✅ System test completed")
    
    def get_detailed_obstacle_info(self, image_path: str) -> Dict[str, Any]:
        """
        Get detailed obstacle information with directional guidance
        
        Args:
            image_path: Image path
            
        Returns:
            Detailed obstacle information
        """
        try:
            # Process image
            result = self.process_realtime_image(image_path)
            
            if "error" in result:
                return result
            
            # Extract obstacle information
            obstacles = result.get("vision_analysis", {}).get("obstacles", [])
            
            # Generate detailed directional guidance
            directional_guidance = self._generate_directional_guidance(obstacles)
            
            # Add to result
            result["directional_guidance"] = directional_guidance
            
            return result
            
        except Exception as e:
            return {"error": f"Error getting detailed obstacle info: {e}"}
    
    def _generate_directional_guidance(self, obstacles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate detailed directional guidance based on obstacles
        
        Args:
            obstacles: List of obstacles
            
        Returns:
            Directional guidance information
        """
        if not obstacles:
            return {
                "action": "proceed",
                "direction": "straight",
                "message": "Path is clear, you can proceed straight ahead.",
                "confidence": "high"
            }
        
        # Group obstacles by direction
        left_obstacles = [obs for obs in obstacles if "left" in obs.get("direction", "")]
        right_obstacles = [obs for obs in obstacles if "right" in obs.get("direction", "")]
        center_obstacles = [obs for obs in obstacles if "ahead" in obs.get("direction", "")]
        
        # Determine best action
        if center_obstacles:
            # Obstacles ahead - need to turn
            high_risk_center = [obs for obs in center_obstacles if obs.get("severity") == "high"]
            if high_risk_center:
                # High risk ahead - must turn
                if len(left_obstacles) < len(right_obstacles):
                    return {
                        "action": "turn",
                        "direction": "left",
                        "message": f"High-risk {high_risk_center[0]['type']} ahead. Turn left to avoid.",
                        "confidence": "high",
                        "reason": f"High-risk obstacle ahead: {high_risk_center[0]['type']}"
                    }
                else:
                    return {
                        "action": "turn",
                        "direction": "right",
                        "message": f"High-risk {high_risk_center[0]['type']} ahead. Turn right to avoid.",
                        "confidence": "high",
                        "reason": f"High-risk obstacle ahead: {high_risk_center[0]['type']}"
                    }
            else:
                # Medium/low risk ahead - proceed carefully
                return {
                    "action": "proceed_carefully",
                    "direction": "straight",
                    "message": f"Proceed carefully past the {center_obstacles[0]['type']} ahead.",
                    "confidence": "medium",
                    "reason": f"Obstacle ahead: {center_obstacles[0]['type']}"
                }
        
        elif left_obstacles and right_obstacles:
            # Obstacles on both sides - choose safer side
            left_risk = max([obs.get("severity", "low") for obs in left_obstacles])
            right_risk = max([obs.get("severity", "low") for obs in right_obstacles])
            
            if left_risk == "high" and right_risk != "high":
                return {
                    "action": "turn",
                    "direction": "right",
                    "message": "Turn right to avoid high-risk obstacles on your left.",
                    "confidence": "high",
                    "reason": "High-risk obstacles on left"
                }
            elif right_risk == "high" and left_risk != "high":
                return {
                    "action": "turn",
                    "direction": "left",
                    "message": "Turn left to avoid high-risk obstacles on your right.",
                    "confidence": "high",
                    "reason": "High-risk obstacles on right"
                }
            else:
                return {
                    "action": "proceed",
                    "direction": "straight",
                    "message": "Proceed straight, obstacles on sides are manageable.",
                    "confidence": "medium",
                    "reason": "Obstacles on both sides"
                }
        
        elif left_obstacles:
            # Obstacles on left - turn right
            return {
                "action": "turn",
                "direction": "right",
                "message": f"Turn right to avoid {left_obstacles[0]['type']} on your left.",
                "confidence": "high",
                "reason": f"Obstacle on left: {left_obstacles[0]['type']}"
            }
        
        elif right_obstacles:
            # Obstacles on right - turn left
            return {
                "action": "turn",
                "direction": "left",
                "message": f"Turn left to avoid {right_obstacles[0]['type']} on your right.",
                "confidence": "high",
                "reason": f"Obstacle on right: {right_obstacles[0]['type']}"
            }
        
        else:
            return {
                "action": "proceed",
                "direction": "straight",
                "message": "Path is clear, proceed straight ahead.",
                "confidence": "high",
                "reason": "No obstacles detected"
            }


def main():
    """
    Main function
    """
    print("🤖 Smart Walker System")
    print("=" * 50)
    
    # Check if CUDA is available
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    
    # Create smart walker system
    system = SmartWalkerSystem(device=device)
    
    # Test system
    system.test_with_assets(max_images=3)
    
    # Save analysis history
    system.save_analysis_history("ai_walker/analysis_history.json")


if __name__ == "__main__":
    main() 