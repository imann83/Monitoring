"""
Product tracking module for detecting changes in product listings
"""

import logging
from typing import List, Dict
from datetime import datetime
from collections import Counter

class ProductTracker:
    """Tracks product changes and maintains state"""
    
    def __init__(self):
        self.previous_products = []
        self.first_run = True
        
    def check_changes(self, current_products: List[Dict]) -> List[Dict]:
        """Check for changes between current and previous product lists"""
        changes = []
        
        if self.first_run:
            logging.info("First run - establishing baseline")
            self.previous_products = current_products.copy()
            self.first_run = False
            return []
        
        # Count signature occurrences
        current_signatures = [p['signature'] for p in current_products if 'signature' in p]
        previous_signatures = [p['signature'] for p in self.previous_products if 'signature' in p]
        
        current_counter = Counter(current_signatures)
        previous_counter = Counter(previous_signatures)
        
        # Detect new products (even if same signature appears more times now)
        for signature, count in current_counter.items():
            prev_count = previous_counter.get(signature, 0)
            if count > prev_count:
                matched = 0
                for product in current_products:
                    if product['signature'] == signature:
                        changes.append({
                            'type': 'new_product',
                            'product': product,
                            'timestamp': datetime.utcnow().isoformat()
                        })
                        matched += 1
                        if matched >= (count - prev_count):
                            break
        
        # Detect removed products
        for signature, count in previous_counter.items():
            curr_count = current_counter.get(signature, 0)
            if curr_count < count:
                matched = 0
                for product in self.previous_products:
                    if product['signature'] == signature:
                        changes.append({
                            'type': 'removed_product',
                            'product': product,
                            'timestamp': datetime.utcnow().isoformat()
                        })
                        matched += 1
                        if matched >= (count - curr_count):
                            break
        
        # Check for position changes
        changes.extend(self.detect_position_changes(current_products))
        
        # Update tracking state
        self.previous_products = current_products.copy()
        
        return changes
    
    def detect_position_changes(self, current_products: List[Dict]) -> List[Dict]:
        """Detect if products have changed positions"""
        position_changes = []
        
        current_positions = {}
        for p in current_products:
            key = (p['signature'], p['position'])
            current_positions.setdefault(p['signature'], []).append(p['position'])
        
        previous_positions = {}
        for p in self.previous_products:
            key = (p['signature'], p['position'])
            previous_positions.setdefault(p['signature'], []).append(p['position'])
        
        # Compare positions
        for signature in current_positions:
            if signature in previous_positions:
                curr_pos_list = current_positions[signature]
                prev_pos_list = previous_positions[signature]
                
                for new_pos in curr_pos_list:
                    if new_pos not in prev_pos_list:
                        product = next((p for p in current_products if p['signature'] == signature and p['position'] == new_pos), None)
                        if product:
                            prev_pos = prev_pos_list[0]  # Take first previous
                            position_changes.append({
                                'type': 'position_change',
                                'product': product,
                                'previous_position': prev_pos,
                                'new_position': new_pos,
                                'timestamp': datetime.utcnow().isoformat()
                            })
        
        return position_changes
        
