# 🧪 Test Suite

## Running Tests

### Quick Run
```bash
./run_tests.sh
```

### Individual Test Suites
```bash
# Unit tests
python3 -m unittest tests.test_extractors -v
python3 -m unittest tests.test_pdf_extraction -v

# Integration tests
python3 -m unittest tests.test_integration -v

# E2E tests
python3 -m unittest tests.test_e2e -v
```

### All Tests
```bash
python3 -m unittest discover tests -v
```

## Test Coverage

### Unit Tests (`test_extractors.py`)
- ✅ Email extraction
- ✅ Phone extraction
- ✅ Name extraction
- ✅ Junk email filtering
- ✅ Date filtering (not extracted as phone)

### PDF Extraction Tests (`test_pdf_extraction.py`)
- ✅ PDF text extraction
- ✅ Lead extraction from PDF text
- ✅ Complete lead structure creation

### Integration Tests (`test_integration.py`)
- ✅ Example query extraction
- ✅ Multiple PDF text formats
- ✅ Real-world scenarios

### E2E Tests (`test_e2e.py`)
- ✅ Database save/retrieve
- ✅ Session tracking
- ✅ Complete extraction pipeline
- ✅ Lead structure validation

## Example Query Test

The integration tests use the example query:
```
"mike@yahoo.com + sbcglobal.net + Vendor invoice + bellsouth.net + pdf"
```

This tests extraction from vendor invoice PDFs with:
- Email addresses (mike@yahoo.com, jane.smith@bellsouth.net)
- Phone numbers
- Contact names
- Business information

## Test Results

After running tests, you'll see:
- ✅ Passed tests
- ❌ Failed tests
- Summary with pass/fail counts

## Adding New Tests

1. Create test file in `tests/` directory
2. Import unittest and your modules
3. Create test class inheriting from `unittest.TestCase`
4. Add test methods starting with `test_`
5. Run with `python3 -m unittest tests.your_test_file`

