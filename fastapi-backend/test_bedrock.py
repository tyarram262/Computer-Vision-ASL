#!/usr/bin/env python3
"""
Test script to verify AWS Bedrock connection
"""

import os
import boto3
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_bedrock_connection():
    """Test if we can connect to AWS Bedrock"""
    print("🧪 Testing AWS Bedrock Connection")
    print("=" * 40)
    
    # Check environment variables
    required_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_REGION']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        return False
    
    print("✅ Environment variables found")
    print(f"   Region: {os.getenv('AWS_REGION')}")
    print(f"   Access Key: {os.getenv('AWS_ACCESS_KEY_ID')[:10]}...")
    
    try:
        # Initialize Bedrock client
        bedrock = boto3.client(
            'bedrock-runtime',
            region_name=os.getenv('AWS_REGION'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            aws_session_token=os.getenv('AWS_SESSION_TOKEN')
        )
        
        print("✅ Bedrock client initialized")
        
        # Test with a simple prompt
        test_prompt = "You are an ASL instructor. Say 'Hello' in a friendly way."
        
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 50,
            "messages": [
                {
                    "role": "user",
                    "content": test_prompt
                }
            ]
        }
        
        print("🔄 Testing model invocation...")
        
        response = bedrock.invoke_model(
            modelId="anthropic.claude-3-haiku-20240307-v1:0",
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response['body'].read())
        feedback = response_body['content'][0]['text'].strip()
        
        print("✅ Bedrock test successful!")
        print(f"   Response: {feedback}")
        
        return True
        
    except Exception as e:
        print(f"❌ Bedrock test failed: {e}")
        print("\n💡 Troubleshooting tips:")
        print("   1. Check if your AWS credentials are valid")
        print("   2. Verify you have access to Bedrock in your region")
        print("   3. Ensure Claude 3 Haiku model is enabled in Bedrock console")
        print("   4. Check if your session token is still valid (they expire)")
        
        return False

def test_fallback_feedback():
    """Test the fallback feedback system"""
    print("\n🔄 Testing fallback feedback...")
    
    from main import get_fallback_feedback
    
    test_codes = ["THUMB_LOW", "FINGERS_SPREAD", "GENERAL_FORM"]
    
    for code in test_codes:
        feedback = get_fallback_feedback(code)
        print(f"   {code}: {feedback}")
    
    print("✅ Fallback feedback working")

if __name__ == "__main__":
    success = test_bedrock_connection()
    test_fallback_feedback()
    
    print("\n" + "=" * 40)
    if success:
        print("🎉 All tests passed! Your Bedrock integration is ready.")
    else:
        print("⚠️  Bedrock not available, but fallback feedback will work.")
    print("\nYou can now start the FastAPI server with: python main.py")