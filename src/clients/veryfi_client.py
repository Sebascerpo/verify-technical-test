"""
Veryfi API Client Module

Handles communication with Veryfi OCR API to extract text from PDF documents.
"""

import os
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
import veryfi
from ..core.logging_config import get_logger
from ..core.retry import retry
from ..core.exceptions import APIError

# Load environment variables
load_dotenv()

logger = get_logger(__name__)


class VeryfiClient:
    """
    Client for interacting with Veryfi OCR API.
    
    Handles API initialization, document processing, and error handling.
    """
    
    def __init__(self):
        """
        Initialize Veryfi client with credentials from environment variables.
        
        Raises:
            ValueError: If required credentials are missing
        """
        self.client_id = os.getenv('VERYFI_CLIENT_ID')
        self.username = os.getenv('VERYFI_USERNAME')
        self.api_key = os.getenv('VERYFI_API_KEY')
        
        if not all([self.client_id, self.username, self.api_key]):
            raise ValueError(
                "Missing Veryfi API credentials. Please set VERYFI_CLIENT_ID, "
                "VERYFI_USERNAME, and VERYFI_API_KEY in your .env file."
            )
        
        # Initialize Veryfi client
        self.client = veryfi.Client(
            client_id=self.client_id,
            client_secret=self.api_key,
            username=self.username,
            api_key=self.api_key
        )
        
        logger.info("Veryfi client initialized successfully")
    
    def process_document(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Process a PDF document through Veryfi OCR API.
        
        Args:
            file_path: Path to the PDF file to process
            
        Returns:
            Dictionary containing API response, or None if processing fails
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            Exception: For API-related errors
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            logger.info(f"Processing document: {file_path}")
            
            # Process document with Veryfi API (with retry)
            @retry(exceptions=(Exception,))
            def _process():
                return self.client.process_document(file_path)
            
            response = _process()
            
            logger.info(f"Successfully processed document: {file_path}")
            return response
            
        except Exception as e:
            logger.error(f"Error processing {file_path}: {str(e)}")
            raise
    
    def extract_ocr_text(self, file_path: str) -> Optional[str]:
        """
        Extract OCR text from a PDF document.
        
        Args:
            file_path: Path to the PDF file to process
            
        Returns:
            OCR text string, or None if extraction fails
        """
        try:
            response = self.process_document(file_path)
            
            if response and 'ocr_text' in response:
                ocr_text = response['ocr_text']
                logger.info(f"Extracted {len(ocr_text)} characters of OCR text")
                return ocr_text
            else:
                logger.warning(f"No ocr_text found in response for {file_path}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to extract OCR text from {file_path}: {str(e)}")
            return None
    
    def get_full_response(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Get full API response for a document.
        
        Args:
            file_path: Path to the PDF file to process
            
        Returns:
            Full API response dictionary
        """
        return self.process_document(file_path)
    
    @staticmethod
    def safe_get_nested_value(data: Dict[str, Any], *keys: str, default: Any = None) -> Any:
        """
        Safely extract nested values from a dictionary.
        Handles both 'field.value' and direct 'field' formats.
        
        Args:
            data: Dictionary to extract from
            *keys: Variable number of keys to traverse (e.g., 'vendor', 'name', 'value')
            default: Default value if key path doesn't exist
            
        Returns:
            Extracted value or default
        """
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        
        # If current is a dict with 'value' key, return that (Veryfi format)
        if isinstance(current, dict) and 'value' in current:
            return current['value']
        
        return current if current is not None else default
    
    @staticmethod
    def extract_structured_field(response: Dict[str, Any], field_path: List[str], 
                                alternative_paths: List[List[str]] = None) -> Optional[Any]:
        """
        Extract a field from Veryfi API response using multiple possible paths.
        
        Args:
            response: Full API response dictionary
            field_path: Primary path to try (e.g., ['vendor', 'name', 'value'])
            alternative_paths: Alternative paths to try if primary fails
            
        Returns:
            Extracted value or None
        """
        if not response:
            return None
        
        # Try primary path
        value = VeryfiClient.safe_get_nested_value(response, *field_path)
        if value:
            return value
        
        # Try alternative paths
        if alternative_paths:
            for alt_path in alternative_paths:
                value = VeryfiClient.safe_get_nested_value(response, *alt_path)
                if value:
                    return value
        
        return None

