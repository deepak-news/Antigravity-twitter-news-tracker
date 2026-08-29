import os
import sys

BASE_DIR = "/Users/deepak/.gemini/antigravity/scratch/twitter-news-tracker"

files = {}

files["requirements.txt"] = """google-genai>=0.1.1
google-generativeai>=0.8.0
playwright>=1.40.0
pydantic>=2.0.0
pyyaml>=6.0.0
python-dotenv>=1.0.0
requests>=2.31.0
beautifulsoup4>=4.12.0
lxml>=5.0.0
urllib3>=2.0.0
"""

files[".gitignore"] = """__pycache__/
*.py[cod]
*$py.class
*.sqlite3
*.db
.env
data/tracker.db
logs/
.venv/
env/
venv/
node_modules/
.DS_Store
"""

files[".env.example"] = """# ==============================================================================
# TWITTER NEWS TRACKER - SECRETS CONFIGURATION
# ==============================================================================

# 1. Google Gemini API Key (100% Free from Google AI Studio: https://aistudio.google.com/)
GEMINI_API_KEY=your_gemini_api_key_here

# 2. Gmail SMTP Credentials (100% Free via Google App Passwords)
# Step 1: Enable 2-Step Verification on your Google Account
# Step 2: Create App Password at: https://myaccount.google.com/apppasswords
GMAIL_ADDRESS=your_email@gmail.com
GMAIL_APP_PASSWORD=your_16_character_app_password

# 3. Notification Recipient Emails (comma-separated for multiple)
ALERT_RECIPIENT_EMAILS=your_personal_email@example.com

# 4. Optional: Twitter Auth Token (only needed if Twitter enforces aggressive rate limits)
# TWITTER_AUTH_TOKEN=
"""

files["config.yaml"] = """# ==============================================================================
# TWITTER NEWS TRACKER - 24/7 CONFIGURATION
# ==============================================================================

# List of Twitter/X handles to monitor 24/7 (without '@')
tracked_accounts:
  - sama
  - elonmusk
  - karpathy
  - OpenAI
  - AnthropicAI
  - GoogleDeepMind
  - MetaAI
  - DemisHassabis
  - ylecun

# Global Newsworthiness Criteria Prompt for Gemini Flash
newsworthiness_prompt: |
  You are an elite news editor and intelligence analyst.
  Evaluate whether the following tweet from a monitored high-profile account contains genuinely NEWSWORTHY information.

  A tweet is considered NEWSWORTHY (is_newsworthy: true) if it communicates:
  1. Major product launches, new feature releases, AI model releases, breakthroughs, or benchmarks.
  2. High-impact corporate announcements, mergers, acquisitions, key leadership shifts, or major funding.
  3. Significant policy decisions, legal/regulatory developments, or industry-defining statements.
  4. Concrete technological, scientific, or economic milestones with wide public/industry interest.

  A tweet is NOT newsworthy (is_newsworthy: false) if it is:
  1. Casual conversation, banter, greetings, emojis, or routine social interactions.
  2. Jokes, memes, philosophical musings, or personal opinions without factual news.
  3. Routine self-promotion, reposts of old content, or generic hype without concrete details.
  4. Minor replies or conversational context without independent significance.

# Minimum confidence score (1 to 10) required to trigger an email alert
# Only tweets with is_newsworthy: true AND confidence_score >= min_confidence_score will be emailed.
min_confidence_score: 7

# Scraper Settings
scraper:
  # Mode: "auto" (tries lightweight syndication first, falls back to Playwright if needed)
  # Options: "auto", "syndication", "browser"
  mode: "auto"
  # Max recent tweets to check per account on each cycle
  max_tweets_per_account: 10
  # Filter out plain @replies (unless they are quote tweets)
  include_replies: false
  # Include retweets / reposts
  include_retweets: false
  # Scraper request timeout in seconds
  timeout_seconds: 20

# Notification Settings
notifications:
  subject_prefix: "[NEWS ALERT]"
  # Fallback recipient list if ALERT_RECIPIENT_EMAILS is not set in .env
  recipient_emails: []

# Daemon Settings (for continuous 24/7 VM background runner)
daemon:
  # Polling interval in seconds between monitoring cycles (e.g., 600 = 10 minutes)
  poll_interval_seconds: 600
  # Random jitter in seconds (+/-) added to cycle intervals to prevent rigid bot timing patterns
  jitter_seconds: 45
"""

files["src/__init__.py"] = '"""Twitter News Tracker Package."""\n'

