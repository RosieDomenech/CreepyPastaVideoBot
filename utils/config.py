"""
utils/config.py
Loads config.toml on first run; prompts user if missing.
"""

import os
import sys

try:
    import tomllib          # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib    # pip install tomli
    except ImportError:
        tomllib = None

CONFIG_FILE = "config.toml"

DEFAULTS = {
    "tts_engine": "gtts",           # "gtts" or "elevenlabs"
    "tts_language": "en",
    "tts_slow": False,
    "max_words": 800,
    "min_words": 150,
    "words_per_chunk": 10,
    "resolution": [1080, 1920],
    "fps": 30,
    "bg_color": [10, 5, 15],
    "text_color": [220, 210, 200],
    "title_color": [180, 30, 30],
}

TEMPLATE = """\
# CreepyPasta Video Bot — Configuration
# Edit these values then re-run main.py

# TTS engine: "gtts" (free) or "elevenlabs" (premium, set ELEVENLABS_API_KEY env var)
tts_engine = "gtts"

# Language code for gTTS (en, es, fr, de, etc.)
tts_language = "en"

# Slow narration? (true for more dramatic pacing)
tts_slow = false

# Story length limits (words)
min_words = 150
max_words = 800

# How many words appear on screen at once
words_per_chunk = 10

# Video resolution [width, height] — 1080x1920 = vertical TikTok/Reels format
resolution = [1080, 1920]
fps = 30

# Background color [R, G, B] — used if no background.mp4 supplied
bg_color = [10, 5, 15]

# Text colors [R, G, B]
text_color = [220, 210, 200]
title_color = [180, 30, 30]

# ── Background Visuals ────────────────────────────────────────────────────
[background]
# Generate AI horror image per story via Pollinations.ai (free, no API key)
use_ai_images = true

# Use random video from assets/backgrounds/ folder
# Download free dark videos from pexels.com and drop them in assets/backgrounds/
use_background_videos = true

# ── YouTube Upload (optional) ─────────────────────────────────────────────
[youtube]
# Set to true to enable automatic YouTube upload after video creation
enabled = false

# Privacy: "public", "unlisted", or "private"
# Recommendation: start with "unlisted" until you're happy with the output
privacy_status = "unlisted"

# Title template — {title} is replaced with the story title
title_template = "{title} 😱 #creepypasta #scary #horror"

# Upload rate limiting (avoids YouTube spam flags)
max_uploads_per_day = 2
min_hours_between_uploads = 12

# YouTube category ID — 24 = Entertainment, 22 = People & Blogs
category_id = "24"

# Tags (added to every video)
tags = [
  "creepypasta", "horror", "scary stories", "creepy",
  "horror stories", "nosleep", "paranormal", "scary"
]
"""


def load_config() -> dict:
    if not os.path.exists(CONFIG_FILE):
        print(f"\n⚙️  No config found. Creating {CONFIG_FILE} with defaults...")
        with open(CONFIG_FILE, "w") as f:
            f.write(TEMPLATE)
        print(f"✅ Config created. Edit {CONFIG_FILE} if needed, then re-run.\n")

    if tomllib is None:
        print("⚠️  tomllib/tomli not available. Using default config.")
        return DEFAULTS.copy()

    try:
        with open(CONFIG_FILE, "rb") as f:
            user_config = tomllib.load(f)
        config = {**DEFAULTS, **user_config}
        return config
    except Exception as e:
        print(f"⚠️  Error reading config: {e}. Using defaults.")
        return DEFAULTS.copy()
