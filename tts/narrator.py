"""
tts/narrator.py
Converts story text to narrated audio.
Supports gTTS (Google TTS) with optional ElevenLabs for premium voice.
"""

import os
import re
from pathlib import Path
from utils.logger import log

OUTPUT_DIR = "assets/audio"


class Narrator:
    def __init__(self, config: dict):
        self.config = config
        self.engine = config.get("tts_engine", "gtts")  # "gtts" or "elevenlabs"
        self.language = config.get("tts_language", "en")
        self.slow = config.get("tts_slow", False)
        Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    def _sanitize_filename(self, title: str) -> str:
        return re.sub(r"[^\w\s-]", "", title).strip().replace(" ", "_")[:50]

    def _build_script(self, story: dict) -> str:
        """
        Build the full narration script.
        Adds intro/outro hooks for engagement.
        """
        intro = f"Here is a story called: {story['title']}."
        outro = "That was a Creepypasta story. Sweet nightmares."
        return f"{intro}\n\n{story['text']}\n\n{outro}"

    def _generate_gtts(self, script: str, output_path: str) -> bool:
        """Generate audio using Google TTS (free, no API key needed)."""
        try:
            from gtts import gTTS
            tts = gTTS(text=script, lang=self.language, slow=self.slow)
            tts.save(output_path)
            return True
        except ImportError:
            log("gTTS not installed. Run: pip install gtts", level="error")
            return False
        except Exception as e:
            log(f"gTTS error: {e}", level="error")
            return False

    def _generate_elevenlabs(self, script: str, output_path: str) -> bool:
        """
        Generate audio using ElevenLabs API (premium, more realistic voice).
        Requires ELEVENLABS_API_KEY env variable.
        """
        import requests

        api_key = os.environ.get("ELEVENLABS_API_KEY")
        if not api_key:
            log("ELEVENLABS_API_KEY not set. Falling back to gTTS.", level="warn")
            return self._generate_gtts(script, output_path)

        # "Adam" voice — deep, dramatic, good for horror
        voice_id = self.config.get("elevenlabs_voice_id", "pNInz6obpgDQGcFmaJgB")
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "text": script,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.4,       # Slightly unstable = more dramatic
                "similarity_boost": 0.8,
            },
        }

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=60)
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(resp.content)
            return True
        except requests.RequestException as e:
            log(f"ElevenLabs error: {e}. Falling back to gTTS.", level="warn")
            return self._generate_gtts(script, output_path)

    def generate(self, story: dict) -> str | None:
        """Generate narration audio. Returns output file path."""
        filename = self._sanitize_filename(story["title"]) + ".mp3"
        output_path = os.path.join(OUTPUT_DIR, filename)

        # Don't regenerate if already exists
        if os.path.exists(output_path):
            log(f"Audio already exists, reusing: {output_path}")
            return output_path

        script = self._build_script(story)
        log(f"Narration script: {len(script.split())} words")

        if self.engine == "elevenlabs":
            success = self._generate_elevenlabs(script, output_path)
        else:
            success = self._generate_gtts(script, output_path)

        return output_path if success else None
