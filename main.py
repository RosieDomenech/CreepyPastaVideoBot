"""
CreepyPasta Video Maker Bot 🕯️
Automatically turns Creepypasta.com horror stories into narrated videos
and optionally uploads them to YouTube.
"""

import sys
from scraper.story_scraper import CreepypastaScraper
from tts.narrator import Narrator
from video_creation.video_maker import VideoMaker
from upload.youtube_uploader import YouTubeUploader
from upload.scheduler import UploadScheduler
from utils.config import load_config
from utils.logger import log


def main():
    log("🕯️  CreepyPasta Video Bot starting...")

    config = load_config()
    upload_enabled = config.get("youtube", {}).get("enabled", False)

    # ── Step 1: Check upload schedule before doing any work ──────────────
    scheduler = None
    if upload_enabled:
        scheduler = UploadScheduler(config)
        allowed, reason = scheduler.can_upload()
        if not allowed:
            log(f"⏳ Upload skipped: {reason}", level="warn")
            log("   (Video will still be created and saved locally.)")

    # ── Step 2: Scrape a story ────────────────────────────────────────────
    log("👻 Fetching a scary story...")
    scraper = CreepypastaScraper(config)
    story = scraper.get_story()

    if not story:
        log("Failed to fetch a story. Check your connection.", level="error")
        sys.exit(1)

    log(f"📖 Story selected: {story['title']}")
    log(f"   Word count: {story['word_count']} words")

    # ── Step 3: Generate TTS narration ───────────────────────────────────
    log("🎙️  Generating narration audio...")
    narrator = Narrator(config)
    audio_path = narrator.generate(story)

    if not audio_path:
        log("TTS generation failed.", level="error")
        sys.exit(1)

    log(f"✅ Audio saved: {audio_path}")

    # ── Step 4: Build the video ───────────────────────────────────────────
    log("🎬 Assembling video...")
    maker = VideoMaker(config)
    video_path = maker.create(story, audio_path)

    if not video_path:
        log("Video creation failed.", level="error")
        sys.exit(1)

    log(f"✅ Video saved: {video_path}")

    # ── Step 5: Upload to YouTube (if enabled and schedule allows) ────────
    if upload_enabled:
        allowed, reason = scheduler.can_upload()
        if allowed:
            log("📤 Uploading to YouTube...")
            uploader = YouTubeUploader(config)
            video_url = uploader.upload(story, video_path)

            if video_url:
                scheduler.record_upload(story["title"], video_url)
                log(f"\n🎉 All done! Video live at: {video_url}")
            else:
                log("Upload failed. Video saved locally.", level="warn")
                log(f"   Local file: {video_path}")
        else:
            log(f"⏳ {reason}")
            log(f"   Video saved locally: {video_path}")
    else:
        log(f"\n✅ Done! Video ready for manual upload: {video_path}")
        log("   To enable auto-upload, set [youtube] enabled = true in config.toml")

    if scheduler:
        scheduler.print_history()


if __name__ == "__main__":
    main()
