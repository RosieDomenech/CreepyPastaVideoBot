"""
video_creation/video_maker.py
Assembles the final horror video using moviepy 2.x API.
"""

import os
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

    def _chunk_text(self, text: str) -> list:
        words = text.split()
        chunks = []
        for i in range(0, len(words), self.words_per_chunk):
            chunks.append(" ".join(words[i: i + self.words_per_chunk]))
        return chunks

    def _rgb_to_hex(self, rgb: list) -> str:
        return "#{:02x}{:02x}{:02x}".format(int(rgb[0]), int(rgb[1]), int(rgb[2]))

    def create(self, story: dict, audio_path: str) -> str | None:
        try:
            from moviepy import (
                AudioFileClip,
                ColorClip,
                CompositeVideoClip,
                TextClip,
                VideoFileClip,
            )
        except ImportError:
            try:
                # fallback for some moviepy 2.x builds
                from moviepy.video.io.VideoFileClip import VideoFileClip
                from moviepy.audio.io.AudioFileClip import AudioFileClip
                from moviepy.video.VideoClip import ColorClip, TextClip
                from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
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
            bg = VideoFileClip(BACKGROUND_VIDEO).with_effects(
                [lambda c: c.resized((W, H))]
            ).looped(duration=total_duration)
        else:
            log("Using solid color background.")
            bg = ColorClip(
                size=(W, H),
                color=self.bg_color,
                duration=total_duration
            )

        clips = [bg]

        # Title card (first 4 seconds)
        title_duration = min(4.0, total_duration * 0.15)
        try:
            title_wrapped = textwrap.fill(story["title"], width=20)
            title_clip = (
                TextClip(
                    text=title_wrapped,
                    font_size=70,
                    color=self._rgb_to_hex(self.title_color),
                    font="Arial",
                    method="caption",
                    size=(W - 100, None),
                    text_align="center",
                    stroke_color="black",
                    stroke_width=3,
                )
                .with_duration(title_duration)
                .with_position("center")
            )
            clips.append(title_clip)
        except Exception as e:
            log(f"Title clip failed (skipping): {e}", level="warn")

        # Body text chunks
        chunks = self._chunk_text(story["text"])
        body_start = title_duration
        body_duration = total_duration - body_start
        chunk_duration = body_duration / max(len(chunks), 1)

        for i, chunk in enumerate(chunks):
            start = body_start + i * chunk_duration
            try:
                wrapped = textwrap.fill(chunk, width=24)
                clip = (
                    TextClip(
                        text=wrapped,
                        font_size=52,
                        color=self._rgb_to_hex(self.text_color),
                        font="Arial",
                        method="caption",
                        size=(W - 120, None),
                        text_align="center",
                        stroke_color="black",
                        stroke_width=2,
                    )
                    .with_duration(chunk_duration)
                    .with_start(start)
                    .with_position("center")
                )
                clips.append(clip)
            except Exception as e:
                log(f"Chunk clip {i} failed (skipping): {e}", level="warn")

        # Compose
        composite = CompositeVideoClip(clips, size=(W, H)).with_duration(total_duration)
        composite = composite.with_audio(audio)

        # Export
        safe_title = story["title"].replace(" ", "_").replace("/", "-")[:40]
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
