"""
scraper/story_scraper.py
Scrapes horror stories from Creepypasta.com
"""

import random
import requests
from bs4 import BeautifulSoup
from utils.logger import log

BASE_URL = "https://www.creepypasta.com"

# Curated category paths with high-quality stories
CATEGORIES = [
    "/category/a-long-scary-story/",
    "/category/monster/",
    "/category/supernatural/",
    "/category/psychological-horror/",
    "/category/paranormal/",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# Stories already used (persisted to avoid repeats)
USED_STORIES_FILE = "assets/used_stories.txt"


class CreepypastaScraper:
    def __init__(self, config: dict):
        self.config = config
        self.max_words = config.get("max_words", 800)
        self.min_words = config.get("min_words", 150)
        self.used_stories = self._load_used()

    def _load_used(self) -> set:
        try:
            with open(USED_STORIES_FILE, "r") as f:
                return set(line.strip() for line in f.readlines())
        except FileNotFoundError:
            return set()

    def _mark_used(self, url: str):
        self.used_stories.add(url)
        with open(USED_STORIES_FILE, "a") as f:
            f.write(url + "\n")

    def _get_story_links(self, category_path: str) -> list[str]:
        """Fetch all story links from a category page."""
        url = BASE_URL + category_path
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as e:
            log(f"Failed to fetch category {url}: {e}", level="warn")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        links = []

        # Creepypasta.com article links are inside h2.entry-title > a
        for tag in soup.select("h2.entry-title a"):
            href = tag.get("href", "")
            if href and href not in self.used_stories:
                links.append(href)

        return links

    def _fetch_story(self, url: str) -> dict | None:
        """Fetch and parse a single story page."""
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as e:
            log(f"Failed to fetch story {url}: {e}", level="warn")
            return None

        soup = BeautifulSoup(resp.text, "html.parser")

        # Title
        title_tag = soup.select_one("h1.entry-title")
        title = title_tag.get_text(strip=True) if title_tag else "Unknown"

        # Story body — main content div
        content_div = soup.select_one("div.entry-content")
        if not content_div:
            return None

        # Remove share buttons, ads, author bios
        for unwanted in content_div.select(
            ".sharedaddy, .jp-relatedposts, .wpcnt, script, .author-bio"
        ):
            unwanted.decompose()

        # Extract paragraphs
        paragraphs = [p.get_text(strip=True) for p in content_div.find_all("p") if p.get_text(strip=True)]
        full_text = "\n\n".join(paragraphs)

        word_count = len(full_text.split())

        return {
            "title": title,
            "text": full_text,
            "url": url,
            "word_count": word_count,
        }

    def _truncate_to_limit(self, story: dict) -> dict:
        """Trim story to max_words, ending at a sentence boundary."""
        words = story["text"].split()
        if len(words) <= self.max_words:
            return story

        truncated = " ".join(words[: self.max_words])
        # End at last sentence
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
        Main method: pick a random category, find a story
        that fits word count limits, return it.
        """
        categories = CATEGORIES.copy()
        random.shuffle(categories)

        for category in categories:
            links = self._get_story_links(category)
            random.shuffle(links)

            for link in links:
                if link in self.used_stories:
                    continue

                story = self._fetch_story(link)
                if not story:
                    continue

                if story["word_count"] < self.min_words:
                    log(f"Skipping '{story['title']}' — too short ({story['word_count']} words)")
                    continue

                # Truncate if over limit
                story = self._truncate_to_limit(story)
                self._mark_used(link)

                return story

        log("No suitable stories found across all categories.", level="warn")
        return None
