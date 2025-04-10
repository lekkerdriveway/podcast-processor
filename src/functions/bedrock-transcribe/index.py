import boto3
import json
import os
import uuid

# Print boto3 version for debugging
print(f"boto3 version: {boto3.__version__}")

def get_project_arn():
    """
    Get the data automation project ARN from environment variable
    """
    project_arn = os.environ.get('DATA_AUTOMATION_PROJECT_ARN')
    if not project_arn:
        raise ValueError("DATA_AUTOMATION_PROJECT_ARN environment variable must be set")
    
    print(f"Using data automation project ARN: {project_arn}")
    return project_arn

def get_profile_arn():
    """
    Dynamically construct the data automation profile ARN
    """
    # Get AWS region
    session = boto3.session.Session()
    region_name = session.region_name or 'us-west-2'
    
    # Get account ID using Lambda context or STS
    account_id = None
    try:
        # Try to extract account ID from Lambda context if available
        if 'context' in globals() and hasattr(globals()['context'], 'invoked_function_arn'):
            account_id = globals()['context'].invoked_function_arn.split(':')[4]
        else:
            # Fall back to STS if context is not available
            sts_client = boto3.client('sts')
            account_id = sts_client.get_caller_identity()['Account']
    except Exception as e:
        print(f"Error getting account ID: {str(e)}")
        # Provide a fallback mechanism for testing
        account_id = os.environ.get('AWS_ACCOUNT_ID', '123456789012')
    
    # Construct the profile ARN
    profile_arn = f'arn:aws:bedrock:{region_name}:{account_id}:data-automation-profile/us.data-automation-v1'
    
    print(f"Constructed profile ARN: {profile_arn}")
    print(f"Region: {region_name}, Account ID: {account_id}")
    return profile_arn

def handler(event, context):
    """
    Lambda function to invoke Bedrock Data Automation transcription
    """
    # Create separate clients for different API endpoints
    client_data_automation = boto3.client('bedrock-data-automation')
    client_runtime = boto3.client('bedrock-data-automation-runtime')
    
    try:
        # Get the project ARN from environment variable
        project_arn = get_project_arn()
        
        # Get the profile ARN for cross-region inference
        profile_arn = get_profile_arn()
        
        # Extract parameters from the Step Functions event
        model_id = event.get('ModelId', 'amazon.titan-tg1-large')
        input_uri = None
        
        # Handle either direct S3 URI or formatted string
        if 'bucket' in event and 'key' in event:
            # Get input bucket from environment variable or event
            input_bucket = os.environ.get('INPUT_BUCKET')
            if not input_bucket:
                # Fall back to event bucket if environment variable is not set
                input_bucket = event['bucket'].lower()
                print(f"Using bucket from event: {input_bucket}")
            else:
                print(f"Using environment variable for input bucket: {input_bucket}")
            
            # Clean the key to ensure it matches the expected pattern
            key = event['key'].replace(' ', '_')  # Replace spaces
            
            # URL encode special characters in the key
            import urllib.parse
            encoded_key = urllib.parse.quote(key)
            
            input_uri = f"s3://{input_bucket}/{encoded_key}"
            print(f"Constructed S3 URI: {input_uri}")
        elif 'S3Uri' in event.get('InputConfig', {}):
            # If S3Uri is provided directly, check if we need to redirect to the correct bucket
            s3_uri = event['InputConfig']['S3Uri']
            input_bucket = os.environ.get('INPUT_BUCKET')
            
            if input_bucket and input_bucket not in s3_uri:
                # Extract just the filename from the URI
                key = s3_uri.split('/')[-1]
                input_uri = f"s3://{input_bucket}/{key}"
                print(f"Redirected S3 URI to correct input bucket: {input_uri}")
            else:
                input_uri = s3_uri
        else:
            raise ValueError("No valid S3 URI found in event")
        
        # Prepare output bucket from environment or event
        output_bucket = os.environ.get('TRANSCRIPTS_BUCKET')
        if not output_bucket:
            raise ValueError("TRANSCRIPTS_BUCKET environment variable is not set")
        
        # Format output bucket name to ensure it's valid
        output_bucket = output_bucket.lower()
        output_uri = f"s3://{output_bucket}/transcripts/"
        print(f"Output S3 URI: {output_uri}")
            
        # Generate a unique client token for idempotency
        client_token = str(uuid.uuid4())
        
        print(f"Invoking Data Automation Async for file {input_uri}")
        
        # Prepare request parameters
        request_params = {
            "clientToken": client_token,
            "dataAutomationProfileArn": profile_arn,  # Required parameter for cross-region inference
            "dataAutomationConfiguration": {
                "dataAutomationProjectArn": project_arn  
            },
            "inputConfiguration": {
                "s3Uri": input_uri
            },
            "outputConfiguration": {
                "s3Uri": output_uri
            },
            "notificationConfiguration": {
                "eventBridgeConfiguration": {
                    "eventBridgeEnabled": True
                }
            }
        }
        
        # Log the full request for debugging
        print(f"Request parameters: {json.dumps(request_params, default=str)}")
        
        # Invoke the data automation async job using the runtime client
        response = client_runtime.invoke_data_automation_async(**request_params)
        
        print(f"Successfully started job with invocation ARN: {response['invocationArn']}")
        
        return {
            "JobId": response["invocationArn"],
            "Status": "SUBMITTED",
            "CreationTime": None  # The response doesn't include creation time
        }
    
    except Exception as e:
        print(f"Error invoking Bedrock Data Automation: {str(e)}")
        raise e
