"""
video_creation/video_maker.py
Assembles the final horror video using moviepy 2.x API.
"""

import os
import re
import textwrap
from pathlib import Path
from utils.logger import log

OUTPUT_DIR = "assets/output"
BACKGROUND_VIDEO = "assets/background.mp4"


class VideoMaker:
    def __init__(self, config: dict):
        self.config = config
        self.resolution = tuple(config.get("resolution", [1080, 1920]))
        self.fps = config.get("fps", 30)
        self.bg_color = config.get("bg_color", [10, 5, 15])
        self.text_color = config.get("text_color", [220, 210, 200])
        self.title_color = config.get("title_color", [180, 30, 30])
        self.words_per_chunk = config.get("words_per_chunk", 10)
        Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        Path("assets/audio").mkdir(parents=True, exist_ok=True)

    def _safe_filename(self, title: str) -> str:
        """Remove all characters illegal in Windows filenames."""
        safe = re.sub(r'[\\/*?:"<>|]', "", title)
        safe = safe.strip().replace(" ", "_")[:50]
        return safe or "story"

    def _chunk_text(self, text: str) -> list:
        words = text.split()
        chunks = []
        for i in range(0, len(words), self.words_per_chunk):
            chunks.append(" ".join(words[i: i + self.words_per_chunk]))
        return chunks

    def _rgb_to_hex(self, rgb: list) -> str:
        return "#{:02x}{:02x}{:02x}".format(int(rgb[0]), int(rgb[1]), int(rgb[2]))

    def _make_text_clip(self, TextClip, text: str, duration: float, font_size: int, color: list, start: float = 0):
        """Create a text clip, trying fonts until one works."""
        fonts_to_try = [None, "Arial", "DejaVu-Sans", "Helvetica", "Verdana"]
        wrapped = textwrap.fill(text, width=22)
        W = self.resolution[0]

        for font in fonts_to_try:
            try:
                kwargs = dict(
                    text=wrapped,
                    font_size=font_size,
                    color=self._rgb_to_hex(color),
                    method="caption",
                    size=(W - 120, None),
                    text_align="center",
                    stroke_color="black",
                    stroke_width=2,
                )
                if font:
                    kwargs["font"] = font

                clip = (
                    TextClip(**kwargs)
                    .with_duration(duration)
                    .with_start(start)
                    .with_position("center")
                )
                return clip
            except Exception:
                continue

        return None

    def create(self, story: dict, audio_path: str):
        try:
            from moviepy import (
                AudioFileClip,
                ColorClip,
                CompositeVideoClip,
                TextClip,
                VideoFileClip,
            )
        except ImportError as e:
            log(f"moviepy import failed: {e}", level="error")
            return None

        W, H = self.resolution[0], self.resolution[1]

        # Load audio
        audio = AudioFileClip(audio_path)
        total_duration = audio.duration
        log(f"Audio duration: {total_duration:.1f}s")

        # Background
        if os.path.exists(BACKGROUND_VIDEO):
            log("Using background video.")
            try:
                bg = VideoFileClip(BACKGROUND_VIDEO).looped(duration=total_duration).resized((W, H))
            except Exception:
                bg = ColorClip(size=(W, H), color=self.bg_color, duration=total_duration)
        else:
            log("Using solid color background.")
            bg = ColorClip(size=(W, H), color=self.bg_color, duration=total_duration)

        clips = [bg]

        # Title card
        title_duration = min(4.0, total_duration * 0.15)
        title_clip = self._make_text_clip(
            TextClip, story["title"], title_duration, 68, self.title_color, start=0
        )
        if title_clip:
            clips.append(title_clip)
            log("Title clip created.")
        else:
            log("Could not create title clip, skipping.", level="warn")

        # Body text chunks
        chunks = self._chunk_text(story["text"])
        body_start = title_duration
        body_duration = total_duration - body_start
        chunk_duration = body_duration / max(len(chunks), 1)

        added = 0
        for i, chunk in enumerate(chunks):
            start = body_start + i * chunk_duration
            clip = self._make_text_clip(
                TextClip, chunk, chunk_duration, 50, self.text_color, start=start
            )
            if clip:
                clips.append(clip)
                added += 1

        log(f"Added {added}/{len(chunks)} text chunks.")

        # Compose and export
        composite = CompositeVideoClip(clips, size=(W, H)).with_duration(total_duration)
        composite = composite.with_audio(audio)

        safe_title = self._safe_filename(story["title"])
        output_path = os.path.join(OUTPUT_DIR, f"{safe_title}.mp4")

        log(f"Rendering to {output_path} ...")
        composite.write_videofile(
            output_path,
            fps=self.fps,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile="assets/temp_audio.m4a",
            remove_temp=True,
            logger=None,
        )

        return output_path
