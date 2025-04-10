#!/usr/bin/env python3
import json
import os
import sys

sys.path.append('src/functions/formatter')
import index

# Create a mock event from the summary
try:
    with open('test-data/summary.json', 'r') as f:
        summary_data = json.load(f)
    
    event = {
        'summary': summary_data['summary'],
        'metadata': summary_data['metadata']
    }
except FileNotFoundError:
    print("❌ Summary not found. Run the summarizer test first.")
    sys.exit(1)

# Override the S3 put_object method
os.environ['OUTPUT_BUCKET'] = 'test-data/output'

def mock_put_object(**kwargs):
    bucket = kwargs['Bucket']
    key = kwargs['Key']
    body = kwargs['Body']
    
    # Create directory if it doesn't exist
    dir_path = f"{bucket}/{os.path.dirname(key)}"
    os.makedirs(dir_path, exist_ok=True)
    
    # Write the file
    with open(f"{bucket}/{key}", 'w') as f:
        f.write(body)

# Replace the S3 client with our mock
index.s3.put_object = mock_put_object

# Execute the function
try:
    result = index.handler(event, None)
    print("✅ Formatter test passed!")
    print(f"Generated markdown saved as: {os.environ['OUTPUT_BUCKET']}/{result['outputKey']}")
    
    # Display the output
    with open(f"{os.environ['OUTPUT_BUCKET']}/{result['outputKey']}", 'r') as f:
        print("\n--- Output Markdown Preview ---\n")
        print(f.read()[:500] + "...\n")
except Exception as e:
    print(f"❌ Test failed: {str(e)}")
    sys.exit(1)

print("\nAll tests completed successfully!")
