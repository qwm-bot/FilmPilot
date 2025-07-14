# modules/advice_generator.py
import json
import requests
from datetime import datetime
from typing import Dict, Any, List

class AdviceGenerator:
    """
    Advice generator using DashScope Qwen API (or other LLM API)
    """

    def __init__(self, api_key: str, model: str = "qwen-turbo"):
        self.api_key = api_key
        self.model = model
        self.api_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"

    def generate_advice(self, analysis_summaries: List[str], user_context: str = "") -> Dict[str, Any]:
        """
        Generate advice using Qwen API, based on a list of frame/video analysis summaries
        """
        try:
            prompt = self._create_qwen_prompt(analysis_summaries, user_context)
            response_text = self._call_dashscope(prompt)
            advice_text = response_text.strip()
            return {
                "advice_type": "api_generated",
                "advice_text": advice_text,
                "confidence": "high",
                "timestamp": datetime.now().isoformat(),
                "model_used": self.model
            }
        except Exception as e:
            print(f"[DashScope Error] {e}")
            return self._generate_fallback_advice(analysis_summaries)

    def _call_dashscope(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "input": {"prompt": prompt},
            "parameters": {"temperature": 0.7, "max_tokens": 200}
        }
        response = requests.post(self.api_url, headers=headers, json=payload)
        result = response.json()
        if "output" in result and "text" in result["output"]:
            return result["output"]["text"]
        else:
            raise ValueError(f"Invalid response: {json.dumps(result, indent=2)}")

    def _create_qwen_prompt(self, analysis_summaries: List[str], user_context: str) -> str:
        prompt = "You are a professional blind navigation assistant. Please provide safe, specific, and actionable advice for blind users based on the following video analysis summaries:\n"
        for i, summary in enumerate(analysis_summaries):
            prompt += f"Frame {i+1}: {summary}\n"
        if user_context:
            prompt += f"\nUser Context: {user_context}\n"
        prompt += "\nPlease provide in clear and concise language:\n1. Primary action recommendation (e.g., stop, turn left, turn right, proceed, etc.)\n2. Specific safety reminders\n3. Navigation instructions\n4. Important notes and warnings\n"
        return prompt

    def _generate_fallback_advice(self, analysis_summaries: List[str]) -> Dict[str, Any]:
        if not analysis_summaries:
            return {
                "advice_type": "fallback",
                "advice_text": "No obstacles detected, path is relatively safe, please proceed normally.",
                "confidence": "low",
                "timestamp": datetime.now().isoformat(),
                "model_used": "fallback"
            }
        return {
            "advice_type": "fallback",
            "advice_text": "Obstacles detected, please proceed with caution and be aware of your surroundings.",
            "confidence": "low",
            "timestamp": datetime.now().isoformat(),
            "model_used": "fallback"
        }

