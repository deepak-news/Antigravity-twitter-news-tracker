"""Main Tracker Orchestration Engine."""
import logging
from typing import List, Optional
from datetime import datetime, timezone
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
                            emailed_at = datetime.now(timezone.utc).isoformat()
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
