#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { StorageStack } from '../lib/storage-stack';
import { LambdaStack } from '../lib/lambda-stack';
import { StepFunctionsStack } from '../lib/step-functions-stack';
import { NotificationsStack } from '../lib/notifications-stack';

const app = new cdk.App();

// Force us-west-2 region for all stacks
const env = { 
  account: process.env.CDK_DEFAULT_ACCOUNT, 
  region: 'us-west-2' // Always use us-west-2 for all stacks
};

// Log the environment settings for debugging
console.log(`Deploying with account=${env.account}, region=${env.region}`);

// Verify we're using the correct region
if (process.env.CDK_DEFAULT_REGION && process.env.CDK_DEFAULT_REGION !== 'us-west-2') {
  console.warn(`WARNING: Environment has CDK_DEFAULT_REGION=${process.env.CDK_DEFAULT_REGION}, but we're forcing us-west-2`);
}

// Create the storage stack (now only transcripts and output buckets)
const storageStack = new StorageStack(app, 'PodcastProcessorStorageStack', {
  env,
});

// Create the Lambda stack
const lambdaStack = new LambdaStack(app, 'PodcastProcessorLambdaStack', {
  env,
  transcriptsBucket: storageStack.transcriptsBucket,
  outputBucket: storageStack.outputBucket,
});

// Create the Step Functions stack with the input bucket from StorageStack
const stepFunctionsStack = new StepFunctionsStack(app, 'PodcastProcessorStepFunctionsStack', {
  env,
  inputBucket: storageStack.inputBucket, // Pass the input bucket from StorageStack
  transcriptsBucket: storageStack.transcriptsBucket,
  outputBucket: storageStack.outputBucket,
  transcriptProcessorFunction: lambdaStack.transcriptProcessorFunction,
  summarizerFunction: lambdaStack.summarizerFunction,
  formatterFunction: lambdaStack.formatterFunction,
});

// Create the Notifications stack to connect S3 events to Step Functions
const notificationsStack = new NotificationsStack(app, 'PodcastProcessorNotificationsStack', {
  env,
  inputBucket: storageStack.inputBucket,
  stateMachine: stepFunctionsStack.stateMachine
});

// Add dependencies to ensure stacks are created in the correct order
lambdaStack.addDependency(storageStack);
stepFunctionsStack.addDependency(lambdaStack);
notificationsStack.addDependency(storageStack);
notificationsStack.addDependency(stepFunctionsStack);
