"""
video_creation/background_manager.py

Manages background visuals for each video:
1. Tries to generate an AI image via Pollinations.ai (free, no API key)
2. Falls back to a random video from assets/backgrounds/
3. Falls back to solid dark color if nothing else available
"""

import os
import random
import re
import requests
import time
from pathlib import Path
from utils.logger import log

BACKGROUNDS_DIR = "assets/backgrounds"
AI_IMAGES_DIR = "assets/ai_images"


class BackgroundManager:
    def __init__(self, config: dict):
        self.config = config
        Path(BACKGROUNDS_DIR).mkdir(parents=True, exist_ok=True)
        Path(AI_IMAGES_DIR).mkdir(parents=True, exist_ok=True)

    def _safe_filename(self, title: str) -> str:
        return re.sub(r'[\\/*?:"<>|]', "", title).strip().replace(" ", "_")[:50]

    # ── AI IMAGE GENERATION ───────────────────────────────────────────────

    def _build_horror_prompt(self, story_title: str) -> str:
        """Build a cinematic horror image prompt from the story title."""
        style = (
            "cinematic horror photography, dark and atmospheric, "
            "dramatic shadows, eerie lighting, mist and fog, "
            "ultra detailed, 4k, moody color grading, no text"
        )
        return f"{story_title}, {style}"

    def generate_ai_image(self, story: dict) -> str | None:
        """
        Generate a horror image using Pollinations.ai (completely free, no key).
        Returns local file path of saved image.
        """
        safe = self._safe_filename(story["title"])
        output_path = os.path.join(AI_IMAGES_DIR, f"{safe}.jpg")

        # Return cached image if already generated
        if os.path.exists(output_path):
            log(f"Using cached AI image: {output_path}")
            return output_path

        prompt = self._build_horror_prompt(story["title"])
        # Pollinations.ai free image API
        encoded_prompt = requests.utils.quote(prompt)
        url = (
            f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            f"?width=1080&height=1920&nologo=true&seed={random.randint(1, 99999)}"
        )

        log(f"Generating AI image for: {story['title']}")
        log("This may take 10-20 seconds...")

        try:
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()

            if "image" not in resp.headers.get("Content-Type", ""):
                log("Pollinations returned non-image response.", level="warn")
                return None

            with open(output_path, "wb") as f:
                f.write(resp.content)

            log(f"AI image saved: {output_path}")
            return output_path

        except requests.RequestException as e:
            log(f"AI image generation failed: {e}", level="warn")
            return None

    # ── BACKGROUND VIDEO PICKER ───────────────────────────────────────────

    def get_random_background_video(self) -> str | None:
        """
        Pick a random video from assets/backgrounds/.
        Supports .mp4, .mov, .avi
        """
        extensions = {".mp4", ".mov", ".avi"}
        videos = [
            f for f in Path(BACKGROUNDS_DIR).iterdir()
            if f.suffix.lower() in extensions
        ]

        if not videos:
            log(
                "No background videos found in assets/backgrounds/\n"
                "  Tip: Download free dark atmospheric videos from pexels.com\n"
                "  and place them in assets/backgrounds/",
                level="warn"
            )
            return None

        chosen = random.choice(videos)
        log(f"Using background video: {chosen.name}")
        return str(chosen)

    # ── MAIN ENTRY ────────────────────────────────────────────────────────

    def get_background(self, story: dict) -> dict:
        """
        Returns a dict describing the best available background:
        {
            "type": "ai_image" | "video" | "color",
            "path": "path/to/file" or None,
            "color": [R, G, B]  (only for type="color")
        }
        """
        cfg = self.config.get("background", {})
        use_ai = cfg.get("use_ai_images", True)
        use_videos = cfg.get("use_background_videos", True)

        # Try AI image first
        if use_ai:
            img_path = self.generate_ai_image(story)
            if img_path:
                return {"type": "ai_image", "path": img_path}

        # Try random background video
        if use_videos:
            vid_path = self.get_random_background_video()
            if vid_path:
                return {"type": "video", "path": vid_path}

        # Fallback: solid color
        log("Using solid color background as fallback.")
        return {
            "type": "color",
            "path": None,
            "color": self.config.get("bg_color", [10, 5, 15])
        }
