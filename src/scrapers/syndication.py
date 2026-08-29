"""Lightweight 100% free syndication and public timeline scraper."""
import json
import re
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Optional
from src.scrapers.base import BaseScraper, Tweet

logger = logging.getLogger(__name__)

class SyndicationScraper(BaseScraper):
    """
    Scrapes tweets via Twitter public syndication endpoints and open CDN widgets.
    Zero-cookie, zero authentication needed, highly reliable and fast.
    """
    def __init__(self, timeout: int = 20):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
        })

    def fetch_tweets(self, handle: str, limit: int = 10) -> List[Tweet]:
        """Fetch recent tweets from syndication endpoints."""
        clean_handle = handle.lstrip("@").strip()
        tweets = []
        
        # Primary strategy: Twitter Syndication CDN timeline endpoint
        try:
            tweets = self._fetch_via_syndication_timeline(clean_handle, limit)
            if tweets:
                return tweets
        except Exception as e:
            logger.debug(f"Syndication timeline fetch error for @{clean_handle}: {e}")

        # Secondary strategy: Twitter embedded widget HTML parsing
        try:
            tweets = self._fetch_via_embed_widget(clean_handle, limit)
            if tweets:
                return tweets
        except Exception as e:
            logger.debug(f"Embed widget fetch error for @{clean_handle}: {e}")

        # Tertiary strategy: Public RSS bridge endpoints (fallback)
        try:
            tweets = self._fetch_via_rss_bridge(clean_handle, limit)
            if tweets:
                return tweets
        except Exception as e:
            logger.debug(f"RSS bridge fetch error for @{clean_handle}: {e}")

        return tweets

    def _fetch_via_syndication_timeline(self, handle: str, limit: int) -> List[Tweet]:
        """Fetch via CDN timeline-profile endpoint."""
        url = f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{handle}"
        params = {"showReplies": "false"}
        resp = self.session.get(url, params=params, timeout=self.timeout)
        
        if resp.status_code != 200:
            return []

        # Find __NEXT_DATA__ JSON script in HTML
        soup = BeautifulSoup(resp.text, "html.parser")
        script_tag = soup.find("script", id="__NEXT_DATA__")
        
        if not script_tag or not script_tag.string:
            return []

        data = json.loads(script_tag.string)
        entries = (
            data.get("props", {})
            .get("pageProps", {})
            .get("timeline", {})
            .get("entries", [])
        )

        tweets: List[Tweet] = []
        for entry in entries:
            if len(tweets) >= limit:
                break
            
            entry_data = entry.get("content", {}).get("tweet", {})
            if not entry_data:
                continue

            tweet_id = str(entry_data.get("id_str", entry_data.get("id", "")))
            if not tweet_id:
                continue

            text = entry_data.get("full_text") or entry_data.get("text", "")
            # Clean HTML entities
            text = BeautifulSoup(text, "html.parser").get_text()

            created_at_str = entry_data.get("created_at")
            posted_at = None
            if created_at_str:
                try:
                    posted_at = datetime.strptime(created_at_str, "%a %b %d %H:%M:%S %z %Y")
                except Exception:
                    pass

            is_reply = bool(entry_data.get("in_reply_to_status_id_str"))
            is_retweet = bool(entry_data.get("retweeted_status"))
            
            url = f"https://x.com/{handle}/status/{tweet_id}"
            
            tweets.append(Tweet(
                id=tweet_id,
                handle=handle,
                text=text.strip(),
                url=url,
                posted_at=posted_at,
                is_reply=is_reply,
                is_retweet=is_retweet,
                like_count=entry_data.get("favorite_count", 0),
                retweet_count=entry_data.get("retweet_count", 0),
                raw_data=entry_data
            ))

        return tweets

    def _fetch_via_embed_widget(self, handle: str, limit: int) -> List[Tweet]:
        """Fetch via publish.twitter.com embedded timeline endpoint."""
        url = "https://cdn.syndication.twimg.com/widgets/followbutton/info.json"
        # Alternate embed query
        embed_url = f"https://syndication.twitter.com/widgets/timelines/pjs?screen_name={handle}&limit={limit}"
        resp = self.session.get(embed_url, timeout=self.timeout)
        if resp.status_code != 200:
            return []
        
        data = resp.json()
        body_html = data.get("body", "")
        if not body_html:
            return []

        soup = BeautifulSoup(body_html, "html.parser")
        tweet_elements = soup.find_all("li", class_=re.compile(r"tweet|timeline-Tweet"))

        tweets: List[Tweet] = []
        for el in tweet_elements:
            if len(tweets) >= limit:
                break
            
            tweet_id = el.get("data-tweet-id")
            if not tweet_id:
                link = el.find("a", href=re.compile(r"/status/(\d+)"))
                if link:
                    match = re.search(r"/status/(\d+)", link["href"])
                    if match:
                        tweet_id = match.group(1)
            
            if not tweet_id:
                continue

            text_el = el.find("p", class_=re.compile(r"e-entry-title|timeline-Tweet-text"))
            text = text_el.get_text() if text_el else el.get_text()

            tweets.append(Tweet(
                id=str(tweet_id),
                handle=handle,
                text=text.strip(),
                url=f"https://x.com/{handle}/status/{tweet_id}"
            ))

        return tweets

    def _fetch_via_rss_bridge(self, handle: str, limit: int) -> List[Tweet]:
        """Fetch via public RSS bridge instances as fallback."""
        rss_instances = [
            f"https://rsshub.app/twitter/user/{handle}",
            f"https://nitter.net/{handle}/rss"
        ]
        
        for rss_url in rss_instances:
            try:
                resp = self.session.get(rss_url, timeout=10)
                if resp.status_code == 200 and "<rss" in resp.text:
                    soup = BeautifulSoup(resp.text, "xml")
                    items = soup.find_all("item")
                    tweets = []
                    for item in items[:limit]:
                        title = item.find("title").get_text() if item.find("title") else ""
                        desc = item.find("description").get_text() if item.find("description") else ""
                        link = item.find("link").get_text() if item.find("link") else ""
                        
                        clean_text = BeautifulSoup(desc or title, "html.parser").get_text()
                        
                        tweet_id_match = re.search(r"/status/(\d+)", link)
                        tweet_id = tweet_id_match.group(1) if tweet_id_match else str(hash(link))
                        
                        tweets.append(Tweet(
                            id=tweet_id,
                            handle=handle,
                            text=clean_text.strip(),
                            url=f"https://x.com/{handle}/status/{tweet_id}"
                        ))
                    if tweets:
                        return tweets
            except Exception:
                continue

        return []
