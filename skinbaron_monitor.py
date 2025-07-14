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
from pushover_notifier import PushoverNotifier
import threading

class SkinBaronMonitor:
    """Main monitor class for SkinBaron marketplace"""
    
    def __init__(self, url: str, telegram_token: str, chat_id: str):
        self.url = url
        self.telegram_notifier = TelegramNotifier(telegram_token, chat_id)
        self.pushover_notifier = PushoverNotifier()
        self.product_tracker = ProductTracker()
        self.session = requests.Session()
        
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
        link = element.select_one('a[href]')
        if link:
            href = link.get('href', '')
            if href.startswith('/'):
                return f"https://skinbaron.de{href}"
            elif href.startswith('http'):
                return href
        
        return "https://skinbaron.de"
    
    def send_message_to_all(self, message: str):
        # ارسال پیام‌ها در ترد جداگانه برای جلوگیری از تاخیر
        threading.Thread(target=self.telegram_notifier.send_message, args=(message,), daemon=True).start()
        threading.Thread(target=self.pushover_notifier.send_message, args=(message,), daemon=True).start()
    
    def send_startup_notification(self):
        message = "🚀 SkinBaron CS:GO Monitor Started!\n\n"
        message += "✅ Monitoring first 10 products\n"
        message += "⏱️ Check interval: 1 second\n"
        message += "🎯 URL: skinbaron.de CS:GO marketplace\n\n"
        message += "Bot is now actively monitoring for changes..."
        
        self.send_message_to_all(message)
    
    def check_for_changes(self):
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
            message = f"Detected {len(changes)} changes:\n"
            for change in changes:
                message += f"- {change['name']} at {change['price']}\n{change['link']}\n\n"
            self.send_message_to_all(message)
        else:
            logging.debug("No changes detected")

def main():
    import os
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
    
    url = "https://skinbaron.de/market/steam/730"
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not telegram_token or not chat_id:
        logging.error("Telegram token or chat ID environment variables not set")
        return
    
    monitor = SkinBaronMonitor(url, telegram_token, chat_id)
    monitor.send_startup_notification()
    
    while True:
        monitor.check_for_changes()
        time.sleep(1)  # 1 second interval

if __name__ == "__main__":
    main()
        
