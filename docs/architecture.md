# Podcast Processor Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────────┐
│ S3 Bucket   │     │ Event Bridge │     │ Step Functions      │
│ (Input MP3) │────▶│ Notification │────▶│ Workflow            │
└─────────────┘     └──────────────┘     └──────────┬──────────┘
                                                    │
                                                    ▼
┌─────────────────┐     ┌───────────────────┐     ┌──────────────────┐
│ S3 Bucket       │     │ Lambda            │     │ Lambda            │
│ (Summaries)     │◀────│ (Formatter)       │◀────│ (Summarizer)      │
└─────────────────┘     └───────────────────┘     └──────────┬───────┘
                                                            │
                                                            ▼
                           ┌─────────────────┐     ┌──────────────────┐
                           │ Lambda           │     │ Lambda            │
                           │ (Transcript      │◀────│ (Bedrock Status)  │
                           │  Processor)      │     └──────────┬───────┘
                           └────────┬─────────┘                │
                                    │                          │
                                    ▼                          │
                           ┌─────────────────┐                 │
                           │ S3 Bucket       │◀────────────────┘
                           │ (Transcripts)   │
                           └────────┬────────┘
                                    │
                                    ▼
                           ┌─────────────────┐
                           │ Bedrock Data    │
                           │ Automation      │
                           └─────────────────┘

```

## Data Flow

1. User uploads an MP3 file to the input S3 bucket
2. S3 event notification triggers Step Functions workflow
3. Workflow launches Bedrock Data Automation for transcription via Lambda proxy
4. Bedrock Status Lambda monitors the transcription job
5. When complete, Transcript Processor Lambda extracts and cleans the text
6. Summarizer Lambda sends transcript to Claude 3.7 for summarization
7. Formatter Lambda converts the summary to markdown format
8. Final markdown summary is saved to the output S3 bucket

## AWS Services Used

- **S3**: Storage for input podcasts, transcripts, and output summaries
- **Lambda**: Processing functions including Bedrock integration
- **Step Functions**: Orchestration of the entire workflow
- **EventBridge**: Event notifications to trigger the workflow
- **Bedrock**: AI services for transcription and summarization
