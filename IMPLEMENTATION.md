# AI Instructions: Fix Invoice Data Extraction Issues

## Context
I have a Python invoice extraction system that processes PDF invoices using Veryfi's OCR API. The system extracts vendor info, invoice metadata, and line items into JSON format. However, there are two critical bugs in the line item extraction.

## Current Problems

### Problem 1: Tax Rate Always Returns 0.0
**Current Output:**
```json
{
  "sku": "",
  "description": "Transport | 971 Gbps Fiber (X6HCHK1C) (10/2023)",
  "tax_rate": 0.0,  // ❌ WRONG - Should be 8.5 or calculated value
  "total": 13046223.62
}
```

**Root Cause:**
- The code tries to extract tax rate PER LINE ITEM from OCR text
- But in B2B invoices (like Switch invoices), tax is calculated at the INVOICE LEVEL, not per item
- The tax rate should be: `(total_tax / subtotal) * 100`

**Where the Data Is:**
- In Veryfi API response: `response['tax']` and `response['subtotal']`
- In OCR text: Lines like "Tax: $425.00" and "Subtotal: $5,000.00"

### Problem 2: SKU Field Is Always Empty
**Current Output:**
```json
{
  "sku": "",  // ❌ WRONG - Should be "X6HCHK1C"
  "description": "Transport | 971 Gbps Fiber (X6HCHK1C) (10/2023)",
}
```

**Root Cause:**
- The code looks for patterns like "sku:", "item #:", "product code:"
- But in Switch invoices, SKUs are EMBEDDED IN DESCRIPTIONS as parenthetical codes
- Example: `"Transport (X6HCHK1C) (10/2023)"` - the SKU is `X6HCHK1C`, not `10/2023`

**Pattern to Extract:**
- SKU format: `(ALPHANUMERIC_CODE)` where length is 4-12 characters
- Must exclude: dates like `(10/2023)`, keywords like `(Taxes)`, pure numbers like `(12345)`

## What You Need to Do

### Task 1: Create a New Improved Extractor
Create a new file: `src/extractors/improved_line_item_extractor.py`

This file should contain a class with THREE methods:

#### Method 1: `extract_sku_from_description(description: str) -> str`
**Purpose:** Extract SKU codes from parentheses in descriptions

