import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import * as tasks from 'aws-cdk-lib/aws-stepfunctions-tasks';
import * as bedrock from 'aws-cdk-lib/aws-bedrock';
import * as s3n from 'aws-cdk-lib/aws-s3-notifications';
import { Construct } from 'constructs';

interface StepFunctionsStackProps extends cdk.StackProps {
  inputBucket?: s3.Bucket; // Made optional
  transcriptsBucket: s3.Bucket;
  outputBucket: s3.Bucket;
  transcriptProcessorFunction: lambda.Function;
  summarizerFunction: lambda.Function;
  formatterFunction: lambda.Function;
}

export class StepFunctionsStack extends cdk.Stack {
  public readonly stateMachine: sfn.StateMachine;

  constructor(scope: Construct, id: string, props: StepFunctionsStackProps) {
    super(scope, id, props);

    // Create a Bedrock Data Automation project
    const bedrockProject = new bedrock.CfnDataAutomationProject(this, 'PodcastTranscriptionProject', {
      projectName: 'PodcastTranscriptionProject',
      projectDescription: 'Automated transcription for podcast audio files',
      standardOutputConfiguration: {
        audio: {
          extraction: {
            category: {
              state: 'ENABLED',
              types: ['TRANSCRIPT']
            }
          }
        }
      }
    });

    // Create a Lambda layer with the latest boto3
    const boto3Layer = new lambda.LayerVersion(this, 'Boto3Layer', {
      code: lambda.Code.fromAsset('layers/boto3'),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_9],
      description: 'Latest boto3 version for Bedrock Data Automation API',
    });

    // Create Lambda proxies for Bedrock Data Automation
    const bedrockTranscribeFunction = new lambda.Function(this, 'BedrockTranscribeFunction', {
      runtime: lambda.Runtime.PYTHON_3_9,
      handler: 'index.handler',
      code: lambda.Code.fromAsset('src/functions/bedrock-transcribe'),
      environment: {
        TRANSCRIPTS_BUCKET: props.transcriptsBucket.bucketName,
        INPUT_BUCKET: props.inputBucket ? props.inputBucket.bucketName : '', // Add input bucket name as env var
        DATA_AUTOMATION_PROJECT_ARN: bedrockProject.attrProjectArn // Pass the project ARN as env var
      },
      timeout: cdk.Duration.seconds(60), // Increase timeout for project creation
      layers: [boto3Layer], // Add the layer with updated boto3
    });

    const bedrockStatusFunction = new lambda.Function(this, 'BedrockStatusFunction', {
      runtime: lambda.Runtime.PYTHON_3_9,
      handler: 'index.handler',
      code: lambda.Code.fromAsset('src/functions/bedrock-status'),
      timeout: cdk.Duration.seconds(30),
      layers: [boto3Layer], // Add the layer with updated boto3
    });

    // We're now constructing the profile ARN dynamically in the Lambda function
    
    // Add necessary permissions for Bedrock Data Automation API
    bedrockTranscribeFunction.addToRolePolicy(new iam.PolicyStatement({
      actions: [
        // Project management permissions
        'bedrock:CreateDataAutomationProject',
        'bedrock:ListDataAutomationProjects'
      ],
      resources: ['*']
    }));
    
    // Add specific permissions for InvokeDataAutomationAsync with the profile ARNs
    bedrockTranscribeFunction.addToRolePolicy(new iam.PolicyStatement({
      actions: [
        'bedrock:InvokeDataAutomationAsync'
      ],
      resources: ['*']
    }));
    
    // Add permission for model invocation and STS
    bedrockTranscribeFunction.addToRolePolicy(new iam.PolicyStatement({
      actions: [
        'bedrock:InvokeModel',
        'sts:GetCallerIdentity'  // Required for getting account ID
      ],
      resources: ['*']
    }));

    bedrockStatusFunction.addToRolePolicy(new iam.PolicyStatement({
      actions: [
        // Status check permission
        'bedrock:GetDataAutomationStatus'
      ],
      resources: ['*']
    }));

    // Allow Lambda to access S3 buckets
    props.transcriptsBucket.grantReadWrite(bedrockTranscribeFunction);
    props.transcriptsBucket.grantReadWrite(bedrockStatusFunction);
    if (props.inputBucket) {
      props.inputBucket.grantReadWrite(bedrockTranscribeFunction); // Changed from grantRead to grantReadWrite
    }

    // Define the Step Functions tasks
    
    // 1. Transcribe Audio using Bedrock Data Automation via Lambda
    const transcribeAudio = new tasks.LambdaInvoke(this, 'TranscribeAudio', {
      lambdaFunction: bedrockTranscribeFunction,
      payload: sfn.TaskInput.fromObject({
        ModelId: 'amazon.titan-tg1-large',
        bucket: sfn.JsonPath.stringAt('$$.Execution.Input.bucket'),
        key: sfn.JsonPath.stringAt('$$.Execution.Input.key')
      }),
      resultPath: '$.TranscriptionJob',
      retryOnServiceExceptions: true,
      // Remove outputPath to use the direct Lambda response
    });

