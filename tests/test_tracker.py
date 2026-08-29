import os
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone

from src.config import AppConfig, load_config
from src.db import TrackerDB
from src.scrapers.base import Tweet
from src.analyzer import NewsEvaluation, TweetAnalyzer
from src.notifier import GmailNotifier

class TestTrackerComponents(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_tracker.db"
        self.state_path = Path(self.temp_dir.name) / "state.json"
        self.db = TrackerDB(db_path=self.db_path, state_json_path=self.state_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_config_loader(self):
        config = load_config()
        self.assertIsInstance(config, AppConfig)
        self.assertTrue(len(config.tracked_accounts) > 0)
        self.assertIn("sama", config.tracked_accounts)
        self.assertEqual(config.min_confidence_score, 7)

    def test_database_deduplication(self):
        tweet_id = "1234567890"
        self.assertFalse(self.db.is_tweet_seen(tweet_id))

        self.db.save_evaluation(
            tweet_id=tweet_id,
            handle="sama",
            text="GPT-5 is now live and freely available to all humanity.",
            posted_at=datetime.now(timezone.utc).isoformat(),
            url="https://x.com/sama/status/1234567890",
            is_newsworthy=True,
            confidence_score=10,
            headline="OpenAI Launches GPT-5 Globally for Free",
            summary="Sam Altman announces the release of GPT-5.",
            category="AI/Tech Breakthrough",
            reasoning="Major AI model launch announcement."
        )

        # Should now be seen
        self.assertTrue(self.db.is_tweet_seen(tweet_id))

        # Test state export and reload
        export_path = Path(self.temp_dir.name) / "exported_state.json"
        self.db.export_state_json(export_path)
        self.assertTrue(export_path.exists())

        alerts = self.db.get_recent_alerts()
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["headline"], "OpenAI Launches GPT-5 Globally for Free")

    def test_html_email_rendering(self):
        tweet = Tweet(
            id="9876543210",
            handle="elonmusk",
            text="Starship Flight 7 was completely successful. All orbital objectives achieved.",
            url="https://x.com/elonmusk/status/9876543210",
            posted_at=datetime.now(timezone.utc)
        )
        evaluation = NewsEvaluation(
            is_newsworthy=True,
            confidence_score=9,
            headline="SpaceX Starship Flight 7 Achieves All Orbital Objectives",
            summary="Elon Musk announces complete mission success for Starship Flight 7.",
            category="Breakthrough",
            reasoning="Critical aerospace milestone with high public relevance."
        )
        notifier = GmailNotifier(
            gmail_address="test@gmail.com",
            gmail_app_password="fakepassword123",
            default_recipients=["alerts@example.com"]
        )

        html = notifier._render_html_template(tweet, evaluation)
        self.assertIn("@elonmusk", html)
        self.assertIn("Score: 9/10", html)
        self.assertIn("SpaceX Starship Flight 7", html)
        self.assertIn("https://x.com/elonmusk/status/9876543210", html)

    def test_analyzer_schema_and_prompt(self):
        analyzer = TweetAnalyzer(
            api_key="mock_key",
            criteria_prompt="Evaluate newsworthiness.",
            min_confidence_score=7
        )
        tweet = Tweet(
            id="1111111",
            handle="testuser",
            text="We just raised $500M Series B.",
            url="https://x.com/testuser/status/1111111"
        )
        prompt = analyzer._build_prompt(tweet)
        self.assertIn("@testuser", prompt)
        self.assertIn("We just raised $500M Series B.", prompt)
        self.assertIn("is_newsworthy", prompt)

if __name__ == "__main__":
    unittest.main()