files["src/config.py"] = '''"""Configuration loader with environment variable validation."""
import os
import yaml
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load .env file
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

class ScraperConfig(BaseModel):
    mode: str = "auto"
    max_tweets_per_account: int = 10
    include_replies: bool = False
    include_retweets: bool = False
    timeout_seconds: int = 20

class NotificationConfig(BaseModel):
    subject_prefix: str = "[NEWS ALERT]"
    recipient_emails: List[str] = Field(default_factory=list)

class DaemonConfig(BaseModel):
    poll_interval_seconds: int = 600
    jitter_seconds: int = 45

class AppConfig(BaseModel):
    tracked_accounts: List[str] = Field(default_factory=list)
    newsworthiness_prompt: str = ""
    min_confidence_score: int = 7
    scraper: ScraperConfig = Field(default_factory=ScraperConfig)
    notifications: NotificationConfig = Field(default_factory=NotificationConfig)
    daemon: DaemonConfig = Field(default_factory=DaemonConfig)
    
    # Secrets from environment
    gemini_api_key: str = ""
    gmail_address: str = ""
    gmail_app_password: str = ""
    recipient_emails: List[str] = Field(default_factory=list)
    twitter_auth_token: Optional[str] = None

def load_config(config_path: Optional[str] = None) -> AppConfig:
    """Load configuration from YAML and overlay environment variables."""
    if config_path is None:
        config_path = str(BASE_DIR / "config.yaml")
    
    config_dict = {}
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config_dict = yaml.safe_load(f) or {}

    app_config = AppConfig(**config_dict)

    # Inject environment variables
    app_config.gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
    app_config.gmail_address = os.getenv("GMAIL_ADDRESS", "").strip()
    app_config.gmail_app_password = os.getenv("GMAIL_APP_PASSWORD", "").strip()
    app_config.twitter_auth_token = os.getenv("TWITTER_AUTH_TOKEN", "").strip() or None

    # Merge recipients from env and config
    env_recipients = os.getenv("ALERT_RECIPIENT_EMAILS", "").strip()
    if env_recipients:
        parsed_recipients = [r.strip() for r in env_recipients.split(",") if r.strip()]
        app_config.recipient_emails = list(set(app_config.notifications.recipient_emails + parsed_recipients))
    else:
        app_config.recipient_emails = app_config.notifications.recipient_emails

    # Clean handles
    app_config.tracked_accounts = [h.strip().lstrip("@") for h in app_config.tracked_accounts if h.strip()]

    return app_config
'''

files["src/db.py"] = '''"""SQLite and JSON database for tracking processed tweets and alert history."""
import os
import json
import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "tracker.db"
STATE_JSON_PATH = DATA_DIR / "state.json"

class TrackerDB:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self._ensure_dirs()
        self.init_db()

    def _ensure_dirs(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initialize SQLite database tables."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processed_tweets (
                    id TEXT PRIMARY KEY,
                    handle TEXT NOT NULL,
                    text TEXT,
                    posted_at TEXT,
                    url TEXT,
                    is_newsworthy INTEGER NOT NULL DEFAULT 0,
                    confidence_score INTEGER NOT NULL DEFAULT 0,
                    headline TEXT,
                    summary TEXT,
                    category TEXT,
                    reasoning TEXT,
                    emailed_at TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_handle ON processed_tweets(handle);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_is_newsworthy ON processed_tweets(is_newsworthy);
            """)
            conn.commit()
            
        # If state.json exists but db is empty, import state.json
        if STATE_JSON_PATH.exists():
            self._sync_from_state_json()

    def is_tweet_seen(self, tweet_id: str) -> bool:
        """Check if a tweet ID has already been evaluated or stored."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM processed_tweets WHERE id = ?", (str(tweet_id),))
            return cursor.fetchone() is not None

    def save_evaluation(
        self,
        tweet_id: str,
        handle: str,
        text: str,
        posted_at: Optional[str],
        url: str,
        is_newsworthy: bool,
        confidence_score: int,
        headline: str,
        summary: str,
        category: str,
        reasoning: str,
        emailed_at: Optional[str] = None
    ):
        """Save an evaluated tweet to the database."""
        now_str = datetime.utcnow().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO processed_tweets (
                    id, handle, text, posted_at, url,
                    is_newsworthy, confidence_score, headline,
                    summary, category, reasoning, emailed_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(tweet_id),
                handle.lower(),
                text,
                posted_at,
                url,
                1 if is_newsworthy else 0,
                confidence_score,
                headline,
                summary,
                category,
                reasoning,
                emailed_at,
                now_str
            ))
            conn.commit()
            
        self.export_state_json()

    def mark_as_emailed(self, tweet_id: str):
        """Update emailed_at timestamp for an alert."""
        now_str = datetime.utcnow().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE processed_tweets SET emailed_at = ? WHERE id = ?
            """, (now_str, str(tweet_id)))
            conn.commit()
        self.export_state_json()

    def get_recent_alerts(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve recent newsworthy alerts."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM processed_tweets
                WHERE is_newsworthy = 1
                ORDER BY created_at DESC LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def export_state_json(self, path: Optional[Path] = None):
        """Export seen tweet IDs to a portable JSON file for git commits/sync."""
        export_path = path or STATE_JSON_PATH
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, handle, is_newsworthy, confidence_score, emailed_at, created_at
                FROM processed_tweets
                ORDER BY created_at DESC LIMIT 5000
            """)
            rows = [dict(row) for row in cursor.fetchall()]
        
        state_data = {
            "last_updated": datetime.utcnow().isoformat(),
            "total_seen": len(rows),
            "tweets": rows
        }
        with open(export_path, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=2)

    def _sync_from_state_json(self):
        """Sync seen IDs from state.json if SQLite is empty (e.g. fresh runner in CI)."""
        try:
            with open(STATE_JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            tweets = data.get("tweets", [])
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM processed_tweets")
                if cursor.fetchone()[0] == 0 and tweets:
                    for t in tweets:
                        cursor.execute("""
                            INSERT OR IGNORE INTO processed_tweets (
                                id, handle, is_newsworthy, confidence_score, emailed_at, created_at
                            ) VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            str(t.get("id")),
                            t.get("handle", ""),
                            t.get("is_newsworthy", 0),
                            t.get("confidence_score", 0),
                            t.get("emailed_at"),
                            t.get("created_at", datetime.utcnow().isoformat())
                        ))
                    conn.commit()
        except Exception:
            pass
'''

