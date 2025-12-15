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
                # Empty line - could be separator or continuation
                # If we have a current item with description, it might be continuation
                # If current item seems complete (has price/total), save it
                if current_item:
                    has_complete_data = (
                        current_item.get('price') or 
                        current_item.get('total') or
                        (current_item.get('description') and len(current_item.get('description', '')) > 30)
                    )
                    if has_complete_data and any(current_item.values()):
                        line_items.append(current_item)
                        current_item = {}
                    # Otherwise, might be continuation - keep current_item
                continue
            
            # Check if this looks like start of new line item
            # Indicators: new quantity at start, new description pattern, new SKU
            looks_like_new_item = False
            if not current_item.get('description'):
                looks_like_new_item = True
            elif current_item.get('price') or current_item.get('total'):
                # Current item seems complete, check if this is new item
                # New item indicators:
                # - Starts with quantity-like number
                # - Has SKU pattern
                # - Has price pattern at start
                if (re.match(r'^\d+\.?\d*\s+', line) or
                    any(pattern.search(line) for pattern in self.patterns.get_sku_patterns()[:3]) or
                    self.patterns.get_price_pattern().search(line.split()[0] if line.split() else '')):
                    looks_like_new_item = True
                    # Save current item
                    if any(current_item.values()):
                        line_items.append(current_item)
                    current_item = {}
            
            # Stop at totals section - improved detection
            line_lower = line.lower().strip()
            # More specific patterns for totals section
            totals_indicators = [
                'subtotal', 'sub total', 'sub-total',
                'tax', 'sales tax', 'tax amount',
                'total', 'total due', 'amount due', 'balance',
                'grand total', 'invoice total', 'final total',
                'payment due', 'amount owed'
            ]
            
            # Check if line is a totals section header (not just contains the word)
            is_totals_section = False
            for indicator in totals_indicators:
                # Check if indicator is at start of line or after common prefixes
                if (line_lower.startswith(indicator) or 
                    re.match(r'^(?:invoice|bill|statement)\s+' + indicator, line_lower) or
                    (indicator in line_lower and any(keyword in line_lower for keyword in [':', '=', '$']))):
                    is_totals_section = True
                    break
            
            if is_totals_section:
                if current_item and any(current_item.values()):
                    line_items.append(current_item)
                logger.debug(f"Stopped parsing at totals section: {line[:50]}")
                break
            
            # Try to extract SKU with enhanced heuristics
            if not current_item.get('sku'):
                # First try explicit SKU patterns
                for pattern in self.patterns.get_sku_patterns()[:3]:  # Original patterns first
                    match = pattern.search(line)
                    if match:
                        sku_candidate = match.group(1).strip()
                        # Validate SKU looks reasonable (not a date, not too long)
                        if len(sku_candidate) >= 3 and len(sku_candidate) <= 20:
                            current_item['sku'] = sku_candidate
                            break
                
                # If no explicit SKU found, try enhanced patterns
                if not current_item.get('sku'):
                    # Look for codes at line start (before description)
                    code_at_start = re.search(r'^([A-Z0-9\-]{3,15})\s+', line)
                    if code_at_start:
                        candidate = code_at_start.group(1).strip()
                        # Don't treat as SKU if it looks like a quantity or date
                        if not re.match(r'^\d+$', candidate) and not re.match(r'^\d{1,2}[/-]\d', candidate):
                            current_item['sku'] = candidate
                    
                    # Look for codes in parentheses
                    if not current_item.get('sku'):
                        paren_code = re.search(r'\(([A-Z0-9\-]{3,20})\)', line)
                        if paren_code:
                            current_item['sku'] = paren_code.group(1).strip()
            
            # Try to extract quantity (support decimals and extract from anywhere in line)
            if not current_item.get('quantity'):
                # First try at line start (most common)
                qty_match = re.search(r'^(\d+\.?\d*)\s+', line)
                if qty_match:
                    try:
                        qty_val = float(qty_match.group(1))
                        # Validate quantity is reasonable (not a date, not a price)
                        if 0.01 <= qty_val <= 1000000:  # Reasonable range
                            current_item['quantity'] = qty_val
                    except ValueError:
                        pass
                
                # If not found at start, try to find decimal quantity in line
                # (but avoid matching prices or dates)
                if not current_item.get('quantity'):
                    # Look for decimal numbers that might be quantities
                    # (not at start of price patterns, not dates)
                    qty_patterns = [
                        r'\b(\d+\.\d+)\s+(?![$])',  # Decimal not followed by $
                        r'^\s*(\d+\.\d+)\s+',  # Decimal at start with whitespace
                    ]
                    for qty_pat in qty_patterns:
                        qty_match = re.search(qty_pat, line)
                        if qty_match:
                            try:
                                qty_val = float(qty_match.group(1))
                                if 0.01 <= qty_val <= 1000000:
                                    current_item['quantity'] = qty_val
                                    break
                            except ValueError:
                                continue
            
            # Try to extract prices (including negative values for discounts/credits)
            # Use finditer to get full match including negative sign
            price_matches = self.patterns.get_price_pattern().finditer(line)
            price_values = []
            
            for match in price_matches:
                # Get the full match to check for negative sign
                full_match = match.group(0)
                price_str = match.group(1)  # The captured number part
                
                try:
                    price_val = float(price_str.replace(',', ''))
                    
                    # Check if the match includes a negative sign in the full match
                    is_negative = False
                    
                    # Method 1: Check if full match starts with negative sign
                    if full_match.strip().startswith('-'):
                        is_negative = True
                    # Method 2: Check character immediately before the match
                    elif match.start() > 0:
                        char_before = line[match.start() - 1]
                        # Check if there's a minus sign before (with optional whitespace)
                        if char_before == '-':
                            is_negative = True
                        elif match.start() > 1 and line[match.start() - 2:match.start()].strip() == '-':
                            is_negative = True
                    
                    # Method 3: Check line context for discount/credit keywords
                    if not is_negative:
                        line_lower = line.lower()
                        line_before_price = line[:match.start()].lower()
                        # Check if discount/credit keyword appears before this price
                        discount_keywords = ['discount', 'credit', 'refund', 'deduction', 'adjustment']
                        if any(keyword in line_before_price for keyword in discount_keywords):
                            # Additional check: make sure it's not a false positive
                            # (e.g., "discount rate" shouldn't make prices negative)
                            keyword_positions = [line_before_price.rfind(kw) for kw in discount_keywords if kw in line_before_price]
                            if keyword_positions:
                                last_keyword_pos = max(keyword_positions)
                                # Check if there's a price-like pattern between keyword and this price
                                text_between = line_before_price[last_keyword_pos:]
                                # If no other numbers/prices between keyword and this price, it's likely negative
                                if not re.search(r'\d+\.?\d*', text_between):
                                    is_negative = True
                    
                    if is_negative:
                        price_val = -abs(price_val)
                    
                    price_values.append(price_val)
                except ValueError:
                    continue
            
            if price_values:
                # Check if this line/item is a discount/credit BEFORE setting prices
                # This ensures we set prices as negative from the start
                is_discount_line = False
                description = current_item.get('description', '').lower()
                line_lower = line.lower()
                discount_keywords = ['discount', 'credit', 'refund', 'deduction', 'adjustment']
                
                # Check description and current line for discount keywords
                if any(keyword in description for keyword in discount_keywords):
                    is_discount_line = True
                elif any(keyword in line_lower for keyword in discount_keywords):
                    is_discount_line = True
                
                # Determine which price is which (first is usually unit price, last is usually total)
                if not current_item.get('price'):
                    price_to_set = price_values[0]
                    # If it's a discount line OR description contains discount keywords, make price negative
                    if is_discount_line:
                        price_to_set = -abs(price_to_set)
                        logger.debug(f"Setting price to negative for discount line: {price_to_set}")
                    current_item['price'] = price_to_set
                
                if len(price_values) > 1 and not current_item.get('total'):
                    total_to_set = price_values[-1]
                    # If it's a discount line, make total negative
                    if is_discount_line:
                        total_to_set = -abs(total_to_set)
                    current_item['total'] = total_to_set
                elif not current_item.get('total'):
                    total_to_set = price_values[0]
                    # If it's a discount line, make total negative
                    if is_discount_line:
                        total_to_set = -abs(total_to_set)
                    current_item['total'] = total_to_set
                
                # Final consistency check: if total is negative but price is positive,
                # and it's a discount line, make price negative too
                if current_item.get('total') and current_item.get('price'):
                    if current_item['total'] < 0 and current_item['price'] > 0:
                        # Re-check if this is a discount/credit line (description might be set now)
                        description_check = current_item.get('description', '').lower()
                        if any(keyword in description_check for keyword in discount_keywords):
                            # Make price negative to match total
                            current_item['price'] = -abs(current_item['price'])
                            logger.debug(f"Made price negative to match negative total for discount/credit line")
            
            # Try to extract tax rate with enhanced patterns and logging
            if not current_item.get('tax_rate'):
                tax_match = self.patterns.get_tax_rate_pattern().search(line)
                if tax_match:
                    try:
                        tax_rate_val = float(tax_match.group(1))
                        # Validate tax rate is reasonable (0-100%)
                        if 0.0 <= tax_rate_val <= 100.0:
                            current_item['tax_rate'] = tax_rate_val
                            logger.debug(f"Extracted tax rate: {tax_rate_val}% from line: {line[:50]}")
                        else:
                            logger.debug(f"Tax rate out of range ({tax_rate_val}%), ignoring")
                    except ValueError:
                        logger.debug(f"Failed to parse tax rate from: {line[:50]}")
                else:
                    # Try alternative patterns for tax rate
                    # Look for "tax: X%" or "tax rate: X%"
                    alt_tax_patterns = [
                        re.compile(r'tax\s*:?\s*(\d+\.?\d*)\s*%', re.IGNORECASE),
                        re.compile(r'tax\s+rate\s*:?\s*(\d+\.?\d*)\s*%', re.IGNORECASE),
                        re.compile(r'(\d+\.?\d*)\s*%\s+tax', re.IGNORECASE),
                    ]
                    for alt_pattern in alt_tax_patterns:
                        alt_match = alt_pattern.search(line)
                        if alt_match:
                            try:
                                tax_rate_val = float(alt_match.group(1))
                                if 0.0 <= tax_rate_val <= 100.0:
                                    current_item['tax_rate'] = tax_rate_val
                                    logger.debug(f"Extracted tax rate (alt pattern): {tax_rate_val}%")
                                    break
                            except ValueError:
                                continue
            
            # Description extraction - improved to handle lines starting with numbers
            # and better multi-line description handling
            is_likely_description = False
            
            # Check if line looks like a description (not just numbers/prices)
            line_clean = line.replace('.', '').replace(',', '').strip()
            has_text = any(c.isalpha() for c in line)
            is_mostly_numbers = len([c for c in line_clean[:10] if c.isdigit()]) > 5
            
            # Description if it has text content or is long enough
            if has_text or (len(line) > 15 and not is_mostly_numbers):
                is_likely_description = True
            # Also consider lines that start with numbers but have substantial text
            elif len(line) > 20 and has_text:
                is_likely_description = True
            
            # Check if this line indicates a discount/credit (for price handling)
            is_discount_indicator = any(keyword in line.lower() 
                                       for keyword in ['discount', 'credit', 'refund', 'deduction', 'adjustment'])
            
            if is_likely_description:
                # Determine if this is continuation or new description
                if current_item.get('description'):
                    # Check if this looks like continuation (no clear item separator)
                    # Continuation indicators: no leading numbers that look like quantity,
                    # or line is clearly part of previous description
                    looks_like_continuation = (
                        not re.match(r'^\d+\.?\d*\s+[A-Z]', line) or  # Not quantity + capital letter
                        len(line) < 30 or  # Short line likely continuation
                        line[0].islower() or  # Starts with lowercase
                        not any(keyword in line.lower() for keyword in ['transport', 'installation', 'carrier', 'discount'])  # Not new item keyword
                    )
                    
                    if looks_like_continuation:
                        # Append to existing description with newline for readability
                        current_item['description'] += '\n' + line
                        # Check if description now contains discount keyword
                        if any(keyword in current_item['description'].lower() 
                               for keyword in ['discount', 'credit', 'refund', 'deduction']):
                            # If price is already set and positive, make it negative
                            if current_item.get('price') and current_item['price'] > 0:
                                current_item['price'] = -abs(current_item['price'])
                                logger.debug(f"Made price negative after detecting discount in description")
                    else:
                        # Might be new item, but be conservative - append if description is short
                        if len(current_item.get('description', '')) < 50:
                            current_item['description'] += '\n' + line
                            # Check for discount in updated description
                            if any(keyword in current_item['description'].lower() 
                                   for keyword in ['discount', 'credit', 'refund', 'deduction']):
                                if current_item.get('price') and current_item['price'] > 0:
                                    current_item['price'] = -abs(current_item['price'])
                        else:
                            # Save current item and start new one
                            if any(current_item.values()):
                                line_items.append(current_item)
                            current_item = {'description': line}
                else:
                    # New description
                    current_item['description'] = line
                    # If description contains discount keyword, mark it
                    if any(keyword in line.lower() for keyword in ['discount', 'credit', 'refund', 'deduction']):
                        # If price was already extracted, make it negative
                        if current_item.get('price') and current_item['price'] > 0:
                            current_item['price'] = -abs(current_item['price'])
                            logger.debug(f"Made price negative for discount description")
            elif not current_item.get('description') and len(line) > 10:
                # Fallback: use line as description if no description yet
                current_item['description'] = line
        
        # Add last item if exists
        if current_item and any(current_item.values()):
            line_items.append(current_item)
        
        # Clean up and validate line items
        cleaned_items = []
        for idx, item in enumerate(line_items):
            cleaned_item = {
                'sku': item.get('sku') or '',
                'description': item.get('description') or '',
                'quantity': item.get('quantity', 0.0),
                'price': item.get('price', 0.0),
                'tax_rate': item.get('tax_rate', 0.0),
                'total': item.get('total', 0.0)
            }
            
            # Final fix: If description contains discount/credit keywords and total is negative,
            # ensure price is also negative
            description_lower = cleaned_item['description'].lower()
            discount_keywords = ['discount', 'credit', 'refund', 'deduction', 'adjustment']
            has_discount_keyword = any(keyword in description_lower for keyword in discount_keywords)
            
            if has_discount_keyword and cleaned_item['total'] < 0 and cleaned_item['price'] > 0:
                cleaned_item['price'] = -abs(cleaned_item['price'])
                logger.debug(f"Fixed price to negative for discount line item {idx + 1}: {cleaned_item['description'][:50]}")
            
            # Validate line item data
            quantity = cleaned_item['quantity']
            price = cleaned_item['price']
            total = cleaned_item['total']
            
            # Validation: quantity * price should approximately equal total (within tolerance)
            if quantity and price and total:
                calculated_total = quantity * price
                difference = abs(calculated_total - abs(total))
                tolerance = max(0.01, abs(total) * 0.01)  # 1% tolerance or $0.01, whichever is larger
                
                if difference > tolerance:
                    logger.warning(
                        f"Line item {idx + 1} calculation mismatch: "
                        f"quantity ({quantity}) * price ({price}) = {calculated_total}, "
                        f"but total is {total} (difference: {difference:.2f})"
                    )
            
            # Validation: flag suspicious values
            if quantity and (quantity < 0.001 or quantity > 1000000):
                logger.warning(f"Line item {idx + 1} has suspicious quantity: {quantity}")
            
            if price and abs(price) > 10000000:
                logger.warning(f"Line item {idx + 1} has suspicious price: {price}")
            
            if total and abs(total) > 100000000:
                logger.warning(f"Line item {idx + 1} has suspicious total: {total}")
            
            # Validation: negative total but positive price might indicate discount
            # Fix it if description contains discount keywords
            if total < 0 and price > 0:
                description_lower = cleaned_item['description'].lower()
                if any(keyword in description_lower for keyword in ['discount', 'credit', 'refund', 'deduction', 'adjustment']):
                    cleaned_item['price'] = -abs(cleaned_item['price'])
                    logger.debug(f"Fixed price to negative for discount line item {idx + 1} (negative total detected)")
                else:
                    logger.debug(f"Line item {idx + 1} appears to be a discount/credit (negative total, positive price)")
            
            # Only include items with description or SKU
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

