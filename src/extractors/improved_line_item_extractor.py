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
        Extract SKU (Stock Keeping Unit) from description with parenthetical codes.
        
        **Field Assumption**: SKU is numeric only (3-12 digits) in parentheses.
        
        **Reasoning**:
        - Based on Veryfi API documentation for line_items_sku field
        - Veryfi extracts SKU as a unique number associated with a product
        - Invoices from USA companies typically use numeric SKUs in parentheses
        - Reference: https://faq.veryfi.com/en/articles/5571268-document-data-extraction-fields-explained
        
        **Format**: Numeric codes in parentheses, e.g., "(12345)", "(67890)"
        - Pattern: matches 3-12 digits in parentheses (numeric only)
        - Excludes dates (e.g., "10/2023"), alphanumeric codes, and years (1900-2100)
        
        **Examples**:
        - "(12345)" → "12345" ✓
        - "(67890)" → "67890" ✓
        - "(10/2023)" → "" (skip dates)
        - "(X6HCHK1C)" → "" (skip alphanumeric)
        - "(2023)" → "" (skip years)
        
        Args:
            description: Line item description text containing potential SKU codes
            
        Returns:
            Extracted SKU code (numeric only) or empty string if not found
        """
        if not description:
            return ''
        
        # Pattern to match numeric codes in parentheses (3-12 digits)
        # Only matches numbers, no letters or special characters
        pattern = r'\((\d{3,12})\)'
        matches = re.findall(pattern, description)
        
        for match in matches:
            if self._is_valid_sku_code(match):
                logger.debug(f"Extracted numeric SKU '{match}' from description: {description[:50]}")
                return match
        
        logger.debug(f"No valid numeric SKU found in description: {description[:50]}")
        return ''
    
    def _is_valid_sku_code(self, code: str) -> bool:
        """
        Validate if a code is a valid SKU (not a date or year).
        
        Args:
            code: Numeric code to validate
            
        Returns:
            True if code is a valid SKU, False otherwise
        """
        # Skip dates like "10/2023" or "01-2024" (contains / or -)
        if '/' in code or '-' in code:
            return False
        
        # Skip if too short (less than 3 digits)
        if len(code) < 3:
            return False
        
        # Skip if looks like a year (1900-2100 range)
        if self._is_year_code(code):
            return False
        
        return True
    
    def _is_year_code(self, code: str) -> bool:
        """
        Check if a 4-digit code is a year (1900-2100).
        
        Args:
            code: 4-digit numeric code
            
        Returns:
            True if code is a year, False otherwise
        """
        if len(code) != 4 or not code.isdigit():
            return False
        
        try:
            year = int(code)
            return 1900 <= year <= 2100
        except ValueError:
            return False
    
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
        total = self._get_invoice_total_from_response(response)
        if total is not None:
            return total
        
        # Method 2: From OCR text
        total = self._get_invoice_total_from_ocr(ocr_text)
        if total is not None:
            return total
        
        # Method 3: Calculate from line items
        return self._calculate_invoice_total_from_line_items(line_items)
    
    def _get_invoice_total_from_response(self, response: Optional[Dict[str, Any]]) -> Optional[float]:
        """
        Get invoice total from API response.
        
        Args:
            response: Veryfi API response dictionary
            
        Returns:
            Invoice total amount or None if not found
        """
        if not response:
            return None
        
        total_raw = response.get('total')
        if isinstance(total_raw, dict) and 'value' in total_raw:
            total_raw = total_raw['value']
        
        if total_raw is None:
            return None
        
        try:
            total = float(total_raw)
            if total > 0:
                logger.debug(f"Found invoice total from response: {total}")
                return total
        except (ValueError, TypeError):
            pass
        
        return None
    
    def _get_invoice_total_from_ocr(self, ocr_text: Optional[str]) -> Optional[float]:
        """
        Get invoice total from OCR text.
        
        Args:
            ocr_text: OCR text from invoice
            
        Returns:
            Invoice total amount or None if not found
        """
        if not ocr_text:
            return None
        
        lines = ocr_text.split('\n')
        amount_pattern = r'\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
        total_keywords = ['total', 'grand total', 'invoice total', 'amount due', 'balance due']
        
        for line in lines:
            lower = line.lower().strip()
            # Look for total keywords (but not "subtotal")
            if 'subtotal' in lower:
                continue
            
            if not any(keyword in lower for keyword in total_keywords):
                continue
            
            nums = re.findall(amount_pattern, line)
            if not nums:
                continue
            
            try:
                total = float(nums[-1].replace(',', ''))
                if total > 0:
                    logger.debug(f"Found invoice total from OCR: {total}")
                    return total
            except (ValueError, IndexError):
                pass
        
        return None
    
    def _calculate_invoice_total_from_line_items(self, line_items: Optional[List[Dict[str, Any]]]) -> Optional[float]:
        """
        Calculate invoice total from line items sum.
        
        Args:
            line_items: List of line items
            
        Returns:
            Invoice total amount or None if not found
        """
        if not line_items:
            return None
        
        total = sum(item.get('total', 0.0) for item in line_items)
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
        
        **Tax Rate Decision**: After analyzing the invoice structure, Switch uses separate
        "Carrier Taxes" line items for regulatory pass-through fees rather than applying
        percentage-based taxes to services. Therefore, tax_rate is set to 0.0 for all items,
        as taxes are represented by dedicated line items rather than rates applied to services.
        This matches standard telecommunications industry billing practices.
        
        Args:
            line_items: List of line items (unused, kept for compatibility)
            response: Veryfi API response (unused, kept for compatibility)
            ocr_text: OCR text (unused, kept for compatibility)
            
        Returns:
            Always returns 0.0, as taxes are represented by dedicated line items
        """
        return 0.0
    
    def _calculate_tax_rate_from_line_items(
        self,
        line_items: Optional[List[Dict[str, Any]]],
        response: Optional[Dict[str, Any]],
        ocr_text: Optional[str]
    ) -> Optional[float]:
        """
        Calculate tax rate from tax line items.
        
        Args:
            line_items: List of line items to identify tax items
            response: Veryfi API response dictionary
            ocr_text: OCR text from invoice
            
        Returns:
            Tax rate as percentage, or None if calculation not possible
        """
        if not line_items:
            return None
        
        tax_items = [item for item in line_items if self._is_tax_line_item(item)]
        if not tax_items:
            logger.debug("No tax line items found in line items list")
            return None
        
        # Sum all tax line item totals (including negatives to get net tax)
        total_tax = sum(item.get('total', 0.0) for item in tax_items)
        total_tax_abs = abs(total_tax)
        
        if total_tax_abs == 0:
            logger.debug(f"Total tax from line items is zero: {total_tax}")
            return None
        
        # Get invoice total
        invoice_total = self._get_invoice_total(response, ocr_text, line_items)
        if not invoice_total or invoice_total <= total_tax_abs:
            logger.debug(
                f"Could not get valid invoice total: {invoice_total}, "
                f"or invoice_total <= total_tax_abs: {invoice_total} <= {total_tax_abs}"
            )
            return None
        
        # Calculate subtotal (invoice total minus net tax)
        subtotal = invoice_total - total_tax_abs
        if subtotal <= 0:
            logger.debug(f"Subtotal is zero or negative: {subtotal}")
            return None
        
        # Calculate tax rate
        rate = (total_tax_abs / subtotal) * 100
        logger.info(
            f"Calculated tax rate from tax line items: {rate:.2f}% "
            f"(net_tax={total_tax:.2f}, tax_abs={total_tax_abs:.2f}, "
            f"invoice_total={invoice_total:.2f}, subtotal={subtotal:.2f})"
        )
        return round(rate, 2)
    
    def _extract_tax_from_structured_response(self, response: Dict[str, Any]) -> tuple[Optional[float], Optional[float]]:
        """
        Extract tax and subtotal from structured response.
        
        Args:
            response: Veryfi API response dictionary
            
        Returns:
            Tuple of (tax, subtotal) or (None, None) if not found
        """
        tax_raw = response.get('tax')
        subtotal_raw = response.get('subtotal')
        
        # Handle nested 'value' format (Veryfi structure)
        if isinstance(tax_raw, dict) and 'value' in tax_raw:
            tax_raw = tax_raw['value']
        if isinstance(subtotal_raw, dict) and 'value' in subtotal_raw:
            subtotal_raw = subtotal_raw['value']
        
        # Convert to float
        tax = None
        subtotal = None
        
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
        
        return tax, subtotal
    
    def _calculate_tax_rate_from_structured_data(self, response: Optional[Dict[str, Any]]) -> Optional[float]:
        """
        Calculate tax rate from structured data.
        
        Args:
            response: Veryfi API response dictionary
            
        Returns:
            Tax rate as percentage, or None if calculation not possible
        """
        if not response:
            return None
        
        tax, subtotal = self._extract_tax_from_structured_response(response)
        
        if subtotal and subtotal > 0 and tax is not None and tax >= 0:
            rate = (tax / subtotal) * 100
            logger.info(f"Calculated tax rate from structured data: {rate:.2f}% (tax={tax}, subtotal={subtotal})")
            return round(rate, 2)
        
        logger.debug(f"Could not calculate tax rate from structured data: tax={tax}, subtotal={subtotal}")
        return None
    
    def _extract_tax_rate_from_ocr_percentage(self, ocr_text: str) -> Optional[float]:
        """
        Extract tax rate percentage from OCR text.
        
        Args:
            ocr_text: OCR text from invoice
            
        Returns:
            Tax rate as percentage, or None if not found
        """
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
        
        return None
    
    def _extract_tax_rate_from_ocr_amounts(self, ocr_text: str) -> Optional[float]:
        """
        Calculate tax rate from tax and subtotal amounts in OCR text.
        
        Args:
            ocr_text: OCR text from invoice
            
        Returns:
            Tax rate as percentage, or None if calculation not possible
        """
        lines = ocr_text.split('\n')
        amount_pattern = r'\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
        
        tax_amount = self._extract_tax_amount_from_ocr(lines, amount_pattern)
        subtotal_amount = self._extract_subtotal_amount_from_ocr(lines, amount_pattern)
        
        # Calculate rate if both amounts found
        if subtotal_amount and subtotal_amount > 0 and tax_amount is not None and tax_amount >= 0:
            rate = (tax_amount / subtotal_amount) * 100
            logger.info(f"Calculated tax rate from OCR amounts: {rate:.2f}% (tax={tax_amount}, subtotal={subtotal_amount})")
            return round(rate, 2)
        
        logger.debug(f"Could not calculate tax rate from OCR: tax={tax_amount}, subtotal={subtotal_amount}")
        return None
    
    def _extract_subtotal_amount_from_ocr(self, lines: List[str], amount_pattern: str) -> Optional[float]:
        """
        Extract subtotal amount from OCR lines.
        
        Args:
            lines: OCR text lines
            amount_pattern: Regex pattern for amounts
            
        Returns:
            Subtotal amount or None
        """
        for line in lines:
            lower = line.lower().strip()
            
            # Look for subtotal (but not "subtotal tax")
            if 'subtotal' not in lower or 'tax' in lower:
                continue
            
            nums = re.findall(amount_pattern, line)
            if not nums:
                continue
            
            try:
                subtotal = float(nums[-1].replace(',', ''))
                logger.debug(f"Found subtotal amount: {subtotal}")
                return subtotal
            except (ValueError, IndexError):
                pass
        
        return None
    
    def _extract_tax_amount_from_ocr(self, lines: List[str], amount_pattern: str) -> Optional[float]:
        """
        Extract tax amount from OCR lines.
        
        Args:
            lines: OCR text lines
            amount_pattern: Regex pattern for amounts
            
        Returns:
            Tax amount or None
        """
        for line in lines:
            lower = line.lower().strip()
            
            # Look for tax (but exclude "carrier tax" which is a line item)
            if 'tax' not in lower or 'carrier' in lower or 'subtotal' in lower:
                continue
            
            # Skip if line has percentage (it's a rate, not amount)
            if '%' in line:
                continue
            
            nums = re.findall(amount_pattern, line)
            if not nums:
                continue
            
            try:
                tax_amount = float(nums[-1].replace(',', ''))
                if tax_amount > 0:
                    logger.debug(f"Found tax amount: {tax_amount}")
                    return tax_amount
            except (ValueError, IndexError):
                pass
        
        return None
    
    def extract_and_improve_line_items(
        self,
        line_items: List[Dict[str, Any]],
        response: Optional[Dict[str, Any]] = None,
        ocr_text: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Improve existing line items with better SKU extraction and description cleaning.
        
        **Tax Rate**: All items have tax_rate = 0.0 because Switch uses separate "Carrier Taxes"
        line items for regulatory pass-through fees rather than percentage-based taxes.
        
        Args:
            line_items: Existing line items from base extractor
            response: Veryfi API response (unused, kept for compatibility)
            ocr_text: OCR text (unused, kept for compatibility)
            
        Returns:
            Improved line items with extracted SKUs, cleaned descriptions, and tax_rate = 0.0
        """
        # Tax rate is always 0.0 - Switch uses separate "Carrier Taxes" line items
        # for regulatory pass-through fees rather than percentage-based taxes
        improved_items = []
        for idx, item in enumerate(line_items):
            improved_item = self._improve_single_line_item(item, idx + 1, 0.0)
            improved_items.append(improved_item)
        
        logger.info(f"Improved {len(improved_items)} line items with SKU extraction and tax rate")
        return improved_items
    
    def _improve_single_line_item(
        self,
        item: Dict[str, Any],
        item_index: int,
        tax_rate: float
    ) -> Dict[str, Any]:
        """
        Improve a single line item with SKU extraction, description cleaning, and tax rate.
        
        Args:
            item: Line item dictionary
            item_index: Index of item (for logging)
            tax_rate: Calculated invoice-level tax rate
            
        Returns:
            Improved line item dictionary
        """
        description = item.get('description', '')
        existing_sku = item.get('sku', '')
        
        # Determine if this is a tax or discount item
        is_tax = self._is_tax_line_item(item)
        is_discount = self._is_discount_line_item(item)
        is_tax_or_discount = is_tax or is_discount
        
        # Extract SKU (only for regular products)
        sku = self._extract_sku_for_item(description, existing_sku, is_tax_or_discount, item_index)
        
        # Clean description
        clean_desc = self._clean_line_item_description(description, item_index)
        
        # Determine tax rate for this item
        item_tax_rate = self._determine_item_tax_rate(is_tax, is_discount, tax_rate, item_index)
        
        # Ensure price consistency with total
        price = self._ensure_price_consistency(item.get('price', 0.0), item.get('total', 0.0), item_index)
            
            # Create improved item
        improved_item = {
                'sku': sku,
                'description': clean_desc,
                'quantity': item.get('quantity', 0.0),
                'price': price,
                'tax_rate': item_tax_rate,
                'total': item.get('total', 0.0)
            }
        
        # Log improvements
        self._log_item_improvements(sku, existing_sku, description, item_index)
        
        return improved_item
    
    def _extract_sku_for_item(
        self,
        description: str,
        existing_sku: str,
        is_tax_or_discount: bool,
        item_index: int
    ) -> str:
        """
        Extract SKU for a line item.
        
        Args:
            description: Item description
            existing_sku: Existing SKU if any
            is_tax_or_discount: Whether item is a tax or discount item
            item_index: Item index for logging
            
        Returns:
            Extracted SKU or empty string
        """
        if is_tax_or_discount:
            logger.debug(f"Item {item_index} is tax/discount, setting SKU to empty")
            return ''
        
        # Regular product - extract SKU (preserve existing if already extracted)
        if existing_sku:
            return existing_sku
        
        return self.extract_sku_from_description(description)
    
    def _clean_line_item_description(self, description: str, item_index: int) -> str:
        """
        Clean and format line item description for professional invoice output.
        
        This method produces descriptions that are:
        - Clear and readable
        - Free of technical codes/dates
        - Properly formatted with consistent separators
        - Business-appropriate
        
        Cleaning steps:
        1. Remove all parenthetical codes (dates, SKUs, technical references)
        2. Remove technical codes (alphanumeric ID-like strings)
        3. Replace pipe separators (|) with commas for consistent formatting
        4. Normalize whitespace and clean up formatting
        
        Args:
            description: Original description
            item_index: Item index for logging
            
        Returns:
            Cleaned and formatted description
        """
        if not description:
            return description
        
        clean_desc = description
        
        # Step 1: Extract bandwidth/speed specifications from parenthetical content before removing it
        # Patterns: "10 Gbps Fiber", "58 Gbps", "971 Gbps", "100 Mbps", etc.
        bandwidth_specs = []
        
        # Find all parenthetical content
        parenthetical_matches = re.finditer(r'\([^)]*\)', description)
        for match in parenthetical_matches:
            paren_content = match.group(0)  # Includes parentheses
            # Extract bandwidth specs from parenthetical content
            # Pattern: digits followed by Gbps/Mbps, optionally followed by "Fiber"
            bandwidth_patterns = [
                r'(\d+\s*Gbps\s*Fiber)',  # "10 Gbps Fiber"
                r'(\d+\s*Gbps)',           # "58 Gbps", "971 Gbps"
                r'(\d+\s*Mbps)',           # "100 Mbps"
            ]
            for pattern in bandwidth_patterns:
                spec_matches = re.finditer(pattern, paren_content, re.IGNORECASE)
                for spec_match in spec_matches:
                    spec = spec_match.group(1).strip()
                    if spec and spec not in bandwidth_specs:
                        bandwidth_specs.append(spec)
        
        # Also check for bandwidth specs outside parentheses (in case they're not in parentheses)
        for pattern in [r'(\d+\s*Gbps\s*Fiber)', r'(\d+\s*Gbps)', r'(\d+\s*Mbps)']:
            all_specs = re.finditer(pattern, description, re.IGNORECASE)
            for spec_match in all_specs:
                spec = spec_match.group(1).strip()
                # Only add if not already in the main description (avoid duplicates)
                if spec and spec not in bandwidth_specs:
                    # Check if it's already in the description (not in parentheses)
                    spec_in_main = re.search(rf'\b{re.escape(spec)}\b', clean_desc.replace('(', '').replace(')', ''), re.IGNORECASE)
                    if not spec_in_main:
                        bandwidth_specs.append(spec)
        
        # Step 2: Remove all parenthetical codes (dates, SKUs, technical references)
        # This includes patterns like (04/2023), (Intra-campus), (10/2023 Taxes), etc.
        clean_desc = re.sub(r'\([^)]*\)', '', clean_desc)
        
        # Step 2: Remove technical codes (alphanumeric ID-like strings)
        # Pattern: Technical codes that are clearly IDs, not real words
        # Examples: "wXv21fam", "HOEpyb", "YDDTJOrnuW", "3XMOyFdB", "dHrINDY", "14AIFIIqmG"
        # These typically:
        # - Start with numbers or have numbers in the middle
        # - Are 6-15 characters
        # - Appear after "to" or at the end of phrases
        # Remove patterns like "to wXv21fam" or "Fiber to dHrINDY"
        clean_desc = re.sub(r'\bto\s+[A-Za-z0-9]{6,15}\b', '', clean_desc, flags=re.IGNORECASE)
        # Remove technical codes that start with numbers (like "14AIFIIqmG", "3XMOyFdB")
        clean_desc = re.sub(r'\b\d+[A-Za-z0-9]{5,14}\b', '', clean_desc)
        # Remove codes with numbers in the middle (like "wXv21fam")
        clean_desc = re.sub(r'\b[A-Za-z]{2,}\d+[A-Za-z]{2,}\b', '', clean_desc)
        
        # Step 3: Replace pipe separators (|) with commas for consistent formatting
        # Handle both " | " and "|" patterns, normalize to ", "
        clean_desc = re.sub(r'\s*\|\s*', ', ', clean_desc)
        
        # Step 4: Normalize whitespace
        # Replace multiple spaces with single space, remove leading/trailing whitespace
        clean_desc = ' '.join(clean_desc.split()).strip()
        
        # Remove trailing commas and clean up comma spacing
        clean_desc = re.sub(r',\s*,', ',', clean_desc)  # Remove double commas
        clean_desc = re.sub(r',\s*$', '', clean_desc)  # Remove trailing comma
        clean_desc = re.sub(r'^\s*,\s*', '', clean_desc)  # Remove leading comma
        clean_desc = clean_desc.strip()
        
        # Step 5: Append extracted bandwidth specifications to the cleaned description
        # Only add specs that aren't already in the cleaned description
        for spec in bandwidth_specs:
            # Check if spec is already in the cleaned description
            spec_normalized = re.escape(spec)
            if not re.search(rf'\b{spec_normalized}\b', clean_desc, re.IGNORECASE):
                if clean_desc:
                    clean_desc = f"{clean_desc}, {spec}"
                else:
                    clean_desc = spec
        
        # Final cleanup: normalize whitespace again after adding specs
        clean_desc = ' '.join(clean_desc.split()).strip()
        clean_desc = re.sub(r',\s*,', ',', clean_desc)  # Remove double commas again
        
        # If description became empty after cleaning, use original
        if not clean_desc:
            logger.debug(f"Description became empty after cleaning, using original for item {item_index}")
            return description
        
        return clean_desc
    
    def _determine_item_tax_rate(self, is_tax: bool, is_discount: bool, tax_rate: float, item_index: int) -> float:
        """
        Determine tax rate for a line item.
        
        **Tax Rate Decision**: All items have tax_rate = 0.0 because Switch uses separate
        "Carrier Taxes" line items for regulatory pass-through fees rather than percentage-based taxes.
        
        Args:
            is_tax: Whether item is a tax item (unused, kept for compatibility)
            is_discount: Whether item is a discount item (unused, kept for compatibility)
            tax_rate: Calculated invoice-level tax rate (unused, kept for compatibility)
            item_index: Item index for logging (unused, kept for compatibility)
            
        Returns:
            Always returns 0.0, as taxes are represented by dedicated line items
        """
        return 0.0
    
    def _ensure_price_consistency(self, price: float, total: float, item_index: int) -> float:
        """
        Ensure price is consistent with total (both negative if total is negative).
        
        Args:
            price: Current price
            total: Item total
            item_index: Item index for logging
            
        Returns:
            Adjusted price if needed
        """
        if total < 0 and price > 0:
            adjusted_price = -abs(price)
            logger.debug(f"Item {item_index}: Made price negative ({adjusted_price}) to match negative total ({total})")
            return adjusted_price
        
        return price
    
    def _log_item_improvements(self, sku: str, existing_sku: str, description: str, item_index: int) -> None:
        """
        Log improvements made to a line item.
        
        Args:
            sku: Extracted SKU
            existing_sku: Previously existing SKU
            description: Item description
            item_index: Item index
        """
        if sku and not existing_sku:
            logger.debug(f"Item {item_index}: Extracted SKU '{sku}' from description")
        elif not sku and description:
            logger.debug(f"Item {item_index}: No SKU found in description: {description[:50]}")