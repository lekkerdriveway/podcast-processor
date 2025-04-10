#!/bin/bash
set -e

# Colors for terminal output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Podcast Processing Pipeline - Local Testing Script${NC}"
echo "--------------------------------------------------------"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}Error: pip3 is not installed. Please install it first.${NC}"
    exit 1
fi

# Install Python dependencies for local testing
echo -e "${YELLOW}Installing Python dependencies...${NC}"
pip3 install boto3 moto pytest --quiet

# Create a test directory for simulating S3 buckets locally
echo -e "${YELLOW}Creating local test directories...${NC}"
mkdir -p test-data/input
mkdir -p test-data/transcripts
mkdir -p test-data/output

# Create a sample transcript for testing
echo -e "${YELLOW}Creating sample test data...${NC}"
cat > test-data/transcripts/test-transcript.json << EOF
{
  "results": {
    "transcripts": [
      {
        "transcript": "Welcome to Pop Culture Parenting! I'm Dr. Billy Garvey, and I'm joined by my friend Nick. Today, we're discussing how to talk to children about emotions, using the movie Inside Out as a backdrop. This Pixar film does an amazing job of anthropomorphizing different emotions and showing how they all play important roles in our lives. Nick, why don't you start by sharing your experience watching this with your kids?"
      },
      {
        "transcript": "Thanks, Billy. My kids were absolutely captivated by Inside Out. What stood out to me was how the film gave us a vocabulary to discuss emotions that might otherwise be difficult to articulate. When my 6-year-old was feeling sad last week, she actually referenced the blue character Sadness and could explain that sometimes it's okay to feel that way. It opened up a whole conversation about emotional health that would've been much harder without that shared reference point."
      },
      {
        "transcript": "That's exactly why films like this are so valuable as parenting tools. From a pediatrician's perspective, children's emotional intelligence is just as important as their cognitive development. The film shows that all emotions serve a purpose, even the ones we typically label as 'negative' like anger or fear. Let's break down some specific strategies parents can use to help children identify and process their emotions."
      },
      {
        "transcript": "First, naming emotions is crucial. The simple act of labeling feelings helps children develop emotional awareness. Second, validate those emotions - there are no 'bad' emotions, just different ways our bodies and minds respond to situations. Third, teach coping strategies tailored to different emotions. And fourth, model healthy emotional expression yourself as a parent."
      }
    ]
  }
}
EOF

# Create a test script for the transcript processor
echo -e "${YELLOW}Creating test script for transcript processor...${NC}"
cat > test-transcript-processor.py << EOF
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
EOF

# Create a test script for the summarizer (with mock Bedrock)
echo -e "${YELLOW}Creating test script for summarizer...${NC}"
cat > test-summarizer.py << EOF
#!/usr/bin/env python3
import json
import os
import sys

sys.path.append('src/functions/summarizer')
import index

# Create a mock event from the processed transcript
try:
    with open('test-data/processed-transcript.json', 'r') as f:
        processed_transcript = json.load(f)
    
    event = {
        'transcript': processed_transcript['transcript'],
        'metadata': processed_transcript['metadata']
    }
except FileNotFoundError:
    print("❌ Processed transcript not found. Run the transcript processor test first.")
    sys.exit(1)

# Mock the Bedrock client
class MockResponse:
    def __init__(self, content):
        self.content = content
    
    def read(self):
        return json.dumps(self.content)

class MockBody:
    def __init__(self, content):
        self.content = content
    
    def read(self):
        return json.dumps(self.content)

def mock_invoke_model(**kwargs):
    # Create a mock Claude 3.7 response
    mock_summary = """
1) Inside Out: Emotional Intelligence

2) Inside Out (Pixar)

3) In this episode Billy and Nick discuss how to help children recognize and process their emotions, in the context of Pixar's Inside Out. They explore how the film provides a valuable framework for understanding different emotions and their purpose in our lives.

4) Parenting Cheat Sheet for Emotional Intelligence:
- Name emotions explicitly to help children develop emotional vocabulary
- Validate all emotions - there are no "bad" feelings, just different responses
- Create a safe space for children to express their full range of emotions
- Use visual aids or characters (like those in Inside Out) to help identify feelings
- Model healthy emotional expression yourself as a parent
- Teach specific coping strategies for different emotions
- Look for emotional themes in media your children consume
- Connect emotions to physical sensations to improve body awareness
- Practice reflective listening when your child shares their feelings
- Remember that emotional intelligence is just as important as cognitive development

5) Search terms:
- Inside Out emotions parenting
- Emotional intelligence children
- Pixar movies parenting lessons
- Teaching kids about feelings
- Dr. Billy Garvey emotional health
"""
    
    return {
        'body': MockBody({
            'content': [
                {
                    'type': 'text',
                    'text': mock_summary
                }
            ]
        })
    }

# Replace the Bedrock client with our mock
index.bedrock.invoke_model = mock_invoke_model

# Execute the function
try:
    result = index.handler(event, None)
    print("✅ Summarizer test passed!")
    print("Summary preview:")
    print(result['summary'][:200] + "...")
    
    # Save summary for next test
    with open('test-data/summary.json', 'w') as f:
        json.dump(result, f, indent=2)
except Exception as e:
    print(f"❌ Test failed: {str(e)}")
    sys.exit(1)

print("\nTest completed successfully!")
EOF

# Create a test script for the formatter
echo -e "${YELLOW}Creating test script for formatter...${NC}"
cat > test-formatter.py << EOF
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
EOF

# Make the test scripts executable
chmod +x test-transcript-processor.py
chmod +x test-summarizer.py
chmod +x test-formatter.py

# Run the tests
echo -e "\n${YELLOW}Running Bedrock Lambda proxy tests...${NC}"
python3 test-bedrock-lambda.py

echo -e "\n${YELLOW}Running transcript processor test...${NC}"
python3 test-transcript-processor.py

echo -e "\n${YELLOW}Running summarizer test...${NC}"
python3 test-summarizer.py

echo -e "\n${YELLOW}Running formatter test...${NC}"
python3 test-formatter.py

echo -e "\n${GREEN}All tests completed successfully!${NC}"
echo -e "${YELLOW}------------------------${NC}"
echo -e "You can find the test outputs in the test-data directory:"
echo -e " - Processed transcript: test-data/processed-transcript.json"
echo -e " - Generated summary: test-data/summary.json"
echo -e " - Formatted markdown: test-data/output/summaries/"
echo -e "${YELLOW}------------------------${NC}"
