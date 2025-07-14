#!/usr/bin/env python3
"""
SkinBaron CS:GO Marketplace Monitor
Monitors the first 10 products on SkinBaron and sends Telegram notifications on changes.
"""

import logging
import time
import sys
from skinbaron_monitor import SkinBaronMonitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('skinbaron_monitor.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

def main():
    """Main function to run the SkinBaron monitor"""
    # Configuration
    SKINBARON_URL = "https://skinbaron.de/en/csgo?plb=0.04&pub=844&sort=BP"
    TELEGRAM_TOKEN = "7794367450:AAG4-FJbNRGja9xbglkgFtE_hyB1Tohb7C8"
    CHAT_ID = "887116840"
    CHECK_INTERVAL = 1  # seconds
    
    logging.info("Starting SkinBaron CS:GO marketplace monitor...")
    logging.info(f"Monitoring URL: {SKINBARON_URL}")
    logging.info(f"Check interval: {CHECK_INTERVAL} second(s)")
    
    # Initialize monitor
    monitor = SkinBaronMonitor(
        url=SKINBARON_URL,
        telegram_token=TELEGRAM_TOKEN,
        chat_id=CHAT_ID
    )
    
    # Send startup notification
    monitor.send_startup_notification()
    
    # Main monitoring loop
    try:
        while True:
            try:
                monitor.check_for_changes()
                time.sleep(CHECK_INTERVAL)
            except KeyboardInterrupt:
                logging.info("Received interrupt signal, shutting down...")
                monitor.send_shutdown_notification()
                break
            except Exception as e:
                logging.error(f"Error in monitoring loop: {e}")
                time.sleep(5)  # Wait 5 seconds before retrying on error
                
    except Exception as e:
        logging.critical(f"Critical error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
