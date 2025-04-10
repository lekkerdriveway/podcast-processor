import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as s3 from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';

interface LambdaStackProps extends cdk.StackProps {
  inputBucket?: s3.Bucket; // Made optional
  transcriptsBucket: s3.Bucket;
  outputBucket: s3.Bucket;
}

export class LambdaStack extends cdk.Stack {
  public readonly transcriptProcessorFunction: lambda.Function;
  public readonly summarizerFunction: lambda.Function;
  public readonly formatterFunction: lambda.Function;

  constructor(scope: Construct, id: string, props: LambdaStackProps) {
    super(scope, id, props);

    // Create Lambda functions
    this.transcriptProcessorFunction = new lambda.Function(this, 'TranscriptProcessor', {
      runtime: lambda.Runtime.PYTHON_3_9,
      handler: 'index.handler',
      code: lambda.Code.fromAsset('src/functions/transcript-processor'),
      environment: {
        TRANSCRIPTS_BUCKET: props.transcriptsBucket.bucketName,
      },
      timeout: cdk.Duration.seconds(30),
      memorySize: 256,
    });

    this.summarizerFunction = new lambda.Function(this, 'Summarizer', {
      runtime: lambda.Runtime.PYTHON_3_9,
      handler: 'index.handler',
      code: lambda.Code.fromAsset('src/functions/summarizer'),
      environment: {
        MODEL_ID: 'us.anthropic.claude-3-7-sonnet-20250219-v1:0',
      },
      timeout: cdk.Duration.minutes(5), // Longer timeout for Bedrock API calls
      memorySize: 512,
    });

    this.formatterFunction = new lambda.Function(this, 'Formatter', {
      runtime: lambda.Runtime.PYTHON_3_9,
      handler: 'index.handler',
      code: lambda.Code.fromAsset('src/functions/formatter'),
      environment: {
        OUTPUT_BUCKET: props.outputBucket.bucketName,
      },
      timeout: cdk.Duration.seconds(30),
      memorySize: 256,
    });

    // Grant permissions
    props.transcriptsBucket.grantRead(this.transcriptProcessorFunction);
    props.outputBucket.grantWrite(this.formatterFunction);
    
    // Add Bedrock permissions to summarizer
    this.summarizerFunction.addToRolePolicy(new iam.PolicyStatement({
      actions: [
        'bedrock:InvokeModel',
        'bedrock:InvokeModelWithResponseStream'
      ],
      resources: ['*'], // In production, scope this down to specific model ARNs
    }));

    // Outputs
    new cdk.CfnOutput(this, 'TranscriptProcessorFunctionArn', {
      value: this.transcriptProcessorFunction.functionArn,
      description: 'ARN of the transcript processor Lambda function',
    });

    new cdk.CfnOutput(this, 'SummarizerFunctionArn', {
      value: this.summarizerFunction.functionArn,
      description: 'ARN of the summarizer Lambda function',
    });

    new cdk.CfnOutput(this, 'FormatterFunctionArn', {
      value: this.formatterFunction.functionArn,
      description: 'ARN of the formatter Lambda function',
    });
  }
}
