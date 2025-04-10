# Podcast Processing Pipeline

An automated podcast processing pipeline using AWS Bedrock Data Automation for transcription and Claude 3.7 for summarization.

## Architecture

This solution implements a fully automated serverless pipeline for processing podcast audio files:

1. Upload MP3 files to an S3 bucket
2. Automatically trigger a Step Functions workflow
3. Transcribe audio using Bedrock Data Automation
4. Process and clean the transcript
5. Generate a summary using Claude 3.7
6. Format and store markdown output

## Key Components

- **S3 Buckets**: For storing input MP3 files, intermediate transcripts, and output summaries
- **AWS Lambda**: For processing functions and Bedrock integration
- **AWS Step Functions**: For orchestrating the workflow
- **AWS Bedrock**: For transcription (Data Automation) and summarization (Claude 3.7)

## Implementation Details

### Lambda Proxy Pattern for Bedrock

This project uses Lambda functions as proxies to interact with Bedrock Data Automation, rather than direct Step Functions service integrations, to avoid service compatibility issues with newly released Bedrock features.

- `src/functions/bedrock-transcribe`: Lambda function to initiate transcription jobs
- `src/functions/bedrock-status`: Lambda function to check job status
- `src/functions/transcript-processor`: Processes raw transcripts
- `src/functions/summarizer`: Generates summaries using Claude 3.7
- `src/functions/formatter`: Creates formatted markdown output

### Infrastructure as Code

The infrastructure is defined using AWS CDK with a proper stack separation:

- `StorageStack`: Manages S3 buckets for transcripts and outputs
- `LambdaStack`: Contains Lambda function definitions
- `StepFunctionsStack`: Defines the workflow and state machine
- `TriggersStack`: Manages S3 event notifications to trigger the workflow

## Testing

Run the local test suite to verify functionality:

```bash
./test-local.sh
```

This will:
1. Test the Bedrock Lambda proxy functions
2. Test the transcript processor
3. Test the summarizer with Claude 3.7
4. Test the markdown formatter

## Deployment

Deploy the full solution to AWS:

```bash
./deploy.sh
```

The script will:
1. Install dependencies
2. Bootstrap your AWS environment (if needed)
3. Deploy all stacks

## Usage

1. Upload an MP3 file to the input S3 bucket with the `uploads/` prefix
2. The Step Functions workflow will automatically start processing
3. The summarized markdown output will be available in the output bucket

## Customization

- Modify the system prompt in the summarizer function to customize the output format
- Adjust wait times in the Step Functions workflow based on your podcast length
- Update the formatter function to change the markdown structure

## Debugging

If you encounter deployment issues with Bedrock service integrations, check that:
- You're deploying to a region where Bedrock is fully available (us-west-2 recommended)
- The Lambda proxy approach bypasses Step Functions service integration limitations
