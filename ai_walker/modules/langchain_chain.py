# modules/langchain_chain.py
import os
import json
from typing import List, Dict, Any, Optional
from pathlib import Path

# LangChain imports
from langchain.schema import HumanMessage, SystemMessage
from langchain.prompts import PromptTemplate
from langchain.schema.output_parser import StrOutputParser
from langchain.schema.runnable import RunnablePassthrough
from langchain.chains import LLMChain
from langchain_community.llms import HuggingFacePipeline
from transformers import pipeline

# Local imports
from .vision_model import VisionModel
from .tts_output import Speaker

class SmartWalkerChain:
    """
    Smart Walker LangChain chain using Hugging Face models
    Integrates vision recognition, voice output, navigation suggestions and other functions
    """
    
    def __init__(self, device: str = "auto"):
        """
        Initialize smart walker chain
        
        Args:
            device: Device to use ('cpu', 'cuda', or 'auto')
        """
        self.device = device
        
        # Initialize components
        self.vision_model = VisionModel(device=device)
        self.speaker = Speaker()
        
        # Initialize HF text generation model
        self._load_text_model()
        
        # Define prompt templates
        self.advice_prompt = PromptTemplate(
            input_variables=["obstacles", "road_condition", "user_context"],
            template="""
You are a professional blind walker assistant. Based on the following information, provide safe and practical advice for blind users:

Obstacle information:
{obstacles}

Road condition information:
{road_condition}

User context:
{user_context}

Please provide:
1. Safety advice (highest priority)
2. Action guidance (specific movement instructions)
3. Navigation suggestions (if applicable)
4. Important notes

Requirements:
- Use clear and concise language
- Consider special needs of blind users
- Provide specific, actionable advice
- Use a gentle but firm tone
- Focus on directional guidance (left, right, straight, stop)
"""
        )
        
        # Create advice generation chain
        self.advice_chain = LLMChain(
            llm=self.text_llm,
            prompt=self.advice_prompt
        )
        
        # Navigation advice template
        self.navigation_prompt = PromptTemplate(
            input_variables=["location", "destination", "obstacles"],
            template="""
You are a navigation assistant. Based on current location and destination, provide navigation advice for blind users:

Current location: {location}
Destination: {destination}
Current obstacles: {obstacles}

Please provide:
1. Best route suggestions
2. Road sections to be aware of
3. Safety reminders
4. Estimated arrival time

Requirements:
- Consider safety needs of blind users
- Avoid dangerous road sections
- Provide clear instructions
- Use directional language (left, right, straight, turn)
"""
        )
        
        self.navigation_chain = LLMChain(
            llm=self.text_llm,
            prompt=self.navigation_prompt
        )
    
    def _load_text_model(self):
        """Load Hugging Face text generation model"""
        try:
            print("Loading text generation model...")
            
            # Use a smaller, faster model for text generation
            text_generator = pipeline(
                "text-generation",
                model="distilgpt2",  # 更轻量的模型
                device=-1 if self.device == "cpu" else 0,
                max_length=200,
                temperature=0.7,
                do_sample=True
            )
            
            # Wrap in LangChain LLM
            self.text_llm = HuggingFacePipeline(pipeline=text_generator)
            
            print("Text model loaded successfully!")
            
        except Exception as e:
            print(f"Error loading text model: {e}")
            raise
    
    def process_image_and_generate_advice(self, image_path: str, user_context: str = "") -> Dict[str, Any]:
        """
        Process image and generate advice
        
        Args:
            image_path: Image path
            user_context: User context information
            
        Returns:
            Processing result dictionary
        """
        try:
            # 1. Vision analysis
            print("🔍 Performing vision analysis...")
            vision_result = self.vision_model.analyze_single_image(image_path)
            
            # 2. Format obstacle information
            obstacles_text = self._format_obstacles(vision_result.get("obstacles", []))
            
            # 3. Generate advice
            print("💡 Generating advice...")
            advice_result = self.advice_chain.run({
                "obstacles": obstacles_text,
                "road_condition": vision_result.get("road_condition", "Unknown road condition"),
                "user_context": user_context
            })
            
            # 4. Generate safety advice
            safety_advice = self.vision_model._generate_safety_advice(vision_result.get("obstacles", []))
            
            # 5. Integrate results
            result = {
                "vision_analysis": vision_result,
                "ai_advice": advice_result,
                "safety_advice": safety_advice,
                "timestamp": self._get_timestamp(),
                "image_path": image_path
            }
            
            return result
            
        except Exception as e:
            print(f"Error processing image: {e}")
            return {
                "error": str(e),
                "vision_analysis": {},
                "ai_advice": "Processing failed, please retry",
                "safety_advice": "Please proceed with caution",
                "timestamp": self._get_timestamp(),
                "image_path": image_path
            }
    
    def process_image_sequence(self, image_paths: List[str], user_context: str = "") -> Dict[str, Any]:
        """
        Process image sequence
        
        Args:
            image_paths: List of image paths
            user_context: User context information
            
        Returns:
            Processing result dictionary
        """
        try:
            # 1. Vision analysis
            print("🔍 Performing sequence vision analysis...")
            vision_result = self.vision_model.analyze_image_sequence(image_paths)
            
            # 2. Format obstacle information
            obstacles_text = self._format_obstacles(vision_result.get("obstacles", []))
            
            # 3. Generate sequence advice
            print("💡 Generating sequence advice...")
            advice_result = self.advice_chain.run({
                "obstacles": obstacles_text,
                "road_condition": vision_result.get("road_condition", "Unknown road condition"),
                "user_context": user_context
            })
            
            # 4. Generate safety advice
            safety_advice = self.vision_model._generate_safety_advice(vision_result.get("obstacles", []))
            
            # 5. Integrate results
            result = {
                "vision_analysis": vision_result,
                "ai_advice": advice_result,
                "safety_advice": safety_advice,
                "timestamp": self._get_timestamp(),
                "image_count": len(image_paths),
                "image_paths": image_paths
            }
            
            return result
            
        except Exception as e:
            print(f"Error processing image sequence: {e}")
            return {
                "error": str(e),
                "vision_analysis": {},
                "ai_advice": "Processing failed, please retry",
                "safety_advice": "Please proceed with caution",
                "timestamp": self._get_timestamp(),
                "image_count": len(image_paths),
                "image_paths": image_paths
            }
    
    def generate_navigation_advice(self, location: str, destination: str, obstacles: List[Dict[str, Any]]) -> str:
        """
        Generate navigation advice
        
        Args:
            location: Current location
            destination: Destination
            obstacles: List of obstacles
            
        Returns:
            Navigation advice text
        """
        try:
            obstacles_text = self._format_obstacles(obstacles)
            
            navigation_result = self.navigation_chain.run({
                "location": location,
                "destination": destination,
                "obstacles": obstacles_text
            })
            
            return navigation_result
            
        except Exception as e:
            print(f"Error generating navigation advice: {e}")
            return "Navigation advice generation failed, please retry."
    
    def speak_advice(self, advice_text: str) -> None:
        """
        Voice broadcast advice
        
        Args:
            advice_text: Advice text
        """
        try:
            print("🔊 Broadcasting advice...")
            self.speaker.speak(advice_text)
        except Exception as e:
            print(f"Error in voice broadcast: {e}")
    
    def process_and_speak(self, image_path: str, user_context: str = "") -> Dict[str, Any]:
        """
        Process image and voice broadcast
        
        Args:
            image_path: Image path
            user_context: User context information
            
        Returns:
            Processing result dictionary
        """
        # Process image
        result = self.process_image_and_generate_advice(image_path, user_context)
        
        # Voice broadcast
        if "ai_advice" in result:
            self.speak_advice(result["ai_advice"])
        
        return result
    
    def _format_obstacles(self, obstacles: List[Dict[str, Any]]) -> str:
        """
        Format obstacle information
        
        Args:
            obstacles: List of obstacles
            
        Returns:
            Formatted obstacle text
        """
        if not obstacles:
            return "No obstacles detected"
        
        formatted = []
        for obs in obstacles:
            obs_text = f"- {obs.get('type', 'Unknown obstacle')}"
            if obs.get('distance'):
                obs_text += f" (Distance: {obs.get('distance')})"
            if obs.get('direction'):
                obs_text += f" (Direction: {obs.get('direction')})"
            if obs.get('severity'):
                obs_text += f" (Danger level: {obs.get('severity')})"
            if obs.get('description'):
                obs_text += f" - {obs.get('description')}"
            formatted.append(obs_text)
        
        return "\n".join(formatted)
    
    def _get_timestamp(self) -> str:
        """
        Get current timestamp
        
        Returns:
            Timestamp string
        """
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def save_analysis_result(self, result: Dict[str, Any], output_path: str) -> None:
        """
        Save analysis result to file
        
        Args:
            result: Analysis result
            output_path: Output file path
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"Analysis result saved to: {output_path}")
        except Exception as e:
            print(f"Error saving result: {e}")
    
    def test_chain(self, assets_dir: str = "ai_walker/assets") -> None:
        """
        Test the entire chain functionality
        
        Args:
            assets_dir: Assets directory path
        """
        print("🧪 Starting smart walker chain test...")
        
        # Get test images
        image_files = []
        for file in os.listdir(assets_dir):
            if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                image_files.append(os.path.join(assets_dir, file))
        
        if not image_files:
            print("No image files found in assets directory")
            return
        
        # Select first 3 images for testing
        test_images = sorted(image_files)[:3]
        
        for i, image_path in enumerate(test_images):
            print(f"\n=== Test {i+1}: {os.path.basename(image_path)} ===")
            
            # Process image and generate advice
            result = self.process_image_and_generate_advice(
                image_path, 
                "User is walking with walker"
            )
            
            print("Analysis result:")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            
            # Voice broadcast (optional)
            # self.speak_advice(result.get("ai_advice", ""))
            
            print("=" * 60)


if __name__ == "__main__":
    # Test code
    print("Testing Smart Walker Chain...")
    
    # Create smart walker chain
    chain = SmartWalkerChain()
    
    # Test chain functionality
    chain.test_chain() 