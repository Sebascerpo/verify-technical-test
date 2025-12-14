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

- `src/`: Source code modules
- `tests/`: Test suite
- `invoices/`: Input PDF files
- `output/`: Generated JSON files

## Adding New Extraction Patterns

To add new extraction patterns, modify `src/invoice_extractor.py`:

1. Add new regex patterns to the `__init__` method
2. Create or modify extraction methods
3. Add corresponding unit tests
4. Update documentation

## Testing

- Run all tests: `pytest tests/`
- Run with coverage: `pytest tests/ --cov=src`
- Run specific test: `pytest tests/test_vendor_extraction.py`

## Code Style

- Follow PEP 8
- Use type hints
- Add docstrings to all functions
- Keep functions focused and reasonably sized

