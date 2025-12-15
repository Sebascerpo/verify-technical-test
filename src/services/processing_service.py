"""
Processing Service.

Orchestrates batch processing of multiple invoices.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
from ..processors.document_processor import DocumentProcessor
from ..services.invoice_service import InvoiceService
from ..json_generator import JSONGenerator
from ..core.logging_config import get_logger
from ..core.results import Result

logger = get_logger(__name__)


class ProcessingService:
    """
    Service for batch processing invoices.
    
    Handles multiple documents, tracks progress, and generates summaries.
    """
    
    def __init__(
        self,
        processor: Optional[DocumentProcessor] = None,
        invoice_service: Optional[InvoiceService] = None,
        json_generator: Optional[JSONGenerator] = None
    ):
        """
        Initialize processing service.
        
        Args:
            processor: Optional document processor (creates default if None)
            invoice_service: Optional invoice service (creates default if None)
            json_generator: Optional JSON generator (creates default if None)
        """
        self.processor = processor
        self.invoice_service = invoice_service or InvoiceService()
        self.json_generator = json_generator or JSONGenerator()
    
    def process_single_file(
        self,
        file_path: str,
        output_dir: str = "output"
    ) -> Result[bool]:
        """
        Process a single invoice file.
        
        Args:
            file_path: Path to PDF file
            output_dir: Output directory for JSON
            
        Returns:
            Result indicating success or failure
        """
        try:
            # Validate file path
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                error_msg = f"File not found: {file_path}"
                logger.error(error_msg)
                return Result.failure_result(error_msg)
            if not file_path_obj.is_file():
                error_msg = f"Path is not a file: {file_path}"
                logger.error(error_msg)
                return Result.failure_result(error_msg)
            
            logger.info(f"Processing file: {file_path}")
            
            if not self.processor:
                self.processor = DocumentProcessor()
            
            # Process document
            result = self.processor.process_document_by_path(file_path)
            
            if not result:
                error_msg = f"Failed to get API response for file: {file_path}"
                logger.error(error_msg)
                return Result.failure_result(error_msg)
            
            response = result.get('response')
            ocr_text = result.get('ocr_text', '')
            filename = result['filename']
            
            # Process invoice
            invoice_result = self.invoice_service.process_invoice(
                response=response,
                ocr_text=ocr_text,
                filename=filename
            )
            
            if invoice_result.is_failure():
                error = invoice_result.get_error()
                logger.warning(f"Failed to process invoice {filename}: {error}")
                return invoice_result
            
            invoice_data = invoice_result.get_value()
            
            # Save JSON
            output_path = Path(output_dir) / f"{Path(filename).stem}.json"
            save_result = self.invoice_service.save_invoice(
                invoice_data,
                str(output_path)
            )
            
            if save_result.is_failure():
                error = save_result.get_error()
                logger.error(f"Failed to save invoice data for {filename}: {error}")
                return save_result
            
            logger.info(f"✓ Successfully processed and saved {filename} to {output_path}")
            return Result.success_result(True)
                
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}", exc_info=True)
            return Result.failure_result(f"Error processing {file_path}: {str(e)}")
    
    def process_all_invoices(
        self,
        invoices_dir: str = "invoices",
        output_dir: str = "output"
    ) -> Dict[str, Any]:
        """
        Process all invoices in a directory.
        
        Args:
            invoices_dir: Directory containing invoice PDFs
            output_dir: Directory to save JSON output files
            
        Returns:
            Dictionary with processing summary
        """
        try:
            if not self.processor:
                self.processor = DocumentProcessor(invoices_dir)
                
                # Process all documents
                logger.info(f"Processing all invoices from {invoices_dir}")
                results = self.processor.process_all_documents()
                
                if not results:
                    logger.warning("No documents were successfully processed")
                    return {
                        'total': 0,
                        'successful': 0,
                        'failed': 0,
                        'excluded': 0
                    }
                
                # Process each document
                all_invoice_data = []
                successful = 0
                failed = 0
                excluded = 0
                
                for result in results:
                    filename = result['filename']
                    response = result.get('response')
                    ocr_text = result.get('ocr_text', '')
                    
                    try:
                        # Process invoice
                        invoice_result = self.invoice_service.process_invoice(
                            response=response,
                            ocr_text=ocr_text,
                            filename=filename
                        )
                        
                        if invoice_result.is_failure():
                            error = invoice_result.get_error()
                            if "does not match expected invoice format" in (error or ""):
                                excluded += 1
                                logger.info(f"✗ Excluded {filename} (format validation failed)")
                            else:
                                failed += 1
                                logger.warning(f"✗ Failed to process {filename}: {error}")
                            continue
                        
                        invoice_data = invoice_result.get_value()
                        
                        # Save individual JSON file
                        output_path = Path(output_dir) / f"{Path(filename).stem}.json"
                        save_result = self.invoice_service.save_invoice(
                            invoice_data,
                            str(output_path)
                        )
                        
                        if save_result.is_failure():
                            error = save_result.get_error()
                            logger.error(f"✗ Failed to save {filename}: {error}")
                            failed += 1
                            continue
                        
                        all_invoice_data.append(invoice_data)
                        successful += 1
                        logger.info(f"✓ Successfully processed {filename}")
                        
                    except Exception as e:
                        logger.error(f"✗ Unexpected error processing {filename}: {str(e)}", exc_info=True)
                        failed += 1
                
                # Save combined JSON file
                if all_invoice_data:
                    combined_data = self.json_generator.generate_combined_json(all_invoice_data)
                    combined_output_path = Path(output_dir) / "all_invoices.json"
                    self.json_generator.save_json(combined_data, str(combined_output_path))
                
                summary = {
                    'total': len(results),
                    'successful': successful,
                    'failed': failed,
                    'excluded': excluded,
                    'output_dir': output_dir
                }
                
                # Print summary
                print("\n" + "="*60)
                print("Processing Summary")
                print("="*60)
                print(f"Total documents: {summary['total']}")
                print(f"Successfully processed: {summary['successful']}")
                print(f"Failed: {summary['failed']}")
                print(f"Excluded (wrong format): {summary['excluded']}")
                print(f"Output directory: {summary['output_dir']}")
                print("="*60)
                
                return summary
                
        except Exception as e:
            logger.error(f"Error in batch processing: {str(e)}", exc_info=True)
            raise

