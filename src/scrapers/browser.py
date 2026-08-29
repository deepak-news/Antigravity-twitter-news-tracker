"""Playwright headless browser scraper fallback for Twitter timelines."""
import logging
import re
from datetime import datetime
from typing import List, Optional
from src.scrapers.base import BaseScraper, Tweet

logger = logging.getLogger(__name__)

class BrowserScraper(BaseScraper):
    """
    Playwright-based headless browser scraper.
    Renders the live Twitter web page, capable of executing JS and extracting live timeline elements.
    """
    def __init__(self, auth_token: Optional[str] = None, timeout: int = 30):
        self.auth_token = auth_token
        self.timeout = timeout

    def fetch_tweets(self, handle: str, limit: int = 10) -> List[Tweet]:
        clean_handle = handle.lstrip("@").strip()
        
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.warning("Playwright is not installed. Install with: pip install playwright && playwright install chromium")
            return []

        tweets: List[Tweet] = []

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
                )
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1280, "height": 800}
                )

                if self.auth_token:
                    context.add_cookies([{
                        "name": "auth_token",
                        "value": self.auth_token,
                        "domain": ".x.com",
                        "path": "/",
                        "secure": True,
                        "httpOnly": True
                    }])

                page = context.new_page()
                page.set_default_timeout(self.timeout * 1000)

                target_url = f"https://x.com/{clean_handle}"
                page.goto(target_url, wait_until="domcontentloaded")

                # Wait for tweet articles to render
                try:
                    page.wait_for_selector('article[data-testid="tweet"]', timeout=15000)
                except Exception:
                    logger.debug(f"Selector timeout on @{clean_handle}")

                # Extract tweet elements
                articles = page.query_selector_all('article[data-testid="tweet"]')
                
                for art in articles[:limit]:
                    try:
                        # Extract tweet URL and ID
                        link_el = art.query_selector('a[href*="/status/"]')
                        if not link_el:
                            continue
                        href = link_el.get_attribute("href") or ""
                        match = re.search(r"/status/(\d+)", href)
                        if not match:
                            continue
                        tweet_id = match.group(1)

                        # Extract text
                        text_el = art.query_selector('div[data-testid="tweetText"]')
                        text = text_el.inner_text() if text_el else ""

                        # Extract time
                        time_el = art.query_selector('time')
                        posted_at = None
                        if time_el:
                            dt_str = time_el.get_attribute("datetime")
                            if dt_str:
                                try:
                                    posted_at = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                                except Exception:
                                    pass

                        tweets.append(Tweet(
                            id=tweet_id,
                            handle=clean_handle,
                            text=text.strip(),
                            url=f"https://x.com/{clean_handle}/status/{tweet_id}",
                            posted_at=posted_at
                        ))
                    except Exception as e:
                        logger.debug(f"Error parsing tweet element: {e}")

                browser.close()
        except Exception as e:
            logger.error(f"Playwright error while scraping @{clean_handle}: {e}")

        return tweets
