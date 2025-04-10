#!/bin/bash
set -e

# Colors for terminal output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}S3 Event Bridge Lambda Test${NC}"
echo "---------------------------------------------------"

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo -e "${RED}Error: Node.js is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo -e "${RED}Error: npm is not installed. Please install it first.${NC}"
    exit 1
fi

# Skip npm dependencies - we're using a standalone test with no external dependencies
echo -e "${YELLOW}Running simplified standalone test (no dependencies required)...${NC}"

# Run the test
echo -e "${YELLOW}Running S3 Event Bridge Lambda test...${NC}"
node test-s3-event-bridge.js

# Check the exit status
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}Test passed successfully!${NC}"
    echo -e "${YELLOW}You can now deploy the updated stack with ./deploy.sh${NC}"
    exit 0
else
    echo -e "\n${RED}Test failed!${NC}"
    echo -e "${YELLOW}Please fix the issues before deploying.${NC}"
    exit 1
fi
