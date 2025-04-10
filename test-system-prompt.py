#!/usr/bin/env python3
import json
import os
import sys
import pathlib

sys.path.append('src/functions/summarizer')
import index

def test_system_prompt_loading():
    """
    Test that the system prompt can be loaded correctly from the JSON file.
    """
    print("\n🔍 Testing system prompt loading from JSON file...")
    
    # Get the system prompt from the Lambda function
    system_prompt = index.load_system_prompt()
    
    # Check if the system prompt was loaded successfully
    if not system_prompt:
        print("❌ Failed to load system prompt from JSON file")
        sys.exit(1)
    
    print("✅ Successfully loaded system prompt from JSON file")
    print(f"\nSystem prompt preview (first 200 chars):\n{system_prompt[:200]}...\n")
    
    # Load the JSON file directly for comparison
    try:
        current_dir = pathlib.Path(__file__).parent.resolve()
        prompt_file_path = os.path.join(current_dir, 'src/functions/summarizer/custom-system-prompt.json')
        with open(prompt_file_path, 'r') as f:
            prompt_data = json.load(f)
        expected_prompt = prompt_data.get('systemPrompt')
        
        if system_prompt == expected_prompt:
            print("✅ System prompt matches the content from custom-system-prompt.json")
        else:
            print("❌ System prompt doesn't match the expected content")
            print("\nExpected prompt (first 200 chars):")
            print(f"{expected_prompt[:200]}...")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error loading JSON file directly: {str(e)}")
        sys.exit(1)
    
    print("\n✅ All system prompt tests passed!")

if __name__ == "__main__":
    test_system_prompt_loading()
