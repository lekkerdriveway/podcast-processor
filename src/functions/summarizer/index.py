import boto3
import json
import os
import pathlib

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
        event: Contains the transcript and metadata
        context: Lambda context
        
    Returns:
        Dictionary with summary and metadata
    """
    print(f"Generating summary with event: {json.dumps(event)[:500]}...")
    
    transcript = event.get('transcript')
    metadata = event.get('metadata', {})
    
    if not transcript:
        raise ValueError("No transcript provided in the event")
    
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
        "max_tokens": 4000,
        "temperature": 0.7,
        "system": system_prompt,  # System prompt as top-level parameter
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
        summary = response_body["content"][0]["text"]
        
        print(f"Successfully generated summary with length: {len(summary)}")
        print(f"Summary preview: {summary[:500]}...")
        
        return {
            "summary": summary,
            "metadata": metadata
        }
        
    except Exception as e:
        print(f"Error invoking Bedrock: {str(e)}")
        raise e