files["src/scrapers/__init__.py"] = '"""Scraper modules for Twitter data ingestion."""\n'

files["src/scrapers/base.py"] = '''"""Base models and abstract scraper interface."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

@dataclass
class Tweet:
    id: str
    handle: str
    text: str
    url: str
    posted_at: Optional[datetime] = None
    is_reply: bool = False
    is_retweet: bool = False
    like_count: int = 0
    retweet_count: int = 0
    raw_data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "handle": self.handle,
            "text": self.text,
            "url": self.url,
            "posted_at": self.posted_at.isoformat() if self.posted_at else None,
            "is_reply": self.is_reply,
            "is_retweet": self.is_retweet,
            "like_count": self.like_count,
            "retweet_count": self.retweet_count
        }

class BaseScraper(ABC):
    @abstractmethod
    def fetch_tweets(self, handle: str, limit: int = 10) -> List[Tweet]:
        """Fetch recent tweets for the specified handle."""
        pass
'''

files["src/scrapers/syndication.py"] = '''"""Lightweight 100% free syndication and public timeline scraper."""
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
'''

files["src/scrapers/browser.py"] = '''"""Playwright headless browser scraper fallback for Twitter timelines."""
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
'''

files["src/analyzer.py"] = '''"""AI Intelligence Layer: Google Gemini Flash Newsworthiness Evaluator."""
import os
import json
import logging
from typing import Optional
from pydantic import BaseModel, Field
import requests
from src.scrapers.base import Tweet

logger = logging.getLogger(__name__)

class NewsEvaluation(BaseModel):
    is_newsworthy: bool = Field(description="True if the tweet contains significant, genuine newsworthy content; False if mundane or conversational.")
    confidence_score: int = Field(description="Confidence score from 1 (lowest) to 10 (highest/breaking news).", ge=1, le=10)
    headline: str = Field(description="A concise, punchy journalistic headline summarizing the news event in 10-15 words.")
    summary: str = Field(description="A 1-2 sentence executive summary explaining what happened and why it matters.")
    category: str = Field(description="Category of the news: 'Product Launch', 'AI/Tech Breakthrough', 'Corporate/M&A', 'Policy & Regulation', 'Industry Statement', or 'Other'.")
    reasoning: str = Field(description="Brief editorial reasoning explaining the score.")

class TweetAnalyzer:
    def __init__(self, api_key: str, criteria_prompt: str, min_confidence_score: int = 7):
        self.api_key = api_key
        self.criteria_prompt = criteria_prompt
        self.min_confidence_score = min_confidence_score

    def evaluate_tweet(self, tweet: Tweet) -> NewsEvaluation:
        """Evaluate a tweet using Google Gemini Flash structured output."""
        if not self.api_key:
            logger.error("GEMINI_API_KEY is not set! Skipping AI evaluation.")
            return NewsEvaluation(
                is_newsworthy=False,
                confidence_score=1,
                headline="API Key Missing",
                summary="Please configure GEMINI_API_KEY in your .env file.",
                category="Other",
                reasoning="Missing API key."
            )

        # Primary method: Direct Google Gemini REST API (Zero-dependency on SDK version mismatches)
        try:
            return self._evaluate_via_rest(tweet)
        except Exception as e:
            logger.warning(f"REST API call failed: {e}. Trying SDK...")

        # Secondary method: google-genai SDK
        try:
            return self._evaluate_via_sdk(tweet)
        except Exception as e:
            logger.error(f"Failed to evaluate tweet {tweet.id}: {e}")
            return NewsEvaluation(
                is_newsworthy=False,
                confidence_score=1,
                headline="Evaluation Error",
                summary="An error occurred while evaluating this tweet.",
                category="Other",
                reasoning=str(e)
            )

    def _build_prompt(self, tweet: Tweet) -> str:
        posted_str = tweet.posted_at.strftime('%Y-%m-%d %H:%M:%S UTC') if tweet.posted_at else 'Recent'
        return f"""{self.criteria_prompt}

--------------------------------------------------
TWEET TO EVALUATE:
Author: @{tweet.handle}
Timestamp: {posted_str}
URL: {tweet.url}
Tweet Content:
\"\"\"
{tweet.text}
\"\"\"
--------------------------------------------------

Respond ONLY with a valid JSON object matching this schema:
{{
  "is_newsworthy": boolean,
  "confidence_score": integer (1 to 10),
  "headline": string,
  "summary": string,
  "category": string,
  "reasoning": string
}}
"""

    def _evaluate_via_rest(self, tweet: Tweet) -> NewsEvaluation:
        """Evaluate via Gemini 2.0 Flash / 1.5 Flash REST endpoint."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.api_key}"
        
        prompt = self._build_prompt(tweet)
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "response_mime_type": "application/json"
            }
        }

        resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
        
        if resp.status_code == 404:
            # Fallback to gemini-1.5-flash
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
            resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=30)

        if resp.status_code != 200:
            raise RuntimeError(f"Gemini API returned status {resp.status_code}: {resp.text}")

        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError("No generation candidates returned from Gemini.")

        text_content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        parsed_json = json.loads(text_content)
        
        return NewsEvaluation(**parsed_json)

    def _evaluate_via_sdk(self, tweet: Tweet) -> NewsEvaluation:
        """Evaluate via google-genai or google-generativeai SDK."""
        prompt = self._build_prompt(tweet)
        
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt,
                config={'response_mime_type': 'application/json'}
            )
            parsed_json = json.loads(response.text)
            return NewsEvaluation(**parsed_json)
        except Exception:
            import google.generativeai as gai
            gai.configure(api_key=self.api_key)
            model = gai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            parsed_json = json.loads(response.text)
            return NewsEvaluation(**parsed_json)
'''

