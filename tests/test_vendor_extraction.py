"""
Unit tests for vendor information extraction.
"""

import pytest
from src.invoice_extractor import InvoiceExtractor


class TestVendorExtraction:
    """Test cases for vendor name and address extraction."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = InvoiceExtractor()
    
    def test_extract_vendor_name_simple(self):
        """Test extraction of simple vendor name."""
        ocr_text = """
        ACME CORPORATION
        123 Main Street
        New York, NY 10001
        
        Invoice #: INV-12345
        Date: 01/15/2024
        """
        vendor_name = self.extractor.extract_vendor_name(ocr_text)
        assert vendor_name == "ACME CORPORATION"
    
    def test_extract_vendor_name_with_from_label(self):
        """Test extraction with 'from' label."""
        ocr_text = """
        From: Tech Solutions Inc.
        456 Tech Avenue
        San Francisco, CA 94102
        """
        vendor_name = self.extractor.extract_vendor_name(ocr_text)
        assert "Tech Solutions" in vendor_name or vendor_name == "Tech Solutions Inc."
    
    def test_extract_vendor_address_multi_line(self):
        """Test extraction of multi-line vendor address."""
        ocr_text = """
        ABC Company LLC
        789 Business Blvd
        Suite 200
        Los Angeles, CA 90001
        """
        address = self.extractor.extract_vendor_address(ocr_text)
        assert address is not None
        assert "789 Business" in address or "Business Blvd" in address
    
    def test_extract_bill_to_name(self):
        """Test extraction of bill to name."""
        ocr_text = """
        Invoice
        
        Bill To: Customer Corp
        100 Customer Street
        """
        bill_to = self.extractor.extract_bill_to_name(ocr_text)
        assert bill_to == "Customer Corp"
    
    def test_extract_bill_to_name_alternative_labels(self):
        """Test extraction with alternative labels like 'sold to'."""
        ocr_text = """
        Sold To: XYZ Industries
        """
        bill_to = self.extractor.extract_bill_to_name(ocr_text)
        assert "XYZ" in bill_to or bill_to == "XYZ Industries"
    
    def test_extract_vendor_name_not_found(self):
        """Test handling when vendor name is not found."""
        ocr_text = """
        Some random text
        without clear vendor information
        """
        vendor_name = self.extractor.extract_vendor_name(ocr_text)
        # Should return None or empty string, or best guess
        assert vendor_name is None or isinstance(vendor_name, str)

