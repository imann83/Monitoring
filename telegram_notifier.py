import requests
import logging
from typing import List, Dict
from datetime import datetime

class TelegramNotifier:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"

    def send_message(self, message: str) -> bool:
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True
            }
            response = requests.post(url, data=data, timeout=5)
            response.raise_for_status()
            return True
        except Exception as e:
            logging.error(f"Telegram send error: {e}")
            return False

    def send_change_notification(self, changes: List[Dict]):
        if not changes:
            return
        message = self.format_changes_message(changes)
        self.send_message(message)

    def format_changes_message(self, changes: List[Dict]) -> str:
        t = datetime.now().strftime("%H:%M:%S")
        new = len([c for c in changes if c['type'] == 'new_product'])
        removed = len([c for c in changes if c['type'] == 'removed_product'])
        moved = len([c for c in changes if c['type'] == 'position_change'])
        return f"🔔 {t}: {new}🆕 / {removed}❌ / {moved}🔄"