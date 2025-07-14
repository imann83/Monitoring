import requests
import logging
import time
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from product_tracker import ProductTracker
from telegram_notifier import TelegramNotifier
from pushover_notifier import PushoverNotifier  # اضافه شده

class SkinBaronMonitor:
    def __init__(self, url: str, telegram_token: str, chat_id: str):
        self.url = url
        self.telegram_notifier = TelegramNotifier(telegram_token, chat_id)
        self.pushover_notifier = PushoverNotifier(  # اضافه شده
            user_key="uuhb4p38no4o13os33uakfe5su3ed4",
            api_token="a5u6n3uhp19izybbhkojqkbfh25ff5"
        )
        self.product_tracker = ProductTracker()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        logging.info("SkinBaron monitor initialized")

    def fetch_page(self) -> Optional[BeautifulSoup]:
        try:
            response = self.session.get(self.url, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching page: {e}")
            return None

    def extract_products(self, soup: BeautifulSoup) -> List[Dict]:
        products = []
        product_selectors = ['.item-card', '.product-item', '.skin-item', '[data-item-id]']
        product_elements = []
        for selector in product_selectors:
            elements = soup.select(selector)
            if elements and len(elements) >= 10:
                product_elements = elements[:10]
                break
        for i, element in enumerate(product_elements):
            try:
                product_data = self.parse_product_element(element, i)
                if product_data:
                    products.append(product_data)
            except Exception as e:
                continue
        return products

    def parse_product_element(self, element, index: int) -> Optional[Dict]:
        try:
            text_content = element.get_text(strip=True)
            price = self.extract_price(element)
            name = self.extract_product_name(element)
            product_id = self.extract_product_id(element)
            product_link = self.extract_product_link(element)
            signature = f"{name}_{price}_{product_id}"
            return {
                'position': index + 1,
                'name': name,
                'price': price,
                'id': product_id,
                'link': product_link,
                'signature': signature,
                'raw_text': text_content[:200]
            }
        except Exception:
            return None

    def extract_price(self, element) -> str:
        selectors = ['.price', '.item-price', '.product-price']
        for selector in selectors:
            price_elem = element.select_one(selector)
            if price_elem:
                return price_elem.get_text(strip=True)
        return "N/A"

    def extract_product_name(self, element) -> str:
        selectors = ['.item-name', '.product-name', '[class*="name"]']
        for selector in selectors:
            name_elem = element.select_one(selector)
            if name_elem:
                return name_elem.get_text(strip=True)
        return "Unknown"

    def extract_product_id(self, element) -> str:
        for attr in ['data-item-id', 'data-product-id']:
            if element.get(attr):
                return str(element.get(attr))
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

    def check_for_changes(self):
        soup = self.fetch_page()
        if not soup:
            return
        current_products = self.extract_products(soup)
        if not current_products:
            return
        changes = self.product_tracker.check_changes(current_products)
        if changes:
            self.telegram_notifier.send_change_notification(changes)
            self.pushover_notifier.send_change_notification(changes)

    def send_startup_notification(self):
        message = "🚀 SkinBaron Monitor Started! Monitoring 10 items."
        self.telegram_notifier.send_message(message)
        self.pushover_notifier.send_message("SkinBaron monitor started.")

    def send_shutdown_notification(self):
        message = "🛑 SkinBaron Monitor Stopped"
        self.telegram_notifier.send_message(message)
        self.pushover_notifier.send_message("SkinBaron monitor stopped.")