"""
Unit tests for structured data extraction from Veryfi API response.
"""

import pytest
from src.invoice_extractor import InvoiceExtractor


class TestStructuredExtraction:
    """Test cases for structured data extraction from Veryfi API response."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = InvoiceExtractor()
    
    def test_extract_vendor_name_from_structured(self):
        """Test extraction of vendor name from structured response."""
        response = {
            'vendor': {
                'name': {
                    'value': 'Switch'
                }
            }
        }
        vendor_name = self.extractor.extract_vendor_name_from_structured(response)
        assert vendor_name == 'Switch'
    
    def test_extract_vendor_name_direct_format(self):
        """Test extraction when vendor.name is direct string."""
        response = {
            'vendor': {
                'name': 'Switch'
            }
        }
        vendor_name = self.extractor.extract_vendor_name_from_structured(response)
        assert vendor_name == 'Switch'
    
    def test_extract_vendor_address_from_structured(self):
        """Test extraction of vendor address from structured response."""
        response = {
            'vendor': {
                'address': {
                    'value': '123 Main St\nDallas, TX 75267'
                }
            }
        }
        address = self.extractor.extract_vendor_address_from_structured(response)
        assert 'Dallas' in address
        assert '75267' in address
    
    def test_extract_bill_to_name_from_structured(self):
        """Test extraction of bill to name from structured response."""
        response = {
            'bill_to': {
                'name': 'Micro Merchant Systems, Inc.'
            }
        }
        bill_to = self.extractor.extract_bill_to_name_from_structured(response)
        assert bill_to == 'Micro Merchant Systems, Inc.'
    
    def test_extract_invoice_number_from_structured(self):
        """Test extraction of invoice number from structured response."""
        response = {
            'invoice_number': '055205954'
        }
        invoice_num = self.extractor.extract_invoice_number_from_structured(response)
        assert invoice_num == '055205954'
    
    def test_extract_date_from_structured(self):
        """Test extraction and formatting of date from structured response."""
        response = {
            'date': '2024-09-06 00:00:00'
        }
        date = self.extractor.extract_date_from_structured(response)
        assert date == '2024-09-06'
    
    def test_extract_date_iso_format(self):
        """Test extraction when date is already in ISO format."""
        response = {
            'date': '2024-09-06'
        }
        date = self.extractor.extract_date_from_structured(response)
        assert date == '2024-09-06'
    
    def test_extract_line_items_from_structured(self):
        """Test extraction of line items from structured response."""
        response = {
            'line_items': [
                {
                    'sku': 'PROD-001',
                    'description': 'Test Product',
                    'quantity': 10.0,
                    'price': 25.50,
                    'tax_rate': 8.5,
                    'total': 255.00
                },
                {
                    'sku': None,
                    'description': 'Product Without SKU',
                    'quantity': 5.0,
                    'price': 15.00,
                    'tax_rate': 0.0,
                    'total': 75.00
                }
            ]
        }
        line_items = self.extractor.extract_line_items_from_structured(response)
        assert len(line_items) == 2
        assert line_items[0]['sku'] == 'PROD-001'
        assert line_items[0]['quantity'] == 10.0
        assert line_items[1]['sku'] == ''  # None should become empty string
    
    def test_extract_all_fields_from_structured(self):
        """Test extraction of all fields from structured response."""
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
        invoice_data = self.extractor.extract_all_fields_from_structured(response)
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
        invoice_data = self.extractor.extract_all_fields_hybrid(response)
        # Should use structured data, not OCR text
        assert invoice_data['vendor_name'] == 'Structured Vendor Name'
        assert invoice_data['vendor_name'] != 'Page 1 of 2'
    
    def test_hybrid_extraction_ocr_fallback(self):
        """Test hybrid extraction falls back to OCR when structured data missing."""
        response = {
            'ocr_text': 'ACME Corporation\n123 Main Street\nInvoice #: INV-123'
        }
        invoice_data = self.extractor.extract_all_fields_hybrid(response)
        # Should extract from OCR text
        assert invoice_data['vendor_name'] is not None or invoice_data['invoice_number'] is not None
    
    def test_extract_line_items_missing_fields(self):
        """Test line item extraction handles missing fields gracefully."""
        response = {
            'line_items': [
                {
                    'description': 'Item without SKU or tax',
                    'quantity': 1.0,
                    'price': 10.0,
                    'total': 10.0
                }
            ]
        }
        line_items = self.extractor.extract_line_items_from_structured(response)
        assert len(line_items) == 1
        assert line_items[0]['sku'] == ''
        assert line_items[0]['tax_rate'] == 0.0
        assert line_items[0]['description'] == 'Item without SKU or tax'

