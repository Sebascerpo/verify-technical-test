"""
Invoice Service.

Orchestrates invoice processing business logic.
"""

from typing import Dict, Optional, Any
from pathlib import Path
from ..extractors.hybrid_extractor import HybridExtractor
from ..extractors.ocr_extractor import OCRExtractor
from ..validators.format_validator import FormatValidator
from ..validators.data_validator import DataValidator
from ..json_generator import JSONGenerator
from ..core.logging_config import get_logger
from ..core.results import Result
from ..config.settings import get_settings

logger = get_logger(__name__)
settings = get_settings()


class InvoiceService:
    """
    Service for processing invoices.
    
    Orchestrates extraction, validation, and JSON generation.
    """
    
    def __init__(
        self,
        extractor: Optional[HybridExtractor] = None,
        format_validator: Optional[FormatValidator] = None,
        data_validator: Optional[DataValidator] = None,
        json_generator: Optional[JSONGenerator] = None
    ):
        """
        Initialize invoice service.
        
        Args:
            extractor: Optional extractor instance (creates default if None)
            format_validator: Optional format validator (creates default if None)
            data_validator: Optional data validator (creates default if None)
            json_generator: Optional JSON generator (creates default if None)
        """
        # Use hybrid extraction if enabled, otherwise OCR only
        if settings.use_hybrid_extraction:
            self.extractor = extractor or HybridExtractor()
        else:
            self.extractor = extractor or OCRExtractor()
            logger.info("Using OCR-only extraction (hybrid disabled)")
        
        self.format_validator = format_validator or FormatValidator()
        self.data_validator = data_validator or DataValidator()
        self.json_generator = json_generator or JSONGenerator()
    
    def process_invoice(
        self,
        response: Optional[Dict[str, Any]] = None,
        ocr_text: Optional[str] = None,
        filename: Optional[str] = None
    ) -> Result[Dict[str, Any]]:
        """
        Process an invoice and extract all data.
        
        Args:
            response: Optional Veryfi API response
            ocr_text: Optional OCR text
            filename: Optional filename for metadata
            
        Returns:
            Result object with extracted invoice data
        """
        try:
            # Get OCR text if not provided
            if ocr_text is None and response:
                ocr_text = response.get('ocr_text', '')
            
            # Validate format if we have OCR text
            if ocr_text:
                if not self.format_validator.is_valid_invoice_format(ocr_text):
                    return Result.failure_result(
                        f"Document does not match expected invoice format"
                    )
                
                # Extract data
                invoice_data = self.extractor.extract_all_fields(
                    ocr_text=ocr_text,
                    response=response
                )
                
                if filename:
                    invoice_data['_source_file'] = filename
                
                # Generate JSON
                json_data = self.json_generator.generate_json(invoice_data, filename)
                
                # Validate JSON structure
                if not self.data_validator.validate(json_data):
                    logger.warning("Generated JSON does not match expected structure")
                    # Still return data, but log warning
                
                return Result.success_result(json_data)
                
        except Exception as e:
            logger.error(f"Error processing invoice: {str(e)}", exc_info=True)
            return Result.failure_result(f"Failed to process invoice: {str(e)}")
    
    def save_invoice(
        self,
        invoice_data: Dict[str, Any],
        output_path: str
    ) -> Result[bool]:
        """
        Save invoice data to JSON file.
        
        Args:
            invoice_data: Invoice data dictionary
            output_path: Path to save JSON file
            
        Returns:
            Result indicating success or failure
        """
        try:
            self.json_generator.save_json(invoice_data, output_path)
            return Result.success_result(True)
        except Exception as e:
            logger.error(f"Error saving invoice: {str(e)}", exc_info=True)
            return Result.failure_result(f"Failed to save invoice: {str(e)}")

