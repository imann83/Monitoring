"""
Product tracking module for detecting changes in product listings
"""

import logging
import json
from typing import List, Dict, Set
from datetime import datetime

class ProductTracker:
    """Tracks product changes and maintains state"""
    
    def __init__(self):
        self.previous_products = []
        self.previous_signatures = set()
        self.first_run = True
        
    def check_changes(self, current_products: List[Dict]) -> List[Dict]:
        """Check for changes between current and previous product lists"""
        changes = []
        
        if self.first_run:
            logging.info("First run - establishing baseline")
            self.previous_products = current_products.copy()
            self.previous_signatures = {p['signature'] for p in current_products}
            self.first_run = False
            return []
        
        current_signatures = {p['signature'] for p in current_products}
        
        # Detect new products (products that weren't in previous list)
        new_signatures = current_signatures - self.previous_signatures
        removed_signatures = self.previous_signatures - current_signatures
        
        # Find new products
        for product in current_products:
            if product['signature'] in new_signatures:
                changes.append({
                    'type': 'new_product',
                    'product': product,
                    'timestamp': datetime.now().isoformat()
                })
        
        # Find removed products
        for product in self.previous_products:
            if product['signature'] in removed_signatures:
                changes.append({
                    'type': 'removed_product',
                    'product': product,
                    'timestamp': datetime.now().isoformat()
                })
        
        # Check for position changes
        changes.extend(self.detect_position_changes(current_products))
        
        # Update tracking state
        self.previous_products = current_products.copy()
        self.previous_signatures = current_signatures
        
        return changes
    
    def detect_position_changes(self, current_products: List[Dict]) -> List[Dict]:
        """Detect if products have changed positions"""
        position_changes = []
        
        # Create mapping of signatures to positions for both lists
        current_positions = {p['signature']: p['position'] for p in current_products}
        previous_positions = {p['signature']: p['position'] for p in self.previous_products}
        
        # Find products that changed position
        for signature in current_positions:
            if signature in previous_positions:
                current_pos = current_positions[signature]
                previous_pos = previous_positions[signature]
                
                if current_pos != previous_pos:
                    # Find the product data
                    product = next(p for p in current_products if p['signature'] == signature)
                    position_changes.append({
                        'type': 'position_change',
                        'product': product,
                        'previous_position': previous_pos,
                        'new_position': current_pos,
                        'timestamp': datetime.now().isoformat()
                    })
        
        return position_changes
