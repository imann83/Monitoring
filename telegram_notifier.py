"""
Telegram notification module for sending alerts about product changes
"""

import requests
import logging
from typing import List, Dict
from datetime import datetime
import json

class TelegramNotifier:
    """Handles Telegram notifications"""
    
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"
        
    def send_message(self, message: str) -> bool:
        """Send a message to Telegram"""
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True
            }
            
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            
            logging.debug(f"Message sent successfully to Telegram")
            return True
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error sending Telegram message: {e}")
            return False
        except Exception as e:
            logging.error(f"Unexpected error sending Telegram message: {e}")
            return False
    
    def send_change_notification(self, changes: List[Dict]):
        """Send notification about product changes"""
        if not changes:
            return
        
        message = self.format_changes_message(changes)
        self.send_message(message)
    
    def format_changes_message(self, changes: List[Dict]) -> str:
        """Format changes into a readable message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        message = f"🔔 <b>SkinBaron Changes Detected</b>\n"
        message += f"⏰ Time: {timestamp}\n\n"
        
        new_products = [c for c in changes if c['type'] == 'new_product']
        removed_products = [c for c in changes if c['type'] == 'removed_product']
        position_changes = [c for c in changes if c['type'] == 'position_change']
        
        if new_products:
            message += f"🆕 <b>New Products ({len(new_products)}):</b>\n"
            for change in new_products:
                product = change['product']
                message += f"  #{product['position']} {product['name']}\n"
                message += f"  💰 {product['price']}\n"
                if product.get('link'):
                    message += f"  🔗 <a href='{product['link']}'>Buy Now</a>\n\n"
                else:
                    message += "\n"
        
        if removed_products:
            message += f"❌ <b>Removed Products ({len(removed_products)}):</b>\n"
            for change in removed_products:
                product = change['product']
                message += f"  #{product['position']} {product['name']}\n"
                message += f"  💰 {product['price']}\n\n"
        
        if position_changes:
            message += f"🔄 <b>Position Changes ({len(position_changes)}):</b>\n"
            for change in position_changes:
                product = change['product']
                message += f"  {product['name']}\n"
                message += f"  💰 {product['price']}\n"
                message += f"  📍 #{change['previous_position']} → #{change['new_position']}\n\n"
        
        # Add footer
        message += f"📊 Total changes: {len(changes)}\n"
        message += "🎯 Monitoring continues..."
        
        # Telegram message limit is 4096 characters
        if len(message) > 4000:
            message = message[:3900] + "\n\n... (message truncated)"
        
        return message
    
    def send_error_notification(self, error_message: str):
        """Send error notification"""
        message = f"⚠️ <b>SkinBaron Monitor Error</b>\n\n"
        message += f"Error: {error_message}\n"
        message += f"Time: {datetime.now().strftime('%H:%M:%S')}\n\n"
        message += "Monitor will continue attempting to recover..."
        
        self.send_message(message)
