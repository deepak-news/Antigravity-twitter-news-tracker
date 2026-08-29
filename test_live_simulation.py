"""
Demo & Verification Script
Simulates a live tracking cycle with realistic sample tweets (both breaking news and mundane posts),
demonstrating AI newsworthiness classification, deduplication, and HTML email alert rendering.
"""
import os
import sys
from datetime import datetime, timezone
from src.config import load_config
from src.tracker import TwitterNewsTracker
from src.scrapers.base import Tweet
from src.analyzer import NewsEvaluation

def run_simulation():
    print("=" * 70)
    print("🛰️  TWITTER NEWS TRACKER - INTERACTIVE LIVE SIMULATION")
    print("=" * 70)

    config = load_config()
    tracker = TwitterNewsTracker(config)

    sample_tweets = [
        Tweet(
            id="sim-001",
            handle="sama",
            text="Today we are releasing GPT-5. It achieves state-of-the-art benchmarks in complex reasoning, mathematics, and autonomous software engineering. Available starting now for all API tiers.",
            url="https://x.com/sama/status/sim-001",
            posted_at=datetime.now(timezone.utc)
        ),
        Tweet(
            id="sim-002",
            handle="sama",
            text="great coffee this morning in SF",
            url="https://x.com/sama/status/sim-002",
            posted_at=datetime.now(timezone.utc)
        ),
        Tweet(
            id="sim-003",
            handle="elonmusk",
            text="Starship Flight 7 launched today and completed its first orbital cargo deployment test. Super Heavy booster was successfully caught by the tower arms.",
            url="https://x.com/elonmusk/status/sim-003",
            posted_at=datetime.now(timezone.utc)
        ),
        Tweet(
            id="sim-004",
            handle="karpathy",
            text="A fun little weekend exploration on nanoGPT tokenizer optimizations.",
            url="https://x.com/karpathy/status/sim-004",
            posted_at=datetime.now(timezone.utc)
        )
    ]

    print(f"\n[1] Ingesting {len(sample_tweets)} simulated tweets across @sama, @elonmusk, @karpathy...\n")

    for tweet in sample_tweets:
        print(f"👉 Processing Tweet [{tweet.id}] from @{tweet.handle}:")
        print(f"   Content: \"{tweet.text}\"")

        # Mock AI evaluation if GEMINI_API_KEY is not set for immediate offline testing
        if not config.gemini_api_key:
            if "GPT-5" in tweet.text:
                evaluation = NewsEvaluation(
                    is_newsworthy=True,
                    confidence_score=10,
                    headline="OpenAI Launches GPT-5 with State-of-the-Art Reasoning",
                    summary="Sam Altman announces the immediate release of GPT-5 across all API tiers with top benchmark scores.",
                    category="AI/Tech Breakthrough",
                    reasoning="Major flagship model launch by leading AI laboratory."
                )
            elif "Starship" in tweet.text:
                evaluation = NewsEvaluation(
                    is_newsworthy=True,
                    confidence_score=9,
                    headline="SpaceX Completes Starship Flight 7 and Booster Catch",
                    summary="Elon Musk confirms successful orbital cargo test and launch tower booster catch for Starship Flight 7.",
                    category="Product Launch / Milestone",
                    reasoning="Key aerospace milestone with major technological impact."
                )
            else:
                evaluation = NewsEvaluation(
                    is_newsworthy=False,
                    confidence_score=2,
                    headline="Casual Social Update",
                    summary="Routine social remark without major news announcement.",
                    category="Other",
                    reasoning="Casual post lacking public or industry significance."
                )
        else:
            evaluation = tracker.analyzer.evaluate_tweet(tweet)

        print(f"   🔍 AI Evaluation:")
        print(f"      • Newsworthy: {'✅ YES' if evaluation.is_newsworthy else '❌ NO'}")
        print(f"      • Confidence Score: {evaluation.confidence_score}/10")
        print(f"      • Category: {evaluation.category}")
        print(f"      • Headline: {evaluation.headline}")
        print(f"      • Summary: {evaluation.summary}")

        if evaluation.is_newsworthy and evaluation.confidence_score >= config.min_confidence_score:
            print(f"   🚨 ALERT TRIGGERED: Sending email to {config.recipient_emails or ['configured recipients']}...")
            # Save demo HTML preview
            preview_file = f"data/preview_alert_{tweet.id}.html"
            os.makedirs("data", exist_ok=True)
            with open(preview_file, "w", encoding="utf-8") as f:
                f.write(tracker.notifier._render_html_template(tweet, evaluation))
            print(f"   📄 Saved HTML email preview -> {preview_file}")
        else:
            print("   💤 Filtered out (Below threshold or not newsworthy). No email sent.")

        # Save to DB
        tracker.db.save_evaluation(
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
            reasoning=evaluation.reasoning
        )
        print()

    print("=" * 70)
    print("✅ Simulation complete! Stored records in data/tracker.db & data/state.json.")
    print("Check generated HTML email alert templates in the data/ directory.")
    print("=" * 70)

if __name__ == "__main__":
    run_simulation()
