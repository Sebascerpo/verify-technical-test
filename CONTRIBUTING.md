# Contributing / Development Notes

## Quick Start

1. **Set up environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure credentials**:
   Create `.env` file with your Veryfi API credentials.

3. **Run tests**:
   ```bash
   pytest tests/
   ```

4. **Run application**:
   ```bash
   python main.py
   ```

## Project Structure

```
verify/
├── src/
│   ├── core/              # Core infrastructure
│   │   ├── cache.py       # API response caching (cost reduction)
│   │   ├── exceptions.py  # Custom exception hierarchy
│   │   ├── interfaces.py  # Protocol definitions (IValidator)
│   │   ├── logging_config.py # Centralized logging
│   │   ├── results.py     # Result objects (functional error handling)
│   │   └── retry.py       # Retry logic & circuit breaker
│   ├── config/            # Configuration management
│   │   ├── patterns.py    # Pre-compiled regex patterns
│   │   └── settings.py    # Centralized settings
│   ├── clients/           # API clients
│   │   └── veryfi_client.py # Veryfi OCR API with caching & circuit breaker
│   ├── processors/        # Document processing
│   │   └── document_processor.py # PDF batch processing
│   ├── extractors/        # Modular extraction (SRP)
│   │   ├── base.py        # Base extractor class
│   │   ├── ocr_extractor.py # OCR text extraction
│   │   ├── structured_extractor.py # Structured data extraction
│   │   ├── line_item_extractor.py # Line items extraction
│   │   └── hybrid_extractor.py # Hybrid strategy orchestrator
│   ├── validators/        # Validation logic
│   │   ├── format_validator.py # Invoice format validation
│   │   └── data_validator.py # Data structure validation
│   ├── services/          # Business logic orchestration
│   │   ├── invoice_service.py # Invoice processing service
│   │   └── processing_service.py # Batch processing service
│   └── json_generator.py  # JSON output generation
├── tests/                 # Comprehensive test suite
│   ├── test_vendor_extraction.py
│   ├── test_line_item_extraction.py
│   ├── test_structured_extraction.py
│   ├── test_ocr_only.py
│   ├── test_integration.py
│   ├── test_services.py
│   ├── test_core_components.py
│   └── ...
├── invoices/             # Input PDF files
├── output/               # Generated JSON files
├── main.py              # Application entry point
└── requirements.txt      # Dependencies
```

## Architecture Overview

The system follows a modular, scalable architecture with clear separation of concerns:

- **Core Infrastructure** (`src/core/`): Caching, retry logic, circuit breaker, error handling, logging
- **Extractors** (`src/extractors/`): Modular extraction classes - use `HybridExtractor` for production, or individual extractors (`OCRExtractor`, `StructuredExtractor`, `LineItemExtractor`) for specific needs
- **Services** (`src/services/`): Business logic orchestration - `InvoiceService` for single invoices, `ProcessingService` for batch processing
- **Validators** (`src/validators/`): Format and data validation using the `IValidator` protocol
- **Clients** (`src/clients/`): API integration with caching and circuit breaker
- **Processors** (`src/processors/`): Document processing pipeline

## Adding New Extraction Patterns

To add new extraction patterns:

1. Add new regex patterns to `src/config/patterns.py` in the `PatternConfig` class
2. Use patterns in extractors (`src/extractors/ocr_extractor.py` or `src/extractors/structured_extractor.py`)
3. Add corresponding unit tests in `tests/`
4. Update documentation

## Testing

- Run all tests: `pytest tests/`
- Run with coverage: `pytest tests/ --cov=src`
- Run specific test: `pytest tests/test_vendor_extraction.py`

### Testing Exclusion Logic

The system includes format validation to exclude non-compatible invoice documents. This is a **required feature** of the technical test.

**Test the exclusion with the provided non-supported invoice**:
```bash
python main.py --file non-supported-invoice/fv089090060802125EB48112325.pdf
```

This should result in the document being excluded (no JSON output generated).

**Unit tests for exclusion**:
- `tests/test_integration.py::TestIntegration::test_exclusion_non_supported_invoice` - Tests exclusion logic
- `tests/test_integration.py::TestIntegration::test_exclusion_logic` - Tests various exclusion scenarios

**How exclusion works**:
1. `FormatValidator` checks if document matches invoice format (keywords, price patterns, length)
2. If validation fails, `InvoiceService` returns a failure result
3. No extraction or JSON generation occurs for excluded documents
4. Excluded documents are tracked separately in batch processing

## Code Style

- Follow PEP 8
- Use type hints
- Add docstrings to all functions
- Keep functions focused and reasonably sized

