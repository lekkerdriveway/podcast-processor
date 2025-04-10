import boto3
import json
import os
import re
from datetime import datetime

s3 = boto3.client('s3')
OUTPUT_BUCKET = os.environ.get('OUTPUT_BUCKET')

def handler(event, context):
    """
    Format the summary into a markdown document and save to S3.
    
    Args:
        event: Contains the summary and metadata
        context: Lambda context
        
    Returns:
        Dictionary with status and output information
    """
    print(f"Formatting output with event: {json.dumps(event)[:500]}...")
    
    summary = event.get('summary')
    metadata = event.get('metadata', {})
    
    if not summary:
        raise ValueError("No summary provided in the event")
    
    if not OUTPUT_BUCKET:
        raise ValueError("OUTPUT_BUCKET environment variable not set")
    
    try:
        # Clean up the summary - remove any numeric prefixes like "1)" or "2)"
        # and preserve the content structure that Claude has already created
        clean_summary = summary
        
        # Try to extract episode name and number for use in the filename
        # Look for something that looks like a title at the beginning
        lines = summary.split('\n')
        episode_name = "Podcast Summary"
        film_name = "Unknown Film"
        episode_number = None
        
        # Try to find the episode name (likely at the beginning)
        for line in lines[:10]:  # Check the first few lines
            if line.strip() and not line.startswith('#') and len(line.strip()) < 100:
                episode_name = line.strip()
                break
        
        # Look for episode number patterns in the summary or title
        # Check for patterns like "Episode X", "EP X", "#X"
        number_patterns = [
            r'(?:episode|ep)\.?\s*#?(\d+)',  # Episode 1, Ep. 1, EP #1
            r'#(\d+)',                        # #1
            r'^(\d+)\s*[-:–]',               # 1 - Title, 1: Title
            r'\bPart\s+(\d+)\b'              # Part 1
        ]
        
        for pattern in number_patterns:
            # Check in episode name first
            match = re.search(pattern, episode_name, re.IGNORECASE)
            if match:
                episode_number = match.group(1).zfill(2)  # Pad with leading zero
                break
                
            # If not found in title, check first 500 chars of summary
            if not episode_number:
                match = re.search(pattern, summary[:500], re.IGNORECASE)
                if match:
                    episode_number = match.group(1).zfill(2)
                    break
        
        # If episode number still not found, look for original filename pattern
        if not episode_number and 'originalFileName' in metadata:
            filename = metadata.get('originalFileName', '')
            match = re.search(r'(\d+)', filename)
            if match:
                episode_number = match.group(1).zfill(2)
        
        # Default to 00 if no episode number found
        if not episode_number:
            episode_number = "00"
        
        # Try to find the film name (likely after "Film:" or similar text)
        film_pattern = re.search(r'(?:film|movie|featured film)[:\s]+([^\n]+)', summary, re.IGNORECASE)
        if film_pattern:
            film_name = film_pattern.group(1).strip()
        
        # Use the Claude output directly without any header
        markdown = clean_summary
        
        # Generate the output filename (sanitize it)
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', episode_name)
        output_key = f"summaries/{episode_number} - {safe_name}.md"
        
        # Write to S3
        print(f"Writing markdown to S3 bucket: {OUTPUT_BUCKET}, key: {output_key}")
        s3.put_object(
            Bucket=OUTPUT_BUCKET,
            Key=output_key,
            Body=markdown,
            ContentType='text/markdown'
        )
        
        print(f"Successfully wrote markdown file to S3: {output_key}")
        
        return {
            "status": "success",
            "outputKey": output_key,
            "episodeName": episode_name,
            "film": film_name
        }
        
    except Exception as e:
        print(f"Error formatting output: {str(e)}")
        raise e
