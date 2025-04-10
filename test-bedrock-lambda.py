#!/usr/bin/env python3
import json
import os
import sys
import uuid
from datetime import datetime

# Add Lambda function directories to the path
sys.path.append('src/functions/bedrock-transcribe')
sys.path.append('src/functions/bedrock-status')

# Import the Lambda handlers
import index as bedrock_transcribe
import importlib.util
spec = importlib.util.spec_from_file_location("bedrock_status", "src/functions/bedrock-status/index.py")
bedrock_status = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bedrock_status)

print("🔍 Testing Bedrock Lambda Proxy functions...")

# Create test directories if they don't exist
os.makedirs('test-data/input', exist_ok=True)
os.makedirs('test-data/transcripts', exist_ok=True)

# Set environment variables
os.environ['TRANSCRIPTS_BUCKET'] = 's3://test-data/transcripts'

# Create a sample MP3 file for reference
if not os.path.exists('test-data/input/sample-podcast.mp3'):
    with open('test-data/input/sample-podcast.mp3', 'wb') as f:
        f.write(b'mock mp3 data')

# Mock the Bedrock Data Automation client
class MockBedrockDataAutomation:
    def __init__(self):
        self.jobs = {}
        
    def create_data_transformation_job(self, **kwargs):
        job_id = str(uuid.uuid4())
        self.jobs[job_id] = {
            "jobId": job_id,
            "status": "IN_PROGRESS",
            "creationTime": datetime.now(),
            "modelId": kwargs.get('modelId'),
            "outputLocation": f"s3://test-data/transcripts/output-{job_id}.json"
        }
        
        # Create a mock output file after a delay in a real scenario
        # Here we'll create it immediately for testing
        os.makedirs('test-data/transcripts', exist_ok=True)
        with open(f'test-data/transcripts/output-{job_id}.json', 'w') as f:
            f.write(json.dumps({
                "results": {
                    "transcripts": [
                        {
                            "transcript": "This is a mock transcript generated for testing."
                        }
                    ]
                }
            }))
        
        return {
            "jobId": job_id,
            "status": "IN_PROGRESS",
            "creationTime": self.jobs[job_id]["creationTime"]
        }
        
    def get_data_transformation_job(self, **kwargs):
        job_id = kwargs.get('jobId')
        if job_id not in self.jobs:
            raise Exception(f"Job {job_id} not found")
            
        # For testing, we'll simulate the job is completed
        self.jobs[job_id]["status"] = "COMPLETED"
        
        return {
            "jobId": job_id,
            "status": "COMPLETED",
            "creationTime": self.jobs[job_id]["creationTime"],
            "outputLocation": self.jobs[job_id]["outputLocation"]
        }
        
# Patch the boto3 client
mock_client = MockBedrockDataAutomation()
bedrock_transcribe.boto3.client = lambda service_name: mock_client
bedrock_status.boto3.client = lambda service_name: mock_client

# Test transcribe Lambda
print("\n1️⃣ Testing Bedrock Transcribe Lambda...")
transcribe_event = {
    'ModelId': 'amazon.titan-tg1-large',
    'bucket': 'test-data',
    'key': 'input/sample-podcast.mp3'
}

try:
    transcribe_result = bedrock_transcribe.handler(transcribe_event, None)
    print("✅ Bedrock Transcribe Lambda test passed!")
    print(f"Job ID: {transcribe_result['JobId']}")
    print(f"Status: {transcribe_result['Status']}")
    
    # Test status Lambda
    print("\n2️⃣ Testing Bedrock Status Lambda...")
    status_event = {
        'JobId': transcribe_result['JobId']
    }
    
    status_result = bedrock_status.handler(status_event, None)
    print("✅ Bedrock Status Lambda test passed!")
    print(f"Job ID: {status_result['JobId']}")
    print(f"Status: {status_result['Status']}")
    print(f"Output location: {status_result['OutputKey']}")
    
except Exception as e:
    print(f"❌ Test failed: {str(e)}")
    sys.exit(1)

print("\n✅ All Bedrock Lambda tests completed successfully!")
