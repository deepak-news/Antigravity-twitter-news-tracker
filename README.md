# 🛰️ 24/7 Free Forever Twitter Newsworthy Tracker

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
