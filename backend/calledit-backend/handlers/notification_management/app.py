#!/usr/bin/env python3
"""
Notification Management Lambda Handler
Handles SNS subscription management for crying/notification features
"""

import json
import logging
import os
import re
from typing import Dict, Any

import boto3
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize AWS clients
sns_client = boto3.client('sns')

# Environment variables
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN', '')

# CORS headers
CORS_HEADERS = {
    'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token',
    'Access-Control-Allow-Methods': 'OPTIONS,GET,POST',
    'Access-Control-Allow-Credentials': 'true',
    'Access-Control-Allow-Origin': '*'  # Update with specific origins in production
}

def get_user_from_event(event: Dict[str, Any]) -> str:
    """Extract user ID from Cognito context"""
    try:
        claims = event['requestContext']['authorizer']['claims']
        return claims.get('sub') or claims.get('email', 'unknown')
    except (KeyError, TypeError):
        return None

def is_valid_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """Main Lambda handler for notification management"""
    
    logger.info(f"Notification management invoked: {event.get('httpMethod')} {event.get('path')}")
    
    # Handle CORS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': ''
        }
    
    try:
        # Get user from Cognito context
        user_id = get_user_from_event(event)
        if not user_id:
            return {
                'statusCode': 401,
                'headers': CORS_HEADERS,
                'body': json.dumps({'error': 'User not authenticated'})
            }
        
        # Route based on path
        path = event.get('path', '')
        method = event.get('httpMethod', '')
        
        if path.endswith('/subscribe-notifications') and method == 'POST':
            return handle_subscribe(event, user_id)
        elif path.endswith('/unsubscribe-notifications') and method == 'POST':
            return handle_unsubscribe(event, user_id)
        elif path.endswith('/notification-status') and method == 'GET':
            return handle_status(event, user_id)
        else:
            return {
                'statusCode': 404,
                'headers': CORS_HEADERS,
                'body': json.dumps({'error': 'Endpoint not found'})
            }
            
    except Exception as e:
        logger.error(f"Error in notification management: {str(e)}")
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': 'Internal server error'})
        }

def handle_subscribe(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Handle email subscription to SNS topic"""
    
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        email = body.get('email', '').strip()
        
        if not email:
            return {
                'statusCode': 400,
                'headers': CORS_HEADERS,
                'body': json.dumps({'error': 'Email address is required'})
            }
        
        if not is_valid_email(email):
            return {
                'statusCode': 400,
                'headers': CORS_HEADERS,
                'body': json.dumps({'error': 'Invalid email address format'})
            }
        
        if not SNS_TOPIC_ARN:
            return {
                'statusCode': 500,
                'headers': CORS_HEADERS,
                'body': json.dumps({'error': 'SNS topic not configured'})
            }
        
        # Check if already subscribed
        existing_subscription = find_email_subscription(email)
        if existing_subscription:
            return {
                'statusCode': 200,
                'headers': CORS_HEADERS,
                'body': json.dumps({
                    'success': True,
                    'message': 'Email is already subscribed',
                    'subscription_arn': existing_subscription
                })
            }
        
        # Subscribe to SNS topic
        response = sns_client.subscribe(
            TopicArn=SNS_TOPIC_ARN,
            Protocol='email',
            Endpoint=email
        )
        
        subscription_arn = response.get('SubscriptionArn', 'pending confirmation')
        
        logger.info(f"Subscribed {email} to notifications: {subscription_arn}")
        
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps({
                'success': True,
                'message': 'Subscription request sent. Please check your email for confirmation.',
                'subscription_arn': subscription_arn
            })
        }
        
    except ClientError as e:
        logger.error(f"AWS error subscribing {email}: {str(e)}")
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': 'Failed to subscribe to notifications'})
        }
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }

def handle_unsubscribe(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Handle unsubscribe from SNS topic"""
    
    try:
        # For now, we'll need the user to provide their email or subscription ARN
        # In a production system, you'd store user->subscription mappings in DynamoDB
        
        # Get all subscriptions and let user unsubscribe from all their emails
        subscriptions = sns_client.list_subscriptions_by_topic(TopicArn=SNS_TOPIC_ARN)
        
        unsubscribed_count = 0
        for subscription in subscriptions.get('Subscriptions', []):
            if subscription.get('Protocol') == 'email':
                # For now, unsubscribe all email subscriptions
                # In production, you'd match by user ID stored in subscription attributes
                try:
                    sns_client.unsubscribe(SubscriptionArn=subscription['SubscriptionArn'])
                    unsubscribed_count += 1
                except ClientError as e:
                    logger.warning(f"Failed to unsubscribe {subscription['SubscriptionArn']}: {str(e)}")
        
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps({
                'success': True,
                'message': f'Unsubscribed from {unsubscribed_count} email notifications'
            })
        }
        
    except ClientError as e:
        logger.error(f"AWS error unsubscribing: {str(e)}")
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': 'Failed to unsubscribe from notifications'})
        }

def handle_status(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Check subscription status for user"""
    
    try:
        # Get all subscriptions
        subscriptions = sns_client.list_subscriptions_by_topic(TopicArn=SNS_TOPIC_ARN)
        
        email_subscriptions = []
        for subscription in subscriptions.get('Subscriptions', []):
            if (subscription.get('Protocol') == 'email' and 
                subscription.get('SubscriptionArn') != 'PendingConfirmation'):
                email_subscriptions.append({
                    'email': subscription.get('Endpoint'),
                    'subscription_arn': subscription.get('SubscriptionArn'),
                    'confirmed': True
                })
        
        # For now, return if any email subscriptions exist
        # In production, you'd filter by user ID
        is_subscribed = len(email_subscriptions) > 0
        
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps({
                'isSubscribed': is_subscribed,
                'email': email_subscriptions[0]['email'] if email_subscriptions else None,
                'subscriptionArn': email_subscriptions[0]['subscription_arn'] if email_subscriptions else None
            })
        }
        
    except ClientError as e:
        logger.error(f"AWS error checking status: {str(e)}")
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': 'Failed to check subscription status'})
        }

def find_email_subscription(email: str) -> str:
    """Find existing subscription for email address"""
    try:
        subscriptions = sns_client.list_subscriptions_by_topic(TopicArn=SNS_TOPIC_ARN)
        
        for subscription in subscriptions.get('Subscriptions', []):
            if (subscription.get('Protocol') == 'email' and 
                subscription.get('Endpoint') == email and
                subscription.get('SubscriptionArn') != 'PendingConfirmation'):
                return subscription.get('SubscriptionArn')
        
        return None
        
    except ClientError as e:
        logger.error(f"Error finding subscription for {email}: {str(e)}")
        return None