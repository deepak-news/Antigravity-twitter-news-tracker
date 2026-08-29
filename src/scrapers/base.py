"""Base models and abstract scraper interface."""
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
