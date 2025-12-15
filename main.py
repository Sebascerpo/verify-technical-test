#!/usr/bin/env python3
"""
Main Application Entry Point

Command-line interface for processing invoices and extracting structured data.
"""

import argparse
import sys
from pathlib import Path

from src.services.processing_service import ProcessingService
from src.core.logging_config import setup_logging, get_logger
from src.config.settings import get_settings

# Configure logging from settings
settings = get_settings()
setup_logging(level=settings.log_level, format_string=settings.log_format)
logger = get_logger(__name__)


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
        # Create processing service
        processing_service = ProcessingService()
        
        # Process file
        result = processing_service.process_single_file(file_path, output_dir)
        
        if result.is_success():
            return True
        else:
            logger.error(f"Failed to process {file_path}: {result.get_error()}")
            return False
        
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
        # Create processing service
        processing_service = ProcessingService()
        
        # Process all invoices
        summary = processing_service.process_all_invoices(invoices_dir, output_dir)
        
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

