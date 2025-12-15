"""
Unit tests for improved line item extraction.

Tests SKU extraction, tax rate calculation, and description cleaning.
"""

import pytest

# Note: This import may require the veryfi package to be installed
# due to package __init__ imports. For unit testing in isolation,
# consider mocking the veryfi import or testing with full environment.
try:
    from src.extractors.improved_line_item_extractor import ImprovedLineItemExtractor
except ImportError as e:
    # If import fails due to missing veryfi, skip tests with a clear message
    pytest.skip(f"Could not import ImprovedLineItemExtractor: {e}. "
                f"Tests require full environment with veryfi package installed.", allow_module_level=True)


class TestImprovedLineItemExtractor:
    """Test cases for improved line item extraction."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = ImprovedLineItemExtractor()
    
    # SKU Extraction Tests (Numeric Only)
    def test_extract_sku_numeric(self):
        """Test SKU extraction with numeric codes."""
        description = "Transport | 971 Gbps Fiber (8963157731) (10/2023)"
        sku = self.extractor.extract_sku_from_description(description)
        assert sku == "8963157731"
        assert sku.isdigit()
    
    def test_extract_sku_numeric_short(self):
        """Test SKU extraction with short numeric codes."""
        description = "Transport | 71 Gbps Fiber (12345) (07/2023)"
        sku = self.extractor.extract_sku_from_description(description)
        assert sku == "12345"
        assert sku.isdigit()
    
    def test_extract_sku_numeric_long(self):
        """Test SKU extraction with long numeric codes."""
        description = "Carrier Taxes for Transport (123456789012) (07/2023 Taxes) (07/2023)"
        sku = self.extractor.extract_sku_from_description(description)
        assert sku == "123456789012"
        assert sku.isdigit()
    
    def test_extract_sku_skip_dates(self):
        """Test that date patterns are skipped."""
        description = "Service (10/2023) (03/2024)"
        sku = self.extractor.extract_sku_from_description(description)
        assert sku == ""
    
    def test_extract_sku_skip_keywords(self):
        """Test that tax keywords are skipped."""
        description = "Service (Taxes) (10/2023)"
        sku = self.extractor.extract_sku_from_description(description)
        assert sku == ""
    
    def test_extract_sku_accepts_numeric(self):
        """Test that numeric codes are accepted (SKU is numeric only)."""
        description = "Service (12345) (10/2023)"
        sku = self.extractor.extract_sku_from_description(description)
        assert sku == "12345"  # Numeric SKUs are now accepted
        assert sku.isdigit()
    
    def test_extract_sku_multiple_codes(self):
        """Test extraction when multiple codes exist - should return first valid numeric."""
        description = "Transport (12345) (67890) (10/2023)"
        sku = self.extractor.extract_sku_from_description(description)
        assert sku == "12345"  # First numeric SKU
        assert sku.isdigit()
    
    def test_extract_sku_no_codes(self):
        """Test when no codes exist."""
        description = "Installation of Cross Connect | 395 Gbps Fiber"
        sku = self.extractor.extract_sku_from_description(description)
        assert sku == ""
    
    def test_extract_sku_empty_description(self):
        """Test with empty description."""
        sku = self.extractor.extract_sku_from_description("")
        assert sku == ""
    
    def test_extract_sku_short_code(self):
        """Test with short valid numeric SKU (3 digits)."""
        description = "Service (123) (10/2023)"
        sku = self.extractor.extract_sku_from_description(description)
        assert sku == "123"
        assert sku.isdigit()
    
    def test_extract_sku_long_code(self):
        """Test with long valid numeric SKU (12 digits)."""
        description = "Service (123456789012) (10/2023)"
        sku = self.extractor.extract_sku_from_description(description)
        assert sku == "123456789012"
        assert sku.isdigit()
    
    # Tax Rate Calculation Tests
    def test_calculate_tax_rate_from_structured_data(self):
        """Test tax rate calculation - always returns 0.0."""
        response = {
            'tax': 850.0,
            'subtotal': 10000.0
        }
        rate = self.extractor.calculate_invoice_tax_rate(response=response)
        assert rate == 0.0  # Always 0.0 - taxes are separate line items
    
    def test_calculate_tax_rate_from_nested_response(self):
        """Test tax rate calculation - always returns 0.0."""
        response = {
            'tax': {'value': 425.0},
            'subtotal': {'value': 5000.0}
        }
        rate = self.extractor.calculate_invoice_tax_rate(response=response)
        assert rate == 0.0  # Always 0.0 - taxes are separate line items
    
    def test_calculate_tax_rate_from_ocr_percentage(self):
        """Test tax rate calculation - always returns 0.0."""
        ocr_text = "Tax Rate: 8.5%\nSubtotal: $10,000.00"
        rate = self.extractor.calculate_invoice_tax_rate(ocr_text=ocr_text)
        assert rate == 0.0  # Always 0.0 - taxes are separate line items
    
    def test_calculate_tax_rate_from_ocr_amounts(self):
        """Test tax rate calculation - always returns 0.0."""
        ocr_text = """
        Subtotal: $10,000.00
        Tax: $850.00
        Total: $10,850.00
        """
        rate = self.extractor.calculate_invoice_tax_rate(ocr_text=ocr_text)
        assert rate == 0.0  # Always 0.0 - taxes are separate line items
    
    def test_calculate_tax_rate_ocr_various_formats(self):
        """Test tax rate calculation - always returns 0.0."""
        test_cases = [
            ("Tax: 8.5%", 0.0),
            ("Tax Rate: 8.5%", 0.0),
            ("8.5% tax", 0.0),
            ("8.5% sales tax", 0.0),
        ]
        for ocr_text, expected_rate in test_cases:
            rate = self.extractor.calculate_invoice_tax_rate(ocr_text=ocr_text)
            assert rate == expected_rate, f"Failed for: {ocr_text}"
    
    def test_calculate_tax_rate_no_data(self):
        """Test when no tax data is available."""
        rate = self.extractor.calculate_invoice_tax_rate()
        assert rate == 0.0
    
    def test_calculate_tax_rate_zero_subtotal(self):
        """Test when subtotal is zero."""
        response = {
            'tax': 100.0,
            'subtotal': 0.0
        }
        rate = self.extractor.calculate_invoice_tax_rate(response=response)
        assert rate == 0.0
    
    def test_calculate_tax_rate_negative_tax(self):
        """Test when tax is negative (should still calculate)."""
        response = {
            'tax': -100.0,
            'subtotal': 1000.0
        }
        rate = self.extractor.calculate_invoice_tax_rate(response=response)
        # Should return 0.0 because tax >= 0 check fails
        assert rate == 0.0
    
    def test_calculate_tax_rate_skip_carrier_tax(self):
        """Test tax rate calculation - always returns 0.0."""
        ocr_text = """
        Carrier Taxes for Transport: $500.00
        Subtotal: $10,000.00
        Tax: $850.00
        """
        rate = self.extractor.calculate_invoice_tax_rate(ocr_text=ocr_text)
        assert rate == 0.0  # Always 0.0 - taxes are separate line items
    
    # Line Item Improvement Tests
    def test_improve_line_items_with_sku_and_tax(self):
        """Test complete line item improvement."""
        line_items = [{
            'sku': '',
            'description': 'Transport | 971 Gbps Fiber (8963157731) (10/2023)',
            'quantity': 100.0,
            'price': 50.0,
            'tax_rate': 0.0,
            'total': 5000.0
        }]
        
        response = {
            'tax': 425.0,
            'subtotal': 5000.0
        }
        
        improved = self.extractor.extract_and_improve_line_items(
            line_items=line_items,
            response=response
        )
        
        assert len(improved) == 1
        assert improved[0]['sku'] == '8963157731'  # Numeric SKU
        assert improved[0]['sku'].isdigit()
        assert improved[0]['tax_rate'] == 0.0  # Always 0.0
        assert improved[0]['description'] == 'Transport | 971 Gbps Fiber'
        assert improved[0]['quantity'] == 100.0
        assert improved[0]['price'] == 50.0
        assert improved[0]['total'] == 5000.0
    
    def test_improve_line_items_preserve_existing_sku(self):
        """Test that existing SKU is preserved."""
        line_items = [{
            'sku': '12345',  # Existing numeric SKU
            'description': 'Transport (67890) (10/2023)',
            'quantity': 100.0,
            'price': 50.0,
            'tax_rate': 0.0,
            'total': 5000.0
        }]
        
        improved = self.extractor.extract_and_improve_line_items(
            line_items=line_items,
            response={'tax': 425.0, 'subtotal': 5000.0}
        )
        
        assert improved[0]['sku'] == '12345'  # Existing numeric SKU preserved
        assert improved[0]['sku'].isdigit()
    
    def test_improve_line_items_clean_description(self):
        """Test that description is cleaned of parenthetical codes."""
        line_items = [{
            'sku': '',
            'description': 'Transport (12345) (10/2023)',
            'quantity': 100.0,
            'price': 50.0,
            'tax_rate': 0.0,
            'total': 5000.0
        }]
        
        improved = self.extractor.extract_and_improve_line_items(
            line_items=line_items,
            response={'tax': 425.0, 'subtotal': 5000.0}
        )
        
        assert improved[0]['description'] == 'Transport'
        assert improved[0]['sku'] == '12345'  # Numeric SKU extracted
        assert improved[0]['sku'].isdigit()
    
    def test_improve_line_items_multiple_items_same_tax_rate(self):
        """Test that all items get the same invoice-level tax rate."""
        line_items = [
            {
                'sku': '',
                'description': 'Item 1 (11111)',
                'quantity': 10.0,
                'price': 100.0,
                'tax_rate': 0.0,
                'total': 1000.0
            },
            {
                'sku': '',
                'description': 'Item 2 (22222)',
                'quantity': 5.0,
                'price': 200.0,
                'tax_rate': 0.0,
                'total': 1000.0
            }
        ]
        
        response = {
            'tax': 170.0,
            'subtotal': 2000.0
        }
        
        improved = self.extractor.extract_and_improve_line_items(
            line_items=line_items,
            response=response
        )
        
        assert len(improved) == 2
        assert improved[0]['tax_rate'] == 0.0  # Always 0.0
        assert improved[1]['tax_rate'] == 0.0  # Always 0.0
    
    def test_improve_line_items_empty_description_after_cleaning(self):
        """Test handling when description becomes empty after cleaning."""
        line_items = [{
            'sku': '',
            'description': '(12345) (10/2023)',
            'quantity': 100.0,
            'price': 50.0,
            'tax_rate': 0.0,
            'total': 5000.0
        }]
        
        improved = self.extractor.extract_and_improve_line_items(
            line_items=line_items,
            response={'tax': 425.0, 'subtotal': 5000.0}
        )
        
        # Should preserve original description if cleaned version is empty
        assert improved[0]['description'] == '(12345) (10/2023)'
        assert improved[0]['sku'] == '12345'  # Numeric SKU extracted
        assert improved[0]['sku'].isdigit()
    
    def test_improve_line_items_no_tax_data(self):
        """Test improvement when no tax data is available."""
        line_items = [{
            'sku': '',
            'description': 'Transport (12345) (10/2023)',
            'quantity': 100.0,
            'price': 50.0,
            'tax_rate': 0.0,
            'total': 5000.0
        }]
        
        improved = self.extractor.extract_and_improve_line_items(
            line_items=line_items
        )
        
        assert improved[0]['sku'] == '12345'  # Numeric SKU extracted
        assert improved[0]['sku'].isdigit()
        assert improved[0]['tax_rate'] == 0.0
        assert improved[0]['description'] == 'Transport'
    
    # Tax Line Item Calculation Tests
    def test_calculate_tax_rate_from_tax_line_items(self):
        """Test tax rate calculation from tax line items."""
        line_items = [
            {
                'description': 'Transport | 971 Gbps Fiber',
                'total': 10000.0
            },
            {
                'description': 'Carrier Taxes for Transport',
                'total': 850.0
            },
            {
                'description': 'Another Service',
                'total': 5000.0
            }
        ]
        
        response = {'total': 15850.0}  # 10000 + 850 + 5000
        
        rate = self.extractor.calculate_invoice_tax_rate(
            line_items=line_items,
            response=response
        )
        
        assert rate == 0.0  # Always 0.0 - taxes are separate line items
    
    def test_calculate_tax_rate_with_negative_tax_item(self):
        """Test tax rate calculation with both positive and negative tax items."""
        line_items = [
            {
                'description': 'Transport Service',
                'total': 10000.0
            },
            {
                'description': 'Carrier Taxes for Transport',
                'total': -1000.0  # Negative tax (credit/refund)
            },
            {
                'description': 'Carrier Taxes for Transport',
                'total': 2000.0  # Positive tax
            },
            {
                'description': 'Another Service',
                'total': 5000.0
            }
        ]
        
        response = {'total': 16000.0}
        
        rate = self.extractor.calculate_invoice_tax_rate(
            line_items=line_items,
            response=response
        )
        
        assert rate == 0.0  # Always 0.0 - taxes are separate line items
    
    def test_calculate_tax_rate_from_multiple_tax_items(self):
        """Test tax rate calculation with multiple tax line items."""
        line_items = [
            {
                'description': 'Product 1',
                'total': 5000.0
            },
            {
                'description': 'Carrier Taxes for Transport',
                'total': 300.0
            },
            {
                'description': 'Sales Tax',
                'total': 200.0
            },
            {
                'description': 'Product 2',
                'total': 3000.0
            }
        ]
        
        response = {'total': 8500.0}
        
        rate = self.extractor.calculate_invoice_tax_rate(
            line_items=line_items,
            response=response
        )
        
        assert rate == 0.0  # Always 0.0 - taxes are separate line items
    
    def test_calculate_tax_rate_invoice_total_from_line_items(self):
        """Test tax rate calculation when invoice total is calculated from line items."""
        line_items = [
            {
                'description': 'Transport Service',
                'total': 10000.0
            },
            {
                'description': 'Carrier Taxes',
                'total': 850.0
            }
        ]
        
        rate = self.extractor.calculate_invoice_tax_rate(
            line_items=line_items
        )
        
        assert rate == 0.0  # Always 0.0 - taxes are separate line items
    
    def test_identify_tax_line_items(self):
        """Test identification of tax line items."""
        tax_item1 = {'description': 'Carrier Taxes for Transport'}
        tax_item2 = {'description': 'Sales Tax'}
        tax_item3 = {'description': 'Tax'}
        regular_item = {'description': 'Transport Service'}
        
        assert self.extractor._is_tax_line_item(tax_item1) is True
        assert self.extractor._is_tax_line_item(tax_item2) is True
        assert self.extractor._is_tax_line_item(tax_item3) is True
        assert self.extractor._is_tax_line_item(regular_item) is False
    
    def test_identify_discount_line_items(self):
        """Test identification of discount line items."""
        discount_item1 = {'description': 'Special Partnership Discount', 'total': -100.0}
        discount_item2 = {'description': 'Credit', 'total': 50.0}
        discount_item3 = {'description': 'Refund', 'total': -200.0}
        regular_item = {'description': 'Transport Service', 'total': 1000.0}
        
        assert self.extractor._is_discount_line_item(discount_item1) is True
        assert self.extractor._is_discount_line_item(discount_item2) is True
        assert self.extractor._is_discount_line_item(discount_item3) is True
        assert self.extractor._is_discount_line_item(regular_item) is False
    
    def test_apply_tax_rate_only_to_regular_items(self):
        """Test that tax rate is always 0.0 for all items."""
        line_items = [
            {
                'description': 'Transport Service (SKU1)',
                'total': 10000.0
            },
            {
                'description': 'Carrier Taxes for Transport',
                'total': 850.0
            },
            {
                'description': 'Special Partnership Discount',
                'total': -500.0
            }
        ]
        
        response = {'total': 10350.0}  # 10000 + 850 - 500
        
        improved = self.extractor.extract_and_improve_line_items(
            line_items=line_items,
            response=response
        )
        
        assert len(improved) == 3
        # All items should have tax_rate = 0.0 (taxes are separate line items)
        assert improved[0]['tax_rate'] == 0.0
        assert improved[1]['tax_rate'] == 0.0
        assert improved[2]['tax_rate'] == 0.0
    
    def test_get_invoice_total_from_response(self):
        """Test getting invoice total from response."""
        response = {'total': 15000.0}
        total = self.extractor._get_invoice_total(response=response)
        assert total == 15000.0
    
    def test_get_invoice_total_from_nested_response(self):
        """Test getting invoice total from nested response structure."""
        response = {'total': {'value': 15000.0}}
        total = self.extractor._get_invoice_total(response=response)
        assert total == 15000.0
    
    def test_get_invoice_total_from_ocr(self):
        """Test getting invoice total from OCR text."""
        ocr_text = """
        Subtotal: $10,000.00
        Tax: $850.00
        Total: $10,850.00
        """
        total = self.extractor._get_invoice_total(ocr_text=ocr_text)
        assert total == 10850.0
    
    def test_get_invoice_total_from_line_items(self):
        """Test calculating invoice total from line items."""
        line_items = [
            {'total': 5000.0},
            {'total': 3000.0},
            {'total': 2000.0}
        ]
        total = self.extractor._get_invoice_total(line_items=line_items)
        assert total == 10000.0
    
    # SKU Extraction Rules Tests
    def test_sku_empty_for_tax_items(self):
        """Test that SKU is empty for tax items."""
        line_items = [
            {
                'description': 'Carrier Taxes for Transport (SKU123)',
                'total': 850.0
            }
        ]
        
        improved = self.extractor.extract_and_improve_line_items(
            line_items=line_items,
            response={'total': 10000.0}
        )
        
        assert improved[0]['sku'] == ''
        assert improved[0]['tax_rate'] == 0.0
    
    def test_sku_empty_for_discount_items(self):
        """Test that SKU is empty for discount items."""
        line_items = [
            {
                'description': 'Special Partnership Discount (DISCOUNT123)',
                'total': -500.0
            }
        ]
        
        improved = self.extractor.extract_and_improve_line_items(
            line_items=line_items,
            response={'total': 10000.0}
        )
        
        assert improved[0]['sku'] == ''
        assert improved[0]['tax_rate'] == 0.0
    
    def test_sku_extracted_for_regular_products(self):
        """Test that SKU is extracted for regular products (numeric only)."""
        line_items = [
            {
                'description': 'Transport Service (12345)',
                'total': 1000.0
            }
        ]
        
        improved = self.extractor.extract_and_improve_line_items(
            line_items=line_items,
            response={'total': 1000.0}
        )
        
        assert improved[0]['sku'] == '12345'
        assert improved[0]['sku'].isdigit()  # Should be numeric only
        assert improved[0]['tax_rate'] == 0.0  # No tax items, so rate is 0
    
    def test_sku_mixed_items(self):
        """Test SKU extraction with mix of tax, discount, and regular items."""
        line_items = [
            {
                'description': 'Carrier Taxes (12345)',  # Tax item - SKU should be empty
                'total': 850.0
            },
            {
                'description': 'Discount (67890)',  # Discount item - SKU should be empty
                'total': -100.0
            },
            {
                'description': 'Transport Service (11111)',  # Regular product - SKU should be extracted
                'total': 1000.0
            }
        ]
        
        improved = self.extractor.extract_and_improve_line_items(
            line_items=line_items,
            response={'total': 1750.0}
        )
        
        assert improved[0]['sku'] == ''  # Tax item
        assert improved[1]['sku'] == ''  # Discount item
        assert improved[2]['sku'] == '11111'  # Regular product - numeric SKU
        assert improved[2]['sku'].isdigit()
    
    # Negative Price Handling Tests
    def test_negative_total_negative_price(self):
        """Test that negative total results in negative price."""
        line_items = [
            {
                'description': 'Carrier Taxes for Transport',
                'price': 1000.0,  # Positive initially
                'total': -5000.0  # Negative total
            }
        ]
        
        improved = self.extractor.extract_and_improve_line_items(
            line_items=line_items
        )
        
        assert improved[0]['total'] < 0
        assert improved[0]['price'] < 0  # Should be negative
        assert improved[0]['price'] == -1000.0
    
    def test_positive_total_keeps_price(self):
        """Test that positive total keeps price as-is."""
        line_items = [
            {
                'description': 'Transport Service',
                'price': 1000.0,
                'total': 5000.0
            }
        ]
        
        improved = self.extractor.extract_and_improve_line_items(
            line_items=line_items
        )
        
        assert improved[0]['total'] > 0
        assert improved[0]['price'] == 1000.0  # Should remain positive
    
    def test_already_negative_price_preserved(self):
        """Test that already negative price is preserved."""
        line_items = [
            {
                'description': 'Discount Item',
                'price': -500.0,  # Already negative
                'total': -2500.0
            }
        ]
        
        improved = self.extractor.extract_and_improve_line_items(
            line_items=line_items
        )
        
        assert improved[0]['total'] < 0
        assert improved[0]['price'] == -500.0  # Should remain negative
    
    # SKU Alphanumeric Validation Tests
    def test_sku_numeric_only(self):
        """Test that SKU contains only numeric characters (numbers only)."""
        line_items = [
            {
                'description': 'Product (12345)',
                'total': 1000.0
            },
            {
                'description': 'Product (67890)',
                'total': 2000.0
            },
            {
                'description': 'Product (111222)',
                'total': 3000.0
            }
        ]
        
        improved = self.extractor.extract_and_improve_line_items(
            line_items=line_items
        )
        
        for item in improved:
            if item['sku']:
                # SKU should contain only numeric characters
                assert item['sku'].isdigit(), f"SKU '{item['sku']}' is not numeric only"
                assert not any(c.isalpha() for c in item['sku']), f"SKU '{item['sku']}' contains letters"
    
    def test_sku_rejects_alphanumeric(self):
        """Test that SKU rejects alphanumeric codes (only numeric allowed)."""
        line_items = [
            {
                'description': 'Product (ABC123)',  # Alphanumeric - should be rejected
                'total': 1000.0
            },
            {
                'description': 'Product (123XYZ)',  # Alphanumeric - should be rejected
                'total': 2000.0
            },
            {
                'description': 'Product (1A2B3C)',  # Alphanumeric - should be rejected
                'total': 3000.0
            },
            {
                'description': 'Product (12345)',  # Numeric - should be accepted
                'total': 4000.0
            }
        ]
        
        improved = self.extractor.extract_and_improve_line_items(
            line_items=line_items
        )
        
        # Alphanumeric SKUs should be empty
        assert improved[0]['sku'] == ''  # ABC123 rejected
        assert improved[1]['sku'] == ''  # 123XYZ rejected
        assert improved[2]['sku'] == ''  # 1A2B3C rejected
        # Numeric SKU should be extracted
        assert improved[3]['sku'] == '12345'  # Numeric accepted
        assert improved[3]['sku'].isdigit()
    
    def test_sku_numeric_only_pattern(self):
        """Test that SKU pattern only matches numeric codes."""
        line_items = [
            {
                'description': 'Product (12345)',  # Numeric - should match
                'total': 1000.0
            },
            {
                'description': 'Product (67890)',  # Numeric - should match
                'total': 2000.0
            },
            {
                'description': 'Product (10/2023)',  # Date - should be rejected
                'total': 3000.0
            }
        ]
        
        improved = self.extractor.extract_and_improve_line_items(
            line_items=line_items
        )
        
        assert improved[0]['sku'] == '12345'
        assert improved[0]['sku'].isdigit()
        assert improved[1]['sku'] == '67890'
        assert improved[1]['sku'].isdigit()
        assert improved[2]['sku'] == ''  # Date rejected

