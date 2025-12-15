"""
Regex pattern definitions.

Centralizes all regex patterns used for extraction.
"""

import re
from typing import List, Pattern, Optional


class PatternConfig:
    """
    Configuration for regex patterns.
    
    Compiles patterns once for performance.
    """
    
    def __init__(self):
        """Initialize and compile all patterns."""
        # Date patterns (compiled for performance)
        self.date_patterns = [
            re.compile(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}'),  # MM/DD/YYYY, DD/MM/YYYY
            re.compile(r'\d{4}[/-]\d{1,2}[/-]\d{1,2}'),    # YYYY/MM/DD
            re.compile(r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}'),  # Month DD, YYYY
        ]
        
        # Invoice number patterns (compiled)
        self.invoice_number_patterns = [
            re.compile(r'(?:invoice|inv|#)\s*:?\s*([A-Z0-9\-]+)', re.IGNORECASE),
            re.compile(r'invoice\s+number\s*:?\s*([A-Z0-9\-]+)', re.IGNORECASE),
            re.compile(r'#\s*([A-Z0-9\-]{4,})', re.IGNORECASE),
        ]
        
        # Price patterns (compiled) - updated to handle negative values
        self.price_pattern = re.compile(r'[-\+]?\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)')
        # Pattern to detect if price is negative (for discounts/credits)
        self.negative_price_pattern = re.compile(r'-\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)')
        self.tax_rate_pattern = re.compile(r'(\d+\.?\d*)\s*%')
        
        # SKU patterns (compiled)
        self.sku_patterns = [
            re.compile(r'sku\s*:?\s*([A-Z0-9\-]+)', re.IGNORECASE),
            re.compile(r'item\s*#\s*:?\s*([A-Z0-9\-]+)', re.IGNORECASE),
            re.compile(r'product\s*code\s*:?\s*([A-Z0-9\-]+)', re.IGNORECASE),
            # Enhanced patterns for codes at line start
            re.compile(r'^([A-Z0-9\-]{3,15})\s+', re.IGNORECASE),
            # Codes in parentheses (common product code format)
            re.compile(r'\(([A-Z0-9\-]{3,20})\)'),
        ]
        
        # Vendor patterns (compiled)
        self.vendor_patterns = [
            re.compile(r'(?:from|vendor|supplier)\s*:?\s*(.+?)(?:\n|$)', re.IGNORECASE | re.MULTILINE),
            re.compile(r'^([A-Z][A-Za-z\s&]+(?:Inc|LLC|Corp|Ltd|Company|Co)\.?)', re.MULTILINE),
        ]
        
        # Bill to patterns (compiled)
        self.bill_to_patterns = [
            re.compile(r'bill\s+to\s*:?\s*(.+?)(?:\n|$)', re.IGNORECASE | re.MULTILINE),
            re.compile(r'bill\s+to\s*:?\s*\n\s*([A-Z][A-Za-z\s&]+)', re.IGNORECASE | re.MULTILINE),
            re.compile(r'sold\s+to\s*:?\s*(.+?)(?:\n|$)', re.IGNORECASE | re.MULTILINE),
            re.compile(r'customer\s*:?\s*(.+?)(?:\n|$)', re.IGNORECASE | re.MULTILINE),
        ]
        
        # Address patterns (compiled)
        self.address_pattern = re.compile(
            r'(\d+\s+[A-Za-z0-9\s,]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr)[\s\S]{0,200}?(?:\d{5}(?:-\d{4})?))',
            re.IGNORECASE
        )
        
        # Date section pattern (compiled)
        self.date_section_pattern = re.compile(r'date\s*:?\s*([^\n]+)', re.IGNORECASE)
    
    def get_date_patterns(self) -> List[Pattern]:
        """Get compiled date patterns."""
        return self.date_patterns
    
    def get_invoice_number_patterns(self) -> List[Pattern]:
        """Get compiled invoice number patterns."""
        return self.invoice_number_patterns
    
    def get_price_pattern(self) -> Pattern:
        """Get compiled price pattern."""
        return self.price_pattern
    
    def get_negative_price_pattern(self) -> Pattern:
        """Get compiled negative price pattern."""
        return self.negative_price_pattern
    
    def get_tax_rate_pattern(self) -> Pattern:
        """Get compiled tax rate pattern."""
        return self.tax_rate_pattern
    
    def get_sku_patterns(self) -> List[Pattern]:
        """Get compiled SKU patterns."""
        return self.sku_patterns
    
    def get_vendor_patterns(self) -> List[Pattern]:
        """Get compiled vendor patterns."""
        return self.vendor_patterns
    
    def get_bill_to_patterns(self) -> List[Pattern]:
        """Get compiled bill to patterns."""
        return self.bill_to_patterns
    
    def get_address_pattern(self) -> Pattern:
        """Get compiled address pattern."""
        return self.address_pattern
    
    def get_date_section_pattern(self) -> Pattern:
        """Get compiled date section pattern."""
        return self.date_section_pattern


# Global pattern config instance
_patterns: Optional[PatternConfig] = None


def get_patterns() -> PatternConfig:
    """Get the global pattern configuration instance."""
    global _patterns
    if _patterns is None:
        _patterns = PatternConfig()
    return _patterns


def set_patterns(patterns: PatternConfig):
    """Set the global pattern configuration (useful for testing)."""
    global _patterns
    _patterns = patterns

