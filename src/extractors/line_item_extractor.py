"""
Line Item Extractor.

Specialized extractor for parsing line items from OCR text and structured data.
"""

import re
from typing import Dict, List, Optional, Any
from .base import BaseExtractor
from ..core.logging_config import get_logger

logger = get_logger(__name__)


class LineItemExtractor(BaseExtractor):
    """
    Extracts line items from invoices.
    
    Handles both OCR text parsing and structured data extraction.
    """
    
    def extract_all_fields(
        self,
        ocr_text: Optional[str] = None,
        response: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extract line items (interface compatibility).
        
        Args:
            ocr_text: Optional OCR text
            response: Optional API response
            
        Returns:
            Dictionary with line_items key
        """
        if response:
            line_items = self.extract_from_structured(response)
        elif ocr_text:
            line_items = self.extract_from_ocr(ocr_text)
        else:
            line_items = []
        
        return {'line_items': line_items}
    
    def extract_from_ocr(self, ocr_text: str) -> List[Dict[str, Any]]:
        """
        Extract line items from OCR text using improved table-aware parsing.
        
        Args:
            ocr_text: Raw OCR text from the invoice
            
        Returns:
            List of dictionaries, each containing line item data
        """
        line_items = []
        lines = ocr_text.split('\n')
        
        # Find the line items section
        item_section_start = -1
        header_line_idx = -1
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in ['item', 'description', 'qty', 'quantity', 'price', 'amount']):
                if any(col in line_lower for col in ['sku', 'item', 'description', 'qty', 'quantity', 'price', 'total']):
                    item_section_start = i + 1
                    header_line_idx = i
                    break
        
        if item_section_start == -1:
            item_section_start = 0
        
        # Improved parsing: Use pattern-based detection to separate items properly
        return self._parse_improved_items(lines, item_section_start)
    
    def _parse_improved_items(self, lines: List[str], start_idx: int) -> List[Dict[str, Any]]:
        """
        Improved line item parser that properly separates individual items.
        
        Strategy: Look for patterns that indicate new line items:
        1. Lines starting with item keywords (Transport, Installation, Carrier Taxes, etc.)
        2. Lines with multiple price values (table row format)
        3. Lines that contain complete item data (description + prices)
        """
        line_items = []
        current_item = {}
        
        # Item start keywords - when we see these at start of line, it's a new item
        item_start_keywords = [
            'transport', 'installation', 'carrier taxes', 'carrier tax',
            'item discount', 'discount', 'credit', 'refund', 'deduction'
        ]
        
        for i in range(start_idx, len(lines)):
            line = lines[i].strip()
            if not line:
                # Empty line - save current item if complete
                if current_item and self._is_item_complete(current_item):
                    line_items.append(current_item)
                    current_item = {}
                continue
            
            # Stop at totals section
            line_lower = line.lower()
            totals_indicators = ['subtotal', 'tax', 'total', 'grand total', 'invoice total', 'amount due']
            if any(indicator in line_lower and any(kw in line_lower for kw in [':', '=', '$']) 
                   for indicator in totals_indicators):
                if current_item and self._is_item_complete(current_item):
                    line_items.append(current_item)
                break
            
            # Detect if this is a new line item
            is_new_item = self._is_new_item(line, current_item, item_start_keywords)
            
            if is_new_item and current_item and self._is_item_complete(current_item):
                # Save previous item and start new one
                line_items.append(current_item)
                current_item = {}
            
            # Extract fields from this line
            self._extract_item_fields_from_line(line, current_item)
        
        # Save last item
        if current_item and self._is_item_complete(current_item):
            line_items.append(current_item)
        
        # Clean and validate items
        return self._clean_and_validate_items(line_items)
    
    def _is_new_item(self, line: str, current_item: Dict[str, Any], item_keywords: List[str]) -> bool:
        """Check if line indicates a new line item."""
        line_lower = line.lower()
        
        # If no current item, this is definitely new
        if not current_item.get('description'):
            return True
        
        # Check if line starts with item keyword
        for keyword in item_keywords:
            if line_lower.startswith(keyword) or re.match(rf'^{re.escape(keyword)}\s+', line_lower):
                return True
        
        # Check if line has multiple prices (table row format) and current item already has prices
        price_count = len(list(self.patterns.get_price_pattern().finditer(line)))
        if price_count >= 2 and (current_item.get('price') or current_item.get('total')):
            return True
        
        # Check if line starts with capital letter and is likely a service name
        if re.match(r'^[A-Z][a-z]+', line) and len(line.split()[0]) > 5:
            # Check if it's a known service type
            service_types = ['transport', 'installation', 'carrier']
            if any(st in line_lower for st in service_types):
                return True
        
        return False
    
    def _is_item_complete(self, item: Dict[str, Any]) -> bool:
        """Check if item has enough data to be considered complete."""
        has_description = bool(item.get('description'))
        has_price_or_total = bool(item.get('price') or item.get('total'))
        # Item is complete if it has description and at least price or total
        return has_description and has_price_or_total
    
    def _extract_item_fields_from_line(self, line: str, item: Dict[str, Any]) -> None:
        """Extract all possible fields from a line and add to item."""
        line_lower = line.lower()
        
        # Extract SKU (if not already set)
        if not item.get('sku'):
            # Try parenthetical codes first (most reliable)
            paren_match = re.search(r'\((\d{3,12})\)', line)
            if paren_match:
                sku = paren_match.group(1)
                # Validate it's not a date or year
                if not self._looks_like_date_or_year(sku):
                    item['sku'] = sku
        
        # Extract quantity (if not already set)
        if not item.get('quantity'):
            # Look for quantity at start of line (common format)
            qty_match = re.search(r'^(\d+\.?\d*)\s+', line)
            if qty_match:
                try:
                    qty = float(qty_match.group(1))
                    if 0.01 <= qty <= 1000000:
                        item['quantity'] = qty
                except ValueError:
                    pass
        
        # Extract prices
        price_matches = list(self.patterns.get_price_pattern().finditer(line))
        price_values = []
        
        for match in price_matches:
            price_str = match.group(1).replace(',', '')
            try:
                price_val = float(price_str)
                # Check for negative
                context_before = line[:match.start()].strip()
                if context_before.endswith('-') or line[match.start():match.end()].startswith('-'):
                    price_val = -abs(price_val)
                price_values.append(price_val)
            except ValueError:
                continue
        
        # Set prices (first is usually unit price, last is usually total)
        if price_values:
            if not item.get('price'):
                item['price'] = price_values[0]
            if not item.get('total'):
                item['total'] = price_values[-1] if len(price_values) > 1 else price_values[0]
        
        # Extract description (text content, excluding prices and quantities)
        # Description is the text part of the line
        description_parts = []
        
        # Remove price patterns from line to get description
        desc_line = line
        for match in reversed(list(self.patterns.get_price_pattern().finditer(line))):
            desc_line = desc_line[:match.start()] + desc_line[match.end():]
        
        # Remove quantity at start
        desc_line = re.sub(r'^\d+\.?\d*\s+', '', desc_line).strip()
        
        # Extract meaningful description text
        if desc_line:
            # Split by common separators and take meaningful parts
            parts = re.split(r'\s{2,}', desc_line)  # Split on multiple spaces
            for part in parts:
                part = part.strip()
                if part and len(part) > 3:
                    # Skip if it's just numbers or dates
                    if not (part.replace('.', '').replace(',', '').isdigit() or 
                            re.match(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', part)):
                        description_parts.append(part)
        
        # Build description
        if description_parts:
            new_desc = ' '.join(description_parts)
            if item.get('description'):
                # Append if current description is short, otherwise it might be continuation
                if len(item['description']) < 100:
                    item['description'] += ' ' + new_desc
                else:
                    # Current description is long, this might be part of it
                    item['description'] += ' ' + new_desc
            else:
                item['description'] = new_desc
        
        # Check for discount/credit keywords
        discount_keywords = ['discount', 'credit', 'refund', 'deduction', 'adjustment']
        if any(kw in line_lower for kw in discount_keywords):
            # Make prices negative if they're positive
            if item.get('price') and item['price'] > 0:
                item['price'] = -abs(item['price'])
            if item.get('total') and item['total'] > 0:
                item['total'] = -abs(item['total'])
        
        # Tax rate is always 0.0 (as per requirements)
        if 'tax_rate' not in item:
            item['tax_rate'] = 0.0
    
    def _looks_like_date_or_year(self, text: str) -> bool:
        """Check if text looks like a date or year."""
        if not text.isdigit():
            return False
        if len(text) == 4:
            try:
                year = int(text)
                return 1900 <= year <= 2100
            except ValueError:
                return False
        if '/' in text or '-' in text:
            return True
        return False
    
    def _clean_and_validate_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Clean and validate extracted line items."""
        cleaned = []
        
        for item in items:
            cleaned_item = {
                'sku': item.get('sku', ''),
                'description': item.get('description', '').strip(),
                'quantity': item.get('quantity', 0.0),
                'price': item.get('price', 0.0),
                'tax_rate': item.get('tax_rate', 0.0),
                'total': item.get('total', 0.0)
            }
            
            # Only include items with description
            if cleaned_item['description']:
                cleaned.append(cleaned_item)
        
        logger.info(f"Extracted {len(cleaned)} line items from OCR")
        return cleaned
    
    def extract_from_structured(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract line items from structured API response.
        
        Args:
            response: Full Veryfi API response dictionary
            
        Returns:
            List of dictionaries, each containing line item data
        """
        line_items = []
        
        if not response or 'line_items' not in response:
            return line_items
        
        veryfi_line_items = response.get('line_items', [])
        
        if not isinstance(veryfi_line_items, list):
            return line_items
        
        for item in veryfi_line_items:
            if not isinstance(item, dict):
                continue
            
            sku = item.get('sku') or item.get('upc') or ''
            description = item.get('description') or item.get('full_description') or ''
            quantity = item.get('quantity', 0.0)
            price = item.get('price', 0.0)
            tax_rate = item.get('tax_rate', 0.0)
            total = item.get('total', 0.0)
            
            # Convert to proper types
            try:
                quantity = float(quantity) if quantity else 0.0
            except (ValueError, TypeError):
                quantity = 0.0
            
            try:
                price = float(price) if price else 0.0
            except (ValueError, TypeError):
                price = 0.0
            
            try:
                tax_rate = float(tax_rate) if tax_rate else 0.0
            except (ValueError, TypeError):
                tax_rate = 0.0
            
            try:
                total = float(total) if total else 0.0
            except (ValueError, TypeError):
                total = 0.0
            
            if description or sku:
                line_items.append({
                    'sku': str(sku).strip() if sku else '',
                    'description': str(description).strip() if description else '',
                    'quantity': quantity,
                    'price': price,
                    'tax_rate': tax_rate,
                    'total': total
                })
        
        logger.info(f"Extracted {len(line_items)} line items from structured data")
        return line_items

