#!/usr/bin/env python3

import logging
import threading
import time
import sys
from datetime import datetime
from flask import Flask, jsonify, render_template_string
from skinbaron_monitor import SkinBaronMonitor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('skinbaron_monitor.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

SKINBARON_URL = "https://skinbaron.de/en/csgo?plb=0.04&pub=71.5&sort=BP"
TELEGRAM_TOKEN = "7794367450:AAG4-FJbNRGja9xbglkgFtE_hyB1Tohb7C8"
CHAT_ID = "887116840"
CHECK_INTERVAL = 1

monitor_status = {
    "is_running": False,
    "start_time": None,
    "last_check": None,
    "total_checks": 0,
    "last_changes": 0,
    "last_error": None
}

app = Flask(__name__)

def monitoring_thread():
    global monitor_status
    logging.info("Starting SkinBaron monitor...")
    monitor = SkinBaronMonitor(
        url=SKINBARON_URL,
        telegram_token=TELEGRAM_TOKEN,
        chat_id=CHAT_ID
    )
    monitor_status["is_running"] = True
    monitor_status["start_time"] = datetime.now()
    try:
        monitor.send_startup_notification()
    except Exception as e:
        monitor_status["last_error"] = str(e)
    while monitor_status["is_running"]:
        try:
            monitor.check_for_changes()
            monitor_status["last_check"] = datetime.now()
            monitor_status["total_checks"] += 1
            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            monitor_status["last_error"] = str(e)
            time.sleep(5)

HTML_TEMPLATE = """<!DOCTYPE html><html><head><title>Monitor</title></head>
<body><h1>SkinBaron Monitor</h1><p>Status: {{ 'Running' if status.is_running else 'Stopped' }}</p></body></html>"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, status=monitor_status)

@app.route('/api/status')
def api_status():
    return jsonify({
        "status": "active" if monitor_status["is_running"] else "inactive",
        "is_running": monitor_status["is_running"],
        "start_time": monitor_status["start_time"].isoformat() if monitor_status["start_time"] else None,
        "last_check": monitor_status["last_check"].isoformat() if monitor_status["last_check"] else None,
        "total_checks": monitor_status["total_checks"],
        "last_error": monitor_status["last_error"]
    })

@app.route('/start')
def start_monitoring():
    global monitoring_thread_obj
    if not monitor_status["is_running"]:
        monitoring_thread_obj = threading.Thread(target=monitoring_thread, daemon=True)
        monitoring_thread_obj.start()
        return jsonify({"message": "Monitoring started"})
    return jsonify({"message": "Already running"})

@app.route('/stop')
def stop_monitoring():
    monitor_status["is_running"] = False
    return jsonify({"message": "Monitoring stopped"})

if __name__ == '__main__':
    monitoring_thread_obj = threading.Thread(target=monitoring_thread, daemon=True)
    monitoring_thread_obj.start()
    app.run(host='0.0.0.0', port=5000, debug=False)