import requests
import logging
import time
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from product_tracker import ProductTracker
from telegram_notifier import TelegramNotifier
from pushover_notifier import PushoverNotifier

class SkinBaronMonitor:
    def __init__(self, url: str, telegram_token: str, chat_id: str):
        self.url = url
        self.telegram_notifier = TelegramNotifier(telegram_token, chat_id)
        self.pushover_notifier = PushoverNotifier(
            user_key="uuhb4p38no4o13os33uakfe5su3ed4",
            api_token="a5u6n3uhp19izybbhkojqkbfh25ff5"
        )
        self.product_tracker = ProductTracker()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
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
        except Exception as e:
            logging.error(f"Error fetching page: {e}")
            return None

    def extract_products(self, soup: BeautifulSoup) -> List[Dict]:
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
                    break

            if not product_elements:
                price_elements = soup.find_all(['div', 'span'], string=lambda t: t and ('€' in t or '$' in t or '£' in t))
                potential_products = []
                for elem in price_elements:
                    for parent in elem.parents:
                        if parent.name in ['div', 'article', 'li'] and parent not in potential_products:
                            if len(parent.get_text().strip()) > 20:
                                potential_products.append(parent)
                                break
                product_elements = potential_products[:10]

            for i, element in enumerate(product_elements):
                if i >= 10:
                    break
                try:
                    product_data = self.parse_product_element(element, i)
                    if product_data:
                        products.append(product_data)
                except Exception as e:
                    logging.warning(f"Error parsing product {i}: {e}")
            logging.info(f"Extracted {len(products)} products")
            return products
        except Exception as e:
            logging.error(f"Error extracting products: {e}")
            return []

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
        text = element.get_text()
        import re
        for pattern in [r'€\s*\d+[.,]\d+', r'\d+[.,]\d+\s*€', r'\$\s*\d+[.,]\d+', r'\d+[.,]\d+\s*\$', r'£\s*\d+[.,]\d+']:
            match = re.search(pattern, text)
            if match:
                return match.group().strip()
        return "N/A"

    def extract_product_name(self, element) -> str:
        selectors = ['.item-name', '.product-name', '.skin-name', '.title', 'h1', 'h2', 'h3', 'h4', '[class*="name"]', '[class*="title"]']
        for selector in selectors:
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
        for attr in ['data-item-id', 'data-product-id', 'data-id', 'id']:
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

    def check_for_changes(self):
        soup = self.fetch_page()
        if not soup:
            logging.warning("No soup returned")
            return
        current_products = self.extract_products(soup)
        if not current_products:
            logging.warning("No products extracted.")
            return
        changes = self.product_tracker.check_changes(current_products)
        if changes:
            self.telegram_notifier.send_change_notification(changes)
            self.pushover_notifier.send_change_notification(changes)

    def send_startup_notification(self):
        self.telegram_notifier.send_message("🚀 SkinBaron Monitor Started")
        self.pushover_notifier.send_message("SkinBaron Monitor Started")

    def send_shutdown_notification(self):
        self.telegram_notifier.send_message("🛑 SkinBaron Monitor Stopped")
        self.pushover_notifier.send_message("SkinBaron Monitor Stopped")