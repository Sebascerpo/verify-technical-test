"""
Unit tests for structured data extraction from Veryfi API response.
"""

import pytest
from src.extractors.structured_extractor import StructuredExtractor
from src.extractors.hybrid_extractor import HybridExtractor


class TestStructuredExtraction:
    """Test cases for structured data extraction from Veryfi API response."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.structured_extractor = StructuredExtractor()
        self.hybrid_extractor = HybridExtractor()
    
    def test_extract_all_fields_from_structured(self):
        """Test extraction of all fields from structured response."""
        from src.extractors.line_item_extractor import LineItemExtractor
        
        response = {
            'vendor': {
                'name': {'value': 'Test Vendor'},
                'address': {'value': '123 Test St'}
            },
            'bill_to': {
                'name': 'Test Customer'
            },
            'invoice_number': 'INV-001',
            'date': '2024-01-15 00:00:00',
            'line_items': [
                {
                    'description': 'Test Item',
                    'quantity': 1.0,
                    'price': 10.0,
                    'total': 10.0
                }
            ]
        }
        invoice_data = self.structured_extractor.extract_all_fields(response=response)
        # Extract line items separately (as StructuredExtractor does)
        line_item_extractor = LineItemExtractor()
        line_items = line_item_extractor.extract_from_structured(response)
        invoice_data['line_items'] = line_items
        
        assert invoice_data['vendor_name'] == 'Test Vendor'
        assert invoice_data['bill_to_name'] == 'Test Customer'
        assert invoice_data['invoice_number'] == 'INV-001'
        assert invoice_data['date'] == '2024-01-15'
        assert len(invoice_data['line_items']) == 1
    
    def test_hybrid_extraction_structured_first(self):
        """Test hybrid extraction uses structured data when available."""
        response = {
            'vendor': {
                'name': {'value': 'Structured Vendor Name'}
            },
            'ocr_text': 'Page 1 of 2\nSome other text'
        }
        invoice_data = self.hybrid_extractor.extract_all_fields(response=response)
        # Should use structured data, not OCR text
        assert invoice_data['vendor_name'] == 'Structured Vendor Name'
        assert invoice_data['vendor_name'] != 'Page 1 of 2'
    
    def test_hybrid_extraction_ocr_fallback(self):
        """Test hybrid extraction falls back to OCR when structured data missing."""
        response = {
            'ocr_text': """
            ACME Corporation
            123 Main Street
            Invoice #: INV-123
            Date: 01/15/2024
            Bill To: Customer Inc.
            Item Description Qty Price Total
            SKU-001 Product A 10 $5.00 $50.00
            Subtotal: $50.00
            Total: $50.00
            """
        }
        invoice_data = self.hybrid_extractor.extract_all_fields(response=response)
        # Should extract from OCR text
        assert invoice_data['vendor_name'] is not None or invoice_data['invoice_number'] is not None

