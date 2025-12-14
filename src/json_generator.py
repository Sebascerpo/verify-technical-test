"""
JSON Generator Module

Converts extracted invoice data into properly formatted JSON output.
"""

import json
import logging
from typing import Dict, Any, List
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class JSONGenerator:
    """
    Generates JSON output from extracted invoice data.
    """
    
    @staticmethod
    def _safe_str(value: Any) -> str:
        """Safely convert value to string, handling None."""
        if value is None:
            return ''
        return str(value).strip()
    
    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        """Safely convert value to float, handling None and invalid values."""
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def generate_json(invoice_data: Dict[str, Any], filename: str = None) -> Dict[str, Any]:
        """
        Generate JSON structure from extracted invoice data.
        Properly handles None values and type conversion.
        
        Args:
            invoice_data: Dictionary containing extracted invoice fields
            filename: Optional filename for metadata
            
        Returns:
            Dictionary with properly structured JSON data
        """
        json_output = {
            'vendor_name': JSONGenerator._safe_str(invoice_data.get('vendor_name')),
            'vendor_address': JSONGenerator._safe_str(invoice_data.get('vendor_address')),
            'bill_to_name': JSONGenerator._safe_str(invoice_data.get('bill_to_name')),
            'invoice_number': JSONGenerator._safe_str(invoice_data.get('invoice_number')),
            'date': JSONGenerator._safe_str(invoice_data.get('date')),
            'line_items': []
        }
        
        # Process line items with proper type conversion
        line_items = invoice_data.get('line_items', [])
        if not isinstance(line_items, list):
            line_items = []
        
        for item in line_items:
            if not isinstance(item, dict):
                continue
            
            line_item = {
                'sku': JSONGenerator._safe_str(item.get('sku')),
                'description': JSONGenerator._safe_str(item.get('description')),
                'quantity': JSONGenerator._safe_float(item.get('quantity'), 0.0),
                'price': JSONGenerator._safe_float(item.get('price'), 0.0),
                'tax_rate': JSONGenerator._safe_float(item.get('tax_rate'), 0.0),
                'total': JSONGenerator._safe_float(item.get('total'), 0.0)
            }
            json_output['line_items'].append(line_item)
        
        # Add metadata if filename provided
        if filename:
            json_output['_metadata'] = {
                'source_file': filename,
                'extraction_timestamp': None  # Could add timestamp if needed
            }
        
        return json_output
    
    @staticmethod
    def save_json(data: Dict[str, Any], output_path: str, pretty: bool = True) -> None:
        """
        Save JSON data to a file.
        
        Args:
            data: Dictionary to save as JSON
            output_path: Path where JSON file should be saved
            pretty: If True, format JSON with indentation
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                if pretty:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                else:
                    json.dump(data, f, ensure_ascii=False)
            
            logger.info(f"Saved JSON output to {output_path}")
        except Exception as e:
            logger.error(f"Failed to save JSON to {output_path}: {str(e)}")
            raise
    
    @staticmethod
    def validate_json_structure(data: Dict[str, Any]) -> bool:
        """
        Validate that JSON structure matches expected schema.
        
        Args:
            data: Dictionary to validate
            
        Returns:
            True if structure is valid, False otherwise
        """
        required_fields = ['vendor_name', 'vendor_address', 'bill_to_name', 
                         'invoice_number', 'date', 'line_items']
        
        for field in required_fields:
            if field not in data:
                logger.warning(f"Missing required field: {field}")
                return False
        
        # Validate line items structure
        if not isinstance(data['line_items'], list):
            logger.warning("line_items must be a list")
            return False
        
        required_line_item_fields = ['sku', 'description', 'quantity', 
                                   'price', 'tax_rate', 'total']
        
        for i, item in enumerate(data['line_items']):
            if not isinstance(item, dict):
                logger.warning(f"Line item {i} is not a dictionary")
                return False
            
            for field in required_line_item_fields:
                if field not in item:
                    logger.warning(f"Line item {i} missing field: {field}")
                    return False
        
        return True
    
    @staticmethod
    def generate_combined_json(all_invoice_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a combined JSON file with all processed invoices.
        
        Args:
            all_invoice_data: List of invoice data dictionaries
            
        Returns:
            Dictionary containing all invoices in a structured format
        """
        return {
            'invoices': all_invoice_data,
            'total_invoices': len(all_invoice_data),
            'metadata': {
                'generated_at': None,  # Could add timestamp
                'version': '1.0'
            }
        }

