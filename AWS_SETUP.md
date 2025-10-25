# AWS Bedrock Setup Guide

This guide will help you set up AWS Bedrock for enhanced sign language analysis in your ASL Form Correction app.

## Prerequisites

1. AWS Account with Bedrock access
2. AWS CLI installed and configured
3. Node.js and npm installed

## Step 1: Enable Bedrock Models

1. Go to the AWS Bedrock console
2. Navigate to "Model access" in the left sidebar
3. Request access to the following models:
   - **Claude 3 Sonnet** (anthropic.claude-3-sonnet-20240229-v1:0)
   - **Claude 3 Haiku** (optional, for faster responses)

## Step 2: Create Cognito Identity Pool

1. Go to Amazon Cognito console
2. Click "Create identity pool"
3. Choose "Allow unauthenticated identities"
4. Create the pool and note the Identity Pool ID

## Step 3: Configure IAM Permissions

Create an IAM role for unauthenticated users with the following policy:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel"
            ],
            "Resource": [
                "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"
            ]
        }
    ]
}
```

## Step 4: Environment Configuration

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Update the values in `.env`:
   ```env
   REACT_APP_AWS_REGION=us-east-1
   REACT_APP_COGNITO_IDENTITY_POOL_ID=us-east-1:your-pool-id-here
   REACT_APP_USE_BEDROCK=true
   REACT_APP_FALLBACK_TO_MEDIAPIPE=true
   ```

## Step 5: Test the Setup

1. Start your app:
   ```bash
   npm start
   ```

2. The app should show "engine: bedrock-claude" when Bedrock is working
3. Try capturing a sign - you should see detailed AI feedback

## Troubleshooting

### Common Issues

1. **"Bedrock not available" error**
   - Check your AWS credentials
   - Verify the Identity Pool ID is correct
   - Ensure the region supports Bedrock

2. **"Model access denied" error**
   - Request access to Claude 3 Sonnet in the Bedrock console
   - Wait for approval (can take a few minutes)

3. **CORS errors**
   - This shouldn't happen with Cognito Identity Pool
   - If it does, check your IAM role permissions

### Cost Considerations

- Claude 3 Sonnet costs approximately $3 per 1M input tokens
- Each image analysis uses ~500-1000 tokens
- Consider using Claude 3 Haiku for lower costs (~$0.25 per 1M tokens)

### Alternative Authentication Methods

Instead of Cognito Identity Pool, you can use:

1. **AWS Amplify** (recommended for production)
2. **Direct AWS credentials** (development only)
3. **AWS STS assume role** (for advanced setups)

Update the `bedrockService.js` credentials configuration accordingly.

## Production Considerations

1. **Security**: Never expose AWS credentials in client-side code
2. **Rate limiting**: Implement request throttling
3. **Error handling**: Add retry logic for transient failures
4. **Monitoring**: Set up CloudWatch metrics for usage tracking
5. **Cost optimization**: Consider caching results for identical images