**Logic:**
1. Find all text in parentheses using regex: `\(([A-Z0-9]+)\)`
2. For each match:
   - Skip if it contains `/` or `-` (it's a date like "10/2023")
   - Skip if it's the word "Taxes" or "Tax"
   - Skip if it's purely numeric (like "12345")
   - Skip if length < 4 or > 12 characters
   - Return the first valid match
3. Return empty string if no valid SKU found

**Examples:**
- Input: `"Transport (X6HCHK1C) (10/2023)"` → Output: `"X6HCHK1C"`
- Input: `"Service (ymEw7J) (Taxes)"` → Output: `"ymEw7J"`
- Input: `"Service (10/2023) (Taxes)"` → Output: `""`
- Input: `"Service without codes"` → Output: `""`

#### Method 2: `calculate_invoice_tax_rate(response: Dict, ocr_text: str) -> float`
**Purpose:** Calculate invoice-level tax rate as a percentage

**Logic (try in order):**
1. **From structured data (preferred):**
   - Get `tax = response.get('tax', 0)` and `subtotal = response.get('subtotal', 0)`
   - If both > 0: `tax_rate = (tax / subtotal) * 100`
   - Return rounded to 2 decimals

2. **From OCR text (fallback):**
   - Look for explicit rate: regex `tax[:\s]+(\d+\.?\d*)%` (case-insensitive)
   - If found, return that percentage
   
3. **Calculate from OCR totals:**
   - Search for line containing "subtotal" → extract the dollar amount
   - Search for line containing "tax" (but not "carrier") → extract the dollar amount
   - If both found: `tax_rate = (tax / subtotal) * 100`
   
4. **Default:** Return `0.0` if nothing works

**Examples:**
- Input: `response = {'tax': 850, 'subtotal': 10000}` → Output: `8.5`
- Input: `ocr_text = "Tax (8.5%): $850"` → Output: `8.5`
- Input: `ocr_text = "Subtotal: $10,000\nTax: $850"` → Output: `8.5`

#### Method 3: `extract_and_improve_line_items(line_items: List[Dict], response: Dict, ocr_text: str) -> List[Dict]`
**Purpose:** Take existing line items and improve them with correct SKU and tax rate

**Logic:**
1. Calculate invoice-level tax rate using Method 2
2. For each line item:
   - Extract SKU from description using Method 1
   - Clean the description by removing all parenthetical codes: `re.sub(r'\([A-Z0-9]+\)', '', description)`
   - Keep all other fields (quantity, price, total) as-is
   - Set `tax_rate` to the calculated invoice-level rate
3. Return the improved list

**Example Transformation:**
```python
# Input
[{
  'sku': '',
  'description': 'Transport (X6HCHK1C) (10/2023)',
  'quantity': 100,
  'price': 50,
  'tax_rate': 0.0,
  'total': 5000
}]

# Output (with response = {'tax': 425, 'subtotal': 5000})
[{
  'sku': 'X6HCHK1C',
  'description': 'Transport',  # cleaned
  'quantity': 100,
  'price': 50,
  'tax_rate': 8.5,  # calculated
  'total': 5000
}]
```

### Task 2: Integrate Into Existing HybridExtractor
Modify the file: `src/extractors/hybrid_extractor.py`

**Changes needed:**

1. **Add import at top:**
```python
from .improved_line_item_extractor import ImprovedLineItemExtractor
```

2. **In `__init__` method, add:**
```python
self.improved_extractor = ImprovedLineItemExtractor()
```

3. **In `extract_all_fields` method, AFTER extracting line_items, add:**
```python
# Improve line items with better SKU and tax rate
if line_items:
    line_items = self.improved_extractor.extract_and_improve_line_items(
        line_items=line_items,
        response=response,
        ocr_text=ocr_text
    )
```

### Task 3: Create Tests
Create file: `tests/test_improved_extraction.py`

Write pytest tests for:
1. SKU extraction from various description formats
2. Tax rate calculation from structured data
3. Tax rate calculation from OCR text
4. Complete line item improvement

## Expected Results

### Before Fix:
```json
{
  "sku": "",
  "description": "Transport | 971 Gbps Fiber to wXv21fam (X6HCHK1C) (10/2023)",
  "quantity": 3372.59,
  "price": 3868.31,
  "tax_rate": 0.0,
  "total": 13046223.62
}
```

### After Fix:
```json
{
  "sku": "X6HCHK1C",
  "description": "Transport | 971 Gbps Fiber to wXv21fam",
  "quantity": 3372.59,
  "price": 3868.31,
  "tax_rate": 8.5,
  "total": 13046223.62
}
```

## Important Notes

1. **Don't modify existing extractors** - Create a NEW improved extractor that wraps/enhances them
2. **Tax rate is invoice-level** - Same rate applies to ALL line items in an invoice
3. **SKU priority** - Take the FIRST valid alphanumeric code, skip dates and keywords
4. **Clean descriptions** - Remove the parenthetical codes after extracting SKU
5. **Preserve other data** - Don't change quantity, price, or total values

## Files to Modify
1. **CREATE:** `src/extractors/improved_line_item_extractor.py` (new file)
2. **MODIFY:** `src/extractors/hybrid_extractor.py` (add 3 lines)
3. **CREATE:** `tests/test_improved_extraction.py` (new test file)

## Validation
After implementing, run:
```bash
pytest tests/test_improved_extraction.py -v
python main.py --file invoices/synth-switch_v5-7.pdf
```

Check that the output JSON has:
- Non-empty SKU fields (like "X6HCHK1C")
- Non-zero tax_rate fields (like 8.5)
- Cleaned descriptions without parenthetical codes

## Code Style Requirements
- Follow existing code style in the project
- Add proper docstrings (Google style)
- Add type hints for all parameters and returns
- Use the existing logger: `from ..core.logging_config import get_logger`
- Handle edge cases gracefully (missing data, malformed input)

## Success Criteria
✅ SKU field populated with correct codes from descriptions
✅ Tax rate calculated at invoice level and applied to all items
✅ Descriptions cleaned of parenthetical codes
✅ All tests passing
✅ Original functionality preserved (no breaking changes)