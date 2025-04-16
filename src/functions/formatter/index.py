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
        
        # First try to extract from the very first line which should be a header
        if lines and lines[0].strip().startswith('#'):
            # Remove the # and any leading/trailing whitespace
            first_line_content = lines[0].lstrip('#').strip()
            episode_name = first_line_content
            print(f"Using first line as episode name: {episode_name}")
        else:
            # Try to find the episode name pattern in the header format: # Episode X: Film & Title
            first_line_pattern = re.search(r'#\s*Episode\s+\d+:(.+?)(?:\n|$)', summary, re.IGNORECASE)
            if first_line_pattern:
                # Get the content after "Episode X:"
                first_line_content = first_line_pattern.group(1).strip()
                episode_name = first_line_content
                print(f"Using header pattern match as episode name: {episode_name}")
            else:
                # Fallback: look for non-header lines at the beginning (original method)
                for line in lines[:10]:  # Check the first few lines
                    if line.strip() and not line.startswith('#') and len(line.strip()) < 100:
                        episode_name = line.strip()
                        print(f"Using fallback method for episode name: {episode_name}")
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
                episode_number = match.group(1).zfill(3)  # Pad with leading zeros to make it 3 digits
                break
                
            # If not found in title, check first 500 chars of summary
            if not episode_number:
                match = re.search(pattern, summary[:500], re.IGNORECASE)
                if match:
                    episode_number = match.group(1).zfill(3)
                    break
        
        # If episode number still not found, look for original filename pattern
        if not episode_number and 'originalFileName' in metadata:
            filename = metadata.get('originalFileName', '')
            match = re.search(r'(\d+)', filename)
            if match:
                episode_number = match.group(1).zfill(3)
        
        # Default to 00 if no episode number found
        if not episode_number:
            episode_number = "000"
        
        # Try to find the film name (likely after "Film:" or similar text)
        film_pattern = re.search(r'(?:film|movie|featured film)[:\s]+([^\n]+)', summary, re.IGNORECASE)
        if film_pattern:
            film_name = film_pattern.group(1).strip()
        
        # Use the Claude output directly without any header
        markdown = clean_summary
        
        # Clean the episode name by removing any "Episode X" prefix patterns
        episode_name = re.sub(r'^(?:Episode|Ep\.?)\s+\d+\s*[-:]\s*', '', episode_name, flags=re.IGNORECASE)
        print(f"Cleaned episode name: {episode_name}")
        
        # Generate the output filename (sanitize it but preserve spaces for readability)
        # Replace colons with hyphens and other problematic characters with underscores
        safe_name = episode_name.replace(':', ' -')
        safe_name = re.sub(r'[^\w\s&-]', '_', safe_name)
        # Replace multiple spaces/underscores with a single space
        safe_name = re.sub(r'[\s_]+', ' ', safe_name)
        # Strip leading/trailing spaces
        safe_name = safe_name.strip()
        # Create output key with 3-digit episode number followed by sanitized name
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
