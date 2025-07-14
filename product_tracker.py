import logging
from typing import List, Dict
from datetime import datetime
import hashlib

class ProductTracker:
    def __init__(self):
        self.previous_products = {}
        self.first_run = True

    def generate_signature(self, product: Dict) -> str:
        raw = f"{product.get('name')}|{product.get('price')}|{product.get('id')}|{product.get('link')}"
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()

    def check_changes(self, current_products: List[Dict]) -> List[Dict]:
        changes = []
        current_signatures = {}

        for p in current_products:
            sig = self.generate_signature(p)
            current_signatures[sig] = p

        if self.first_run:
            logging.info("First run - saving baseline.")
            self.previous_products = {self.generate_signature(p): p for p in current_products}
            self.first_run = False
            return []

        # Detect new and removed products
        prev_sigs = set(self.previous_products.keys())
        curr_sigs = set(current_signatures.keys())

        new_sigs = curr_sigs - prev_sigs
        removed_sigs = prev_sigs - curr_sigs

        for sig in new_sigs:
            product = current_signatures[sig]
            changes.append({
                'type': 'new_product',
                'product': product,
                'timestamp': datetime.now().isoformat()
            })

        for sig in removed_sigs:
            product = self.previous_products[sig]
            changes.append({
                'type': 'removed_product',
                'product': product,
                'timestamp': datetime.now().isoformat()
            })

        # Check for field-level changes on products with same ID
        current_by_id = {p['id']: p for p in current_products}
        previous_by_id = {p['id']: p for p in self.previous_products.values()}

        for pid in current_by_id:
            if pid in previous_by_id:
                prev = previous_by_id[pid]
                curr = current_by_id[pid]

                if prev['price'] != curr['price']:
                    changes.append({
                        'type': 'price_change',
                        'product': curr,
                        'old_price': prev['price'],
                        'new_price': curr['price'],
                        'timestamp': datetime.now().isoformat()
                    })
                if prev['name'] != curr['name']:
                    changes.append({
                        'type': 'name_change',
                        'product': curr,
                        'old_name': prev['name'],
                        'new_name': curr['name'],
                        'timestamp': datetime.now().isoformat()
                    })
                if prev['position'] != curr['position']:
                    changes.append({
                        'type': 'position_change',
                        'product': curr,
                        'previous_position': prev['position'],
                        'new_position': curr['position'],
                        'timestamp': datetime.now().isoformat()
                    })

        # Save current state
        self.previous_products = {self.generate_signature(p): p for p in current_products}
        return changes