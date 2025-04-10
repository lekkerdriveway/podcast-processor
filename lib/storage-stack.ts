import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

export class StorageStack extends cdk.Stack {
  public readonly transcriptsBucket: s3.Bucket;
  public readonly outputBucket: s3.Bucket;
  public readonly inputBucket: s3.Bucket;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Intermediate storage for transcripts
    this.transcriptsBucket = new s3.Bucket(this, 'TranscriptsBucket', {
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
    });

    // Add permissions for Bedrock Data Automation to access the transcripts bucket
    const bedrockTranscriptsPolicy = new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      principals: [new iam.ServicePrincipal('bedrock.amazonaws.com')],
      actions: ['s3:GetObject', 's3:PutObject', 's3:ListBucket'],
      resources: [this.transcriptsBucket.bucketArn, `${this.transcriptsBucket.bucketArn}/*`]
    });
    this.transcriptsBucket.addToResourcePolicy(bedrockTranscriptsPolicy);

    // Input bucket for MP3 files
    this.inputBucket = new s3.Bucket(this, 'PodcastInputBucket', {
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      lifecycleRules: [
        {
          expiration: cdk.Duration.days(30),
        },
      ],
    });
    
    // Add permissions for Bedrock Data Automation to access the input bucket
    const bedrockInputPolicy = new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      principals: [new iam.ServicePrincipal('bedrock.amazonaws.com')],
      actions: ['s3:GetObject', 's3:ListBucket'],
      resources: [this.inputBucket.bucketArn, `${this.inputBucket.bucketArn}/*`]
    });
    this.inputBucket.addToResourcePolicy(bedrockInputPolicy);

    // Output bucket for markdown summaries
    this.outputBucket = new s3.Bucket(this, 'SummariesOutputBucket', {
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
    });

    // Add permissions for Bedrock Data Automation to access the output bucket
    const bedrockOutputPolicy = new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      principals: [new iam.ServicePrincipal('bedrock.amazonaws.com')],
      actions: ['s3:GetObject', 's3:PutObject', 's3:ListBucket'],
      resources: [this.outputBucket.bucketArn, `${this.outputBucket.bucketArn}/*`]
    });
    this.outputBucket.addToResourcePolicy(bedrockOutputPolicy);

    // Output for cross-stack references
    new cdk.CfnOutput(this, 'TranscriptsBucketName', {
      value: this.transcriptsBucket.bucketName,
      description: 'Name of the bucket for transcript storage',
    });

    new cdk.CfnOutput(this, 'OutputBucketName', {
      value: this.outputBucket.bucketName,
      description: 'Name of the output bucket for markdown summaries',
    });

    new cdk.CfnOutput(this, 'InputBucketName', {
      value: this.inputBucket.bucketName,
      description: 'Name of the input bucket for MP3 files',
    });
  }
}
