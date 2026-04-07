"""
upload/youtube_uploader.py

Uploads the final video to YouTube using the YouTube Data API v3.
Handles OAuth 2.0 authentication, metadata, and upload progress.

Setup:
  1. Go to https://console.cloud.google.com
  2. Create a project → Enable "YouTube Data API v3"
  3. Create OAuth 2.0 credentials (Desktop App) → Download as client_secrets.json
  4. Place client_secrets.json in the project root
  5. First run will open a browser for Google login — token is cached after that
"""

import os
import time
import random
import pickle
from pathlib import Path
from utils.logger import log

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_FILE = "assets/youtube_token.pickle"
SECRETS_FILE = "client_secrets.json"

# YouTube resumable upload chunk size (10MB)
CHUNK_SIZE = 10 * 1024 * 1024

# Retry config for transient upload errors
MAX_RETRIES = 5
RETRYABLE_STATUS_CODES = [500, 502, 503, 504]


class YouTubeUploader:
    def __init__(self, config: dict):
        self.config = config
        self.youtube = None

    def _authenticate(self):
        """
        Authenticate via OAuth 2.0.
        Caches the token so user only logs in once.
        """
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            import google.oauth2.credentials
        except ImportError:
            log(
                "Google API packages not installed.\n"
                "Run: pip install google-api-python-client google-auth-oauthlib google-auth-httplib2",
                level="error",
            )
            return None

        creds = None

        # Load cached token
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "rb") as f:
                creds = pickle.load(f)

        # Refresh or re-authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
            else:
                if not os.path.exists(SECRETS_FILE):
                    log(
                        f"'{SECRETS_FILE}' not found.\n"
                        "  → Go to https://console.cloud.google.com\n"
                        "  → Enable YouTube Data API v3\n"
                        "  → Create OAuth 2.0 Desktop credentials\n"
                        "  → Download and save as client_secrets.json",
                        level="error",
                    )
                    return None

                flow = InstalledAppFlow.from_client_secrets_file(SECRETS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)

            # Cache token for next run
            Path("assets").mkdir(exist_ok=True)
            with open(TOKEN_FILE, "wb") as f:
                pickle.dump(creds, f)

        youtube = build("youtube", "v3", credentials=creds)
        return youtube

    def _build_metadata(self, story: dict) -> dict:
        """Build YouTube video metadata from story data."""
        cfg = self.config.get("youtube", {})

        title_template = cfg.get(
            "title_template", "{title} 😱 #creepypasta #scary #horror"
        )
        title = title_template.replace("{title}", story["title"])
        # YouTube title max = 100 chars
        title = title[:100]

        description_template = cfg.get(
            "description",
            (
                "🕯️ {title}\n\n"
                "{snippet}\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "📖 Full story: {url}\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "#creepypasta #horror #scarystories #scary #creepy "
                "#horrorstories #nosleep #paranormal"
            ),
        )

        # First 200 chars of story as snippet
        snippet_text = story["text"][:200].rsplit(" ", 1)[0] + "..."

        description = (
            description_template
            .replace("{title}", story["title"])
            .replace("{snippet}", snippet_text)
            .replace("{url}", story.get("url", "https://www.creepypasta.com"))
        )

        tags = cfg.get(
            "tags",
            [
                "creepypasta", "horror", "scary stories", "creepy",
                "horror stories", "nosleep", "paranormal", "supernatural",
                "scary", "frightening", "horror narration",
            ],
        )

        privacy = cfg.get("privacy_status", "public")   # public / unlisted / private
        category_id = cfg.get("category_id", "24")      # 24 = Entertainment

        return {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": category_id,
                "defaultLanguage": "en",
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False,
            },
        }

    def _upload_with_retry(self, request) -> str | None:
        """
        Execute a resumable upload with exponential backoff retry
        on transient server errors.
        """
        from googleapiclient.errors import HttpError

        response = None
        error = None
        retry = 0

        while response is None:
            try:
                log(f"Uploading... (attempt {retry + 1})")
                status, response = request.next_chunk()

                if status:
                    pct = int(status.progress() * 100)
                    log(f"Upload progress: {pct}%")

            except HttpError as e:
                if e.resp.status in RETRYABLE_STATUS_CODES:
                    error = f"HTTP {e.resp.status} — retrying..."
                else:
                    log(f"Non-retryable HTTP error: {e}", level="error")
                    return None

            except Exception as e:
                error = str(e)

            if error:
                retry += 1
                if retry > MAX_RETRIES:
                    log(f"Max retries reached. Last error: {error}", level="error")
                    return None
                sleep_time = (2 ** retry) + random.random()
                log(f"{error} Waiting {sleep_time:.1f}s before retry...")
                time.sleep(sleep_time)
                error = None

        video_id = response.get("id")
        return video_id

    def upload(self, story: dict, video_path: str) -> str | None:
        """
        Upload video to YouTube.
        Returns the YouTube video URL on success, None on failure.
        """
        try:
            from googleapiclient.http import MediaFileUpload
        except ImportError:
            log("google-api-python-client not installed.", level="error")
            return None

        if not os.path.exists(video_path):
            log(f"Video file not found: {video_path}", level="error")
            return None

        log("🔐 Authenticating with YouTube...")
        self.youtube = self._authenticate()
        if not self.youtube:
            return None

        metadata = self._build_metadata(story)
        log(f"📋 Title: {metadata['snippet']['title']}")
        log(f"🔒 Privacy: {metadata['status']['privacyStatus']}")

        media = MediaFileUpload(
            video_path,
            mimetype="video/mp4",
            chunksize=CHUNK_SIZE,
            resumable=True,
        )

        request = self.youtube.videos().insert(
            part="snippet,status",
            body=metadata,
            media_body=media,
        )

        log("📤 Starting YouTube upload...")
        video_id = self._upload_with_retry(request)

        if not video_id:
            log("Upload failed.", level="error")
            return None

        url = f"https://www.youtube.com/watch?v={video_id}"
        log(f"✅ Video live: {url}")
        return url
