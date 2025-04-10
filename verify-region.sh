#!/bin/bash
set -e

# Colors for terminal output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}CDK Region Verification Script${NC}"
echo "---------------------------------------------------"

# Force region to us-west-2 in all environment variables
export AWS_REGION=us-west-2
export AWS_DEFAULT_REGION=us-west-2
export CDK_DEFAULT_REGION=us-west-2

echo -e "${YELLOW}Current AWS/CDK environment variables:${NC}"
echo "AWS_REGION=$AWS_REGION"
echo "AWS_DEFAULT_REGION=$AWS_DEFAULT_REGION"
echo "CDK_DEFAULT_REGION=$CDK_DEFAULT_REGION"
echo "CDK_DEFAULT_ACCOUNT=$CDK_DEFAULT_ACCOUNT"

# Verify AWS configuration
echo -e "\n${YELLOW}AWS Config Check:${NC}"
echo "aws configure get region: $(aws configure get region)"
aws configure list | grep region

# Clean any cached output
echo -e "\n${YELLOW}Cleaning CDK output cache...${NC}"
rm -rf cdk.out
rm -f cdk.context.json

# Get AWS account
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
echo -e "\n${YELLOW}Using AWS Account: ${AWS_ACCOUNT}, Region: ${AWS_REGION}${NC}"

# Just synth a single stack to verify region
echo -e "\n${YELLOW}Synthesizing first stack to verify region...${NC}"
npx cdk synth PodcastProcessorStorageStack --region ${AWS_REGION} > /dev/null

# Check manifest.json for region setting
echo -e "\n${YELLOW}Checking manifest.json for region settings:${NC}"
grep -A 2 "environment" cdk.out/manifest.json

echo -e "\n${GREEN}Region verification complete. Make sure the environment shows us-west-2!${NC}"
