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
