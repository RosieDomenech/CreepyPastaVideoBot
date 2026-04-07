"""
upload/scheduler.py

Controls upload timing to avoid YouTube spam detection.
Tracks upload history and enforces configurable delays between uploads.
"""

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from utils.logger import log

HISTORY_FILE = "assets/upload_history.json"


class UploadScheduler:
    def __init__(self, config: dict):
        cfg = config.get("youtube", {})
        # Minimum hours between uploads (default: 12)
        self.min_gap_hours = cfg.get("min_hours_between_uploads", 12)
        # Max uploads per day (default: 2)
        self.max_per_day = cfg.get("max_uploads_per_day", 2)
        self.history = self._load_history()

    def _load_history(self) -> list:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE) as f:
                return json.load(f)
        return []

    def _save_history(self):
        Path("assets").mkdir(exist_ok=True)
        with open(HISTORY_FILE, "w") as f:
            json.dump(self.history, f, indent=2)

    def _uploads_today(self) -> int:
        today = datetime.now().date().isoformat()
        return sum(1 for entry in self.history if entry["date"] == today)

    def _last_upload_time(self) -> datetime | None:
        if not self.history:
            return None
        return datetime.fromisoformat(self.history[-1]["timestamp"])

    def can_upload(self) -> tuple[bool, str]:
        """Returns (allowed, reason_if_blocked)."""
        # Check daily limit
        today_count = self._uploads_today()
        if today_count >= self.max_per_day:
            return False, f"Daily limit reached ({today_count}/{self.max_per_day} uploads today)"

        # Check minimum gap
        last = self._last_upload_time()
        if last:
            gap = datetime.now() - last
            required = timedelta(hours=self.min_gap_hours)
            if gap < required:
                wait = required - gap
                hours, rem = divmod(int(wait.total_seconds()), 3600)
                mins = rem // 60
                return False, f"Too soon — wait {hours}h {mins}m before next upload"

        return True, "ok"

    def record_upload(self, story_title: str, video_url: str):
        """Log a successful upload."""
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "date": datetime.now().date().isoformat(),
            "title": story_title,
            "url": video_url,
        })
        self._save_history()
        log(f"Upload logged. Total uploads: {len(self.history)}")

    def print_history(self):
        if not self.history:
            log("No upload history yet.")
            return
        log(f"\n📊 Upload History ({len(self.history)} total):")
        for entry in self.history[-10:]:  # Last 10
            print(f"  [{entry['date']}] {entry['title']} → {entry['url']}")
