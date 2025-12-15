"""
Veryfi API Client Module

Handles communication with Veryfi OCR API to extract text from PDF documents.
"""

import os
import hashlib
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
import veryfi
from ..core.logging_config import get_logger
from ..core.retry import retry, CircuitBreaker
from ..core.exceptions import APIError
from ..core.cache import get_cache
from ..config.settings import get_settings

# Load environment variables
load_dotenv()

logger = get_logger(__name__)
settings = get_settings()


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
        
        # Initialize cache if enabled
        self.cache = get_cache() if settings.enable_caching else None
        
        # Initialize circuit breaker for API calls
        # Opens after 5 failures, recovers after 60 seconds
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=Exception
        )
        
        logger.info("Veryfi client initialized successfully")
        if settings.enable_caching:
            logger.info(f"Caching enabled with TTL: {settings.cache_ttl}s")
        logger.info("Circuit breaker enabled for API calls")
    
    def _get_file_hash(self, file_path: str) -> str:
        """
        Generate hash of file content for cache key.
        
        Args:
            file_path: Path to file
            
        Returns:
            SHA256 hash of file content
        """
        hash_sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def process_document(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Process a PDF document through Veryfi OCR API.
        Uses caching if enabled to reduce API calls and costs.
        
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
        
        # Check cache if enabled
        cache_key = None
        if self.cache and settings.enable_caching:
            cache_key = f"veryfi_response:{self._get_file_hash(file_path)}"
            cached_response = self.cache.get(cache_key)
            if cached_response is not None:
                logger.info(f"Cache hit for document: {file_path}")
                return cached_response
        
        try:
            logger.info(f"Processing document: {file_path}")
            
            # Process document with Veryfi API (with retry and circuit breaker)
            @retry(exceptions=(Exception,))
            def _process():
                # Use circuit breaker to protect against cascading failures
                return self.circuit_breaker.call(
                    lambda: self.client.process_document(file_path)
                )
            
            response = _process()
            
            # Cache response if enabled
            if self.cache and settings.enable_caching and cache_key and response:
                self.cache.set(cache_key, response)
                logger.debug(f"Cached response for document: {file_path}")
            
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