    // 2. Wait for transcription to complete
    const waitForTranscription = new sfn.Wait(this, 'WaitForTranscription', {
      time: sfn.WaitTime.duration(cdk.Duration.seconds(30))
    });

    // 3. Check transcription status via Lambda
    const checkTranscriptionStatus = new tasks.LambdaInvoke(this, 'CheckTranscriptionStatus', {
      lambdaFunction: bedrockStatusFunction,
      payload: sfn.TaskInput.fromObject({
        JobId: sfn.JsonPath.stringAt('$.TranscriptionJob.Payload.JobId')
      }),
      resultPath: '$.TranscriptionStatus',
      retryOnServiceExceptions: true,
      // Remove outputPath to use the direct Lambda response
    });

    // Define success state
    const workflowComplete = new sfn.Succeed(this, 'WorkflowComplete');

    // Define error states
    const transcriptionFailed = new sfn.Fail(this, 'TranscriptionFailed', {
      cause: 'Transcription job failed',
      error: 'TranscriptionError'
    });

    const processingFailed = new sfn.Fail(this, 'ProcessingFailed', {
      cause: 'Transcript processing failed',
      error: 'ProcessingError'
    });

    const summarizationFailed = new sfn.Fail(this, 'SummarizationFailed', {
      cause: 'Summary generation failed',
      error: 'SummarizationError'
    });

    const formattingFailed = new sfn.Fail(this, 'FormattingFailed', {
      cause: 'Output formatting failed',
      error: 'FormattingError'
    });

    // Create processing tasks as separate tasks
    // Process transcript task
    const processTranscript = new tasks.LambdaInvoke(this, 'ProcessTranscript', {
      lambdaFunction: props.transcriptProcessorFunction,
      inputPath: '$',
      // Remove outputPath to use the direct Lambda response
      payload: sfn.TaskInput.fromObject({
        TranscriptionStatus: {
          OutputBucket: sfn.JsonPath.stringAt('$.TranscriptionStatus.Payload.OutputBucket'),
          // Use the OutputKey directly from the status function
          OutputKey: sfn.JsonPath.stringAt('$.TranscriptionStatus.Payload.OutputKey')
        },
        originalFileName: sfn.JsonPath.stringAt('$$.Execution.Input.key')
      }),
      retryOnServiceExceptions: true,
      resultPath: '$.ProcessingResult'
    });

    // 5. Generate summary using Claude 3.7
    const generateSummary = new tasks.LambdaInvoke(this, 'GenerateSummary', {
      lambdaFunction: props.summarizerFunction,
      inputPath: '$',
      // Remove outputPath to use the direct Lambda response
      payload: sfn.TaskInput.fromObject({
        transcript: sfn.JsonPath.stringAt('$.ProcessingResult.Payload.transcript'),
        metadata: sfn.JsonPath.stringAt('$.ProcessingResult.Payload.metadata')
      }),
      retryOnServiceExceptions: true,
      resultPath: '$.SummaryResult'
    });

    // 6. Format output as markdown
    const formatOutput = new tasks.LambdaInvoke(this, 'FormatOutput', {
      lambdaFunction: props.formatterFunction,
      inputPath: '$',
      // Remove outputPath to use the direct Lambda response
      payload: sfn.TaskInput.fromObject({
        summary: sfn.JsonPath.stringAt('$.SummaryResult.Payload.summary'),
        metadata: sfn.JsonPath.stringAt('$.SummaryResult.Payload.metadata')
      }),
      retryOnServiceExceptions: true,
      resultPath: '$.FormattingResult'
    });

    // Add error handling
    transcribeAudio.addCatch(transcriptionFailed);
    checkTranscriptionStatus.addCatch(transcriptionFailed);
    processTranscript.addCatch(processingFailed);
    generateSummary.addCatch(summarizationFailed);
    formatOutput.addCatch(formattingFailed);

    // Chain the post-processing tasks
    processTranscript
      .next(generateSummary)
      .next(formatOutput)
      .next(workflowComplete);

    // 4. Check if transcription is complete with explicit next states
    const isTranscriptionComplete = new sfn.Choice(this, 'IsTranscriptionComplete')
      .when(sfn.Condition.or(
        sfn.Condition.stringEquals('$.TranscriptionStatus.Payload.Status', 'COMPLETED'),
        sfn.Condition.stringEquals('$.TranscriptionStatus.Payload.Status', 'SUCCESS')
      ), processTranscript)
      .when(sfn.Condition.stringEquals('$.TranscriptionStatus.Payload.Status', 'FAILED'), transcriptionFailed)
      .otherwise(waitForTranscription);

    // Chain the initial steps together
    const definition = transcribeAudio
      .next(waitForTranscription)
      .next(checkTranscriptionStatus)
      .next(isTranscriptionComplete);

    // Create the state machine
    this.stateMachine = new sfn.StateMachine(this, 'PodcastProcessingStateMachine', {
      definition,
      timeout: cdk.Duration.minutes(30),
      tracingEnabled: true,
    });

    // S3 event notification is now handled in the NotificationsStack

    // Output the state machine ARN for reference
    new cdk.CfnOutput(this, 'StateMachineArn', {
      value: this.stateMachine.stateMachineArn,
      description: 'ARN of the podcast processing state machine',
    });
  }
}