files["src/notifier.py"] = '''"""Email dispatch module using 100% free Gmail SMTP with App Passwords."""
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List
from datetime import datetime
from src.scrapers.base import Tweet
from src.analyzer import NewsEvaluation

logger = logging.getLogger(__name__)

class GmailNotifier:
    """
    Sends rich HTML news alerts via Gmail SMTP.
    Uses free Google App Passwords (500 emails/day completely free forever).
    """
    def __init__(self, gmail_address: str, gmail_app_password: str, default_recipients: List[str], subject_prefix: str = "[NEWS ALERT]"):
        self.gmail_address = gmail_address.strip()
        self.gmail_app_password = gmail_app_password.replace(" ", "").strip()
        self.default_recipients = default_recipients
        self.subject_prefix = subject_prefix

    def send_alert(self, tweet: Tweet, evaluation: NewsEvaluation, recipients: List[str] = None) -> bool:
        target_recipients = recipients or self.default_recipients
        if not target_recipients:
            logger.warning("No email recipients configured! Alert not sent.")
            return False

        if not self.gmail_address or not self.gmail_app_password:
            logger.error("GMAIL_ADDRESS or GMAIL_APP_PASSWORD not set in .env! Cannot send email.")
            return False

        subject = f"{self.subject_prefix} @{tweet.handle}: {evaluation.headline}"
        html_content = self._render_html_template(tweet, evaluation)
        text_content = self._render_plain_text(tweet, evaluation)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"Twitter News Tracker <{self.gmail_address}>"
        msg["To"] = ", ".join(target_recipients)
        msg["Date"] = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")

        msg.attach(MIMEText(text_content, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        try:
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(self.gmail_address, self.gmail_app_password)
                server.sendmail(self.gmail_address, target_recipients, msg.as_string())
            
            logger.info(f"Successfully sent email alert to {target_recipients} for @{tweet.handle} (Score: {evaluation.confidence_score}/10)")
            return True
        except Exception as e:
            logger.error(f"Failed to send email alert via Gmail SMTP: {e}")
            return False

    def _render_plain_text(self, tweet: Tweet, eval: NewsEvaluation) -> str:
        return f"""
{self.subject_prefix} - {eval.headline}

Author: @{tweet.handle}
Category: {eval.category}
Confidence Score: {eval.confidence_score}/10
Link: {tweet.url}

EXECUTIVE SUMMARY:
{eval.summary}

ORIGINAL TWEET:
\"{tweet.text}\"

EDITORIAL REASONING:
{eval.reasoning}

---
Tracked 24/7 by Twitter News Tracker (100% Free Forever)
"""

    def _render_html_template(self, tweet: Tweet, eval: NewsEvaluation) -> str:
        score_color = "#10b981" if eval.confidence_score >= 8 else "#f59e0b"
        posted_str = tweet.posted_at.strftime('%B %d, %Y at %H:%M UTC') if tweet.posted_at else 'Just now'
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{eval.headline}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #0f172a; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #f8fafc;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: #0f172a; padding: 30px 10px;">
    <tr>
      <td align="center">
        <!-- Container -->
        <table role="presentation" width="100%" style="max-width: 600px; background-color: #1e293b; border-radius: 16px; overflow: hidden; border: 1px solid #334155; box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);">
          
          <!-- Header Banner -->
          <tr>
            <td style="background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #4338ca 100%); padding: 24px 30px;">
              <table width="100%" cellspacing="0" cellpadding="0">
                <tr>
                  <td>
                    <span style="background-color: rgba(255, 255, 255, 0.15); color: #e0e7ff; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; padding: 4px 10px; border-radius: 9999px; display: inline-block;">
                      {eval.category}
                    </span>
                  </td>
                  <td align="right">
                    <span style="background-color: {score_color}; color: #ffffff; font-size: 12px; font-weight: 800; padding: 4px 10px; border-radius: 9999px; display: inline-block;">
                      Score: {eval.confidence_score}/10
                    </span>
                  </td>
                </tr>
                <tr>
                  <td colspan="2" style="padding-top: 14px;">
                    <h1 style="color: #ffffff; font-size: 22px; font-weight: 800; line-height: 1.3; margin: 0;">
                      {eval.headline}
                    </h1>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Body Content -->
          <tr>
            <td style="padding: 28px 30px;">
              
              <!-- Author Card -->
              <table width="100%" cellspacing="0" cellpadding="0" style="margin-bottom: 20px; background-color: #0f172a; padding: 12px 16px; border-radius: 10px; border: 1px solid #334155;">
                <tr>
                  <td>
                    <span style="font-size: 15px; font-weight: 700; color: #38bdf8;">@{tweet.handle}</span>
                    <span style="font-size: 12px; color: #94a3b8; margin-left: 8px;">• {posted_str}</span>
                  </td>
                </tr>
              </table>

              <!-- Summary Card -->
              <div style="margin-bottom: 24px;">
                <h3 style="font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: #94a3b8; margin: 0 0 8px 0;">
                  Executive Summary
                </h3>
                <p style="font-size: 16px; line-height: 1.5; color: #f1f5f9; margin: 0; font-weight: 500;">
                  {eval.summary}
                </p>
              </div>

              <!-- Original Tweet Quote -->
              <div style="background-color: #0f172a; border-left: 4px solid #6366f1; padding: 16px 20px; border-radius: 0 10px 10px 0; margin-bottom: 24px;">
                <h4 style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: #818cf8; margin: 0 0 8px 0;">
                  Original Post Content
                </h4>
                <p style="font-size: 14px; line-height: 1.6; color: #cbd5e1; margin: 0; white-space: pre-wrap;">{tweet.text}</p>
              </div>

              <!-- Reasoning -->
              <div style="margin-bottom: 28px;">
                <h4 style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: #64748b; margin: 0 0 4px 0;">
                  Editor Analysis
                </h4>
                <p style="font-size: 13px; color: #94a3b8; line-height: 1.4; margin: 0;">
                  {eval.reasoning}
                </p>
              </div>

              <!-- Action Button -->
              <table width="100%" cellspacing="0" cellpadding="0">
                <tr>
                  <td align="center">
                    <a href="{tweet.url}" target="_blank" style="background-color: #6366f1; color: #ffffff; text-decoration: none; padding: 12px 28px; border-radius: 8px; font-size: 14px; font-weight: 700; display: inline-block; box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);">
                      View Original Post on X &rarr;
                    </a>
                  </td>
                </tr>
              </table>

            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background-color: #0f172a; padding: 16px 30px; border-top: 1px solid #334155; text-align: center;">
              <p style="font-size: 11px; color: #64748b; margin: 0;">
                Twitter News Tracker • 24/7 Autonomous Intelligence • 100% Free Forever
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
'''

