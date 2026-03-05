#!/bin/bash
# Run all tests for Lead Extractor

cd "$(dirname "$0")"

echo "🧪 Running Lead Extractor Tests"
echo "================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test results
PASSED=0
FAILED=0

# Function to run test suite
run_test() {
    local test_file=$1
    local test_name=$2
    
    echo -e "${YELLOW}Running: ${test_name}${NC}"
    python3 -m unittest "$test_file" -v 2>&1 | tee /tmp/test_output.log
    
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        echo -e "${GREEN}✅ ${test_name} PASSED${NC}"
        ((PASSED++))
    else
        echo -e "${RED}❌ ${test_name} FAILED${NC}"
        ((FAILED++))
    fi
    echo ""
}

# Run unit tests
echo "📦 Unit Tests"
echo "-------------"
run_test "tests.test_extractors" "Extractors Unit Tests"
run_test "tests.test_pdf_extraction" "PDF Extraction Tests"

# Run integration tests
echo "🔗 Integration Tests"
echo "-------------------"
run_test "tests.test_integration" "Integration Tests"

# Run E2E tests
echo "🎯 End-to-End Tests"
echo "------------------"
run_test "tests.test_e2e" "E2E Tests"
run_test "tests.test_search_and_save" "Search & Save Tests"

# Run browser automation tests (may require network)
echo "🌐 Browser Automation Tests"
echo "---------------------------"
run_test "tests.test_browser_automation" "Browser Automation Tests"

# Summary
echo "================================"
echo "📊 Test Summary"
echo "================================"
echo -e "${GREEN}Passed: ${PASSED}${NC}"
echo -e "${RED}Failed: ${FAILED}${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed${NC}"
    exit 1
fi

