"""
SkinBaron marketplace monitor module
Handles scraping and change detection for SkinBaron CS:GO marketplace
"""

import requests
import logging
import re
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from product_tracker import ProductTracker
from telegram_notifier import TelegramNotifier


class SkinBaronMonitor:
    """Main monitor class for SkinBaron marketplace"""

    def __init__(self, url: str, telegram_token: str, chat_id: str):
        self.url = url
        self.telegram_notifier = TelegramNotifier(telegram_token, chat_id)
        self.product_tracker = ProductTracker()
        self.session = requests.Session()

        # Set headers to mimic a real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })

        logging.info("✅ SkinBaron monitor initialized")

    def fetch_page(self) -> Optional[BeautifulSoup]:
        """Fetch the SkinBaron page and return parsed HTML"""
        try:
            response = self.session.get(self.url, timeout=10)
            response.raise_for_status()
            logging.debug(f"✅ Page fetched successfully (status: {response.status_code})")
            return BeautifulSoup(response.content, 'html.parser')
        except requests.exceptions.RequestException as e:
            logging.error(f"❌ RequestException while fetching page: {e}")
        except Exception as e:
            logging.error(f"❌ Unexpected error while fetching page: {e}")
        return None

    def extract_products(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract the first 10 products from the page"""
        products = []
        product_elements = []

        selectors = [
            '.item-card', '.product-item', '.skin-item', '.market-item',
            '[data-item-id]', '.item-list .item', '.product-list .product', '.skin-list .skin'
        ]

        # Try known selectors
        for selector in selectors:
            elements = soup.select(selector)
            if len(elements) >= 10:
                product_elements = elements[:10]
                logging.debug(f"✅ Found products using selector: {selector}")
                break

        # Fallback: price-based heuristic
        if not product_elements:
            price_elements = soup.find_all(['div', 'span'], string=lambda t: t and any(c in t for c in '€$£'))
            candidates = set()

            for elem in price_elements:
                for parent in elem.parents:
                    if parent.name in ['div', 'article', 'li'] and len(parent.get_text(strip=True)) > 20:
                        candidates.add(parent)
                        break

            product_elements = list(candidates)[:10]
            logging.debug(f"ℹ️ Fallback - found {len(product_elements)} products using price-based detection")

        # Parse each element
        for i, element in enumerate(product_elements):
            try:
                product_data = self.parse_product_element(element, i)
                if product_data:
                    products.append(product_data)
            except Exception as e:
                logging.warning(f"⚠️ Error parsing product {i}: {e}")

        logging.info(f"✅ Extracted {len(products)} products")
        return products

    def parse_product_element(self, element, index: int) -> Optional[Dict]:
        """Extract data from product card"""
        try:
            text_content = element.get_text(strip=True)
            name = self.extract_product_name(element)
            price = self.extract_price(element)
            product_id = self.extract_product_id(element)
            link = self.extract_product_link(element)

            signature = f"{name}_{price}_{product_id}"

            return {
                'position': index + 1,
                'name': name,
                'price': price,
                'id': product_id,
                'link': link,
                'signature': signature,
                'raw_text': text_content[:200]
            }

        except Exception as e:
            logging.warning(f"⚠️ Failed to parse product element: {e}")
            return None

    def extract_price(self, element) -> str:
        """Extract price using known classes or regex"""
        price_selectors = ['.price', '.item-price', '.product-price', '[class*="price"]', '[data-price]']

        for selector in price_selectors:
            price_elem = element.select_one(selector)
            if price_elem:
                return price_elem.get_text(strip=True)

        text = element.get_text()
        patterns = [r'€\s*\d+[.,]\d+', r'\d+[.,]\d+\s*€', r'\$\s*\d+[.,]\d+', r'\d+[.,]\d+\s*\$', r'£\s*\d+[.,]\d+']

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group().strip()

        return "N/A"

    def extract_product_name(self, element) -> str:
        """Extract product name from element"""
        name_selectors = [
            '.item-name', '.product-name', '.skin-name', '.title',
            'h1', 'h2', 'h3', '[class*="name"]', '[class*="title"]'
        ]

        for selector in name_selectors:
            name_elem = element.select_one(selector)
            if name_elem:
                name = name_elem.get_text(strip=True)
                if len(name) > 5:
                    return name

        for text in element.stripped_strings:
            if len(text) > 10 and not any(c in text for c in '€$£'):
                return text[:50]

        return f"Product {element.get('data-id', 'Unknown')}"

    def extract_product_id(self, element) -> str:
        """Try to extract product ID from attributes or URLs"""
        for attr in ['data-item-id', 'data-product-id', 'data-id', 'id']:
            val = element.get(attr)
            if val:
                return str(val)

        a_tag = element.select_one('a[href]')
        if a_tag:
            href = a_tag.get('href', '')
            match = re.search(r'/(\d+)', href)
            if match:
                return match.group(1)

        return str(hash(element.get_text(strip=True)[:100]) % 10000)

    def extract_product_link(self, element) -> str:
        """Extract link to product"""
        link = element.select_one('a[href]')
        if link:
            href = link.get('href', '')
            if href.startswith('/'):
                return f"https://skinbaron.de{href}"
            elif href.startswith('http'):
                return href
        return "https://skinbaron.de"

    def check_for_changes(self):
        """Fetch and compare current products to detect changes"""
        logging.debug("🔍 Checking for changes...")

        soup = self.fetch_page()
        if not soup:
            logging.warning("⚠️ No soup - skipping check")
            return

        products = self.extract_products(soup)
        if not products:
            logging.warning("⚠️ No products extracted")
            return

        changes = self.product_tracker.check_changes(products)
        if changes:
            logging.info(f"🔄 Detected {len(changes)} changes")
            self.telegram_notifier.send_change_notification(changes)
        else:
            logging.debug("✅ No changes detected")

    def send_startup_notification(self):
        """Notify when bot starts"""
        message = (
            "🚀 SkinBaron Monitor Started!\n"
            "👁️ Watching first 10 products\n"
            f"🌐 URL: {self.url}\n"
            "⏱️ Interval: 1s\n"
            "-----------------------"
        )
        self.telegram_notifier.send_message(message)

    def send_shutdown_notification(self):
        """Notify when bot stops"""
        self.telegram_notifier.send_message("🛑 SkinBaron Monitor Stopped.")
                