files["src/tracker.py"] = '''"""Main Tracker Orchestration Engine."""
import logging
from typing import List, Optional
from datetime import datetime
from src.config import AppConfig, load_config
from src.db import TrackerDB
from src.scrapers.base import BaseScraper, Tweet
from src.scrapers.syndication import SyndicationScraper
from src.scrapers.browser import BrowserScraper
from src.analyzer import TweetAnalyzer, NewsEvaluation
from src.notifier import GmailNotifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("TrackerEngine")

class TwitterNewsTracker:
    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or load_config()
        self.db = TrackerDB()
        
        # Initialize scrapers
        self.syndication_scraper = SyndicationScraper(timeout=self.config.scraper.timeout_seconds)
        self.browser_scraper = BrowserScraper(
            auth_token=self.config.twitter_auth_token,
            timeout=self.config.scraper.timeout_seconds
        )
        
        # Initialize AI Analyzer
        self.analyzer = TweetAnalyzer(
            api_key=self.config.gemini_api_key,
            criteria_prompt=self.config.newsworthiness_prompt,
            min_confidence_score=self.config.min_confidence_score
        )
        
        # Initialize Notifier
        self.notifier = GmailNotifier(
            gmail_address=self.config.gmail_address,
            gmail_app_password=self.config.gmail_app_password,
            default_recipients=self.config.recipient_emails,
            subject_prefix=self.config.notifications.subject_prefix
        )

    def fetch_account_tweets(self, handle: str) -> List[Tweet]:
        """Fetch tweets for a handle based on configured scraper mode."""
        mode = self.config.scraper.mode.lower()
        limit = self.config.scraper.max_tweets_per_account
        
        if mode == "syndication":
            return self.syndication_scraper.fetch_tweets(handle, limit=limit)
        elif mode == "browser":
            return self.browser_scraper.fetch_tweets(handle, limit=limit)
        else: # auto mode: try syndication first, fallback to browser
            tweets = self.syndication_scraper.fetch_tweets(handle, limit=limit)
            if not tweets:
                logger.info(f"Syndication returned 0 tweets for @{handle}. Falling back to browser scraper...")
                tweets = self.browser_scraper.fetch_tweets(handle, limit=limit)
            return tweets

    def run_cycle(self) -> int:
        """
        Execute one complete monitoring cycle across all tracked accounts.
        Returns the number of newsworthy alerts dispatched.
        """
        logger.info(f"--- Starting Twitter News Tracker Cycle: {len(self.config.tracked_accounts)} accounts ---")
        alerts_sent = 0
        total_tweets_evaluated = 0

        for handle in self.config.tracked_accounts:
            try:
                logger.info(f"Checking @{handle}...")
                tweets = self.fetch_account_tweets(handle)
                
                for tweet in tweets:
                    # Filter replies/retweets if disabled in config
                    if not self.config.scraper.include_replies and tweet.is_reply:
                        continue
                    if not self.config.scraper.include_retweets and tweet.is_retweet:
                        continue

                    # Check if already processed in database
                    if self.db.is_tweet_seen(tweet.id):
                        continue

                    logger.info(f"New tweet found from @{handle} [{tweet.id}]: {tweet.text[:60]}...")
                    total_tweets_evaluated += 1

                    # AI Evaluation via Gemini Flash
                    evaluation: NewsEvaluation = self.analyzer.evaluate_tweet(tweet)
                    logger.info(
                        f"AI Decision for @{handle} [{tweet.id}]: "
                        f"Newsworthy={evaluation.is_newsworthy} | "
                        f"Score={evaluation.confidence_score}/10 | "
                        f"Category='{evaluation.category}'"
                    )

                    emailed_at = None
                    # Trigger alert if criteria met
                    if evaluation.is_newsworthy and evaluation.confidence_score >= self.config.min_confidence_score:
                        logger.info(f"🚨 NEWSWORTHY ALERT: '{evaluation.headline}' (Score: {evaluation.confidence_score})")
                        email_success = self.notifier.send_alert(tweet, evaluation)
                        if email_success:
                            emailed_at = datetime.utcnow().isoformat()
                            alerts_sent += 1

                    # Save to DB and export state JSON
                    self.db.save_evaluation(
                        tweet_id=tweet.id,
                        handle=tweet.handle,
                        text=tweet.text,
                        posted_at=tweet.posted_at.isoformat() if tweet.posted_at else None,
                        url=tweet.url,
                        is_newsworthy=evaluation.is_newsworthy,
                        confidence_score=evaluation.confidence_score,
                        headline=evaluation.headline,
                        summary=evaluation.summary,
                        category=evaluation.category,
                        reasoning=evaluation.reasoning,
                        emailed_at=emailed_at
                    )

            except Exception as e:
                logger.error(f"Error while processing @{handle}: {e}", exc_info=True)

        logger.info(
            f"--- Cycle Complete: {total_tweets_evaluated} new tweets evaluated, "
            f"{alerts_sent} alerts sent ---"
        )
        return alerts_sent
'''

