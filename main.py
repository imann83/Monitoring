#!/usr/bin/env python3
"""
SkinBaron CS:GO Marketplace Monitor
Monitors the first 10 products on SkinBaron and sends Telegram notifications on changes.
"""

import logging
import time
import sys
import threading
from flask import Flask
from skinbaron_monitor import SkinBaronMonitor

# Flask app برای روشن نگه داشتن سرور در Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running ✅"

def run_flask():
    app.run(host='0.0.0.0', port=10000)

# توکن و آیدی برای تلگرام
SKINBARON_URL = "https://skinbaron.de/en/csgo?plb=0.03&pub=844&sort=BP"
TELEGRAM_TOKEN = "7794367450:AAG4-FJbNRGja9xbglkgFtE_hyB1Tohb7C8"
CHAT_ID = "887116840"
CHECK_INTERVAL = 1  # seconds

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('skinbaron_monitor.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

def monitor_loop():
    """حلقه‌ی اصلی مانیتورینگ سایت"""
    monitor = SkinBaronMonitor(
        url=SKINBARON_URL,
        telegram_token=TELEGRAM_TOKEN,
        chat_id=CHAT_ID
    )
    
    logging.info("Starting SkinBaron CS:GO marketplace monitor...")
    logging.info(f"Monitoring URL: {SKINBARON_URL}")
    logging.info(f"Check interval: {CHECK_INTERVAL} second(s)")
    
    monitor.send_startup_notification()

    last_alive_message = time.time()

    try:
        while True:
            monitor.check_for_changes()
            time.sleep(CHECK_INTERVAL)

            # هر یک ساعت یک‌بار پیام بده که زنده است
            if time.time() - last_alive_message > 3600:
                monitor.send_alive_notification("✅ ربات مانیتور هنوز فعال است.")
                last_alive_message = time.time()

    except KeyboardInterrupt:
        logging.info("Received interrupt signal, shutting down...")
        monitor.send_shutdown_notification()
    except Exception as e:
        logging.error(f"Error in monitoring loop: {e}")
        time.sleep(5)

if __name__ == "__main__":
    # اجرای Flask در Thread جداگانه
    threading.Thread(target=run_flask).start()
    # اجرای مانیتورینگ در Thread اصلی
    monitor_loop()
    
