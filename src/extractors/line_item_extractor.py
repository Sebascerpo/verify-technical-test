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
        Extract line items from OCR text.
        
        Args:
            ocr_text: Raw OCR text from the invoice
            
        Returns:
            List of dictionaries, each containing line item data
        """
        line_items = []
        lines = ocr_text.split('\n')
        
        # Find the line items section
        item_section_start = -1
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in ['item', 'description', 'qty', 'quantity', 'price', 'amount']):
                if any(col in line_lower for col in ['sku', 'item', 'description', 'qty', 'quantity', 'price', 'total']):
                    item_section_start = i + 1
                    break
        
        if item_section_start == -1:
            item_section_start = 0
        
        # Parse line items
        current_item = {}
        
        for i in range(item_section_start, len(lines)):
            line = lines[i].strip()
            if not line:
                if current_item and any(current_item.values()):
                    line_items.append(current_item)
                    current_item = {}
                continue
            
            # Stop at totals section
            if any(stop in line.lower() for stop in ['subtotal', 'tax', 'total', 'amount due', 'balance']):
                if current_item and any(current_item.values()):
                    line_items.append(current_item)
                break
            
            # Try to extract SKU
            if not current_item.get('sku'):
                for pattern in self.patterns.get_sku_patterns():
                    match = pattern.search(line)
                    if match:
                        current_item['sku'] = match.group(1).strip()
                        break
            
            # Try to extract quantity
            if not current_item.get('quantity'):
                qty_match = re.search(r'^(\d+)\s+', line)
                if qty_match:
                    try:
                        current_item['quantity'] = float(qty_match.group(1))
                    except ValueError:
                        pass
            
            # Try to extract prices
            prices = self.patterns.get_price_pattern().findall(line)
            if prices:
                price_values = []
                for price_str in prices:
                    try:
                        price_val = float(price_str.replace(',', ''))
                        price_values.append(price_val)
                    except ValueError:
                        continue
                
                if price_values:
                    if not current_item.get('price'):
                        current_item['price'] = price_values[0]
                    if len(price_values) > 1 and not current_item.get('total'):
                        current_item['total'] = price_values[-1]
                    elif not current_item.get('total'):
                        current_item['total'] = price_values[0]
            
            # Try to extract tax rate
            if not current_item.get('tax_rate'):
                tax_match = self.patterns.get_tax_rate_pattern().search(line)
                if tax_match:
                    try:
                        current_item['tax_rate'] = float(tax_match.group(1))
                    except ValueError:
                        pass
            
            # Description extraction
            if not any(char.isdigit() for char in line.replace('.', '').replace(',', '').strip()[:5]):
                if current_item.get('description'):
                    current_item['description'] += ' ' + line
                else:
                    current_item['description'] = line
            elif not current_item.get('description') and len(line) > 10:
                current_item['description'] = line
        
        # Add last item if exists
        if current_item and any(current_item.values()):
            line_items.append(current_item)
        
        # Clean up line items
        cleaned_items = []
        for item in line_items:
            cleaned_item = {
                'sku': item.get('sku') or '',
                'description': item.get('description') or '',
                'quantity': item.get('quantity', 0.0),
                'price': item.get('price', 0.0),
                'tax_rate': item.get('tax_rate', 0.0),
                'total': item.get('total', 0.0)
            }
            if cleaned_item['description'] or cleaned_item['sku']:
                cleaned_items.append(cleaned_item)
        
        logger.info(f"Extracted {len(cleaned_items)} line items from OCR")
        return cleaned_items
    
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

