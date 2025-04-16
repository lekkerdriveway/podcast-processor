import boto3
import json
import os
import pathlib

s3 = boto3.client('s3')
bedrock = boto3.client('bedrock-runtime')
MODEL_ID = os.environ.get('MODEL_ID', 'anthropic.claude-3-7-sonnet-20250219-v1:0')

def load_system_prompt():
    """
    Load system prompt from JSON file.
    
    Returns:
        String containing the system prompt
    """
    try:
        # Get the directory of the current file
        current_dir = pathlib.Path(__file__).parent.resolve()
        # Path to the system prompt JSON file
        prompt_file_path = os.path.join(current_dir, 'custom-system-prompt.json')
        
        # Check if the file exists
        if not os.path.exists(prompt_file_path):
            print(f"Warning: System prompt file not found at: {prompt_file_path}")
            return None
            
        # Read and parse the JSON file
        with open(prompt_file_path, 'r') as f:
            prompt_data = json.load(f)
            
        return prompt_data.get('systemPrompt')
    except Exception as e:
        print(f"Error loading system prompt: {str(e)}")
        return None

def handler(event, context):
    """
    Generate a summary of the podcast transcript using Claude 3.7.
    
    Args:
        event: Contains the transcript location and metadata
        context: Lambda context
        
    Returns:
        Dictionary with summary and metadata
    """
    print(f"Generating summary with event: {json.dumps(event)[:500]}...")
    
    # Get transcript location from event
    transcript_location = event.get('transcript_location', {})
    bucket = transcript_location.get('bucket')
    key = transcript_location.get('key')
    metadata = event.get('metadata', {})
    
    if not bucket or not key:
        raise ValueError(f"Missing transcript location information: bucket={bucket}, key={key}")
    
    try:
        # Fetch the transcript from S3
        print(f"Retrieving transcript from S3: bucket={bucket}, key={key}")
        response = s3.get_object(Bucket=bucket, Key=key)
        transcript_data = json.loads(response['Body'].read().decode('utf-8'))
        
        # Process the transcript based on structure
        transcript = ""
        
        # Try to extract transcript from the standardOutput format
        if isinstance(transcript_data, dict) and 'standardOutput' in transcript_data:
            std_output = transcript_data['standardOutput']
            if 'audio' in std_output:
                audio_data = std_output['audio']
                if 'extraction' in audio_data and 'text' in audio_data['extraction']:
                    text_data = audio_data['extraction']['text']
                    if 'segments' in text_data:
                        segments = text_data['segments']
                        for segment in segments:
                            start_time = segment.get('startTime', 0)
                            text = segment.get('text', '')
                            start_formatted = f"{int(start_time // 60):02d}:{int(start_time % 60):02d}"
                            transcript += f"[{start_formatted}] {text}\n\n"
                    elif 'content' in text_data:
                        transcript = text_data['content']
        
        # If we couldn't find the transcript in the expected structure, try common patterns
        if not transcript and isinstance(transcript_data, dict):
            if 'text' in transcript_data:
                transcript = transcript_data['text']
            elif 'transcript' in transcript_data:
                transcript = transcript_data['transcript']
            elif 'content' in transcript_data:
                transcript = transcript_data['content']
        
        # Last resort fallback
        if not transcript:
            print("Could not find transcript in expected format, using raw JSON")
            transcript = json.dumps(transcript_data, indent=2)
            
        print(f"Retrieved transcript with length: {len(transcript)}")
    except Exception as e:
        print(f"Error retrieving transcript from S3: {str(e)}")
        raise e
    
    # Load system prompt from JSON file
    system_prompt = load_system_prompt()
    
    # Fallback to default prompt if loading fails
    if not system_prompt:
        print("Using default system prompt as loading from file failed")
        system_prompt = """The follow is a transcript of an audio podcast. The podcast is called Pop Culture Parenting, it is hosted by a Pediatrician (Dr Billy Garvey), and his friend (Nick) who is a parent to young children, but not formally qualified in this domain. Each episode they discuss a topic related to parenting in the context of a film. It has a preamble covering general topics and then provides specific, actionable parenting advice on a given topic. I'd like you to create a a number of outputs.

1) The name of the episode.
2) the film featured in the episode
3) A short summary of the episode, this summary should begin with In this episode Billy and Nick discuss <Topic of episode>, in the context of <Film Name>
4) a single page, easy to consume "cheat sheet" that summarises the advice in the podcast into actional insights, consumable at a glance.
5) 5 search terms that can be used to find the episode. These shouldn't be generic to the podcast, only specific to the topic of the episode."""
    
    # Format user message with transcript
    # If the transcript is very long, we might need to truncate it
    max_transcript_length = 100000  # Adjust based on model token limits
    truncated_transcript = transcript[:max_transcript_length]
    if len(transcript) > max_transcript_length:
        truncated_transcript += "\n\n[Transcript truncated due to length]"
    
    user_message = f"Here's the podcast transcript to analyze:\n\n{truncated_transcript}"
    
    # Create the request for Claude 3.7
    request = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 10000,
        # Temperature and sampling params not compatible with thinking feature
        #"temperature": 0.2,   # Lower temperature for more focused outputs
        #"top_p": 0.95,        # Limit to the most probable tokens (95% cumulative probability)
        #"top_k": 30,          # Limit to the top 30 most likely tokens
        "system": system_prompt,  # System prompt as top-level parameter
        "thinking": {
            "type": "enabled", 
            "budget_tokens": 4000  # Allocate tokens for reasoning process
        },
        "messages": [
            {
                "role": "user",
                "content": user_message
            }
        ]
    }
    
    try:
        print(f"Invoking Bedrock model: {MODEL_ID}")
        # Invoke Claude 3.7
        response = bedrock.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps(request)
        )
        
        response_body = json.loads(response["body"].read())
        
        # Find the text content using next() - works regardless of position or thinking being enabled
        text_item = next((item for item in response_body["content"] if item.get("type") == "text"), None)
        if text_item and "text" in text_item:
            summary = text_item["text"]
        else:
            print(f"Error: Unable to find text content in response: {json.dumps(response_body)[:1000]}")
            raise ValueError("No text content found in the model response")
        
        print(f"Successfully generated summary with length: {len(summary)}")
        print(f"Summary preview: {summary[:500]}...")
        
        # Return only essential data to stay within Step Functions payload limits
        # Extract only necessary metadata fields if needed
        essential_metadata = {}
        if metadata:
            # Include only essential metadata fields that the formatter needs
            # For example, we might need the original filename or other small metadata
            if "originalFileName" in metadata:
                essential_metadata["originalFileName"] = metadata["originalFileName"]
            # Add other essential metadata fields as needed
        
        return {
            "summary": summary,
            "essential_metadata": essential_metadata
        }
        
    except Exception as e:
        print(f"Error invoking Bedrock: {str(e)}")
        raise e
