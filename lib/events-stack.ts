import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import * as s3n from 'aws-cdk-lib/aws-s3-notifications';
import { Construct } from 'constructs';

interface EventsStackProps extends cdk.StackProps {
  inputBucket: s3.Bucket; // Input bucket from the StorageStack
  stateMachine: sfn.StateMachine; // State machine from the StepFunctionsStack
}

export class EventsStack extends cdk.Stack {
  private s3EventBridgeFunction: lambda.Function;

  constructor(scope: Construct, id: string, props: EventsStackProps) {
    super(scope, id, props);

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
        STATE_MACHINE_ARN: props.stateMachine.stateMachineArn
      },
      memorySize: 256,
      timeout: cdk.Duration.seconds(30)
    });
    
    // Grant permission to invoke the state machine
    props.stateMachine.grantStartExecution(this.s3EventBridgeFunction);
    
    // Add S3 event notification to trigger the Lambda
    props.inputBucket.addEventNotification(
      s3.EventType.OBJECT_CREATED,
      new s3n.LambdaDestination(this.s3EventBridgeFunction),
      { prefix: 'uploads/' } // Optional prefix filter
    );

    // Output the Lambda function ARN
    new cdk.CfnOutput(this, 'S3EventBridgeFunctionArn', {
      value: this.s3EventBridgeFunction.functionArn,
      description: 'ARN of the S3 event bridge Lambda function',
    });
  }
}
