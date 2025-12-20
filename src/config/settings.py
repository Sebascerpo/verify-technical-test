"""
Application settings and configuration.

Centralizes all configurable values.
"""

import os
from typing import Optional, Dict, Any
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings:
    """
    Application settings.
    
    Centralizes all configuration values.
    """
    
    def __init__(self):
        """Initialize settings from environment and defaults."""
        # API Settings
        self.veryfi_client_id = os.getenv('VERYFI_CLIENT_ID')
        self.veryfi_username = os.getenv('VERYFI_USERNAME')
        self.veryfi_api_key = os.getenv('VERYFI_API_KEY')
        
        # Processing Settings
        self.invoices_dir = os.getenv('INVOICES_DIR', 'invoices')
        self.output_dir = os.getenv('OUTPUT_DIR', 'output')
        
        # Validation Settings
        self.min_ocr_length = int(os.getenv('MIN_OCR_LENGTH', '100'))
        self.required_keywords_count = int(os.getenv('REQUIRED_KEYWORDS_COUNT', '2'))
        self.min_price_patterns = int(os.getenv('MIN_PRICE_PATTERNS', '1'))
        
        # Performance Settings
        self.enable_caching = os.getenv('ENABLE_CACHING', 'true').lower() == 'true'
        self.cache_ttl = int(os.getenv('CACHE_TTL', '3600'))  # 1 hour
        self.max_retries = int(os.getenv('MAX_RETRIES', '3'))
        self.retry_delay = float(os.getenv('RETRY_DELAY', '1.0'))
        
        # Logging Settings
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.log_format = os.getenv(
            'LOG_FORMAT',
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Feature Flags
        self.use_structured_data = os.getenv('USE_STRUCTURED_DATA', 'false').lower() == 'true'
        self.use_hybrid_extraction = os.getenv('USE_HYBRID_EXTRACTION', 'true').lower() == 'true'
        self.enable_parallel_processing = os.getenv('ENABLE_PARALLEL_PROCESSING', 'false').lower() == 'true'
        self.max_workers = int(os.getenv('MAX_WORKERS', '4'))
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: Configuration key (supports dot notation)
            default: Default value if not found
            
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self
        
        for k in keys:
            if hasattr(value, k):
                value = getattr(value, k)
            else:
                return default
        
        return value if value is not None else default
    
    def validate(self) -> bool:
        """
        Validate that required settings are present.
        
        Returns:
            True if valid, False otherwise
        """
        if not all([self.veryfi_client_id, self.veryfi_username, self.veryfi_api_key]):
            return False
        
        # Validate directories exist or can be created
        invoices_path = Path(self.invoices_dir)
        if not invoices_path.exists() and not invoices_path.parent.exists():
            return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary (excluding sensitive data)."""
        return {
            'invoices_dir': self.invoices_dir,
            'output_dir': self.output_dir,
            'min_ocr_length': self.min_ocr_length,
            'required_keywords_count': self.required_keywords_count,
            'min_price_patterns': self.min_price_patterns,
            'enable_caching': self.enable_caching,
            'cache_ttl': self.cache_ttl,
            'max_retries': self.max_retries,
            'retry_delay': self.retry_delay,
            'log_level': self.log_level,
            'use_structured_data': self.use_structured_data,
            'use_hybrid_extraction': self.use_hybrid_extraction,
            'enable_parallel_processing': self.enable_parallel_processing,
            'max_workers': self.max_workers,
        }


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def set_settings(settings: Settings):
    """Set the global settings instance (useful for testing)."""
    global _settings
    _settings = settings

