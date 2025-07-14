# modules/tts_auto.py

import pyttsx3
from langdetect import detect
import re

class Speaker:
    def __init__(self, rate=150):
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", rate)
        self.voices = self.engine.getProperty("voices")
        self.lang_voice_map = self._build_lang_voice_map()

    def _build_lang_voice_map(self):
        """build language to voice.id mapping"""
        lang_voice_map = {}
        for voice in self.voices:
            langs = voice.languages if voice.languages else []
            for lang in langs:
                try:
                    lang_str = lang.decode("utf-8").lower()
                    lang_code = re.findall(r'[a-z]{2}', lang_str)[0]
                    if lang_code not in lang_voice_map:
                        lang_voice_map[lang_code] = voice.id
                except Exception:
                    continue
        return lang_voice_map

    def _detect_lang(self, text):
        try:
            return detect(text)[:2]  # return  'zh', 'en' ...
        except Exception:
            return "en"

    def speak(self, text):
        if not text.strip():
            return
        lang = self._detect_lang(text)
        voice_id = self.lang_voice_map.get(lang)
        if voice_id:
            self.engine.setProperty("voice", voice_id)
        else:
            print(f"[TTS] No voice found for language '{lang}', using default.")

        print(f"[TTS] Speaking ({lang}): {text}")
        self.engine.say(text)
        self.engine.runAndWait()

