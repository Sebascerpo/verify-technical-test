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
    
    # SKU Extraction Tests
    def test_extract_sku_uppercase(self):
        """Test SKU extraction with uppercase codes."""
        description = "Transport | 971 Gbps Fiber (X6HCHK1C) (10/2023)"
        sku = self.extractor.extract_sku_from_description(description)
        assert sku == "X6HCHK1C"
    
    def test_extract_sku_lowercase(self):
        """Test SKU extraction with lowercase codes."""
        description = "Transport | 71 Gbps Fiber to 04pBZ (a488ZH) (07/2023)"
        sku = self.extractor.extract_sku_from_description(description)
        assert sku == "a488ZH"
    
    def test_extract_sku_mixed_case(self):
        """Test SKU extraction with mixed case codes."""
        description = "Carrier Taxes for Transport (SNpTfT) (07/2023 Taxes) (07/2023)"
        sku = self.extractor.extract_sku_from_description(description)
        assert sku == "SNpTfT"
    
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
    
    def test_extract_sku_skip_pure_numbers(self):
        """Test that pure numeric codes are skipped."""
        description = "Service (12345) (10/2023)"
        sku = self.extractor.extract_sku_from_description(description)
        assert sku == ""
    
    def test_extract_sku_multiple_codes(self):
        """Test extraction when multiple codes exist - should return first valid."""
        description = "Transport (X6HCHK1C) (YSPG4VFH) (10/2023)"
        sku = self.extractor.extract_sku_from_description(description)
        assert sku == "X6HCHK1C"
    
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
        """Test with short valid SKU (3 chars)."""
        description = "Service (ABC) (10/2023)"
        sku = self.extractor.extract_sku_from_description(description)
        assert sku == "ABC"
    
    def test_extract_sku_long_code(self):
        """Test with long valid SKU (12 chars)."""
        description = "Service (ABCDEFGHIJKL) (10/2023)"
        sku = self.extractor.extract_sku_from_description(description)
        assert sku == "ABCDEFGHIJKL"
    
    # Tax Rate Calculation Tests
    def test_calculate_tax_rate_from_structured_data(self):
        """Test tax rate calculation from structured response."""
        response = {
            'tax': 850.0,
            'subtotal': 10000.0
        }
        rate = self.extractor.calculate_invoice_tax_rate(response=response)
        assert rate == 8.5
    
    def test_calculate_tax_rate_from_nested_response(self):
        """Test tax rate calculation from nested response structure."""
        response = {
            'tax': {'value': 425.0},
            'subtotal': {'value': 5000.0}
        }
        rate = self.extractor.calculate_invoice_tax_rate(response=response)
        assert rate == 8.5
    
    def test_calculate_tax_rate_from_ocr_percentage(self):
        """Test tax rate extraction from OCR text with percentage."""
        ocr_text = "Tax Rate: 8.5%\nSubtotal: $10,000.00"
        rate = self.extractor.calculate_invoice_tax_rate(ocr_text=ocr_text)
        assert rate == 8.5
    
    def test_calculate_tax_rate_from_ocr_amounts(self):
        """Test tax rate calculation from OCR tax and subtotal amounts."""
        ocr_text = """
        Subtotal: $10,000.00
        Tax: $850.00
        Total: $10,850.00
        """
        rate = self.extractor.calculate_invoice_tax_rate(ocr_text=ocr_text)
        assert rate == 8.5
    
    def test_calculate_tax_rate_ocr_various_formats(self):
        """Test tax rate extraction from various OCR formats."""
        test_cases = [
            ("Tax: 8.5%", 8.5),
            ("Tax Rate: 8.5%", 8.5),
            ("8.5% tax", 8.5),
            ("8.5% sales tax", 8.5),
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
        """Test that carrier tax line items are skipped."""
        ocr_text = """
        Carrier Taxes for Transport: $500.00
        Subtotal: $10,000.00
        Tax: $850.00
        """
        rate = self.extractor.calculate_invoice_tax_rate(ocr_text=ocr_text)
        # Should use "Tax: $850.00", not carrier tax
        assert rate == 8.5
    
    # Line Item Improvement Tests
    def test_improve_line_items_with_sku_and_tax(self):
        """Test complete line item improvement."""
        line_items = [{
            'sku': '',
            'description': 'Transport | 971 Gbps Fiber (X6HCHK1C) (10/2023)',
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
        assert improved[0]['sku'] == 'X6HCHK1C'
        assert improved[0]['tax_rate'] == 8.5
        assert improved[0]['description'] == 'Transport | 971 Gbps Fiber'
        assert improved[0]['quantity'] == 100.0
        assert improved[0]['price'] == 50.0
        assert improved[0]['total'] == 5000.0
    
    def test_improve_line_items_preserve_existing_sku(self):
        """Test that existing SKU is preserved."""
        line_items = [{
            'sku': 'EXISTING-SKU',
            'description': 'Transport (X6HCHK1C) (10/2023)',
            'quantity': 100.0,
            'price': 50.0,
            'tax_rate': 0.0,
            'total': 5000.0
        }]
        
        improved = self.extractor.extract_and_improve_line_items(
            line_items=line_items,
            response={'tax': 425.0, 'subtotal': 5000.0}
        )
        
        assert improved[0]['sku'] == 'EXISTING-SKU'
    
    def test_improve_line_items_clean_description(self):
        """Test that description is cleaned of parenthetical codes."""
        line_items = [{
            'sku': '',
            'description': 'Transport (X6HCHK1C) (10/2023) (Taxes)',
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
    
    def test_improve_line_items_multiple_items_same_tax_rate(self):
        """Test that all items get the same invoice-level tax rate."""
        line_items = [
            {
                'sku': '',
                'description': 'Item 1 (SKU1)',
                'quantity': 10.0,
                'price': 100.0,
                'tax_rate': 0.0,
                'total': 1000.0
            },
            {
                'sku': '',
                'description': 'Item 2 (SKU2)',
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
        assert improved[0]['tax_rate'] == 8.5
        assert improved[1]['tax_rate'] == 8.5
    
    def test_improve_line_items_empty_description_after_cleaning(self):
        """Test handling when description becomes empty after cleaning."""
        line_items = [{
            'sku': '',
            'description': '(X6HCHK1C) (10/2023)',
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
        assert improved[0]['description'] == '(X6HCHK1C) (10/2023)'
        assert improved[0]['sku'] == 'X6HCHK1C'
    
    def test_improve_line_items_no_tax_data(self):
        """Test improvement when no tax data is available."""
        line_items = [{
            'sku': '',
            'description': 'Transport (X6HCHK1C) (10/2023)',
            'quantity': 100.0,
            'price': 50.0,
            'tax_rate': 0.0,
            'total': 5000.0
        }]
        
        improved = self.extractor.extract_and_improve_line_items(
            line_items=line_items
        )
        
        assert improved[0]['sku'] == 'X6HCHK1C'
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
        
        # tax_total = 850, invoice_total = 15850, subtotal = 15000
        # rate = (850 / 15000) * 100 = 5.67%
        assert abs(rate - 5.67) < 0.01
    
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
        
        # Net tax = -1000 + 2000 = 1000
        # Invoice total = 10000 - 1000 + 2000 + 5000 = 16000
        # Subtotal = 16000 - 1000 = 15000
        # Rate = (1000 / 15000) * 100 = 6.67%
        response = {'total': 16000.0}
        
        rate = self.extractor.calculate_invoice_tax_rate(
            line_items=line_items,
            response=response
        )
        
        assert abs(rate - 6.67) < 0.01
    
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
        
        # Total tax = 300 + 200 = 500
        # Invoice total = 5000 + 300 + 200 + 3000 = 8500
        # Subtotal = 8500 - 500 = 8000
        # Rate = (500 / 8000) * 100 = 6.25%
        response = {'total': 8500.0}
        
        rate = self.extractor.calculate_invoice_tax_rate(
            line_items=line_items,
            response=response
        )
        
        assert abs(rate - 6.25) < 0.01
    
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
        
        # No response total, should calculate from line items
        # Invoice total = 10000 + 850 = 10850
        # Tax total = 850
        # Subtotal = 10850 - 850 = 10000
        # Rate = (850 / 10000) * 100 = 8.5%
        rate = self.extractor.calculate_invoice_tax_rate(
            line_items=line_items
        )
        
        assert abs(rate - 8.5) < 0.01
    
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
        """Test that tax rate is applied only to regular products, not taxes or discounts."""
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
        
        # Tax total = 850, invoice_total = 10350, subtotal = 9500
        # Rate = (850 / 9500) * 100 = 8.95%
        expected_rate = round((850.0 / 9500.0) * 100, 2)
        
        assert len(improved) == 3
        # Regular product should have tax rate
        assert abs(improved[0]['tax_rate'] - expected_rate) < 0.01
        # Tax item should have tax_rate = 0.0
        assert improved[1]['tax_rate'] == 0.0
        # Discount item should have tax_rate = 0.0
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
        """Test that SKU is extracted for regular products."""
        line_items = [
            {
                'description': 'Transport Service (PROD123)',
                'total': 1000.0
            }
        ]
        
        improved = self.extractor.extract_and_improve_line_items(
            line_items=line_items,
            response={'total': 1000.0}
        )
        
        assert improved[0]['sku'] == 'PROD123'
        assert improved[0]['tax_rate'] == 0.0  # No tax items, so rate is 0
    
    def test_sku_mixed_items(self):
        """Test SKU extraction with mix of tax, discount, and regular items."""
        line_items = [
            {
                'description': 'Carrier Taxes (TAX123)',
                'total': 850.0
            },
            {
                'description': 'Discount (DISC123)',
                'total': -100.0
            },
            {
                'description': 'Transport Service (PROD123)',
                'total': 1000.0
            }
        ]
        
        improved = self.extractor.extract_and_improve_line_items(
            line_items=line_items,
            response={'total': 1750.0}
        )
        
        assert improved[0]['sku'] == ''  # Tax item
        assert improved[1]['sku'] == ''  # Discount item
        assert improved[2]['sku'] == 'PROD123'  # Regular product
    
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

