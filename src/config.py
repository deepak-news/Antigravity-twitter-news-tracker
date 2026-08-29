"""Configuration loader with environment variable validation."""
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
