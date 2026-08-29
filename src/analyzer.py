"""AI Intelligence Layer: Google Gemini Flash Newsworthiness Evaluator."""
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
        separator = "-" * 50
        return (
            f"{self.criteria_prompt}\n\n"
            f"{separator}\n"
            f"TWEET TO EVALUATE:\n"
            f"Author: @{tweet.handle}\n"
            f"Timestamp: {posted_str}\n"
            f"URL: {tweet.url}\n"
            f"Tweet Content:\n"
            f"'''\n{tweet.text}\n'''\n"
            f"{separator}\n\n"
            "Respond ONLY with a valid JSON object matching this schema:\n"
            "{\n"
            '  "is_newsworthy": boolean,\n'
            '  "confidence_score": integer (1 to 10),\n'
            '  "headline": string,\n'
            '  "summary": string,\n'
            '  "category": string,\n'
            '  "reasoning": string\n'
            "}\n"
        )

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
