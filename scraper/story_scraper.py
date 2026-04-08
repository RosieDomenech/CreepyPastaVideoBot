"""
scraper/story_scraper.py
Scrapes horror stories from Creepypasta.com
Uses RSS feed first (harder to block), falls back to direct scraping.
"""

import random
import time
import xml.etree.ElementTree as ET
import requests
from bs4 import BeautifulSoup
from utils.logger import log

BASE_URL = "https://www.creepypasta.com"

# RSS feeds by category — much harder to block than scraping HTML
RSS_FEEDS = [
    "https://www.creepypasta.com/category/a-long-scary-story/feed/",
    "https://www.creepypasta.com/category/monster/feed/",
    "https://www.creepypasta.com/category/supernatural/feed/",
    "https://www.creepypasta.com/category/psychological-horror/feed/",
    "https://www.creepypasta.com/category/paranormal/feed/",
    "https://www.creepypasta.com/feed/",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Referer": "https://www.google.com/",
}

RSS_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.creepypasta.com/",
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

    def _get_links_from_rss(self, feed_url: str) -> list:
        try:
            resp = requests.get(feed_url, headers=RSS_HEADERS, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            log(f"RSS fetch failed for {feed_url}: {e}", level="warn")
            return []
        try:
            root = ET.fromstring(resp.content)
            links = []
            for item in root.findall(".//item"):
                link_el = item.find("link")
                if link_el is not None and link_el.text:
                    url = link_el.text.strip()
                    if url not in self.used_stories:
                        links.append(url)
            return links
        except ET.ParseError as e:
            log(f"RSS parse error: {e}", level="warn")
            return []

    def _get_links_from_html(self, category_path: str) -> list:
        url = BASE_URL + category_path
        try:
            time.sleep(random.uniform(1.5, 3.0))
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            log(f"HTML scrape failed for {url}: {e}", level="warn")
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        links = []
        for tag in soup.select("h2.entry-title a"):
            href = tag.get("href", "")
            if href and href not in self.used_stories:
                links.append(href)
        return links

    def _fetch_story(self, url: str):
        try:
            time.sleep(random.uniform(1.0, 2.5))
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            log(f"Failed to fetch story {url}: {e}", level="warn")
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        title_tag = soup.select_one("h1.entry-title")
        title = title_tag.get_text(strip=True) if title_tag else "Unknown"
        content_div = soup.select_one("div.entry-content")
        if not content_div:
            return None
        for unwanted in content_div.select(
            ".sharedaddy, .jp-relatedposts, .wpcnt, script, .author-bio, .wp-block-buttons, .aligncenter"
        ):
            unwanted.decompose()
        paragraphs = [
            p.get_text(strip=True)
            for p in content_div.find_all("p")
            if p.get_text(strip=True)
        ]
        full_text = "\n\n".join(paragraphs)
        if not full_text:
            return None
        return {
            "title": title,
            "text": full_text,
            "url": url,
            "word_count": len(full_text.split()),
        }

    def _truncate_to_limit(self, story: dict) -> dict:
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

    def get_story(self):
        all_links = []

        log("Trying RSS feeds...")
        feeds = RSS_FEEDS.copy()
        random.shuffle(feeds)
        for feed in feeds:
            links = self._get_links_from_rss(feed)
            if links:
                log(f"Got {len(links)} links from RSS: {feed}")
                all_links.extend(links)

        if not all_links:
            log("RSS failed, trying direct HTML scraping...", level="warn")
            categories = [
                "/category/a-long-scary-story/",
                "/category/monster/",
                "/category/supernatural/",
                "/category/psychological-horror/",
                "/category/paranormal/",
            ]
            random.shuffle(categories)
            for cat in categories:
                links = self._get_links_from_html(cat)
                if links:
                    all_links.extend(links)

        if not all_links:
            log("Could not retrieve any story links.", level="error")
            return None

        all_links = list(dict.fromkeys(all_links))
        random.shuffle(all_links)

        for link in all_links:
            if link in self.used_stories:
                continue
            log(f"Fetching: {link}")
            story = self._fetch_story(link)
            if not story:
                continue
            if story["word_count"] < self.min_words:
                log(f"Skipping '{story['title']}' -- too short ({story['word_count']} words)")
                continue
            story = self._truncate_to_limit(story)
            self._mark_used(link)
            return story

        log("No suitable stories found.", level="warn")
        return None
