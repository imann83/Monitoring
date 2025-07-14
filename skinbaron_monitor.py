"""
SkinBaron marketplace monitor module
Handles scraping and change detection for SkinBaron CS:GO marketplace
"""

import requests
import logging
import time
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from product_tracker import ProductTracker
from telegram_notifier import TelegramNotifier

# اضافه کردن ماژول pushover
import http.client
import json

class PushoverNotifier:
    """Simple Pushover notifier"""
    def __init__(self, user_key: str, app_token: str):
        self.user_key = user_key
        self.app_token = app_token

    def send_message(self, message: str):
        conn = http.client.HTTPSConnection("api.pushover.net:443")
        payload = f"user={self.user_key}&token={self.app_token}&message={message}"
        headers = { 'Content-Type': 'application/x-www-form-urlencoded' }
        conn.request("POST", "/1/messages.json", payload, headers)
        response = conn.getresponse()
        if response.status != 200:
            logging.error(f"Pushover send failed: {response.status} {response.reason}")
        conn.close()

class SkinBaronMonitor:
    """Main monitor class for SkinBaron marketplace"""
    
    def __init__(self, url: str, telegram_token: str, chat_id: str, pushover_user: str = None, pushover_token: str = None):
        self.url = url
        self.telegram_notifier = TelegramNotifier(telegram_token, chat_id)
        self.product_tracker = ProductTracker()
        self.session = requests.Session()
        
        # Pushover notifier if credentials provided
        self.pushover_notifier = None
        if pushover_user and pushover_token:
            self.pushover_notifier = PushoverNotifier(pushover_user, pushover_token)
        
        # Set headers to mimic a real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        logging.info("SkinBaron monitor initialized")
    
    def fetch_page(self) -> Optional[BeautifulSoup]:
        """Fetch the SkinBaron page and return parsed HTML"""
        try:
            response = self.session.get(self.url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            logging.debug(f"Successfully fetched page, status code: {response.status_code}")
            return soup
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching page: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error while fetching page: {e}")
            return None
    
    def extract_products(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract the first 10 products from the page"""
        products = []
        
        try:
            # ... (همون کد قبلی extract_products بدون تغییر)
            
            product_selectors = [
                '.item-card',
                '.product-item',
                '.skin-item',
                '.market-item',
                '[data-item-id]',
                '.item-list .item',
                '.product-list .product',
                '.skin-list .skin'
            ]
            
            product_elements = []
            
            for selector in product_selectors:
                elements = soup.select(selector)
                if elements and len(elements) >= 10:
                    product_elements = elements[:10]
                    logging.debug(f"Found products using selector: {selector}")
                    break
            
            if not product_elements:
                price_elements = soup.find_all(['div', 'span'], string=lambda text: text and ('€' in text or '$' in text or '£' in text))
                if price_elements:
                    potential_products = []
                    for price_elem in price_elements:
                        for parent in price_elem.parents:
                            if parent.name in ['div', 'article', 'li'] and parent not in potential_products:
                                if len(parent.get_text().strip()) > 20:
                                    potential_products.append(parent)
                                    break
                    product_elements = potential_products[:10]
                    logging.debug(f"Found {len(product_elements)} products using price-based detection")
            
            for i, element in enumerate(product_elements):
                if i >= 10:
                    break
                try:
                    product_data = self.parse_product_element(element, i)
                    if product_data:
                        products.append(product_data)
                except Exception as e:
                    logging.warning(f"Error parsing product {i}: {e}")
                    continue
            
            logging.info(f"Successfully extracted {len(products)} products")
            return products
            
        except Exception as e:
            logging.error(f"Error extracting products: {e}")
            return []
    
    def parse_product_element(self, element, index: int) -> Optional[Dict]:
        """Parse individual product element to extract key information"""
        # ... (همون کد بدون تغییر)
        try:
            text_content = element.get_text(strip=True)
            price = self.extract_price(element)
            name = self.extract_product_name(element)
            product_id = self.extract_product_id(element)
            product_link = self.extract_product_link(element)
            signature = f"{name}_{price}_{product_id}_{index}"
            product_data = {
                'position': index + 1,
                'name': name,
                'price': price,
                'id': product_id,
                'link': product_link,
                'signature': signature,
                'raw_text': text_content[:200]
            }
            return product_data
        except Exception as e:
            logging.warning(f"Error parsing product element: {e}")
            return None
    
    def extract_price(self, element) -> str:
        # ... (بدون تغییر)
        price_selectors = [
            '.price',
            '.item-price',
            '.product-price',
            '[class*="price"]',
            '[data-price]'
        ]
        for selector in price_selectors:
            price_elem = element.select_one(selector)
            if price_elem:
                return price_elem.get_text(strip=True)
        text = element.get_text()
        import re
        price_patterns = [
            r'€\s*\d+[.,]?\d*',
            r'\d+[.,]?\d*\s*€',
            r'\$\s*\d+[.,]?\d*',
            r'\d+[.,]?\d*\s*\$',
            r'£\s*\d+[.,]?\d*'
        ]
        for pattern in price_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group().strip()
        return "N/A"
    
    def extract_product_name(self, element) -> str:
        # ... (بدون تغییر)
        name_selectors = [
            '.item-name',
            '.product-name',
            '.skin-name',
            '.title',
            'h1', 'h2', 'h3', 'h4',
            '[class*="name"]',
            '[class*="title"]'
        ]
        for selector in name_selectors:
            name_elem = element.select_one(selector)
            if name_elem:
                name = name_elem.get_text(strip=True)
                if len(name) > 5:
                    return name
        texts = [t.strip() for t in element.stripped_strings]
        for text in texts:
            if len(text) > 10 and not any(char in text for char in '€$£'):
                return text[:50]
        return f"Product {element.get('data-id', 'Unknown')}"
    
    def extract_product_id(self, element) -> str:
        # ... (بدون تغییر)
        id_attrs = ['data-item-id', 'data-product-id', 'data-id', 'id']
        for attr in id_attrs:
            if element.get(attr):
                return str(element.get(attr))
        link = element.select_one('a[href]')
        if link:
            href = link.get('href', '')
            import re
            id_match = re.search(r'/(\d+)', href)
            if id_match:
                return id_match.group(1)
        return str(hash(element.get_text()[:100]) % 10000)
    
    def extract_product_link(self, element) -> str:
        # ... (بدون تغییر)
        link = element.select_one('a[href]')
        if link:
            href = link.get('href', '')
            if href.startswith('/'):
                return f"https://skinbaron.de{href}"
            elif href.startswith('http'):
                return href
        return "https://skinbaron.de"
    
    def check_for_changes(self):
        """Main method to check for product changes"""
        logging.debug("Checking for changes...")
        
        soup = self.fetch_page()
        if not soup:
            logging.warning("Failed to fetch page, skipping this check")
            return
        
        current_products = self.extract_products(soup)
        if not current_products:
            logging.warning("No products extracted, skipping this check")
            return
        
        changes = self.product_tracker.check_changes(current_products)
        
        if changes:
            logging.info(f"Detected {len(changes)} changes")
            # پیام تغییرات خیلی کوتاه شد
            summary = "\n".join([f"{c['position']}. {c['name']} - {c['price']}" for c in changes])
            message = f"🔔 SkinBaron changes detected:\n{summary}"
            self.telegram_notifier.send_message(message)
            if self.pushover_notifier:
                self.pushover_notifier.send_message(message)
        else:
            logging.debug("No changes detected")
    
    def send_startup_notification(self):
        """Send notification when monitor starts"""
        message = "🚀 SkinBaron CS:GO Monitor Started!\n\n"
        message += "✅ Monitoring first 10 products\n"
        message += "⏱️ Check interval: 2 seconds\n"
        message += "🎯 URL: skinbaron.de CS:GO marketplace\n\n"
        message += "Bot is now actively monitoring for changes..."
        
        self.telegram_notifier.send_message(message)
        if self.pushover_notifier:
            self.pushover_notifier.send_message("SkinBaron Monitor started and running.")
        
def main():
    import os
    import logging
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )
    
    url = "https://skinbaron.de/market/steam/730"  # SkinBaron CS:GO marketplace URL
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    pushover_user = os.getenv("PUSHOVER_USER_KEY")
    pushover_token = os.getenv("PUSHOVER_APP_TOKEN")
    
    if not telegram_token or not chat_id:
        logging.error("Telegram token or chat ID environment variables not set")
        return
    
    monitor = SkinBaronMonitor(url, telegram_token, chat_id, pushover_user, pushover_token)
    monitor.send_startup_notification()
    
    while True:
        monitor.check_for_changes()
        time.sleep(2)  # زمان ۲ ثانیه
    
if __name__ == "__main__":
    main()
            
