"""
Document Processor Module

Handles batch processing of PDF documents and file management.
"""

import os
from typing import List, Dict, Optional, Any
from pathlib import Path
from ..clients.veryfi_client import VeryfiClient
from ..core.logging_config import get_logger

logger = get_logger(__name__)


class DocumentProcessor:
    """
    Processes PDF documents in batch using Veryfi OCR API.
    """
    
    def __init__(self, invoices_dir: str = "invoices"):
        """
        Initialize document processor.
        
        Args:
            invoices_dir: Directory containing invoice PDF files
        """
        self.invoices_dir = Path(invoices_dir)
        self.veryfi_client = VeryfiClient()
        
        if not self.invoices_dir.exists():
            raise FileNotFoundError(f"Invoices directory not found: {invoices_dir}")
    
    def get_pdf_files(self) -> List[Path]:
        """
        Get all PDF files from the invoices directory.
        
        Returns:
            List of Path objects for PDF files
        """
        pdf_files = list(self.invoices_dir.glob("*.pdf"))
        logger.info(f"Found {len(pdf_files)} PDF files in {self.invoices_dir}")
        return pdf_files
    
    def process_single_document(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Process a single PDF document and get full API response.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Dictionary with file path, filename, full API response, and OCR text, or None if processing fails
        """
        try:
            # Get full API response
            response = self.veryfi_client.get_full_response(str(file_path))
            
            if response:
                # Extract OCR text from response for fallback
                ocr_text = response.get('ocr_text', '')
                
                return {
                    'file_path': str(file_path),
                    'filename': file_path.name,
                    'response': response,
                    'ocr_text': ocr_text
                }
            else:
                logger.warning(f"Failed to get API response from {file_path}")
                return None
                
        except Exception as e:
            logger.error(f"Error processing {file_path}: {str(e)}")
            return None
    
    def process_all_documents(self) -> List[Dict[str, Any]]:
        """
        Process all PDF documents in the invoices directory.
        
        Returns:
            List of dictionaries containing file information, API response, and OCR text
        """
        pdf_files = self.get_pdf_files()
        results = []
        
        for pdf_file in pdf_files:
            logger.info(f"Processing: {pdf_file.name}")
            result = self.process_single_document(pdf_file)
            
            if result:
                results.append(result)
            else:
                logger.warning(f"Skipping {pdf_file.name} due to processing error")
        
        logger.info(f"Successfully processed {len(results)} out of {len(pdf_files)} documents")
        return results
    
    def process_document_by_path(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Process a specific document by file path.
        
        Args:
            file_path: Full path to the PDF file
            
        Returns:
            Dictionary with file path, filename, API response, and OCR text, or None if processing fails
        """
        file_path_obj = Path(file_path)
        
        if not file_path_obj.exists():
            logger.error(f"File not found: {file_path}")
            return None
        
        if not file_path_obj.suffix.lower() == '.pdf':
            logger.error(f"File is not a PDF: {file_path}")
            return None
        
        return self.process_single_document(file_path_obj)

