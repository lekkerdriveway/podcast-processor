#!/bin/bash
set -e

# Colors for terminal output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Podcast Processing Pipeline - Deployment Script${NC}"
echo "---------------------------------------------------"

# Force region to us-west-2 in all environment variables
export AWS_REGION=us-west-2
export AWS_DEFAULT_REGION=us-west-2
export CDK_DEFAULT_REGION=us-west-2

echo -e "${YELLOW}Forcing region to us-west-2 for all AWS operations${NC}"

# Clean any cached output
echo -e "${YELLOW}Cleaning CDK output cache...${NC}"
rm -rf cdk.out
rm -f cdk.context.json

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if CDK is installed
if ! command -v cdk &> /dev/null; then
    echo -e "${YELLOW}AWS CDK not found. Installing...${NC}"
    npm install -g aws-cdk
fi

# Install dependencies
echo -e "${YELLOW}Installing project dependencies...${NC}"
npm install

# Check if environment is bootstrapped
echo -e "${YELLOW}Checking if AWS environment is bootstrapped...${NC}"
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)

echo -e "${YELLOW}Using AWS Account: ${AWS_ACCOUNT}, Region: ${AWS_REGION}${NC}"

# Verify AWS configuration
echo -e "${YELLOW}AWS Config Check:${NC}"
aws configure get region
aws configure list | grep region

# Bootstrap CDK (if not already done)
echo -e "${YELLOW}Bootstrapping CDK environment...${NC}"
npx cdk bootstrap aws://${AWS_ACCOUNT}/${AWS_REGION} --region ${AWS_REGION} || {
    echo -e "${RED}Failed to bootstrap CDK environment.${NC}"
    exit 1
}

# Synthesize CloudFormation templates
echo -e "${YELLOW}Synthesizing CloudFormation templates...${NC}"
npx cdk synth --region ${AWS_REGION} || {
    echo -e "${RED}Failed to synthesize CloudFormation templates.${NC}"
    exit 1
}

# Deploy the stacks
echo -e "${YELLOW}Deploying CDK stacks...${NC}"
npx cdk deploy --all --region ${AWS_REGION} --require-approval never || {
    echo -e "${RED}Failed to deploy stacks.${NC}"
    exit 1
}

echo -e "\n${GREEN}Deployment completed successfully!${NC}"
echo -e "${YELLOW}------------------------------------${NC}"
echo -e "${YELLOW}Next steps:${NC}"
echo -e "1. Upload MP3 files to the input S3 bucket shown in the outputs above."
echo -e "2. Check the Step Functions console for workflow executions."
echo -e "3. Find generated markdown summaries in the output S3 bucket."
echo -e "${YELLOW}------------------------------------${NC}"
