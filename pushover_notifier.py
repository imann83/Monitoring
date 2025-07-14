import requests
import logging

class PushoverNotifier:
    def __init__(self):
        self.user_key = "uuhb4p38no4o13os33uakfe5su3ed4"
        self.app_token = "a5u6n3uhp19izybbhkojqkbfh25ff5"

    def send_message(self, message: str, title: str = "🔔 Notification"):
        try:
            response = requests.post(
                "https://api.pushover.net/1/messages.json",
                data={
                    "token": self.app_token,
                    "user": self.user_key,
                    "message": message,
                    "title": title,
                    "priority": 1
                },
                timeout=3
            )
            if response.status_code != 200:
                logging.warning(f"Pushover failed: {response.status_code} - {response.text}")
            else:
                logging.info("✅ Pushover notification sent")
        except Exception as e:
            logging.error(f"🚨 Pushover error: {e}")
          
