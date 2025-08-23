#!/usr/bin/env python3
"""
Periodic test to verify all key Lambda functions have proper alias + provisioned concurrency setup
Run this test regularly to ensure no cold starts on critical functions
"""
import boto3
import json
import sys
from typing import Dict, List

def test_provisioned_concurrency():
    """Test that all key functions have aliases with provisioned concurrency"""
    
    # Functions that should have provisioned concurrency
    REQUIRED_FUNCTIONS = [
        'ListPredictions',
        'MakeCallStreamFunction', 
        'LogCall'
    ]
    
    # Initialize AWS clients
    cf_client = boto3.client('cloudformation', region_name='us-west-2')
    lambda_client = boto3.client('lambda', region_name='us-west-2')
    apigateway_client = boto3.client('apigateway', region_name='us-west-2')
    
    print("🔍 Testing Provisioned Concurrency Setup")
    print("=" * 60)
    
    results = []
    
    for logical_id in REQUIRED_FUNCTIONS:
        print(f"\n📋 Testing {logical_id}...")
        
        try:
            # Get physical function name from CloudFormation
            response = cf_client.describe_stack_resources(
                StackName='calledit-backend',
                LogicalResourceId=logical_id
            )
            function_name = response['StackResources'][0]['PhysicalResourceId']
            print(f"   Function: {function_name}")
            
            # Check alias exists
            try:
                alias_response = lambda_client.get_alias(
                    FunctionName=function_name,
                    Name='live'
                )
                print(f"   ✅ Alias 'live' exists, points to version {alias_response['FunctionVersion']}")
                
                # Check provisioned concurrency
                try:
                    pc_response = lambda_client.get_provisioned_concurrency_config(
                        FunctionName=function_name,
                        Qualifier='live'
                    )
                    
                    status = pc_response['Status']
                    requested = pc_response['RequestedProvisionedConcurrentExecutions']
                    available = pc_response['AvailableProvisionedConcurrentExecutions']
                    
                    if status == 'READY' and available >= 1:
                        print(f"   ✅ Provisioned Concurrency: {available}/{requested} units READY")
                        result = 'PASS'
                    else:
                        print(f"   ❌ Provisioned Concurrency: Status={status}, Available={available}")
                        result = 'FAIL'
                        
                except Exception as e:
                    print(f"   ❌ No provisioned concurrency configured: {e}")
                    result = 'FAIL'
                    
            except Exception as e:
                print(f"   ❌ Alias 'live' not found: {e}")
                result = 'FAIL'
                
        except Exception as e:
            print(f"   ❌ Function not found in CloudFormation: {e}")
            result = 'FAIL'
            
        results.append({
            'function': logical_id,
            'result': result
        })
    
    # Test API Gateway integrations point to aliases
    print(f"\n🌐 Testing API Gateway Integrations...")
    
    try:
        # Test ListPredictions API integration
        resources = apigateway_client.get_resources(restApiId='zvdf8sswt3')
        list_pred_resource = next(r for r in resources['items'] if r.get('pathPart') == 'list-predictions')
        
        integration = apigateway_client.get_integration(
            restApiId='zvdf8sswt3',
            resourceId=list_pred_resource['id'],
            httpMethod='GET'
        )
        
        if ':live/invocations' in integration['uri']:
            print("   ✅ ListPredictions API calls alias")
        else:
            print("   ❌ ListPredictions API calls function directly")
            results.append({'function': 'ListPredictions-API', 'result': 'FAIL'})
            
    except Exception as e:
        print(f"   ❌ API Gateway test failed: {e}")
        results.append({'function': 'API-Gateway', 'result': 'FAIL'})
    
    # Summary
    print(f"\n📊 Test Results Summary:")
    print("-" * 40)
    
    passed = sum(1 for r in results if r['result'] == 'PASS')
    total = len(results)
    
    for result in results:
        status = "✅ PASS" if result['result'] == 'PASS' else "❌ FAIL"
        print(f"   {result['function']}: {status}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All provisioned concurrency tests PASSED!")
    else:
        print("⚠️  Some tests FAILED - cold starts may occur!")
    
    # Use assertion instead of return for pytest compatibility
    assert passed == total, f"Only {passed}/{total} provisioned concurrency tests passed"

if __name__ == "__main__":
    success = test_provisioned_concurrency()
    sys.exit(0 if success else 1)