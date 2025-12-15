"""
Tests for service layer components.

Tests InvoiceService and ProcessingService business logic.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from src.services.invoice_service import InvoiceService
from src.services.processing_service import ProcessingService
from src.extractors.hybrid_extractor import HybridExtractor
from src.validators.format_validator import FormatValidator
from src.validators.data_validator import DataValidator
from src.json_generator import JSONGenerator
from src.core.results import Result


class TestInvoiceService:
    """Test InvoiceService business logic."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = InvoiceService()
    
    def test_process_invoice_success(self):
        """Test successful invoice processing."""
        ocr_text = """
        ACME CORPORATION
        Invoice #: INV-001
        Date: 01/15/2024
        Total: $100.00
        """
        
        result = self.service.process_invoice(ocr_text=ocr_text, filename="test.pdf")
        
        assert result.is_success()
        json_data = result.get_value()
        assert 'vendor_name' in json_data
        assert 'invoice_number' in json_data
        assert 'date' in json_data
    
    def test_process_invoice_invalid_format(self):
        """Test processing invalid format document."""
        ocr_text = "Just random text"
        
        result = self.service.process_invoice(ocr_text=ocr_text)
        
        assert result.is_failure()
        assert "does not match expected invoice format" in result.get_error()
    
    def test_save_invoice_success(self, tmp_path):
        """Test successful invoice save."""
        invoice_data = {
            'vendor_name': 'Test Vendor',
            'invoice_number': 'INV-001',
            'date': '2024-01-15',
            'line_items': []
        }
        
        output_path = tmp_path / "test.json"
        result = self.service.save_invoice(invoice_data, str(output_path))
        
        assert result.is_success()
        assert output_path.exists()
    
    def test_save_invoice_failure(self):
        """Test invoice save failure."""
        invoice_data = {'test': 'data'}
        invalid_path = "/invalid/path/test.json"
        
        result = self.service.save_invoice(invoice_data, invalid_path)
        
        assert result.is_failure()


class TestProcessingService:
    """Test ProcessingService batch processing."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = ProcessingService()
    
    def test_process_single_file_success(self, tmp_path):
        """Test successful single file processing."""
        # Mock processor
        mock_processor = Mock()
        mock_processor.process_document_by_path.return_value = {
            'filename': 'test.pdf',
            'response': {},
            'ocr_text': """
            ACME CORPORATION
            123 Main Street
            Invoice #: INV-001
            Date: 01/15/2024
            Bill To: Customer Inc.
            Item Description Qty Price Total
            SKU-001 Product A 10 $5.00 $50.00
            Subtotal: $50.00
            Tax: $4.00
            Total: $54.00
            """
        }
        
        service = ProcessingService(processor=mock_processor)
        output_dir = str(tmp_path)
        
        result = service.process_single_file('test.pdf', output_dir)
        
        assert result is not None
        assert result.is_success()
    
    @patch('src.services.processing_service.DocumentProcessor')
    def test_process_single_file_processing_failed(self, mock_processor_class):
        """Test single file processing failure."""
        mock_processor = Mock()
        mock_processor.process_document_by_path.return_value = None
        mock_processor_class.return_value = mock_processor
        
        service = ProcessingService(processor=mock_processor)
        
        result = service.process_single_file('test.pdf', 'output')
        
        assert result.is_failure()
        assert "Failed to process" in result.get_error()

