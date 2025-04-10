import boto3
import json
import re

# Print boto3 version for debugging
print(f"boto3 version: {boto3.__version__}")

def extract_s3_path(s3_uri):
    """
    Extract bucket and key from S3 URI
    """
    match = re.match(r's3://([^/]+)/(.+)', s3_uri)
    if match:
        return match.group(1), match.group(2)
    return None, None

def handler(event, context):
    """
    Lambda function to check Bedrock Data Automation job status
    """
    # Use the runtime client for status checking
    client = boto3.client('bedrock-data-automation-runtime')
    
    print(f"Event received: {json.dumps(event)}")
    
    try:
        # Get invocation ARN from the event
        invocation_arn = event.get('JobId')
        if not invocation_arn and 'TranscriptionJob' in event:
            invocation_arn = event['TranscriptionJob'].get('JobId')
            
        if not invocation_arn:
            raise ValueError("No JobId (invocation ARN) found in event")
        
        print(f"Checking status of job with invocation ARN: {invocation_arn}")
            
        # Get the job status using the runtime client
        response = client.get_data_automation_status(
            invocationArn=invocation_arn
        )
        
        print(f"Job status response: {json.dumps(response, default=str)}")
        
        # Extract and return important fields - normalize to uppercase for consistency
        raw_status = response.get("status", "UNKNOWN")
        # Convert the status to uppercase for consistent checking
        status = raw_status.upper()
        
        result = {
            "JobId": invocation_arn,
            "Status": status,
        }
        
        # Include output information if job is completed (check both "COMPLETED" and "SUCCESS")
        if status in ["COMPLETED", "SUCCESS"]:
            print(f"Job completed with status: {raw_status}")
            
            # The output path can be in different locations based on response structure
            output_uri = None
            
            # Check standard result path
            if "result" in response and "outputS3Uri" in response["result"]:
                output_uri = response["result"]["outputS3Uri"]
            
            # Check outputConfiguration path (from CLI output)
            elif "outputConfiguration" in response and "s3Uri" in response["outputConfiguration"]:
                output_uri = response["outputConfiguration"]["s3Uri"]
                
            if output_uri:
                print(f"Found output URI: {output_uri}")
                
                # Extract output location
                bucket, key = extract_s3_path(output_uri)
                if bucket and key:
                    # Store the transcript location
                    result["OutputBucket"] = bucket
                    result["OutputKey"] = key
                    
                    # If we found a metadata file, try to find the actual transcript
                    if key.endswith("job_metadata.json"):
                        # Use a more robust method: extract the UUID pattern from the path
                        import re
                        uuid_pattern = re.compile(r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})')
                        match = uuid_pattern.search(key)
                        
                        if match:
                            # Extract job ID from UUID pattern
                            job_id = match.group(1)
                            standard_output_key = f"transcripts//{job_id}/0/standard_output/0/result.json"
                            print(f"Using job ID from UUID pattern: {job_id}")
                            print(f"Using standard output key: {standard_output_key}")
                            result["OutputKey"] = standard_output_key
                        else:
                            # Fallback to extraction from invocation ARN if UUID not found in path
                            job_id = invocation_arn.split('/')[-1]
                            standard_output_key = f"transcripts//{job_id}/0/standard_output/0/result.json"
                            print(f"Using job ID from invocation ARN: {job_id}")
                            print(f"Using standard output key: {standard_output_key}")
                            result["OutputKey"] = standard_output_key
            
        return result
    
    except Exception as e:
        print(f"Error checking Bedrock Data Automation job status: {str(e)}")
        raise e
