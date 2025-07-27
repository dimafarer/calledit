#!/usr/bin/env python3
"""
Test script to verify API Gateway is calling the correct Lambda alias
"""
import requests
import json
import boto3

def test_api_gateway_integration():
    """Test that API Gateway calls the alias, not the function directly"""
    
    # API Gateway details
    api_id = "zvdf8sswt3"
    region = "us-west-2"
    resource_id = "xqqey9"  # list-predictions resource
    
    # Initialize AWS clients
    apigateway = boto3.client('apigateway', region_name=region)
    lambda_client = boto3.client('lambda', region_name=region)
    
    print("🔍 Testing API Gateway Lambda Integration")
    print("=" * 50)
    
    # 1. Check current API Gateway integration
    try:
        integration = apigateway.get_integration(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='GET'
        )
        
        current_uri = integration['uri']
        print(f"Current Integration URI: {current_uri}")
        
        # Check if it's pointing to alias or function
        if ':live' in current_uri:
            print("✅ API Gateway is calling the ALIAS")
        else:
            print("❌ API Gateway is calling the FUNCTION directly")
            
    except Exception as e:
        print(f"Error checking integration: {e}")
    
    # 2. Check Lambda alias exists
    try:
        function_name = "calledit-backend-ListPredictions-IhwjzJTTl8xC"
        alias_response = lambda_client.get_alias(
            FunctionName=function_name,
            Name='live'
        )
        print(f"✅ Alias 'live' exists: {alias_response['AliasArn']}")
        print(f"   Points to version: {alias_response['FunctionVersion']}")
        
    except Exception as e:
        print(f"❌ Error checking alias: {e}")
    
    # 3. Test actual API call
    api_url = f"https://{api_id}.execute-api.{region}.amazonaws.com/Prod/list-predictions"
    print(f"\n🌐 Testing API endpoint: {api_url}")
    
    try:
        response = requests.get(api_url)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 401:
            print("🔒 Expected 401 - endpoint requires authentication")
        else:
            print(f"Response: {response.text[:100]}...")
            
    except Exception as e:
        print(f"Error calling API: {e}")
    
    print("\n🎯 Expected Behavior:")
    print("- API Gateway should call ListPredictions:live alias")
    print("- Alias should point to specific version")
    print("- Provisioned concurrency should be on the alias")

if __name__ == "__main__":
    test_api_gateway_integration()