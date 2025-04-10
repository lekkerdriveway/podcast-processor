#!/usr/bin/env python3
import json

def test_path_extraction(key, invocation_arn=None):
    """Test various path extraction methods to find the job ID"""
    print(f"\nTesting path extraction for: {key}")
    print("-" * 50)
    
    # Method 1: Current implementation (trying to extract from path)
    print("Method 1: Current implementation")
    parts = key.split('/')
    print(f"  Split parts: {parts}")
    
    if len(parts) >= 2:
        job_id = parts[1]
        print(f"  Job ID from parts[1]: '{job_id}'")
        standard_output_key = f"{parts[0]}//{job_id}/0/standard_output/0/result.json"
        print(f"  Output key: {standard_output_key}")
    else:
        print("  Not enough parts in path")
        
    # Method 2: Alternative path parsing
    print("\nMethod 2: More robust path parsing")
    # Try to find a UUID-like pattern in the path
    import re
    uuid_pattern = re.compile(r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})')
    match = uuid_pattern.search(key)
    if match:
        job_id = match.group(1)
        print(f"  Job ID from UUID pattern: '{job_id}'")
        standard_output_key = f"transcripts//{job_id}/0/standard_output/0/result.json"
        print(f"  Output key: {standard_output_key}")
    else:
        print("  No UUID pattern found in path")
    
    # Method 3: Extract job ID from invocation ARN (if available)
    if invocation_arn:
        print("\nMethod 3: Extract from invocation ARN")
        arn_parts = invocation_arn.split('/')
        if len(arn_parts) > 0:
            job_id = arn_parts[-1]
            print(f"  Job ID from invocation ARN: '{job_id}'")
            standard_output_key = f"transcripts//{job_id}/0/standard_output/0/result.json"
            print(f"  Output key: {standard_output_key}")
        
    print("-" * 50)

# Test with different path formats
print("\n=== TESTING VARIOUS PATH FORMATS ===")
test_path_extraction("transcripts/job_metadata.json")
test_path_extraction("transcripts//job_metadata.json")
test_path_extraction("transcripts/45deb974-7b6f-455b-a68a-41a0fcc5e3ae/job_metadata.json")
test_path_extraction("transcripts//45deb974-7b6f-455b-a68a-41a0fcc5e3ae/job_metadata.json")

# Test with a mock response from the Bedrock Data Automation API
print("\n=== TESTING WITH MOCK API RESPONSE ===")
mock_response = {
    "status": "Success",
    "outputConfiguration": {
        "s3Uri": "s3://podcastprocessorstoragest-transcriptsbucketf640f86-gndfzzaqytbc/transcripts//6517f068-117a-41f1-b80a-0fc8dde15707/job_metadata.json"
    }
}

# Extract bucket and key from the S3 URI
import re
s3_uri = mock_response["outputConfiguration"]["s3Uri"]
print(f"S3 URI: {s3_uri}")

match = re.match(r's3://([^/]+)/(.+)', s3_uri)
if match:
    bucket, key = match.group(1), match.group(2)
    print(f"Extracted bucket: {bucket}")
    print(f"Extracted key: {key}")
    
    # Test our extraction method on the real path format
    test_path_extraction(key, "arn:aws:bedrock:us-west-2:574482439656:data-automation-invocation/6517f068-117a-41f1-b80a-0fc8dde15707")
else:
    print("Failed to extract bucket and key from S3 URI")
