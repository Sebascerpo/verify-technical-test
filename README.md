# Veryfi Data Annotations Engineer Technical Test

This project implements a Python-based system for extracting structured invoice data from PDF documents using Veryfi's OCR API.

## Overview

The system processes invoice PDFs, extracts key information **from the `ocr_text` field** of Veryfi's OCR API response (as required), and outputs structured JSON data containing:
- Vendor information (name, address)
- Invoice metadata (invoice number, date, bill to name)
- Line items (SKU, description, quantity, price, tax rate, total)

**Compliance**: The system fully complies with the technical test requirements:
- ✅ Uses Veryfi's Python API to get OCR output (`ocr_text`)
- ✅ Extracts all requested information from `ocr_text` 
- ✅ Outputs data in JSON format
- ✅ Supports documents with the same format while excluding others
- ✅ Tested with non-supported invoice (correctly excluded)

## Project Structure

```
verify/
├── src/
│   ├── veryfi_client.py      # Veryfi API integration
│   ├── document_processor.py # PDF processing
│   ├── invoice_extractor.py  # Data extraction logic
│   └── json_generator.py     # JSON output generation
├── tests/
│   ├── test_vendor_extraction.py
│   ├── test_line_item_extraction.py
│   └── test_integration.py
├── invoices/                 # Input PDF files
├── output/                   # Generated JSON files
├── main.py                   # Application entry point
├── requirements.txt          # Python dependencies
├── APPROACH.md              # Detailed approach documentation
├── BEST_PRACTICES.md        # Coding best practices
└── README.md                # This file
```

## Setup

1. **Install Dependencies**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure API Credentials**
   - Create a `.env` file in the project root
   - Add your Veryfi API credentials:
     ```
     VERYFI_CLIENT_ID=your_client_id
     VERYFI_USERNAME=your_username
     VERYFI_API_KEY=your_api_key
     ```
   - **Important**: Make sure you have an OCR API account (gray pane in hub), not a Receipts OCR account
   - Get your credentials from https://hub.veryfi.com/

3. **Run the Application**
   ```bash
   python main.py
   ```

## Usage

Process all invoices in the `invoices/` directory:
```bash
python main.py
```

Process a specific invoice:
```bash
python main.py --file invoices/synth-switch_v5-14.pdf
```

## Testing

Run all tests:
```bash
pytest tests/
```

Run with coverage:
```bash
pytest tests/ --cov=src --cov-report=html
```

## Extraction Approach

The system extracts all required fields **from the `ocr_text` field** as specified in the requirements, using:
- Advanced regex patterns for field detection
- NLP techniques for text parsing
- Table parsing for line items
- Format validation to exclude non-invoice documents

**Enhancement**: When available, the system also uses Veryfi's structured data fields to validate and enhance OCR text extraction results, improving accuracy while maintaining full compliance with the requirement to extract from `ocr_text`.

## Documentation

- **APPROACH.md**: Detailed explanation of the extraction approach, assumptions, and strategies
- **BEST_PRACTICES.md**: Coding best practices, code organization, and testing approach

## Exclusion Testing

The system includes format validation to exclude documents that don't match the expected invoice format. This has been tested with:
- ✅ Valid invoice documents (processed successfully)
- ✅ Non-supported invoice document (`non-supported-invoice/fv089090060802125EB48112325.pdf` - correctly excluded)

To test exclusion with your own document:
```bash
python main.py --file path/to/your/document.pdf
```

## Requirements

- Python 3.8+
- Veryfi OCR API account (https://hub.veryfi.com/signup/)
- API credentials (Client ID, Username, API Key)

## License

This project is part of a technical test for Veryfi's Data Annotations Engineer position.

