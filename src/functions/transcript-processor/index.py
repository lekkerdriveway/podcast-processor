import boto3
import json
import os
import re
from datetime import datetime

s3 = boto3.client('s3')
TRANSCRIPTS_BUCKET = os.environ.get('TRANSCRIPTS_BUCKET')

def handler(event, context):
    """
    Process the transcript from Bedrock Data Automation.
    
    Args:
        event: Contains the transcript key and original file name
        context: Lambda context
        
    Returns:
        Dictionary with processed transcript and metadata
    """
    print(f"Processing transcript with event: {json.dumps(event)}")
    
    # Get the transcript information from the event
    transcript_bucket = event.get('TranscriptionStatus', {}).get('OutputBucket')
    transcript_key = event.get('TranscriptionStatus', {}).get('OutputKey')
    original_file_name = event.get('originalFileName', 'unknown.mp3')
    
    if not transcript_bucket or not transcript_key:
        raise ValueError(f"Missing transcript location information: bucket={transcript_bucket}, key={transcript_key}")
    
    try:
        # Get the transcript from S3
        print(f"Retrieving transcript from bucket: {transcript_bucket}, key: {transcript_key}")
        response = s3.get_object(
            Bucket=transcript_bucket,
            Key=transcript_key
        )
        
        transcript_data = json.loads(response['Body'].read().decode('utf-8'))
        print(f"Retrieved transcript data with keys: {list(transcript_data.keys()) if isinstance(transcript_data, dict) else 'Not a dictionary'}")
        
        # Process the transcript based on Bedrock Data Automation format
        full_transcript = ""
        
        # The Bedrock Data Automation output format should contain a standardOutput section
        if isinstance(transcript_data, dict) and 'standardOutput' in transcript_data:
            std_output = transcript_data['standardOutput']
            
            # For audio transcription, look for the text extraction in the audio section
            if 'audio' in std_output:
                audio_data = std_output['audio']
                
                # Check if there's an extraction section with text
                if 'extraction' in audio_data and 'text' in audio_data['extraction']:
                    text_data = audio_data['extraction']['text']
                    
                    # If there are segments with timestamps
                    if 'segments' in text_data:
                        segments = text_data['segments']
                        for segment in segments:
                            start_time = segment.get('startTime', 0)
                            end_time = segment.get('endTime', 0)
                            text = segment.get('text', '')
                            
                            # Format timestamp as [MM:SS]
                            start_formatted = f"{int(start_time // 60):02d}:{int(start_time % 60):02d}"
                            
                            full_transcript += f"[{start_formatted}] {text}\n\n"
                    
                    # If there's a full transcript 
                    elif 'content' in text_data:
                        full_transcript = text_data['content']
        
        # If we couldn't find the transcript in the expected structure, try common patterns
        if not full_transcript and isinstance(transcript_data, dict):
            # Try to find any text content at various locations
            if 'text' in transcript_data:
                full_transcript = transcript_data['text']
            elif 'transcript' in transcript_data:
                full_transcript = transcript_data['transcript']
            elif 'content' in transcript_data:
                full_transcript = transcript_data['content']
        
        # Last resort fallback
        if not full_transcript:
            print("Could not find transcript in expected format, using raw JSON")
            full_transcript = json.dumps(transcript_data, indent=2)
            print(f"Using raw transcript data as fallback: {full_transcript[:100]}...")
        
        # Extract basic metadata
        metadata = {
            'originalFileName': original_file_name,
            'processingTimestamp': datetime.now().isoformat(),
            'transcriptLength': len(full_transcript),
            'transcriptSource': f"s3://{transcript_bucket}/{transcript_key}"
        }
        
        print(f"Successfully processed transcript with length: {len(full_transcript)}")
        
        # Return the processed transcript and metadata
        return {
            'transcript': full_transcript,
            'metadata': metadata
        }
        
    except Exception as e:
        print(f"Error processing transcript: {str(e)}")
        raise e