files["run_once.py"] = '''"""Single-pass runner for cron jobs and GitHub Actions."""
import sys
from src.tracker import TwitterNewsTracker

def main():
    tracker = TwitterNewsTracker()
    alerts = tracker.run_cycle()
    print(f"Execution finished successfully. {alerts} alert(s) sent.")
    sys.exit(0)

if __name__ == "__main__":
    main()
'''

files["run_daemon.py"] = '''"""24/7 continuous background runner for Always-Free Cloud VMs / servers."""
import time
import random
import signal
import sys
import logging
from src.tracker import TwitterNewsTracker
from src.config import load_config

logger = logging.getLogger("TwitterNewsDaemon")

running = True

def handle_exit(signum, frame):
    global running
    logger.info("Received termination signal. Shutting down daemon gracefully...")
    running = False

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

def main():
    config = load_config()
    tracker = TwitterNewsTracker(config)
    
    poll_interval = config.daemon.poll_interval_seconds
    jitter = config.daemon.jitter_seconds

    logger.info(f"Starting 24/7 Twitter News Tracker Daemon (Interval: {poll_interval}s +/- {jitter}s)")
    
    while running:
        try:
            tracker.run_cycle()
        except Exception as e:
            logger.error(f"Unexpected error during cycle: {e}", exc_info=True)

        if not running:
            break

        # Calculate sleep time with randomized jitter
        sleep_duration = max(10, poll_interval + random.randint(-jitter, jitter))
        logger.info(f"Sleeping for {sleep_duration} seconds until next cycle...")
        
        # Sleep in small increments to respond promptly to termination signals
        for _ in range(sleep_duration):
            if not running:
                break
            time.sleep(1)

    logger.info("Twitter News Tracker Daemon has stopped.")
    sys.exit(0)

if __name__ == "__main__":
    main()
'''

