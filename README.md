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

[Architecture Diagram](docs/architecture.md)

## Prerequisites

- **AWS Account** with permissions for:
  - S3, Lambda, Step Functions, IAM, CloudFormation
  - Bedrock access for Claude 3.7 and Data Automation
- **Node.js** (v16 or later)
- **AWS CLI** configured with appropriate credentials
- **AWS CDK** installed globally (`npm install -g aws-cdk`)

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

## Deployment

Deploy the full solution to AWS:

```bash
# Install dependencies
npm install

# Deploy the solution (will bootstrap CDK if needed)
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

## Customizing the System Prompt

The summarizer uses a system prompt to guide Claude 3.7's output. You can customize this in:
`src/functions/summarizer/custom-system-prompt.json`

The default prompt asks Claude to generate:
1. Episode name
2. Film featured in the episode
3. Short episode summary
4. A "cheat sheet" of actionable insights
5. Search terms for the episode

Example format:

```markdown
# Episode 5: Raising Resilient Kids

## Film: Inside Out

In this episode Billy and Nick discuss emotional resilience in children, in the context of Pixar's Inside Out. They explore how the film's portrayal of emotions offers a framework for helping children understand and process their feelings.

## Parenting Cheat Sheet: Building Emotional Resilience

1. **Name emotions**: Help children identify and label their feelings
2. **Validate experiences**: Acknowledge that all emotions are valid and important
3. **Create safe spaces**: Designate areas where children can express big emotions
4. **Model regulation**: Demonstrate healthy emotional processing yourself
5. **Use media as teaching tools**: Reference familiar characters when discussing emotions

## Search Terms
- Emotional intelligence children
- Inside Out parenting lessons
- Resilience skills toddlers
- Validating children's feelings
- Pediatric emotional development
```

## Troubleshooting

If you encounter deployment issues with Bedrock service integrations, check that:
- You're deploying to a region where Bedrock is fully available (us-west-2 recommended)
- Your AWS account has been granted access to Bedrock services
- The Lambda proxy approach bypasses Step Functions service integration limitations

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
