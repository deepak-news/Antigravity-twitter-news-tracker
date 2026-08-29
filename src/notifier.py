"""Email dispatch module using 100% free Gmail SMTP with App Passwords."""
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List
from datetime import datetime, timezone
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
        msg["Date"] = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")

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
"{tweet.text}"

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
