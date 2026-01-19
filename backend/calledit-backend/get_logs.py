#!/usr/bin/env python3
"""
Quick script to fetch CloudWatch logs for the Lambda function
"""
import boto3
import sys
from datetime import datetime, timedelta

def get_lambda_logs(function_name_pattern, minutes=10):
    """Fetch recent logs from CloudWatch"""
    logs_client = boto3.client('logs', region_name='us-west-2')
    
    # Find log groups matching pattern
    response = logs_client.describe_log_groups(
        logGroupNamePrefix=f'/aws/lambda/{function_name_pattern}'
    )
    
    if not response['logGroups']:
        print(f"No log groups found matching: /aws/lambda/{function_name_pattern}")
        return
    
    log_group = response['logGroups'][0]['logGroupName']
    print(f"Reading logs from: {log_group}\n")
    print("=" * 80)
    
    # Get recent log streams
    start_time = int((datetime.now() - timedelta(minutes=minutes)).timestamp() * 1000)
    
    try:
        # Get log events
        response = logs_client.filter_log_events(
            logGroupName=log_group,
            startTime=start_time,
            limit=100
        )
        
        if not response['events']:
            print("No recent log events found")
            return
        
        # Print events
        for event in response['events']:
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            message = event['message'].strip()
            print(f"[{timestamp}] {message}")
            
    except Exception as e:
        print(f"Error fetching logs: {e}")

if __name__ == '__main__':
    function_pattern = 'calledit-backend-MakeCallStreamFunction'
    get_lambda_logs(function_pattern, minutes=15)
