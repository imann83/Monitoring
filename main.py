#!/usr/bin/env python3

import logging
import time
import sys
from skinbaron_monitor import SkinBaronMonitor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('skinbaron_monitor.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

def main():
    SKINBARON_URL = "https://skinbaron.de/en/csgo?plb=0.04&pub=71.5&sort=BP"
    TELEGRAM_TOKEN = "7794367450:AAG4-FJbNRGja9xbglkgFtE_hyB1Tohb7C8"
    CHAT_ID = "887116840"
    CHECK_INTERVAL = 1

    logging.info("Starting SkinBaron monitor...")
    monitor = SkinBaronMonitor(
        url=SKINBARON_URL,
        telegram_token=TELEGRAM_TOKEN,
        chat_id=CHAT_ID
    )

    monitor.send_startup_notification()

    try:
        while True:
            monitor.check_for_changes()
            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        monitor.send_shutdown_notification()
        logging.info("Shutting down monitor...")

if __name__ == "__main__":
    main()