import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import * as s3n from 'aws-cdk-lib/aws-s3-notifications';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

interface TriggersStackProps extends cdk.StackProps {
  stateMachine?: sfn.StateMachine; // Make stateMachine optional
  inputBucket: s3.Bucket; // Input bucket from the StorageStack
}

export class TriggersStack extends cdk.Stack {
  public readonly inputBucket: s3.Bucket;
  private s3EventBridgeFunction?: lambda.Function; // Store the function to update later
  private stateMachine?: sfn.StateMachine; // Store the state machine

  constructor(scope: Construct, id: string, props: TriggersStackProps) {
    super(scope, id, props);

    // We now use the input bucket passed from the StorageStack
    this.inputBucket = props.inputBucket;

    // Create a Lambda function to bridge S3 events to Step Functions
    // Using inline code with Node.js 16.x to use AWS SDK v2 which is included in the runtime
    this.s3EventBridgeFunction = new lambda.Function(this, 'S3EventBridgeFunction', {
      runtime: lambda.Runtime.NODEJS_16_X, // Use Node.js 16.x which includes AWS SDK v2
      handler: 'index.handler',
      code: lambda.Code.fromInline(`
        // AWS SDK v2 is available in Node.js 16.x runtime
        const AWS = require('aws-sdk');
        const stepfunctions = new AWS.StepFunctions();
        
        /**
         * Lambda handler for S3 events that triggers a Step Functions workflow
         */
        exports.handler = async (event) => {
          console.log('Received S3 event:', JSON.stringify(event, null, 2));
          
          try {
            // Get the state machine ARN from environment variable
            const stateMachineArn = process.env.STATE_MACHINE_ARN;
            if (!stateMachineArn) {
              throw new Error('STATE_MACHINE_ARN environment variable is not set');
            }
            
            // Process each S3 record
            const results = await Promise.all(
              event.Records.map(async (record) => {
                const bucket = record.s3.bucket.name;
                const key = record.s3.object.key;
                
                console.log(\`Processing S3 event for s3://\${bucket}/\${key}\`);
                
                try {
                  // Create input for the state machine
                  const input = JSON.stringify({ bucket, key });
                  
                  // Start the execution
                  const response = await stepfunctions.startExecution({
                    stateMachineArn,
                    input
                  }).promise();
                  
                  console.log(\`Started execution: \${response.executionArn} for s3://\${bucket}/\${key}\`);
                  
                  return {
                    bucket,
                    key,
                    executionArn: response.executionArn
                  };
                } catch (recordError) {
                  console.error(\`Error processing record s3://\${bucket}/\${key}:\`, recordError);
                  // Return error info but don't fail the whole batch
                  return {
                    bucket,
                    key,
                    error: recordError.message
                  };
                }
              })
            );
            
            console.log('Finished processing executions:', results);
            
            return {
              status: 'success',
              executions: results
            };
          } catch (error) {
            console.error('Error processing S3 event batch:', error);
            throw error;
          }
        };
      `),
      environment: {
        // We'll set this later when we have the state machine
        STATE_MACHINE_ARN: props.stateMachine?.stateMachineArn || 'WILL_BE_SET_LATER'
      },
      memorySize: 256,
      timeout: cdk.Duration.seconds(30)
    });
    
    // Store the state machine if provided
    if (props.stateMachine) {
      this.setStateMachine(props.stateMachine);
    }
    
    // Add S3 event notification to trigger the Lambda
    this.inputBucket.addEventNotification(
      s3.EventType.OBJECT_CREATED,
      new s3n.LambdaDestination(this.s3EventBridgeFunction),
      { prefix: 'uploads/' } // Optional prefix filter
    );

    // Output the bucket name
    new cdk.CfnOutput(this, 'InputBucketName', {
      value: this.inputBucket.bucketName,
      description: 'Name of the input bucket for MP3 files',
    });

    // Output the Lambda function ARN
    new cdk.CfnOutput(this, 'S3EventBridgeFunctionArn', {
      value: this.s3EventBridgeFunction.functionArn,
      description: 'ARN of the S3 event bridge Lambda function',
    });
  }

  // Method to set the state machine after stack creation
  public setStateMachine(stateMachine: sfn.StateMachine): void {
    this.stateMachine = stateMachine;
    
    // Update the Lambda function environment variable
    if (this.s3EventBridgeFunction) {
      // Add the state machine ARN to the Lambda environment
      this.s3EventBridgeFunction.addEnvironment('STATE_MACHINE_ARN', stateMachine.stateMachineArn);
      
      // Grant permission to invoke the state machine
      stateMachine.grantStartExecution(this.s3EventBridgeFunction);
    }
  }
}
