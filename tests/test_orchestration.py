import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
import tempfile

from src.config import AppConfig, ScraperConfig, NotificationConfig, DaemonConfig
from src.tracker import TwitterNewsTracker
from src.scrapers.base import Tweet
from src.analyzer import NewsEvaluation

class TestTrackerOrchestration(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_tracker.db"
        self.state_path = Path(self.temp_dir.name) / "state.json"
        
        self.config = AppConfig(
            tracked_accounts=["sama", "elonmusk"],
            newsworthiness_prompt="Test prompt",
            min_confidence_score=7,
            scraper=ScraperConfig(mode="auto", max_tweets_per_account=5, include_replies=False, include_retweets=False),
            notifications=NotificationConfig(subject_prefix="[TEST ALERT]", recipient_emails=["test@example.com"]),
            daemon=DaemonConfig(poll_interval_seconds=60),
            gemini_api_key="fake_key",
            gmail_address="fake@gmail.com",
            gmail_app_password="fake_password",
            recipient_emails=["test@example.com"]
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_full_pipeline_with_newsworthy_tweet(self):
        tracker = TwitterNewsTracker(self.config)
        tracker.db.db_path = self.db_path
        tracker.db.state_json_path = self.state_path
        tracker.db._ensure_dirs()
        tracker.db.init_db()

        # Mock scraper output
        sample_tweet = Tweet(
            id="10001",
            handle="sama",
            text="Announcing GPT-5 today with revolutionary reasoning capabilities.",
            url="https://x.com/sama/status/10001"
        )
        tracker.fetch_account_tweets = MagicMock(side_effect=lambda handle: [sample_tweet] if handle == "sama" else [])

        # Mock analyzer evaluation
        mock_eval = NewsEvaluation(
            is_newsworthy=True,
            confidence_score=9,
            headline="OpenAI Announces GPT-5 with Revolutionary Reasoning",
            summary="Sam Altman announces GPT-5 release.",
            category="AI/Tech Breakthrough",
            reasoning="Major AI model launch."
        )
        tracker.analyzer.evaluate_tweet = MagicMock(return_value=mock_eval)

        # Mock email sender
        tracker.notifier.send_alert = MagicMock(return_value=True)

        # Run cycle
        alerts = tracker.run_cycle()

        # Assertions
        self.assertEqual(alerts, 1)
        tracker.analyzer.evaluate_tweet.assert_called_once_with(sample_tweet)
        tracker.notifier.send_alert.assert_called_once_with(sample_tweet, mock_eval)
        self.assertTrue(tracker.db.is_tweet_seen("10001"))

        # Second run should skip already seen tweet
        alerts_second_run = tracker.run_cycle()
        self.assertEqual(alerts_second_run, 0)
        # Analyzer should NOT be called again
        self.assertEqual(tracker.analyzer.evaluate_tweet.call_count, 1)

    def test_pipeline_filters_non_newsworthy_tweet(self):
        tracker = TwitterNewsTracker(self.config)
        tracker.db.db_path = self.db_path
        tracker.db.state_json_path = self.state_path
        tracker.db._ensure_dirs()
        tracker.db.init_db()

        sample_tweet = Tweet(
            id="10002",
            handle="elonmusk",
            text="gm everyone :)",
            url="https://x.com/elonmusk/status/10002"
        )
        tracker.fetch_account_tweets = MagicMock(return_value=[sample_tweet])

        mock_eval = NewsEvaluation(
            is_newsworthy=False,
            confidence_score=2,
            headline="Casual Greeting",
            summary="Elon Musk posts a casual morning greeting.",
            category="Other",
            reasoning="Casual greeting, not newsworthy."
        )
        tracker.analyzer.evaluate_tweet = MagicMock(return_value=mock_eval)
        tracker.notifier.send_alert = MagicMock(return_value=True)

        alerts = tracker.run_cycle()

        self.assertEqual(alerts, 0)
        tracker.notifier.send_alert.assert_not_called()
        self.assertTrue(tracker.db.is_tweet_seen("10002"))

if __name__ == "__main__":
    unittest.main()
