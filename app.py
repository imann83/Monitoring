#!/usr/bin/env python3
"""
Flask Web Server for SkinBaron CS:GO Marketplace Monitor
Runs the monitoring as a background thread and provides a web interface for uptime monitoring.
"""

import logging
import threading
import time
import sys
import os
from datetime import datetime
from flask import Flask, jsonify, render_template_string
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

# Configuration
SKINBARON_URL = "https://skinbaron.de/en/csgo?plb=0.03&pub=844&sort=BP"
TELEGRAM_TOKEN = "7794367450:AAG4-FJbNRGja9xbglkgFtE_hyB1Tohb7C8"
CHAT_ID = "887116840"
CHECK_INTERVAL = 1  # seconds

# Get port from environment variable for Render.com compatibility
PORT = int(os.environ.get("PORT", 5000))

# Global variables for monitoring status
monitor_status = {
    "is_running": False,
    "start_time": None,
    "last_check": None,
    "total_checks": 0,
    "last_changes": 0,
    "last_error": None
}

# Flask app initialization
app = Flask(__name__)

def monitoring_thread():
    global monitor_status
    
    logging.info("Starting SkinBaron CS:GO marketplace monitor in background thread...")
    logging.info(f"Monitoring URL: {SKINBARON_URL}")
    logging.info(f"Check interval: {CHECK_INTERVAL} second(s)")
    
    # Initialize monitor
    monitor = SkinBaronMonitor(
        url=SKINBARON_URL,
        telegram_token=TELEGRAM_TOKEN,
        chat_id=CHAT_ID
    )
    
    monitor_status["is_running"] = True
    monitor_status["start_time"] = datetime.now()

    try:
        # Send startup notification
        try:
            monitor.send_startup_notification()
            logging.info("Startup notification sent successfully")
        except Exception as e:
            logging.error(f"Failed to send startup notification: {e}")
            monitor_status["last_error"] = str(e)

        while monitor_status["is_running"]:
            try:
                monitor.check_for_changes()
                monitor_status["last_check"] = datetime.now()
                monitor_status["total_checks"] += 1
                monitor_status["last_error"] = None
                
                time.sleep(CHECK_INTERVAL)
            except Exception as e:
                logging.error(f"Error in monitoring loop: {e}")
                monitor_status["last_error"] = str(e)
                time.sleep(5)

    except Exception as e:
        logging.error(f"Fatal error in monitoring thread: {e}")
        monitor_status["last_error"] = str(e)

    finally:
        # وقتی اینجا رسیدیم یعنی thread داره تموم میشه، وضعیت رو False کن
        monitor_status["is_running"] = False

# HTML template for status page
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>SkinBaron Monitor Status</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 40px; 
            background-color: #f5f5f5; 
        }
        .container { 
            max-width: 600px; 
            margin: 0 auto; 
            background: white; 
            padding: 30px; 
            border-radius: 10px; 
            box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
        }
        .status { 
            padding: 15px; 
            border-radius: 5px; 
            margin: 20px 0; 
            font-weight: bold; 
        }
        .running { 
            background-color: #d4edda; 
            color: #155724; 
            border: 1px solid #c3e6cb; 
        }
        .error { 
            background-color: #f8d7da; 
            color: #721c24; 
            border: 1px solid #f5c6cb; 
        }
        .info { 
            margin: 10px 0; 
            padding: 10px; 
            background-color: #e3f2fd; 
            border-left: 4px solid #2196F3; 
        }
        h1 { 
            color: #333; 
            text-align: center; 
        }
        .refresh-btn { 
            background-color: #007bff; 
            color: white; 
            padding: 10px 20px; 
            border: none; 
            border-radius: 5px; 
            cursor: pointer; 
            margin: 20px 0; 
        }
        .refresh-btn:hover { 
            background-color: #0056b3; 
        }
    </style>
    <script>
        function refreshPage() {
            location.reload();
        }
        // Auto-refresh every 30 seconds
        setInterval(refreshPage, 30000);
    </script>
</head>
<body>
    <div class="container">
        <h1>🎯 SkinBaron CS:GO Monitor</h1>
        
        <div class="status {{ 'running' if status.is_running else 'error' }}">
            {% if status.is_running %}
                ✅ ربات فعال است و در حال مانیتورینگ
            {% else %}
                ❌ ربات غیرفعال است
            {% endif %}
        </div>
        
        <div class="info">
            <strong>📊 آمار مانیتورینگ:</strong><br>
            🕐 زمان شروع: {{ status.start_time.strftime('%Y-%m-%d %H:%M:%S') if status.start_time else 'نامشخص' }}<br>
            ⏰ آخرین بررسی: {{ status.last_check.strftime('%H:%M:%S') if status.last_check else 'هنوز انجام نشده' }}<br>
            🔢 تعداد کل بررسی‌ها: {{ status.total_checks }}<br>
            🎯 URL مانیتور: {{ url }}<br>
            ⏱️ فاصله بررسی: {{ interval }} ثانیه
        </div>
        
        {% if status.last_error %}
        <div class="error">
            ⚠️ آخرین خطا: {{ status.last_error }}
        </div>
        {% endif %}
        
        <button class="refresh-btn" onclick="refreshPage()">🔄 بروزرسانی</button>
        
        <div class="info">
            <strong>💡 نکته:</strong> این صفحه هر ۳۰ ثانیه خودکار بروزرسانی می‌شود.
            <br><strong>🔗 برای uptime monitoring:</strong> از آدرس <code>/api/status</code> استفاده کنید.
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    """Main status page"""
    return render_template_string(HTML_TEMPLATE, 
                                status=monitor_status,
                                url=SKINBARON_URL,
                                interval=CHECK_INTERVAL)

@app.route('/api/status')
def api_status():
    """API endpoint for status - useful for uptime monitoring services"""
    return jsonify({
        "status": "active" if monitor_status["is_running"] else "inactive",
        "is_running": monitor_status["is_running"],
        "start_time": monitor_status["start_time"].isoformat() if monitor_status["start_time"] else None,
        "last_check": monitor_status["last_check"].isoformat() if monitor_status["last_check"] else None,
        "total_checks": monitor_status["total_checks"],
        "last_error": monitor_status["last_error"],
        "uptime_seconds": (datetime.now() - monitor_status["start_time"]).total_seconds() if monitor_status["start_time"] else 0
    })

@app.route('/health')
def health():
    """Simple health check endpoint for uptime services"""
    if monitor_status["is_running"]:
        return "OK", 200
    else:
        return "Service Unavailable", 503

@app.route('/start')
def start_monitoring():
    """Start monitoring (if not already running)"""
    global monitoring_thread_obj
    
    if not monitor_status["is_running"]:
        monitoring_thread_obj = threading.Thread(target=monitoring_thread, daemon=True)
        monitoring_thread_obj.start()
        return jsonify({"message": "Monitoring started"})
    else:
        return jsonify({"message": "Monitoring already running"})

@app.route('/stop')
def stop_monitoring():
    """Stop monitoring"""
    monitor_status["is_running"] = False
    return jsonify({"message": "Monitoring stopped"})

if __name__ == '__main__':
    # Start monitoring thread
    monitoring_thread_obj = threading.Thread(target=monitoring_thread, daemon=True)
    monitoring_thread_obj.start()
    
    # Start Flask web server, binding to the port from environment (Render requirement)
    logging.info(f"Starting Flask web server on port {PORT}...")
    app.run(host='0.0.0.0', port=PORT, debug=False)
