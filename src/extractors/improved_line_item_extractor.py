"""
Improved Line Item Extractor for Complex Invoices

Handles:
- SKU extraction from parenthetical codes
- Invoice-level tax rate calculation
- Better number parsing
"""

import re
from typing import Dict, List, Optional, Any
from ..core.logging_config import get_logger

logger = get_logger(__name__)


class ImprovedLineItemExtractor:
    """Enhanced line item extraction."""
    
    def extract_sku_from_description(self, description: str) -> str:
        """
        Extract SKU from description with parenthetical codes.
        
        Examples:
        - "(X6HCHK1C)" → "X6HCHK1C"
        - "(a488ZH)" → "a488ZH"
        - "(10/2023)" → "" (skip dates)
        - "(Taxes)" → "" (skip keywords)
        
        Args:
            description: Line item description text
            
        Returns:
            Extracted SKU code or empty string
        """
        if not description:
            return ''
        
        # Pattern to match alphanumeric codes in parentheses (3-12 chars)
        # Handles both uppercase and lowercase
        pattern = r'\(([A-Za-z0-9]{3,12})\)'
        matches = re.findall(pattern, description)
        
        for match in matches:
            # Skip dates like "10/2023" or "01-2024"
            if '/' in match or '-' in match:
                continue
            
            # Skip keywords
            match_lower = match.lower()
            if match_lower in ['taxes', 'tax']:
                continue
            
            # Skip if purely numeric (likely not a SKU)
            if match.isdigit():
                continue
            
            # Additional validation: skip if looks like a date pattern
            # (e.g., "2023", "2024" as standalone numbers)
            if len(match) == 4 and match.isdigit():
                # Could be a year, but also could be a SKU
                # Only skip if it's clearly a year (1900-2100 range)
                try:
                    year = int(match)
                    if 1900 <= year <= 2100:
                        continue
                except ValueError:
                    pass
            
            # Found valid SKU
            logger.debug(f"Extracted SKU '{match}' from description: {description[:50]}")
            return match
        
        logger.debug(f"No valid SKU found in description: {description[:50]}")
        return ''
    
    def _is_tax_line_item(self, item: Dict[str, Any]) -> bool:
        """
        Check if a line item is a tax item.
        
        Args:
            item: Line item dictionary
            
        Returns:
            True if item is a tax item, False otherwise
        """
        description = item.get('description', '').lower()
        tax_keywords = ['tax', 'carrier tax', 'carrier taxes', 'sales tax']
        return any(keyword in description for keyword in tax_keywords)
    
    def _is_discount_line_item(self, item: Dict[str, Any]) -> bool:
        """
        Check if a line item is a discount item.
        
        Args:
            item: Line item dictionary
            
        Returns:
            True if item is a discount item, False otherwise
        """
        description = item.get('description', '').lower()
        total = item.get('total', 0.0)
        discount_keywords = ['discount', 'credit', 'refund', 'deduction', 'adjustment']
        return any(keyword in description for keyword in discount_keywords) or total < 0
    
    def _get_invoice_total(
        self,
        response: Optional[Dict[str, Any]] = None,
        ocr_text: Optional[str] = None,
        line_items: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[float]:
        """
        Get invoice total from various sources.
        
        Args:
            response: Veryfi API response dictionary
            ocr_text: OCR text from invoice
            line_items: List of line items
            
        Returns:
            Invoice total amount or None if not found
        """
        # Method 1: From response
        if response:
            total_raw = response.get('total')
            if isinstance(total_raw, dict) and 'value' in total_raw:
                total_raw = total_raw['value']
            if total_raw is not None:
                try:
                    total = float(total_raw)
                    if total > 0:
                        logger.debug(f"Found invoice total from response: {total}")
                        return total
                except (ValueError, TypeError):
                    pass
        
        # Method 2: From OCR text
        if ocr_text:
            lines = ocr_text.split('\n')
            amount_pattern = r'\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
            total_keywords = ['total', 'grand total', 'invoice total', 'amount due', 'balance due']
            
            for line in lines:
                lower = line.lower().strip()
                # Look for total keywords (but not "subtotal")
                if any(keyword in lower for keyword in total_keywords) and 'subtotal' not in lower:
                    nums = re.findall(amount_pattern, line)
                    if nums:
                        try:
                            total = float(nums[-1].replace(',', ''))
                            if total > 0:
                                logger.debug(f"Found invoice total from OCR: {total}")
                                return total
                        except (ValueError, IndexError):
                            pass
        
        # Method 3: Calculate from line items (sum of all totals, including negatives for discounts)
        if line_items:
            total = sum(item.get('total', 0.0) for item in line_items)
            # Use absolute value for validation, but return actual sum
            if abs(total) > 0:
                logger.debug(f"Calculated invoice total from line items: {total}")
                return abs(total)  # Return absolute value as invoice total should be positive
        
        return None
    
    def calculate_invoice_tax_rate(
        self,
        line_items: Optional[List[Dict[str, Any]]] = None,
        response: Optional[Dict[str, Any]] = None,
        ocr_text: Optional[str] = None
    ) -> float:
        """
        Calculate invoice-level tax rate.
        
        Strategy (in order of priority):
        1. From tax line items (NEW - primary method):
           - Identify tax line items from descriptions
           - Sum all tax line item totals
           - Get invoice total from response/OCR or calculate from line items
           - Calculate: tax_rate = (total_tax / (invoice_total - total_tax)) * 100
        2. From structured data: tax_rate = (tax / subtotal) * 100
        3. From OCR: Look for explicit rate percentage
        4. From OCR: Calculate from tax and subtotal amounts
        
        Args:
            line_items: List of line items (for tax line item analysis)
            response: Veryfi API response dictionary
            ocr_text: OCR text from invoice
            
        Returns:
            Tax rate as percentage (e.g., 8.5 for 8.5%), or 0.0 if not found
        """
        # Strategy 1: Calculate from tax line items (NEW - primary method)
        if line_items:
            # Identify tax line items
            tax_items = [item for item in line_items if self._is_tax_line_item(item)]
            
            if tax_items:
                # Sum all tax line item totals (including negatives to get net tax)
                # Some invoices may have tax credits/refunds (negative tax items)
                total_tax = sum(item.get('total', 0.0) for item in tax_items)
                
                # Use absolute value for calculation, but preserve sign for logging
                total_tax_abs = abs(total_tax)
                
                if total_tax_abs > 0:
                    # Get invoice total
                    invoice_total = self._get_invoice_total(response, ocr_text, line_items)
                    
                    if invoice_total and invoice_total > total_tax_abs:
                        # Calculate subtotal (invoice total minus net tax)
                        # Use absolute value of tax for subtotal calculation
                        subtotal = invoice_total - total_tax_abs
                        
                        if subtotal > 0:
                            # Calculate tax rate using absolute value of net tax
                            # This gives us the effective tax rate regardless of credits
                            rate = (total_tax_abs / subtotal) * 100
                            logger.info(
                                f"Calculated tax rate from tax line items: {rate:.2f}% "
                                f"(net_tax={total_tax:.2f}, tax_abs={total_tax_abs:.2f}, "
                                f"invoice_total={invoice_total:.2f}, subtotal={subtotal:.2f})"
                            )
                            return round(rate, 2)
                        else:
                            logger.debug(f"Subtotal is zero or negative: {subtotal}")
                    else:
                        logger.debug(
                            f"Could not get valid invoice total: {invoice_total}, "
                            f"or invoice_total <= total_tax_abs: {invoice_total} <= {total_tax_abs}"
                        )
                else:
                    logger.debug(f"Total tax from line items is zero: {total_tax} (abs: {total_tax_abs})")
            else:
                logger.debug("No tax line items found in line items list")
        
        # Strategy 2: From structured data (fallback)
        if response:
            tax = None
            subtotal = None
            
            # Try direct fields first
            tax_raw = response.get('tax')
            subtotal_raw = response.get('subtotal')
            
            # Handle nested 'value' format (Veryfi structure)
            if isinstance(tax_raw, dict) and 'value' in tax_raw:
                tax_raw = tax_raw['value']
            if isinstance(subtotal_raw, dict) and 'value' in subtotal_raw:
                subtotal_raw = subtotal_raw['value']
            
            # Try to convert to float
            try:
                if tax_raw is not None:
                    tax = float(tax_raw)
            except (ValueError, TypeError):
                pass
            
            try:
                if subtotal_raw is not None:
                    subtotal = float(subtotal_raw)
            except (ValueError, TypeError):
                pass
            
            # Calculate rate if both values are available
            if subtotal and subtotal > 0 and tax and tax >= 0:
                rate = (tax / subtotal) * 100
                logger.info(f"Calculated tax rate from structured data: {rate:.2f}% (tax={tax}, subtotal={subtotal})")
                return round(rate, 2)
            else:
                logger.debug(f"Could not calculate tax rate from structured data: tax={tax}, subtotal={subtotal}")
        
        
        # Strategy 3: From OCR text (fallback)
        if ocr_text:
            # Strategy 1: Look for explicit tax rate percentage
            # Patterns: "Tax: 8.5%", "Tax Rate: 8.5%", "8.5% tax", etc.
            tax_rate_patterns = [
                r'tax\s*:?\s*rate\s*:?\s*(\d+\.?\d*)\s*%',  # "Tax Rate: 8.5%"
                r'tax\s*:?\s*(\d+\.?\d*)\s*%',  # "Tax: 8.5%"
                r'(\d+\.?\d*)\s*%\s*tax',  # "8.5% tax"
                r'(\d+\.?\d*)\s*%\s*sales\s*tax',  # "8.5% sales tax"
            ]
            
            for pattern in tax_rate_patterns:
                match = re.search(pattern, ocr_text, re.IGNORECASE)
                if match:
                    try:
                        rate = float(match.group(1))
                        if 0.0 <= rate <= 100.0:  # Validate reasonable range
                            logger.info(f"Extracted tax rate from OCR text: {rate:.2f}%")
                            return round(rate, 2)
                    except (ValueError, IndexError):
                        continue
            
            # Strategy 2: Calculate from tax and subtotal amounts
            lines = ocr_text.split('\n')
            tax_amount = None
            subtotal_amount = None
            
            # Improved patterns for finding amounts
            amount_pattern = r'\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
            
            for line in lines:
                lower = line.lower().strip()
                
                # Look for subtotal (but not "subtotal tax")
                if 'subtotal' in lower and 'tax' not in lower:
                    # Extract the last number (usually the amount)
                    nums = re.findall(amount_pattern, line)
                    if nums:
                        try:
                            subtotal_amount = float(nums[-1].replace(',', ''))
                            logger.debug(f"Found subtotal amount: {subtotal_amount}")
                        except (ValueError, IndexError):
                            pass
                
                # Look for tax (but exclude "carrier tax" which is a line item)
                # Also exclude "subtotal" to avoid confusion
                if 'tax' in lower and 'carrier' not in lower and 'subtotal' not in lower:
                    # Check if this line has a percentage (if so, skip - it's a rate, not amount)
                    if '%' not in line:
                        nums = re.findall(amount_pattern, line)
                        if nums:
                            try:
                                tax_amount = float(nums[-1].replace(',', ''))
                                logger.debug(f"Found tax amount: {tax_amount}")
                            except (ValueError, IndexError):
                                pass
            
            # Calculate rate if both amounts found
            if subtotal_amount and subtotal_amount > 0 and tax_amount and tax_amount >= 0:
                rate = (tax_amount / subtotal_amount) * 100
                logger.info(f"Calculated tax rate from OCR amounts: {rate:.2f}% (tax={tax_amount}, subtotal={subtotal_amount})")
                return round(rate, 2)
            else:
                logger.debug(f"Could not calculate tax rate from OCR: tax={tax_amount}, subtotal={subtotal_amount}")
        
        logger.warning("Could not determine tax rate from response or OCR text")
        return 0.0
    
    def extract_and_improve_line_items(
        self,
        line_items: List[Dict[str, Any]],
        response: Optional[Dict[str, Any]] = None,
        ocr_text: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Improve existing line items with better SKU and tax rate.
        
        Args:
            line_items: Existing line items from base extractor
            response: Veryfi API response
            ocr_text: OCR text
            
        Returns:
            Improved line items with extracted SKUs, cleaned descriptions, and invoice-level tax rate
        """
        # Calculate invoice-level tax rate once for all items
        tax_rate = self.calculate_invoice_tax_rate(line_items, response, ocr_text)
        
        if tax_rate > 0:
            logger.info(f"Calculated invoice-level tax rate: {tax_rate:.2f}%")
        else:
            logger.warning("Tax rate is 0.0 - may indicate missing tax information")
        
        improved_items = []
        for idx, item in enumerate(line_items):
            description = item.get('description', '')
            existing_sku = item.get('sku', '')
            
            # Determine if this is a tax or discount item
            is_tax = self._is_tax_line_item(item)
            is_discount = self._is_discount_line_item(item)
            
            # Extract SKU from description ONLY for regular products (not taxes or discounts)
            if is_tax or is_discount:
                sku = ''  # No SKU for taxes or discounts
                logger.debug(f"Item {idx + 1} is {'tax' if is_tax else 'discount'}, setting SKU to empty")
            else:
                # Regular product - extract SKU (preserve existing if already extracted)
                sku = existing_sku if existing_sku else self.extract_sku_from_description(description)
            
            # Clean description: remove all parenthetical codes (SKUs and dates)
            # Pattern matches: (X6HCHK1C), (10/2023), (a488ZH), etc.
            # This removes both SKU codes and date codes
            clean_desc = re.sub(r'\([A-Za-z0-9/]+\)', '', description)
            # Clean up extra whitespace
            clean_desc = ' '.join(clean_desc.split()).strip()
            
            # If description became empty after cleaning, use original
            if not clean_desc:
                clean_desc = description
                logger.debug(f"Description became empty after cleaning, using original for item {idx + 1}")
            
            # Determine tax rate for this item
            # - Tax items: keep tax_rate = 0.0
            # - Discount items: keep tax_rate = 0.0
            # - Regular products: apply calculated tax_rate
            item_tax_rate = 0.0
            if is_tax:
                logger.debug(f"Item {idx + 1} is a tax item, keeping tax_rate = 0.0")
            elif is_discount:
                logger.debug(f"Item {idx + 1} is a discount item, keeping tax_rate = 0.0")
            else:
                # Regular product - apply calculated tax rate
                item_tax_rate = tax_rate
            
            # Get price and total from item
            price = item.get('price', 0.0)
            total = item.get('total', 0.0)
            
            # Fix negative price handling: if total is negative, price should also be negative
            if total < 0 and price > 0:
                price = -abs(price)
                logger.debug(f"Item {idx + 1}: Made price negative ({price}) to match negative total ({total})")
            
            # Create improved item
            improved_item = {
                'sku': sku,
                'description': clean_desc,
                'quantity': item.get('quantity', 0.0),
                'price': price,  # May be negative if total is negative
                'tax_rate': item_tax_rate,  # Apply tax rate only to regular products
                'total': total
            }
            
            improved_items.append(improved_item)
            
            # Log improvements
            if sku and not existing_sku:
                logger.debug(f"Item {idx + 1}: Extracted SKU '{sku}' from description")
            elif not sku and description:
                logger.debug(f"Item {idx + 1}: No SKU found in description: {description[:50]}")
        
        logger.info(f"Improved {len(improved_items)} line items with SKU extraction and tax rate")
        return improved_items