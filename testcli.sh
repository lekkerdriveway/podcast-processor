# First, create a unique client token
CLIENT_TOKEN=$(uuidgen | tr -d '-')

# Set your bucket names (replace with your actual bucket names)
INPUT_BUCKET="podcastprocessortriggerss-podcastinputbuckete4b360-ddrq30cjzdjz"
OUTPUT_BUCKET="podcastprocessorstoragest-transcriptsbucketf640f86-gndfzzaqytbc"  # Replace with your actual transcript bucket name

# Set your project ARN (replace with your actual project ARN from Lambda logs)
PROJECT_ARN="arn:aws:bedrock:us-west-2:574482439656:data-automation-project/5300463dbdb2"

PROFILE_ARN='arn:aws:bedrock:us-west-2:574482439656:data-automation-profile/us.data-automation-v1'
# Set the input file key (replace with your actual file)
INPUT_FILE="uploads/pod1.mp3"

# Run the command in debug mode to see the full request and response
aws bedrock-data-automation-runtime invoke-data-automation-async \
  --client-token "$CLIENT_TOKEN" \
  --data-automation-profile-arn "$PROFILE_ARN" \
  --data-automation-configuration "{\"dataAutomationProjectArn\": \"$PROJECT_ARN\"}" \
  --input-configuration "{\"s3Uri\": \"s3://$INPUT_BUCKET/$INPUT_FILE\"}" \
  --output-configuration "{\"s3Uri\": \"s3://$OUTPUT_BUCKET/transcripts/\"}" \
  --notification-configuration "{\"eventBridgeConfiguration\": {\"eventBridgeEnabled\": true}}" \
  --region us-west-2 \
  --debug
