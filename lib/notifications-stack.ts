import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import * as cr from 'aws-cdk-lib/custom-resources';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

interface NotificationsStackProps extends cdk.StackProps {
  inputBucket: s3.Bucket;
  stateMachine: sfn.StateMachine;
}

export class NotificationsStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: NotificationsStackProps) {
    super(scope, id, props);

    // Create a Lambda function to bridge S3 events to Step Functions
    const s3EventBridgeFunction = new lambda.Function(this, 'S3EventBridgeFunction', {
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
    props.stateMachine.grantStartExecution(s3EventBridgeFunction);
    
    // Create a custom resource to set up the S3 event notification
    // This avoids the circular dependency that happens with the higher-level construct
    const notificationFunctionRole = new iam.Role(this, 'NotificationFunctionRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole')
      ]
    });
    
    // Add S3 permissions to the role
    notificationFunctionRole.addToPolicy(new iam.PolicyStatement({
      actions: ['s3:PutBucketNotification', 's3:GetBucketNotification'],
      resources: [props.inputBucket.bucketArn]
    }));
    
    // Create the notification function
    const notificationFunction = new lambda.Function(this, 'NotificationFunction', {
      runtime: lambda.Runtime.NODEJS_16_X,
      handler: 'index.handler',
      code: lambda.Code.fromInline(`
        const AWS = require('aws-sdk');
        const s3 = new AWS.S3();
        const response = require('cfn-response');
        
        exports.handler = async (event, context) => {
          console.log('Event:', JSON.stringify(event, null, 2));
          
          try {
            const props = event.ResourceProperties;
            const bucketName = props.BucketName;
            const lambdaArn = props.LambdaArn;
            const prefix = props.Prefix || '';
            
            if (event.RequestType === 'Delete') {
              // Remove notification configuration
              await s3.putBucketNotificationConfiguration({
                Bucket: bucketName,
                NotificationConfiguration: {}
              }).promise();
              
              await response.send(event, context, response.SUCCESS, {});
              return;
            }
            
            // Create or update notification
            await s3.putBucketNotificationConfiguration({
              Bucket: bucketName,
              NotificationConfiguration: {
                LambdaFunctionConfigurations: [
                  {
                    Events: ['s3:ObjectCreated:*'],
                    LambdaFunctionArn: lambdaArn,
                    Filter: {
                      Key: {
                        FilterRules: [
                          {
                            Name: 'prefix',
                            Value: prefix
                          }
                        ]
                      }
                    }
                  }
                ]
              }
            }).promise();
            
            await response.send(event, context, response.SUCCESS, {});
          } catch (error) {
            console.error('Error:', error);
            await response.send(event, context, response.FAILED, { Error: error.message });
          }
        };
      `),
      timeout: cdk.Duration.seconds(30),
      role: notificationFunctionRole
    });
    
    // Create the custom resource provider
    const provider = new cr.Provider(this, 'NotificationProvider', {
      onEventHandler: notificationFunction
    });
    
    // Create the custom resource
    new cdk.CustomResource(this, 'BucketNotificationResource', {
      serviceToken: provider.serviceToken,
      properties: {
        BucketName: props.inputBucket.bucketName,
        LambdaArn: s3EventBridgeFunction.functionArn,
        Prefix: 'uploads/'
      }
    });

    // Grant the S3 bucket permission to invoke the Lambda function
    s3EventBridgeFunction.addPermission('AllowS3Invocation', {
      principal: new iam.ServicePrincipal('s3.amazonaws.com'),
      action: 'lambda:InvokeFunction',
      sourceArn: props.inputBucket.bucketArn
    });

    // Output the Lambda function ARN for reference
    new cdk.CfnOutput(this, 'S3EventBridgeFunctionArn', {
      value: s3EventBridgeFunction.functionArn,
      description: 'ARN of the S3 event bridge Lambda function',
    });
  }
}
