"""
video_creation/video_maker.py
Assembles the final horror video using moviepy 2.x API.
Supports AI images and background videos via BackgroundManager.
"""

import os
import re
import textwrap
from pathlib import Path
from utils.logger import log
from video_creation.background_manager import BackgroundManager

OUTPUT_DIR = "assets/output"


class VideoMaker:
    def __init__(self, config: dict):
        self.config = config
        self.resolution = tuple(config.get("resolution", [1080, 1920]))
        self.fps = config.get("fps", 30)
        self.bg_color = config.get("bg_color", [10, 5, 15])
        self.text_color = config.get("text_color", [220, 210, 200])
        self.title_color = config.get("title_color", [180, 30, 30])
        self.words_per_chunk = config.get("words_per_chunk", 10)
        self.bg_manager = BackgroundManager(config)
        Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        Path("assets/audio").mkdir(parents=True, exist_ok=True)

    def _safe_filename(self, title: str) -> str:
        safe = re.sub(r'[\\/*?:"<>|]', "", title).strip().replace(" ", "_")[:50]
        return safe or "story"

    def _chunk_text(self, text: str) -> list:
        words = text.split()
        return [
            " ".join(words[i: i + self.words_per_chunk])
            for i in range(0, len(words), self.words_per_chunk)
        ]

    def _rgb_to_hex(self, rgb: list) -> str:
        return "#{:02x}{:02x}{:02x}".format(int(rgb[0]), int(rgb[1]), int(rgb[2]))

    def _make_text_clip(self, TextClip, text, duration, font_size, color, start=0):
        wrapped = textwrap.fill(text, width=22)
        W = self.resolution[0]
        for font in [None, "Arial", "DejaVu-Sans", "Helvetica"]:
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
                return (
                    TextClip(**kwargs)
                    .with_duration(duration)
                    .with_start(start)
                    .with_position("center")
                )
            except Exception:
                continue
        return None

    def _build_background_clip(self, bg_info: dict, total_duration: float,
                                ColorClip, ImageClip, VideoFileClip):
        """Build the background clip from AI image, video, or solid color."""
        W, H = self.resolution[0], self.resolution[1]
        bg_type = bg_info["type"]

        try:
            if bg_type == "ai_image":
                log("Applying AI image background...")
                clip = (
                    ImageClip(bg_info["path"])
                    .with_duration(total_duration)
                    .resized((W, H))
                )
                # Darken slightly so text is readable
                clip = clip.with_effects(
                    [lambda c: c.image_transform(lambda f: (f * 0.55).clip(0, 255).astype("uint8"))]
                )
                return clip

            elif bg_type == "video":
                log("Applying background video...")
                clip = (
                    VideoFileClip(bg_info["path"])
                    .looped(duration=total_duration)
                    .resized((W, H))
                )
                clip = clip.with_effects(
                    [lambda c: c.image_transform(lambda f: (f * 0.45).clip(0, 255).astype("uint8"))]
                )
                return clip

        except Exception as e:
            log(f"Background clip failed ({e}), using color fallback.", level="warn")

        # Solid color fallback
        color = bg_info.get("color", self.bg_color)
        return ColorClip(size=(W, H), color=color, duration=total_duration)

    def create(self, story: dict, audio_path: str) -> str | None:
        try:
            from moviepy import (
                AudioFileClip,
                ColorClip,
                CompositeVideoClip,
                ImageClip,
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

        # Get background (AI image, video, or color)
        bg_info = self.bg_manager.get_background(story)
        bg = self._build_background_clip(
            bg_info, total_duration, ColorClip, ImageClip, VideoFileClip
        )

        clips = [bg]

        # Title card
        title_duration = min(4.0, total_duration * 0.15)
        title_clip = self._make_text_clip(
            TextClip, story["title"], title_duration, 68, self.title_color, start=0
        )
        if title_clip:
            clips.append(title_clip)
            log("Title clip created.")

        # Body text chunks
        chunks = self._chunk_text(story["text"])
        body_start = title_duration
        body_duration = total_duration - body_start
        chunk_duration = body_duration / max(len(chunks), 1)

        added = 0
        for i, chunk in enumerate(chunks):
            clip = self._make_text_clip(
                TextClip, chunk, chunk_duration, 50,
                self.text_color, start=body_start + i * chunk_duration
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
