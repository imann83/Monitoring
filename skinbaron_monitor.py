import logging
import time
from typing import List, Dict, Optional
from datetime import datetime
import hashlib

import requests
from bs4 import BeautifulSoup

from product_tracker import ProductTracker
from telegram_notifier import TelegramNotifier

class SkinBaronMonitor:
    """Improved SkinBaron Monitor with better signature detection"""

    def __init__(self, url: str, telegram_token: str, chat_id: str):
        self.url = url
        self.telegram_notifier = TelegramNotifier(telegram_token, chat_id)
        self.product_tracker = ProductTracker()
        self.session = requests.Session()

        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        })

    def fetch_page(self) -> Optional[BeautifulSoup]:
        try:
            response = self.session.get(self.url, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            logging.error(f"Fetch error: {e}")
            return None

    def extract_products(self, soup: BeautifulSoup) -> List[Dict]:
        products = []
        product_elements = soup.select('.item-card, .product-item, .skin-item, .market-item, [data-item-id]')
        if not product_elements:
            logging.warning("No product elements found!")
            return []

        for i, el in enumerate(product_elements[:10]):
            try:
                name = self.extract_name(el)
                price = self.extract_price(el)
                pid = self.extract_id(el)
                link = self.extract_link(el)

                raw_text = el.get_text(strip=True)
                sig = hashlib.md5((name + price + pid + raw_text).encode()).hexdigest()

                products.append({
                    'position': i + 1,
                    'name': name,
                    'price': price,
                    'id': pid,
                    'link': link,
                    'signature': sig
                })
            except Exception as e:
                logging.warning(f"Error parsing product {i}: {e}")
        return products

    def extract_name(self, el) -> str:
        name_el = el.select_one('.item-name, .product-name, .title, h3')
        return name_el.get_text(strip=True) if name_el else 'Unknown'

    def extract_price(self, el) -> str:
        price_el = el.select_one('.price, .item-price')
        if price_el:
            return price_el.get_text(strip=True)
        import re
        match = re.search(r'[\u20AC\$\u00A3]\s*\d+[\.,]\d+', el.get_text())
        return match.group() if match else 'N/A'

    def extract_id(self, el) -> str:
        for attr in ['data-id', 'data-product-id', 'id']:
            if el.has_attr(attr):
                return el[attr]
        return str(hash(el.get_text()) % 100000)

    def extract_link(self, el) -> str:
        a_tag = el.select_one('a[href]')
        if not a_tag:
            return ""
        href = a_tag['href']
        return href if href.startswith('http') else f"https://skinbaron.de{href}"

    def check_for_changes(self):
        logging.debug("Checking for updates...")
        soup = self.fetch_page()
        if not soup:
            return

        products = self.extract_products(soup)
        if not products:
            logging.warning("No products extracted.")
            return

        changes = self.product_tracker.check_changes(products)
        if changes:
            logging.info(f"Detected {len(changes)} changes")
            self.telegram_notifier.send_change_notification(changes)

    def send_startup_notification(self):
        msg = f"\n🚀 SkinBaron Monitor Started\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nURL: {self.url}"
        self.telegram_notifier.send_message(msg)

    def send_shutdown_notification(self):
        msg = "🛑 SkinBaron Monitor Stopped"
        self.telegram_notifier.send_message(msg)
