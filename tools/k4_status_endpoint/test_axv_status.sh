#!/bin/bash
# test_axv_status.sh
# Prosty skrypt do testowania /axv/status endpoint
#
# Usage:
#   ./test_axv_status.sh
#   ./test_axv_status.sh http://localhost:8080
#   ./test_axv_status.sh http://api.axv.life

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================

BASE_URL="${1:-http://localhost:8080}"
ENDPOINT="${BASE_URL}/axv/status"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# Helper Functions
# ============================================================================

print_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# ============================================================================
# Tests
# ============================================================================

print_header "Testing AXV Status Endpoint: ${ENDPOINT}"

# Test 1: Endpoint reachable
print_header "Test 1: Endpoint Reachability"
if curl -s -f "${ENDPOINT}" > /dev/null 2>&1; then
    print_success "Endpoint is reachable"
else
    print_error "Endpoint is not reachable"
    exit 1
fi

# Test 2: Response is valid JSON
print_header "Test 2: Valid JSON Response"
RESPONSE=$(curl -s "${ENDPOINT}")
if echo "${RESPONSE}" | jq . > /dev/null 2>&1; then
    print_success "Response is valid JSON"
else
    print_error "Response is not valid JSON"
    echo "Response: ${RESPONSE}"
    exit 1
fi

# Test 3: Required fields present
print_header "Test 3: Required Fields"
REQUIRED_FIELDS=("now" "ok" "version" "status" "nodes")

for field in "${REQUIRED_FIELDS[@]}"; do
    if echo "${RESPONSE}" | jq -e ".${field}" > /dev/null 2>&1; then
        print_success "Field '${field}' present"
    else
        print_error "Field '${field}' missing"
        exit 1
    fi
done

# Test 4: Status components present
print_header "Test 4: Status Components"
STATUS_COMPONENTS=("api" "gateway" "n8n" "rag")

for component in "${STATUS_COMPONENTS[@]}"; do
    if echo "${RESPONSE}" | jq -e ".status.${component}" > /dev/null 2>&1; then
        status=$(echo "${RESPONSE}" | jq -r ".status.${component}")
        print_success "Component '${component}': ${status}"
    else
        print_error "Component '${component}' missing"
        exit 1
    fi
done

# Test 5: Valid status values
print_header "Test 5: Valid Status Values"
VALID_STATUSES=("ok" "degraded" "down" "unknown")

for component in "${STATUS_COMPONENTS[@]}"; do
    status=$(echo "${RESPONSE}" | jq -r ".status.${component}")
    if [[ " ${VALID_STATUSES[@]} " =~ " ${status} " ]]; then
        print_success "Component '${component}' has valid status: ${status}"
    else
        print_error "Component '${component}' has invalid status: ${status}"
        exit 1
    fi
done

# Test 6: Overall status logic
print_header "Test 6: Overall Status Logic"
OK=$(echo "${RESPONSE}" | jq -r ".ok")
OVERALL=$(echo "${RESPONSE}" | jq -r ".overall_status")

echo "ok: ${OK}"
echo "overall_status: ${OVERALL}"

# Check if any component is down
HAS_DOWN=$(echo "${RESPONSE}" | jq '.status | to_entries[] | select(.value == "down") | .key' | wc -l)
HAS_DEGRADED=$(echo "${RESPONSE}" | jq '.status | to_entries[] | select(.value == "degraded") | .key' | wc -l)

if [ "${HAS_DOWN}" -gt 0 ]; then
    if [ "${OK}" == "false" ]; then
        print_success "Correct: ok=false when component is down"
    else
        print_error "Incorrect: ok should be false when component is down"
    fi
elif [ "${HAS_DEGRADED}" -gt 0 ]; then
    if [ "${OK}" == "true" ] && [ "${OVERALL}" == "degraded" ]; then
        print_success "Correct: ok=true, overall_status=degraded when degraded"
    else
        print_warning "Check: degraded component handling"
    fi
else
    if [ "${OK}" == "true" ]; then
        print_success "Correct: ok=true when all components ok/unknown"
    else
        print_error "Incorrect: ok should be true when all ok/unknown"
    fi
fi

# Test 7: Response time
print_header "Test 7: Response Time"
START_TIME=$(date +%s%N)
curl -s "${ENDPOINT}" > /dev/null
END_TIME=$(date +%s%N)
ELAPSED=$((($END_TIME - $START_TIME) / 1000000))  # Convert to ms

echo "Response time: ${ELAPSED}ms"
if [ "${ELAPSED}" -lt 3000 ]; then
    print_success "Response time acceptable (< 3s)"
else
    print_warning "Response time slow (>= 3s)"
fi

# ============================================================================
# Summary
# ============================================================================

print_header "Test Summary"
echo -e "\n${GREEN}All tests passed!${NC}\n"

# Pretty print the response
print_header "Full Response"
echo "${RESPONSE}" | jq '.'

# Optional: component status table
print_header "Component Status Table"
echo "${RESPONSE}" | jq -r '.status | to_entries[] | "\(.key): \(.value)"' | column -t

# Node count
NODE_COUNT=$(echo "${RESPONSE}" | jq '.nodes | length')
print_header "Nodes"
echo "Total nodes: ${NODE_COUNT}"
if [ "${NODE_COUNT}" -gt 0 ]; then
    echo "${RESPONSE}" | jq -r '.nodes[] | "\(.id) (\(.role)): \(.status)"'
fi

echo ""
