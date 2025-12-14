#!/usr/bin/env python3
"""
Main Application Entry Point

Command-line interface for processing invoices and extracting structured data.
"""

import argparse
import sys
import logging
from pathlib import Path
from typing import Optional

from src.document_processor import DocumentProcessor
from src.invoice_extractor import InvoiceExtractor
from src.json_generator import JSONGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def process_single_file(file_path: str, output_dir: str = "output") -> bool:
    """
    Process a single invoice file.
    
    Args:
        file_path: Path to the PDF file to process
        output_dir: Directory to save JSON output
        
    Returns:
        True if processing succeeded, False otherwise
    """
    try:
        # Initialize components
        processor = DocumentProcessor()
        extractor = InvoiceExtractor()
        json_gen = JSONGenerator()
        
        # Process document
        logger.info(f"Processing file: {file_path}")
        result = processor.process_document_by_path(file_path)
        
        if not result:
            logger.error(f"Failed to process {file_path}")
            return False
        
        response = result.get('response')
        ocr_text = result.get('ocr_text', '')
        filename = result['filename']
        
        # Validate invoice format (use OCR text for validation)
        if ocr_text and not extractor.is_valid_invoice_format(ocr_text):
            logger.warning(f"Document {filename} does not match expected invoice format. Skipping.")
            return False
        
        # Extract data using hybrid strategy (structured data first, OCR fallback)
        logger.info(f"Extracting data from {filename}")
        invoice_data = extractor.extract_all_fields(ocr_text=ocr_text, response=response)
        invoice_data['_source_file'] = filename
        
        # Generate JSON
        json_data = json_gen.generate_json(invoice_data, filename)
        
        # Validate JSON structure
        if not json_gen.validate_json_structure(json_data):
            logger.warning(f"Generated JSON for {filename} does not match expected structure")
        
        # Save JSON
        output_path = Path(output_dir) / f"{Path(filename).stem}.json"
        json_gen.save_json(json_data, str(output_path))
        
        logger.info(f"Successfully processed {filename}")
        return True
        
    except Exception as e:
        logger.error(f"Error processing {file_path}: {str(e)}", exc_info=True)
        return False


def process_all_invoices(invoices_dir: str = "invoices", output_dir: str = "output") -> None:
    """
    Process all invoices in the specified directory.
    
    Args:
        invoices_dir: Directory containing invoice PDFs
        output_dir: Directory to save JSON output files
    """
    try:
        # Initialize components
        processor = DocumentProcessor(invoices_dir)
        extractor = InvoiceExtractor()
        json_gen = JSONGenerator()
        
        # Process all documents
        logger.info(f"Processing all invoices from {invoices_dir}")
        results = processor.process_all_documents()
        
        if not results:
            logger.warning("No documents were successfully processed")
            return
        
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
                # Validate invoice format (use OCR text for validation)
                if ocr_text and not extractor.is_valid_invoice_format(ocr_text):
                    logger.warning(f"Document {filename} does not match expected invoice format. Excluding.")
                    excluded += 1
                    continue
                
                # Extract data using hybrid strategy (structured data first, OCR fallback)
                logger.info(f"Extracting data from {filename}")
                invoice_data = extractor.extract_all_fields(ocr_text=ocr_text, response=response)
                invoice_data['_source_file'] = filename
                
                # Generate JSON
                json_data = json_gen.generate_json(invoice_data, filename)
                
                # Validate JSON structure
                if not json_gen.validate_json_structure(json_data):
                    logger.warning(f"Generated JSON for {filename} does not match expected structure")
                
                # Save individual JSON file
                output_path = Path(output_dir) / f"{Path(filename).stem}.json"
                json_gen.save_json(json_data, str(output_path))
                
                all_invoice_data.append(json_data)
                successful += 1
                logger.info(f"✓ Successfully processed {filename}")
                
            except Exception as e:
                logger.error(f"Error processing {filename}: {str(e)}")
                failed += 1
        
        # Save combined JSON file
        if all_invoice_data:
            combined_data = json_gen.generate_combined_json(all_invoice_data)
            combined_output_path = Path(output_dir) / "all_invoices.json"
            json_gen.save_json(combined_data, str(combined_output_path))
        
        # Print summary
        print("\n" + "="*60)
        print("Processing Summary")
        print("="*60)
        print(f"Total documents: {len(results)}")
        print(f"Successfully processed: {successful}")
        print(f"Failed: {failed}")
        print(f"Excluded (wrong format): {excluded}")
        print(f"Output directory: {output_dir}")
        print("="*60)
        
    except Exception as e:
        logger.error(f"Error in batch processing: {str(e)}", exc_info=True)
        sys.exit(1)


def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(
        description='Extract structured data from invoice PDFs using Veryfi OCR API'
    )
    
    parser.add_argument(
        '--file',
        type=str,
        help='Process a specific PDF file'
    )
    
    parser.add_argument(
        '--invoices-dir',
        type=str,
        default='invoices',
        help='Directory containing invoice PDFs (default: invoices)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='output',
        help='Directory to save JSON output files (default: output)'
    )
    
    args = parser.parse_args()
    
    # Create output directory
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    
    try:
        if args.file:
            # Process single file
            success = process_single_file(args.file, args.output_dir)
            sys.exit(0 if success else 1)
        else:
            # Process all invoices
            process_all_invoices(args.invoices_dir, args.output_dir)
            sys.exit(0)
            
    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()

