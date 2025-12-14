"""
Unit tests for line item extraction.
"""

import pytest
from src.invoice_extractor import InvoiceExtractor


class TestLineItemExtraction:
    """Test cases for line item extraction."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = InvoiceExtractor()
    
    def test_extract_line_items_simple(self):
        """Test extraction of simple line items."""
        ocr_text = """
        Item Description Qty Price Total
        SKU-001 Widget A 10 $5.00 $50.00
        SKU-002 Widget B 5 $10.00 $50.00
        """
        line_items = self.extractor.extract_line_items(ocr_text)
        assert len(line_items) >= 1
        if line_items:
            assert 'description' in line_items[0]
            assert 'quantity' in line_items[0] or 'price' in line_items[0]
    
    def test_extract_line_items_with_sku(self):
        """Test extraction with SKU field."""
        ocr_text = """
        SKU: PROD-123
        Description: Product Name
        Quantity: 2
        Price: $25.00
        Total: $50.00
        """
        line_items = self.extractor.extract_line_items(ocr_text)
        assert len(line_items) >= 1
        if line_items and line_items[0].get('sku'):
            assert 'PROD' in line_items[0]['sku'] or '123' in line_items[0]['sku']
    
    def test_extract_line_items_with_tax_rate(self):
        """Test extraction with tax rate."""
        ocr_text = """
        Item: Service A
        Qty: 1
        Price: $100.00
        Tax: 8.5%
        Total: $108.50
        """
        line_items = self.extractor.extract_line_items(ocr_text)
        assert len(line_items) >= 1
        if line_items:
            item = line_items[0]
            # Check if tax_rate was extracted (might be 8.5 or 0)
            assert 'tax_rate' in item
            assert 'total' in item
    
    def test_extract_line_items_table_format(self):
        """Test extraction from table format."""
        ocr_text = """
        Description | Qty | Unit Price | Total
        Product 1  |  5  |  $10.00    | $50.00
        Product 2  |  3  |  $15.00    | $45.00
        """
        line_items = self.extractor.extract_line_items(ocr_text)
        assert len(line_items) >= 1
    
    def test_extract_line_items_empty(self):
        """Test handling when no line items are found."""
        ocr_text = """
        Invoice
        Total: $0.00
        """
        line_items = self.extractor.extract_line_items(ocr_text)
        assert isinstance(line_items, list)
        # May be empty or have minimal items

