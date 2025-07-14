import requests
import logging

class PushoverNotifier:
    def __init__(self, user_key: str, api_token: str):
        self.user_key = user_key
        self.api_token = api_token

    def send_message(self, message: str, title: str = "SkinBaron Alert"):
        try:
            response = requests.post(
                "https://api.pushover.net/1/messages.json",
                data={
                    "token": self.api_token,
                    "user": self.user_key,
                    "title": title,
                    "message": message
                },
                timeout=5
            )
            response.raise_for_status()
        except Exception as e:
            logging.error(f"Pushover error: {e}")

    def send_change_notification(self, changes):
        count = len(changes)
        summary = f"{count} change(s) on SkinBaron."
        self.send_message(summary)