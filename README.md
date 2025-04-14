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

# Create the boto3 Lambda layer (required before first deployment)
./create-boto3-layer.sh

# Deploy the solution (will bootstrap CDK if needed)
./deploy.sh
```

The deployment process:
1. Install dependencies
2. Create the boto3 Lambda layer (needs to be run once or when updating boto3)
3. Bootstrap your AWS environment (if needed)
4. Deploy all stacks

## Usage

1. Upload an MP3 file to the input S3 bucket with the `uploads/` prefix
2. The Step Functions workflow will automatically start processing
3. The summarized markdown output will be available in the output bucket

## Customizing the System Prompt

The summarizer uses a system prompt to guide Claude 3.7's output. You can customize this in:
`src/functions/summarizer/custom-system-prompt.json`

The system prompt defines the structure and content of the generated summary. You can modify it to:
1. Change the output format
2. Request different types of information
3. Adjust the style and tone of the summary
4. Add specific instructions for handling your content

Example format of a generated summary:

```markdown
# Episode 42: Understanding Machine Learning

## Topic: Artificial Intelligence

In this episode, the hosts discuss the fundamentals of machine learning and its applications in everyday technology. They explore how AI systems learn from data and make predictions.

## Key Insights

1. **Types of ML**: Overview of supervised, unsupervised, and reinforcement learning
2. **Data requirements**: How to prepare and structure data for ML models
3. **Ethical considerations**: Addressing bias and transparency in AI systems
4. **Practical applications**: Real-world examples of ML in various industries
5. **Future trends**: Emerging technologies and research directions

## Search Terms
- Machine learning fundamentals
- AI data preparation
- Ethical AI development
- Practical machine learning applications
- Future of artificial intelligence
```

To customize the system prompt for your specific content:
1. Open the `custom-system-prompt.json` file
2. Modify the "systemPrompt" value with your desired instructions
3. Be specific about the structure and elements you want in the output
4. Redeploy the application for changes to take effect

## Troubleshooting

If you encounter deployment issues with Bedrock service integrations, check that:
- You're deploying to a region where Bedrock is fully available (us-west-2 recommended)
- Your AWS account has been granted access to Bedrock services
- The Lambda proxy approach bypasses Step Functions service integration limitations

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
