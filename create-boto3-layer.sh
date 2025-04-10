#!/bin/bash

# Script to create a Lambda layer with the latest boto3 version

# Ensure the directory structure exists
mkdir -p layers/boto3/python

# Install boto3 directly to the layer directory
echo "Installing boto3 version 1.37.29 to Lambda layer..."
pip install boto3==1.37.29 -t layers/boto3/python/

# Remove unnecessary files to reduce layer size
echo "Cleaning up unnecessary files..."
find layers/boto3/python -name "*.dist-info" -type d -exec rm -rf {} +
find layers/boto3/python -name "*.egg-info" -type d -exec rm -rf {} +
find layers/boto3/python -name "__pycache__" -type d -exec rm -rf {} +

echo "Lambda layer created successfully at layers/boto3/"
echo "You can now deploy your CDK stack with the updated boto3 layer."
