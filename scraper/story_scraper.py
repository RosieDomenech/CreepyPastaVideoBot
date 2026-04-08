"""
scraper/story_scraper.py
Fetches horror stories from Reddit's r/nosleep and r/creepypasta
using Reddit's public JSON API — no API key required.
"""

import random
import time
import requests
from utils.logger import log

# Subreddits to pull from — all horror focused
SUBREDDITS = [
    "nosleep",
    "creepypasta",
    "shortscarystories",
    "TrueScaryStories",
]

HEADERS = {
    "User-Agent": "CreepyPastaVideoBot/1.0 (horror story video maker)",
}

USED_STORIES_FILE = "assets/used_stories.txt"


class CreepypastaScraper:
    def __init__(self, config: dict):
        self.config = config
        self.max_words = config.get("max_words", 800)
        self.min_words = config.get("min_words", 150)
        self.used_stories = self._load_used()

    def _load_used(self) -> set:
        try:
            with open(USED_STORIES_FILE, "r", encoding="utf-8") as f:
                return set(line.strip() for line in f.readlines())
        except FileNotFoundError:
            return set()

    def _mark_used(self, url: str):
        self.used_stories.add(url)
        with open(USED_STORIES_FILE, "a", encoding="utf-8") as f:
            f.write(url + "\n")

    def _fetch_subreddit_posts(self, subreddit: str, sort: str = "top", limit: int = 25) -> list:
        """
        Fetch posts from a subreddit using Reddit's public JSON API.
        sort: 'top', 'hot', 'new'
        """
        url = f"https://www.reddit.com/r/{subreddit}/{sort}.json?limit={limit}&t=month"
        try:
            time.sleep(random.uniform(1.0, 2.0))  # Polite delay
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            posts = data.get("data", {}).get("children", [])
            return [p["data"] for p in posts]
        except Exception as e:
            log(f"Failed to fetch r/{subreddit}: {e}", level="warn")
            return []

    def _post_to_story(self, post: dict) -> dict | None:
        """Convert a Reddit post dict into a story dict."""
        title = post.get("title", "").strip()
        text = post.get("selftext", "").strip()
        url = "https://www.reddit.com" + post.get("permalink", "")

        # Skip deleted, removed, or link-only posts
        if not text or text in ("[deleted]", "[removed]"):
            return None

        # Skip posts already used
        if url in self.used_stories:
            return None

        word_count = len(text.split())

        return {
            "title": title,
            "text": text,
            "url": url,
            "word_count": word_count,
        }

    def _truncate_to_limit(self, story: dict) -> dict:
        """Trim story to max_words at a sentence boundary."""
        words = story["text"].split()
        if len(words) <= self.max_words:
            return story

        truncated = " ".join(words[: self.max_words])
        last_period = max(
            truncated.rfind("."), truncated.rfind("!"), truncated.rfind("?")
        )
        if last_period > 0:
            truncated = truncated[: last_period + 1]

        story["text"] = truncated
        story["word_count"] = len(truncated.split())
        story["truncated"] = True
        return story

    def get_story(self) -> dict | None:
        """
        Main method: fetch posts from horror subreddits,
        return the first valid story within word count limits.
        """
        subreddits = SUBREDDITS.copy()
        random.shuffle(subreddits)

        for subreddit in subreddits:
            sort = random.choice(["top", "hot"])
            log(f"Checking r/{subreddit} ({sort})...")
            posts = self._fetch_subreddit_posts(subreddit, sort=sort)

            if not posts:
                continue

            random.shuffle(posts)

            for post in posts:
                story = self._post_to_story(post)
                if not story:
                    continue

                if story["word_count"] < self.min_words:
                    log(f"Skipping '{story['title']}' -- too short ({story['word_count']} words)")
                    continue

                story = self._truncate_to_limit(story)
                self._mark_used(story["url"])
                log(f"Selected: '{story['title']}' from r/{subreddit} ({story['word_count']} words)")
                return story

        log("No suitable stories found across all subreddits.", level="warn")
        return None
