# Lambda Layers

This directory contains Lambda layers used by the application. Lambda layers are a way to package and share common code and libraries between Lambda functions.

## boto3 Layer

The boto3 layer contains the AWS SDK for Python and is used by our Lambda functions to interact with AWS services. This layer is not committed to Git and must be created locally before deployment.

To create the boto3 layer:

```bash
./create-boto3-layer.sh
```

This script will:
1. Create the necessary directory structure
2. Install the boto3 library (version 1.37.29) directly into the layer directory
3. Clean up unnecessary files to reduce the layer size

The layer will be created at `layers/boto3/` and will be included in the deployed Lambda functions.

Note: This directory is excluded from Git in `.gitignore` because:
- The layer can be large and would bloat the repository
- It's better practice to generate dependencies during the build process
- The exact same layer can be reproduced using the script

## Adding New Layers

If you need to add more layers for other dependencies:

1. Create a new directory in this `layers/` directory
2. Add a script similar to `create-boto3-layer.sh` to generate the layer
3. Update the Lambda stack to include the new layer
4. Update the `.gitignore` file to exclude the layer directory if appropriate
