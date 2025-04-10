#!/usr/bin/env python3
import json
import os
import sys

sys.path.append('src/functions/transcript-processor')
import index

# Mock the S3 client and environment variables
os.environ['TRANSCRIPTS_BUCKET'] = 'test-data/transcripts'

# Create a mock event
event = {
    'transcriptKey': 'test-transcript.json',
    'originalFileName': 'test-podcast.mp3'
}

# Create a mock context
class MockContext:
    def __init__(self):
        self.invoked_function_arn = 'arn:aws:lambda:us-west-2:123456789012:function:test'

# Override the S3 client with a mock version
def mock_get_object(**kwargs):
    bucket = kwargs['Bucket']
    key = kwargs['Key']
    filepath = f"{bucket}/{key}"
    with open(filepath, 'r') as file:
        content = file.read()
    
    class MockBody:
        def read(self):
            return content.encode('utf-8')
    
    return {
        'Body': MockBody()
    }

index.s3.get_object = mock_get_object

# Execute the function
try:
    result = index.handler(event, MockContext())
    print("✅ Transcript processor test passed!")
    print(f"Processed transcript length: {len(result['transcript'])}")
    print(f"Metadata: {json.dumps(result['metadata'], indent=2)}")
    
    # Save transcript for next test
    with open('test-data/processed-transcript.json', 'w') as f:
        json.dump(result, f, indent=2)
except Exception as e:
    print(f"❌ Test failed: {str(e)}")
    sys.exit(1)

print("\nTest completed successfully!")
