"""24/7 continuous background runner for Always-Free Cloud VMs / servers."""
import time
import random
import signal
import sys
import logging
from src.tracker import TwitterNewsTracker
from src.config import load_config

logger = logging.getLogger("TwitterNewsDaemon")

running = True

def handle_exit(signum, frame):
    global running
    logger.info("Received termination signal. Shutting down daemon gracefully...")
    running = False

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

def main():
    config = load_config()
    tracker = TwitterNewsTracker(config)
    
    poll_interval = config.daemon.poll_interval_seconds
    jitter = config.daemon.jitter_seconds

    logger.info(f"Starting 24/7 Twitter News Tracker Daemon (Interval: {poll_interval}s +/- {jitter}s)")
    
    while running:
        try:
            tracker.run_cycle()
        except Exception as e:
            logger.error(f"Unexpected error during cycle: {e}", exc_info=True)

        if not running:
            break

        # Calculate sleep time with randomized jitter
        sleep_duration = max(10, poll_interval + random.randint(-jitter, jitter))
        logger.info(f"Sleeping for {sleep_duration} seconds until next cycle...")
        
        # Sleep in small increments to respond promptly to termination signals
        for _ in range(sleep_duration):
            if not running:
                break
            time.sleep(1)

    logger.info("Twitter News Tracker Daemon has stopped.")
    sys.exit(0)

if __name__ == "__main__":
    main()
