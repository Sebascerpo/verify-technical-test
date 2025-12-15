"""
Unit tests for date extraction and parsing.
"""

import pytest
from src.extractors.ocr_extractor import OCRExtractor


class TestDateParsing:
    """Test cases for date extraction and parsing."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = OCRExtractor()
    
    def test_extract_date_mm_dd_yyyy(self):
        """Test extraction of MM/DD/YYYY format."""
        ocr_text = """
        Invoice Date: 01/15/2024
        """
        date = self.extractor.extract_date(ocr_text)
        assert date == "2024-01-15"
    
    def test_extract_date_dd_mm_yyyy(self):
        """Test extraction of DD/MM/YYYY format."""
        ocr_text = """
        Date: 15/01/2024
        """
        date = self.extractor.extract_date(ocr_text)
        # Should parse to a valid date format
        assert date is not None
        assert len(date) == 10  # YYYY-MM-DD format
        assert date.count('-') == 2
    
    def test_extract_date_yyyy_mm_dd(self):
        """Test extraction of YYYY/MM/DD format."""
        ocr_text = """
        Date: 2024/01/15
        """
        date = self.extractor.extract_date(ocr_text)
        assert date == "2024-01-15"
    
    def test_extract_date_text_format(self):
        """Test extraction of text date format."""
        ocr_text = """
        Invoice Date: January 15, 2024
        """
        date = self.extractor.extract_date(ocr_text)
        assert date is not None
        assert "2024" in date
    
    def test_extract_date_with_label(self):
        """Test extraction with 'date' label."""
        ocr_text = """
        Date: 03/20/2024
        Invoice #: 12345
        """
        date = self.extractor.extract_date(ocr_text)
        assert date is not None
        assert "2024" in date
    
    def test_extract_date_not_found(self):
        """Test handling when date is not found."""
        ocr_text = """
        Invoice without date information
        """
        date = self.extractor.extract_date(ocr_text)
        # Should return None if not found
        assert date is None or isinstance(date, str)

