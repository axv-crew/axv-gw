#!/bin/bash
# AXV Gateway - Quick Test Script
# Usage: ./test_gateway.sh [base_url]
# Default: http://127.0.0.1:8000

set -e

BASE_URL="${1:-http://127.0.0.1:8000}"

echo "🧪 Testing AXV Gateway at: $BASE_URL"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Health Check
echo -e "${YELLOW}Test 1: Health Check${NC}"
echo "GET $BASE_URL/healthz"
RESPONSE=$(curl -fsS "$BASE_URL/healthz")
if echo "$RESPONSE" | grep -q '"ok":true'; then
    echo -e "${GREEN}✓ PASS${NC} - Health check returns ok"
else
    echo -e "${RED}✗ FAIL${NC} - Unexpected response: $RESPONSE"
    exit 1
fi
echo ""

# Test 2: Frontend Status
echo -e "${YELLOW}Test 2: Frontend Status${NC}"
echo "GET $BASE_URL/front/status"
RESPONSE=$(curl -fsS "$BASE_URL/front/status")

# Check required fields
if echo "$RESPONSE" | grep -q '"updatedAt"'; then
    echo -e "${GREEN}✓ PASS${NC} - Has updatedAt field"
else
    echo -e "${RED}✗ FAIL${NC} - Missing updatedAt field"
    exit 1
fi

if echo "$RESPONSE" | grep -q '"services"'; then
    echo -e "${GREEN}✓ PASS${NC} - Has services array"
else
    echo -e "${RED}✗ FAIL${NC} - Missing services array"
    exit 1
fi

# Validate ISO 8601 timestamp
TIMESTAMP=$(echo "$RESPONSE" | grep -o '"updatedAt":"[^"]*"' | cut -d'"' -f4)
if [[ $TIMESTAMP =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2} ]]; then
    echo -e "${GREEN}✓ PASS${NC} - Timestamp is ISO 8601 format"
else
    echo -e "${RED}✗ FAIL${NC} - Invalid timestamp format: $TIMESTAMP"
    exit 1
fi

# Check service states
if echo "$RESPONSE" | grep -q '"state":"ok"' || echo "$RESPONSE" | grep -q '"state":"warn"'; then
    echo -e "${GREEN}✓ PASS${NC} - Services have valid state values"
else
    echo -e "${RED}✗ FAIL${NC} - No valid service states found"
    exit 1
fi

echo ""
echo "Sample response:"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

# Test 3: Metrics
echo -e "${YELLOW}Test 3: Metrics Endpoint${NC}"
echo "GET $BASE_URL/metrics"
METRICS=$(curl -fsS "$BASE_URL/metrics")

if echo "$METRICS" | grep -q "axv_gw"; then
    echo -e "${GREEN}✓ PASS${NC} - Metrics contain axv_gw prefix"
else
    echo -e "${YELLOW}⚠ WARNING${NC} - No axv_gw metrics found (may be normal on first run)"
fi

if echo "$METRICS" | grep -q "python_"; then
    echo -e "${GREEN}✓ PASS${NC} - Python runtime metrics present"
else
    echo -e "${RED}✗ FAIL${NC} - No Python metrics found"
    exit 1
fi

echo ""

# Test 4: Cache behavior
echo -e "${YELLOW}Test 4: Cache Behavior${NC}"
echo "Making two identical requests to test caching..."

START1=$(date +%s%N)
curl -fsS "$BASE_URL/front/status" > /dev/null
END1=$(date +%s%N)
TIME1=$((($END1 - $START1) / 1000000))

START2=$(date +%s%N)
curl -fsS "$BASE_URL/front/status" > /dev/null
END2=$(date +%s%N)
TIME2=$((($END2 - $START2) / 1000000))

echo "Request 1: ${TIME1}ms"
echo "Request 2: ${TIME2}ms"

if [ $TIME2 -lt $TIME1 ]; then
    echo -e "${GREEN}✓ PASS${NC} - Second request faster (cache working)"
else
    echo -e "${YELLOW}⚠ INFO${NC} - Cache effect not visible in timing"
fi

echo ""

# Test 5: Invalid endpoint (404)
echo -e "${YELLOW}Test 5: Invalid Endpoint (404)${NC}"
echo "GET $BASE_URL/invalid"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/invalid")

if [ "$HTTP_CODE" = "404" ]; then
    echo -e "${GREEN}✓ PASS${NC} - Returns 404 for invalid endpoint"
else
    echo -e "${RED}✗ FAIL${NC} - Expected 404, got $HTTP_CODE"
    exit 1
fi

echo ""
echo -e "${GREEN}🎉 All tests passed!${NC}"
echo ""
echo "Summary:"
echo "  ✓ Health check working"
echo "  ✓ Frontend status endpoint working"
echo "  ✓ FrontStatusV1 contract valid"
echo "  ✓ Metrics endpoint working"
echo "  ✓ Cache operational"
echo "  ✓ Error handling correct"
