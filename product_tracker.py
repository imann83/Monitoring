"""
Improved product tracking for SkinBaron monitor
Detects new, removed, and moved products with robust hashing
"""

import logging
from typing import List, Dict
from datetime import datetime

class ProductTracker:
    """Tracks changes in SkinBaron product listings"""

    def __init__(self):
        self.previous_products = []
        self.previous_signatures = set()
        self.first_run = True

    def check_changes(self, current_products: List[Dict]) -> List[Dict]:
        changes = []

        if self.first_run:
            logging.info("First run: baseline established.")
            self.previous_products = current_products.copy()
            self.previous_signatures = {p['signature'] for p in current_products}
            self.first_run = False
            return []

        current_signatures = {p['signature'] for p in current_products}
        new_signatures = current_signatures - self.previous_signatures
        removed_signatures = self.previous_signatures - current_signatures

        # New products
        for p in current_products:
            if p['signature'] in new_signatures:
                changes.append({
                    'type': 'new_product',
                    'product': p,
                    'timestamp': datetime.now().isoformat()
                })

        # Removed products
        for p in self.previous_products:
            if p['signature'] in removed_signatures:
                changes.append({
                    'type': 'removed_product',
                    'product': p,
                    'timestamp': datetime.now().isoformat()
                })

        # Position changes (only for unchanged signatures)
        changes += self.detect_position_changes(current_products)

        # Update state
        self.previous_products = current_products.copy()
        self.previous_signatures = current_signatures
        return changes

    def detect_position_changes(self, current_products: List[Dict]) -> List[Dict]:
        moves = []
        current_pos = {p['signature']: p['position'] for p in current_products}
        previous_pos = {p['signature']: p['position'] for p in self.previous_products}

        for sig in current_pos:
            if sig in previous_pos:
                old, new = previous_pos[sig], current_pos[sig]
                if old != new:
                    product = next(p for p in current_products if p['signature'] == sig)
                    moves.append({
                        'type': 'position_change',
                        'product': product,
                        'previous_position': old,
                        'new_position': new,
                        'timestamp': datetime.now().isoformat()
                    })
        return moves
