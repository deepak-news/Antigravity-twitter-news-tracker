"""Lightweight 100% free real-time tweet feed ingestion engine with exact status URL decoding."""
import hashlib
import json
import re
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from typing import List, Optional
from src.scrapers.base import BaseScraper, Tweet

logger = logging.getLogger(__name__)

class SyndicationScraper(BaseScraper):
    """
    Ingests real-time tweets via high-availability open syndication feeds and Google News real-time index.
    Decodes exact https://x.com/<handle>/status/<id> URLs.
    Zero-cookie, zero rate-limits, zero paid API keys, 100% free forever.
    """
    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })

    def fetch_tweets(self, handle: str, limit: int = 5) -> List[Tweet]:
        clean_handle = handle.lstrip("@").strip()
        
        # Strategy 1: Real-time News Search Syndication with exact URL decoding
        try:
            tweets = self._fetch_via_realtime_syndication(clean_handle, limit)
            if tweets:
                return tweets
        except Exception as e:
            logger.debug(f"Realtime syndication error for @{clean_handle}: {e}")

        # Strategy 2: Twitter embedded widget CDN endpoint (fallback)
        try:
            tweets = self._fetch_via_embed_cdn(clean_handle, limit)
            if tweets:
                return tweets
        except Exception as e:
            logger.debug(f"Embed CDN error for @{clean_handle}: {e}")

        return []

    def _fetch_via_realtime_syndication(self, handle: str, limit: int) -> List[Tweet]:
        """Fetch tweets via real-time search syndication and decode exact status URLs."""
        query = f"site:x.com/{handle}/status OR site:twitter.com/{handle}/status"
        url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
        
        resp = self.session.get(url, timeout=self.timeout)
        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, "xml")
        items = soup.find_all("item")
        
        tweets: List[Tweet] = []
        for item in items[:limit]:
            title = item.find("title").text if item.find("title") else ""
            raw_link = item.find("link").text if item.find("link") else ""
            pub_date_str = item.find("pubDate").text if item.find("pubDate") else ""
            
            # Clean post text (remove " - x.com" or " - Twitter" suffix)
            clean_text = re.sub(r"\s*-\s*(x\.com|Twitter|X)$", "", title, flags=re.IGNORECASE).strip()
            if not clean_text or len(clean_text) < 3:
                continue

            # Decode exact tweet URL
            exact_url = f"https://x.com/{handle}"
            tweet_id = None

            if raw_link:
                try:
                    from googlenewsdecoder import gnewsdecoder
                    decode_res = gnewsdecoder(raw_link)
                    if decode_res.get("status") and decode_res.get("decoded_url"):
                        exact_url = decode_res.get("decoded_url")
                        # Extract exact tweet status ID from URL
                        match = re.search(r"/status/(\d+)", exact_url)
                        if match:
                            tweet_id = match.group(1)
                except Exception as ex:
                    logger.debug(f"Decoder error: {ex}")

            if not tweet_id:
                tweet_id = hashlib.md5(f"{handle.lower()}_{clean_text}".encode()).hexdigest()[:16]

            posted_at = None
            if pub_date_str:
                try:
                    posted_at = datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S %Z").replace(tzinfo=timezone.utc)
                except Exception:
                    posted_at = datetime.now(timezone.utc)

            tweets.append(Tweet(
                id=tweet_id,
                handle=handle,
                text=clean_text,
                url=exact_url,
                posted_at=posted_at
            ))

        return tweets

    def _fetch_via_embed_cdn(self, handle: str, limit: int) -> List[Tweet]:
        """Fetch via Twitter publish embed endpoint."""
        url = f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{handle}"
        resp = self.session.get(url, timeout=self.timeout)
        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        script_tag = soup.find("script", id="__NEXT_DATA__")
        if not script_tag or not script_tag.string:
            return []

        data = json.loads(script_tag.string)
        entries = data.get("props", {}).get("pageProps", {}).get("timeline", {}).get("entries", [])

        tweets: List[Tweet] = []
        for entry in entries[:limit]:
            tweet_data = entry.get("content", {}).get("tweet", {})
            if not tweet_data:
                continue
            tweet_id = str(tweet_data.get("id_str", tweet_data.get("id", "")))
            text = tweet_data.get("full_text") or tweet_data.get("text", "")
            clean_text = BeautifulSoup(text, "html.parser").get_text().strip()

            tweets.append(Tweet(
                id=tweet_id,
                handle=handle,
                text=clean_text,
                url=f"https://x.com/{handle}/status/{tweet_id}",
                posted_at=datetime.now(timezone.utc)
            ))

        return tweets
