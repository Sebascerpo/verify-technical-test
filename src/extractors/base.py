"""
Base extractor classes.

Provides abstract base classes for all extractors.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
import re
from ..config.patterns import get_patterns
from ..core.logging_config import get_logger


class BaseExtractor(ABC):
    """
    Abstract base class for all extractors.
    
    Provides common functionality and defines the interface.
    """
    
    def __init__(self):
        """Initialize base extractor with patterns."""
        self.patterns = get_patterns()
        self.logger = get_logger(self.__class__.__name__)
    
    @abstractmethod
    def extract_all_fields(
        self,
        ocr_text: Optional[str] = None,
        response: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extract all required fields.
        
        Args:
            ocr_text: Optional OCR text
            response: Optional API response
            
        Returns:
            Dictionary with extracted data
        """
        pass
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """
        Parse a date string into USA format (MM/DD/YYYY).
        
        **Field Assumption**: Dates are in MM/DD/YYYY format (USA format).
        
        **Reasoning**:
        - Invoices are from USA companies, so dates follow USA format
        - Veryfi API extracts date as "document issue/transaction date"
        - Reference: https://faq.veryfi.com/en/articles/5571268-document-data-extraction-fields-explained
        - Veryfi documentation indicates date field contains the document issue date
        
        **Supported Input Formats**:
        - MM/DD/YYYY, DD/MM/YYYY, YYYY/MM/DD
        - MM-DD-YYYY, DD-MM-YYYY, YYYY-MM-DD
        - Text formats: "January 15, 2024", "Jan 15, 2024"
        
        **Output Format**: MM/DD/YYYY (USA format)
        
        Args:
            date_str: Date string in various formats
            
        Returns:
            Date string in USA format (MM/DD/YYYY), or None if parsing fails
        """
        date_str = date_str.strip()
        
        # Try common formats
        formats = [
            '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d',
            '%m-%d-%Y', '%d-%m-%Y', '%Y-%m-%d',
            '%B %d, %Y', '%b %d, %Y',
            '%d %B %Y', '%d %b %Y',
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%m/%d/%Y')  # USA format: MM/DD/YYYY
            except ValueError:
                continue
        
        # Try to extract year-month-day from various patterns
        year_match = re.search(r'(\d{4})', date_str)
        
        if year_match:
            year = year_match.group(1)
            # Try to find month and day
            parts = re.findall(r'\d{1,2}', date_str)
            if len(parts) >= 3:
                try:
                    # Assume MM/DD/YYYY or DD/MM/YYYY
                    if len(parts[0]) == 4:  # YYYY/MM/DD
                        dt = datetime(int(parts[0]), int(parts[1]), int(parts[2]))
                    else:  # MM/DD/YYYY or DD/MM/YYYY
                        # Try both interpretations
                        try:
                            dt = datetime(int(parts[2]), int(parts[0]), int(parts[1]))
                        except ValueError:
                            dt = datetime(int(parts[2]), int(parts[1]), int(parts[0]))
                    return dt.strftime('%m/%d/%Y')  # USA format: MM/DD/YYYY
                except (ValueError, IndexError):
                    pass
        
        return None
    
    def _clean_vendor_name(self, vendor_name: str) -> str:
        """
        Clean and normalize vendor name professionally.
        
        **Field Assumption**: Vendor name includes company suffix (Ltd., Inc., LLC, etc.)
        and is extracted from "Please make payments to:" section or top of document.
        
        **Reasoning**:
        - Veryfi API extracts vendor information at document level
        - Vendor name typically appears in payment instructions section
        - Company suffixes (Ltd., Inc., LLC, Corp.) are legal identifiers and should be preserved
        - Reference: https://faq.veryfi.com/en/articles/5571268-document-data-extraction-fields-explained
        - Veryfi documentation indicates vendor.name field contains vendor information
        
        **Transformations**:
        - Preserves company suffixes (Ltd., Inc., LLC, Corp., Company, Co.)
        - Standardizes suffix capitalization (ltd → Ltd., inc → Inc.)
        - Handles domain-to-company name transformations (fb.com → Facebook, Inc.)
        - Proper capitalization of company names
        
        Args:
            vendor_name: Raw vendor name string from extraction
            
        Returns:
            Cleaned and normalized vendor name with proper formatting
        """
        if not vendor_name:
            return ''
        
        # Strip whitespace
        cleaned = vendor_name.strip()
        
        # Remove extra whitespace
        cleaned = ' '.join(cleaned.split())
        
        # Common domain-to-company transformations
        domain_transformations = {
            'fb.com': 'Facebook, Inc.',
            'facebook.com': 'Facebook, Inc.',
            'google.com': 'Google LLC',
            'amazon.com': 'Amazon.com, Inc.',
            'apple.com': 'Apple Inc.',
        }
        
        cleaned_lower = cleaned.lower()
        for domain, company_name in domain_transformations.items():
            if domain in cleaned_lower:
                return company_name
        
        # Ensure proper capitalization for company suffixes
        # Preserve existing suffixes
        suffix_patterns = [
            r'\b(Ltd\.?|Inc\.?|LLC|Corp\.?|Corporation|Company|Co\.?)\b',
        ]
        
        # Check if name already has a suffix
        has_suffix = False
        for pattern in suffix_patterns:
            if re.search(pattern, cleaned, re.IGNORECASE):
                has_suffix = True
                break
        
        # If no suffix and name looks like it should have one, don't add it
        # (we preserve what's there, just clean it)
        
        # Capitalize first letter of each word, but preserve existing capitalization
        # for company suffixes
        words = cleaned.split()
        if words:
            # Capitalize first word
            words[0] = words[0].capitalize()
            # Preserve suffix capitalization (Ltd., Inc., etc.)
            for i in range(1, len(words)):
                word_lower = words[i].lower()
                if word_lower in ['ltd.', 'ltd', 'inc.', 'inc', 'llc', 'corp.', 'corp', 'corporation', 'company', 'co.', 'co']:
                    # Keep suffix as-is or standardize
                    if word_lower in ['ltd.', 'ltd']:
                        words[i] = 'Ltd.'
                    elif word_lower in ['inc.', 'inc']:
                        words[i] = 'Inc.'
                    elif word_lower == 'llc':
                        words[i] = 'LLC'
                    elif word_lower in ['corp.', 'corp']:
                        words[i] = 'Corp.'
                    elif word_lower == 'corporation':
                        words[i] = 'Corporation'
                    elif word_lower in ['company', 'co.', 'co']:
                        words[i] = 'Company' if word_lower == 'company' else 'Co.'
                else:
                    # Capitalize other words
                    words[i] = words[i].capitalize()
        
        cleaned = ' '.join(words)
        
        return cleaned