files[".github/workflows/tracker_cron.yml"] = """name: 24/7 Twitter News Tracker Cron

on:
  schedule:
    # Runs every 15 minutes (100% free on GitHub Actions)
    - cron: '*/15 * * * *'
  workflow_dispatch: # Allows manual trigger from GitHub UI

jobs:
  track-news:
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4
        with:
          persist-credentials: true

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run Tracker Single Cycle
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          GMAIL_ADDRESS: ${{ secrets.GMAIL_ADDRESS }}
          GMAIL_APP_PASSWORD: ${{ secrets.GMAIL_APP_PASSWORD }}
          ALERT_RECIPIENT_EMAILS: ${{ secrets.ALERT_RECIPIENT_EMAILS }}
        run: |
          python run_once.py

      - name: Commit & Push Updated State
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "github-actions[bot]@users.noreply.github.com"
          git add data/state.json
          git diff --staged --quiet || git commit -m "Auto-update processed tweet state [skip ci]"
          git push
"""

files["Dockerfile"] = """FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browser dependencies if needed
# RUN playwright install --with-deps chromium

COPY . .

ENV PYTHONUNBUFFERED=1

CMD ["python", "run_daemon.py"]
"""

files["docker-compose.yml"] = """version: '3.8'

services:
  twitter-tracker:
    build: .
    container_name: twitter-news-tracker
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./data:/app/data
      - ./config.yaml:/app/config.yaml
"""

files["setup_systemd.sh"] = """#!/bin/bash
# ------------------------------------------------------------------
# 1-Click Systemd Service Installer for Always-Free Linux VMs
# (e.g. Oracle Cloud Free Tier / GCP e2-micro / Ubuntu / Debian)
# ------------------------------------------------------------------

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
USER="$(whoami)"
SERVICE_FILE="/etc/systemd/system/twitter-tracker.service"

echo "Configuring Twitter News Tracker systemd service for user $USER in $DIR..."

sudo bash -c "cat << EOF > $SERVICE_FILE
[Unit]
Description=24/7 Twitter News Tracker Daemon (Free Forever)
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$DIR
ExecStart=/usr/bin/python3 $DIR/run_daemon.py
Restart=always
RestartSec=10
EnvironmentFile=$DIR/.env

[Install]
WantedBy=multi-user.target
EOF"

sudo systemctl daemon-reload
sudo systemctl enable twitter-tracker.service
sudo systemctl restart twitter-tracker.service

echo "=========================================================="
echo "✅ Twitter News Tracker is now running 24/7 as a system service!"
echo "Check status: sudo systemctl status twitter-tracker.service"
echo "View live logs: sudo journalctl -u twitter-tracker.service -f"
echo "=========================================================="
"""

