import boto3

# Claude model ID
CLAUDE_MODEL = "anthropic.claude-3-5-sonnet-20241022-v2:0"

# AWS Region (same one you set in aws configure)
AWS_REGION = "us-west-2"

# Create Claude client
claude_client = boto3.client(
    service_name='bedrock-runtime',
    region_name=AWS_REGION
)