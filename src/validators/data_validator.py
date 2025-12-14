"""
Data Validator.

Validates extracted invoice data structure and content.
"""

from typing import Dict, Any, List
from ..core.logging_config import get_logger
from ..core.interfaces import IValidator

logger = get_logger(__name__)


class DataValidator(IValidator):
    """
    Validates extracted invoice data.
    
    Ensures data structure is correct and fields are valid.
    """
    
    def validate(self, data: Any) -> bool:
        """
        Validate invoice data structure.
        
        Args:
            data: Dictionary with extracted invoice data
            
        Returns:
            True if structure is valid, False otherwise
        """
        if not isinstance(data, dict):
            return False
        
        required_fields = [
            'vendor_name', 'vendor_address', 'bill_to_name',
            'invoice_number', 'date', 'line_items'
        ]
        
        for field in required_fields:
            if field not in data:
                logger.warning(f"Missing required field: {field}")
                return False
        
        # Validate line items structure
        if not isinstance(data['line_items'], list):
            logger.warning("line_items must be a list")
            return False
        
        required_line_item_fields = [
            'sku', 'description', 'quantity',
            'price', 'tax_rate', 'total'
        ]
        
        for i, item in enumerate(data['line_items']):
            if not isinstance(item, dict):
                logger.warning(f"Line item {i} is not a dictionary")
                return False
            
            for field in required_line_item_fields:
                if field not in item:
                    logger.warning(f"Line item {i} missing field: {field}")
                    return False
        
        return True
    
    def validate_line_item(self, item: Dict[str, Any]) -> bool:
        """
        Validate a single line item.
        
        Args:
            item: Line item dictionary
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['sku', 'description', 'quantity', 'price', 'tax_rate', 'total']
        
        for field in required_fields:
            if field not in item:
                return False
        
        # Validate types
        try:
            float(item['quantity'])
            float(item['price'])
            float(item['tax_rate'])
            float(item['total'])
        except (ValueError, TypeError):
            return False
        
        return True

