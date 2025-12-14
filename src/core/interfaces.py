"""
Interface definitions using Python Protocols.

Defines contracts for all major components to enable dependency injection
and improve testability.
"""

from typing import Protocol, Dict, List, Optional, Any
from abc import ABC, abstractmethod


class IExtractor(Protocol):
    """Protocol for data extractors."""
    
    def extract_all_fields(
        self, 
        ocr_text: Optional[str] = None, 
        response: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extract all required fields from OCR text and/or API response.
        
        Args:
            ocr_text: Optional OCR text
            response: Optional API response
            
        Returns:
            Dictionary with extracted invoice data
        """
        ...


class IValidator(Protocol):
    """Protocol for validators."""
    
    def validate(self, data: Any) -> bool:
        """
        Validate data.
        
        Args:
            data: Data to validate
            
        Returns:
            True if valid, False otherwise
        """
        ...


class IClient(Protocol):
    """Protocol for API clients."""
    
    def process_document(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Process a document through the API.
        
        Args:
            file_path: Path to document
            
        Returns:
            API response dictionary
        """
        ...


class IProcessor(Protocol):
    """Protocol for document processors."""
    
    def process_single_document(self, file_path: Any) -> Optional[Dict[str, Any]]:
        """
        Process a single document.
        
        Args:
            file_path: Path to document
            
        Returns:
            Processing result dictionary
        """
        ...
    
    def process_all_documents(self) -> List[Dict[str, Any]]:
        """
        Process all documents.
        
        Returns:
            List of processing results
        """
        ...


class IRepository(Protocol):
    """Protocol for data repositories."""
    
    def save(self, data: Dict[str, Any], path: str) -> bool:
        """
        Save data to storage.
        
        Args:
            data: Data to save
            path: Storage path
            
        Returns:
            True if successful
        """
        ...
    
    def load(self, path: str) -> Optional[Dict[str, Any]]:
        """
        Load data from storage.
        
        Args:
            path: Storage path
            
        Returns:
            Loaded data or None
        """
        ...


class IConfig(Protocol):
    """Protocol for configuration management."""
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.
        
        Args:
            key: Configuration key
            default: Default value
            
        Returns:
            Configuration value
        """
        ...

