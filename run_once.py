"""Single-pass runner for cron jobs and GitHub Actions."""
import sys
from src.tracker import TwitterNewsTracker

def main():
    tracker = TwitterNewsTracker()
    alerts = tracker.run_cycle()
    print(f"Execution finished successfully. {alerts} alert(s) sent.")
    sys.exit(0)

if __name__ == "__main__":
    main()