files["README.md"] = """# 🛰️ 24/7 Free Forever Twitter Newsworthy Tracker

An autonomous, **100% zero-cost** news intelligence engine that monitors high-impact Twitter/X accounts 24/7, evaluates every new post with **Google Gemini Flash AI** against rigorous journalistic criteria, and delivers instant, beautiful HTML news alerts straight to your Gmail inbox.

---

## 💎 Why This is 100% Free Forever

| Component | Standard Paid Cost | Our Free Architecture | Monthly Cost |
| :--- | :--- | :--- | :--- |
| **Twitter / X API** | \$100 – \$5,000 / mo | Open Syndication Endpoints + Playwright fallback | **\$0.00** |
| **AI News Evaluation** | \$20 – \$50 / mo | Google Gemini Flash Free Tier (1,500 req/day) | **\$0.00** |
| **Email Delivery** | \$15 – \$35 / mo | Direct Gmail SMTP via Google App Passwords (500/day) | **\$0.00** |
| **24/7 Cloud Hosting** | \$5 – \$20 / mo | GitHub Actions Cron OR Oracle Cloud Always-Free VM | **\$0.00** |
| **TOTAL** | **\$140+ / month** | **Completely Free Forever** | **\$0.00** |

---

## 🚀 Quick Start (Local Setup in 2 Minutes)

### 1. Clone and Install Dependencies
```bash
git clone <your-repo-url>
cd twitter-news-tracker
pip install -r requirements.txt
```

### 2. Configure Your Free API Keys (`.env`)
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Fill in the 3 required secrets:
1. **`GEMINI_API_KEY`**: Get a free API key instantly at [Google AI Studio](https://aistudio.google.com/).
2. **`GMAIL_ADDRESS`**: Your personal Gmail address.
3. **`GMAIL_APP_PASSWORD`**: Generate a free 16-character App Password at [Google Account App Passwords](https://myaccount.google.com/apppasswords).
4. **`ALERT_RECIPIENT_EMAILS`**: Where you want alerts delivered.

### 3. Customize Monitored Accounts & Criteria (`config.yaml`)
Open `config.yaml` to adjust the tracked handles or customize the global newsworthiness criteria prompt.

### 4. Run a Test Cycle
```bash
python run_once.py
```

---

## 🌐 24/7 Deployment Options (Choose Either)

### Option 1: GitHub Actions (Easiest — Zero Server Required)
GitHub Actions provides free scheduled cron jobs forever:
1. Push this project to a GitHub repository (Public repos have **unlimited free minutes**; Private repos have 2,000 mins/mo).
2. Go to **Settings > Secrets and variables > Actions** in your GitHub repo.
3. Add these repository secrets:
   - `GEMINI_API_KEY`
   - `GMAIL_ADDRESS`
   - `GMAIL_APP_PASSWORD`
   - `ALERT_RECIPIENT_EMAILS`
4. That's it! The workflow in `.github/workflows/tracker_cron.yml` will run automatically every 15 minutes and commit the updated `data/state.json` history back to your repository.

---

### Option 2: Always-Free Cloud VM (Oracle Cloud / GCP / Local Server)
For continuous sub-minute tracking on a cloud server:
1. Launch an [Oracle Cloud Always Free VM](https://www.oracle.com/cloud/free/) (4 ARM cores, 24 GB RAM forever free) or a [Google Cloud e2-micro VM](https://cloud.google.com/free).
2. Clone the repo and configure `.env`.
3. Run the automated 1-click systemd installer:
   ```bash
   chmod +x setup_systemd.sh
   ./setup_systemd.sh
   ```
4. Check status anytime:
   ```bash
   sudo systemctl status twitter-tracker.service
   sudo journalctl -u twitter-tracker.service -f
   ```

---

## 🛠️ Architecture Overview

```
                          [ Tracked Twitter Accounts ]
                                      │
              ┌───────────────────────┴───────────────────────┐
              ▼                                               ▼
    [ Syndication Scraper ]                        [ Playwright Scraper ]
   (Zero-cookie CDN Timeline)                      (Dynamic Browser Fallback)
              │                                               │
              └───────────────────────┬───────────────────────┘
                                      ▼
                        [ SQLite Deduplication DB ]
                        (Skips already-seen tweets)
                                      ▼
                       [ Google Gemini Flash Free ]
                      (Strict Newsworthiness Score)
                                      │
               ┌──────────────────────┴──────────────────────┐
               ▼                                             ▼
       [ Non-Newsworthy ]                            [ Newsworthy (Score >= 7) ]
     (Logged & Saved to DB)                                  │
                                                             ▼
                                                    [ Gmail SMTP Engine ]
                                                   (Rich HTML News Alert)
                                                             │
                                                             ▼
                                                    [ Delivered to Inbox ]
```

---

## 📄 License
MIT License — Free to modify, distribute, and use for personal or commercial projects forever.
"""

for rel_path, content in files.items():
    full_path = os.path.join(BASE_DIR, rel_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Wrote {rel_path}")

print("All project files created successfully!")
