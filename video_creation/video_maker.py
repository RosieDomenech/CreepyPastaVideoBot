"""
video_creation/video_maker.py

Assembles the final horror video:
  - Dark atmospheric background (color or user-supplied footage)
  - Story text rendered in creepy font, appearing in sync with narration
  - Subtle flicker / vignette effects
  - Audio narration baked in
  - Output: MP4 ready for upload
"""

import os
import textwrap
from pathlib import Path
from utils.logger import log

OUTPUT_DIR = "assets/output"
FONT_PATH = "assets/fonts/CreepsterCaps.ttf"   # Fallback to system if missing
BACKGROUND_VIDEO = "assets/background.mp4"     # User-supplied (e.g., dark forest loop)


class VideoMaker:
    def __init__(self, config: dict):
        self.config = config
        self.resolution = tuple(config.get("resolution", [1080, 1920]))   # 9:16 portrait
        self.fps = config.get("fps", 30)
        self.bg_color = tuple(config.get("bg_color", [10, 5, 15]))        # Near-black purple
        self.text_color = tuple(config.get("text_color", [220, 210, 200])) # Off-white
        self.title_color = tuple(config.get("title_color", [180, 30, 30])) # Blood red
        self.words_per_chunk = config.get("words_per_chunk", 10)
        Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    def _chunk_text(self, text: str) -> list[str]:
        """Split story into short display chunks (subtitle-style)."""
        words = text.split()
        chunks = []
        for i in range(0, len(words), self.words_per_chunk):
            chunk = " ".join(words[i : i + self.words_per_chunk])
            chunks.append(chunk)
        return chunks

    def _make_text_clip(self, moviepy, text: str, duration: float, is_title: bool = False):
        """Create a text clip with a creepy aesthetic."""
        from moviepy.editor import TextClip

        color = self.title_color if is_title else self.text_color
        fontsize = 72 if is_title else 54
        font = FONT_PATH if os.path.exists(FONT_PATH) else "DejaVu-Sans"

        wrapped = textwrap.fill(text, width=22)

        clip = (
            TextClip(
                wrapped,
                fontsize=fontsize,
                color=f"rgb({color[0]},{color[1]},{color[2]})",
                font=font,
                method="caption",
                size=(self.resolution[0] - 120, None),
                align="center",
                stroke_color="black",
                stroke_width=3,
            )
            .set_duration(duration)
            .set_position("center")
        )
        return clip

    def _build_background(self, moviepy, duration: float):
        """Create a dark background — uses supplied video or solid color."""
        from moviepy.editor import VideoFileClip, ColorClip

        if os.path.exists(BACKGROUND_VIDEO):
            log("Using supplied background video.")
            bg = VideoFileClip(BACKGROUND_VIDEO).loop(duration=duration)
            bg = bg.resize(self.resolution[::-1])   # MoviePy uses (W, H)
            # Darken it
            bg = bg.fl_image(lambda frame: (frame * 0.35).astype("uint8"))
        else:
            log("No background video found — using dark color background.")
            log("Tip: Place a looping dark video at assets/background.mp4 for best results.")
            bg = ColorClip(
                size=(self.resolution[0], self.resolution[1]),
                color=self.bg_color,
                duration=duration,
            )

        return bg

    def _add_flicker(self, clip):
        """Apply a subtle brightness flicker for atmosphere."""
        import random

        def flicker(get_frame, t):
            frame = get_frame(t)
            # Random slight darkening
            factor = random.uniform(0.92, 1.0)
            return (frame * factor).clip(0, 255).astype("uint8")

        return clip.fl(flicker, apply_to="video")

    def create(self, story: dict, audio_path: str) -> str | None:
        """Main method — assembles and exports the final video."""
        try:
            import moviepy.editor as mpy
            from moviepy.editor import (
                AudioFileClip,
                CompositeVideoClip,
                concatenate_videoclips,
            )
        except ImportError:
            log("moviepy not installed. Run: pip install moviepy", level="error")
            return None

        # Load audio to get total duration
        audio = AudioFileClip(audio_path)
        total_duration = audio.duration
        log(f"Audio duration: {total_duration:.1f}s")

        # Build background
        background = self._build_background(mpy, total_duration)

        # Title card (first 4 seconds)
        title_duration = min(4.0, total_duration * 0.1)
        title_clip = self._make_text_clip(
            mpy, story["title"], duration=title_duration, is_title=True
        ).set_start(0)

        # Body text — distribute chunks evenly over remaining time
        chunks = self._chunk_text(story["text"])
        body_start = title_duration
        body_duration = total_duration - body_start
        chunk_duration = body_duration / max(len(chunks), 1)

        body_clips = []
        for i, chunk in enumerate(chunks):
            start = body_start + i * chunk_duration
            clip = self._make_text_clip(mpy, chunk, duration=chunk_duration).set_start(start)
            body_clips.append(clip)

        # Compose all layers
        all_clips = [background, title_clip] + body_clips
        composite = CompositeVideoClip(all_clips, size=(self.resolution[0], self.resolution[1]))
        composite = composite.set_duration(total_duration)

        # Add flicker
        composite = self._add_flicker(composite)

        # Bake audio
        composite = composite.set_audio(audio)

        # Export
        safe_title = story["title"].replace(" ", "_").replace("/", "-")[:40]
        output_path = os.path.join(OUTPUT_DIR, f"{safe_title}.mp4")

        log(f"Rendering video to {output_path} ...")
        composite.write_videofile(
            output_path,
            fps=self.fps,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile="assets/temp_audio.m4a",
            remove_temp=True,
            logger=None,   # Suppress verbose moviepy output
        )

        return output_path
