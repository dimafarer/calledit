#!/usr/bin/env python3
"""
Lambda Handler for Prediction Verification
Integrates with existing SAM app structure
"""

import json
import logging
import os
from typing import Dict, Any

import boto3
from verification_agent import PredictionVerificationAgent
from verification_result import VerificationResult, VerificationStatus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
s3_client = boto3.client('s3')
sns_client = boto3.client('sns')

# Environment variables
TABLE_NAME = os.environ.get('DYNAMODB_TABLE', 'calledit-db')
S3_BUCKET = os.environ.get('S3_BUCKET', 'calledit-verification-logs')
SNS_TOPIC = os.environ.get('SNS_TOPIC_ARN', '')

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Lambda handler for prediction verification
    
    Event types:
    - EventBridge scheduled verification
    - Manual invocation with specific prediction
    - API Gateway request
    """
    try:
        logger.info(f"Verification lambda invoked with event: {json.dumps(event, default=str)}")
        
        # Determine event source and action
        source = event.get('source', 'manual')
        action = event.get('action', 'verify_predictions')
        limit = event.get('limit')
        
        if action == 'verify_predictions':
            return handle_batch_verification(limit)
        elif action == 'verify_single':
            prediction_id = event.get('prediction_id')
            return handle_single_verification(prediction_id)
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': f'Unknown action: {action}'})
            }
            
    except Exception as e:
        logger.error(f"Verification lambda error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def handle_batch_verification(limit: int = None) -> Dict[str, Any]:
    """Handle batch verification of ALL predictions in database"""
    
    # Get ALL predictions from database
    table = dynamodb.Table(TABLE_NAME)
    
    # Scan for ALL predictions (not just pending)
    response = table.scan()
    
    all_predictions = response.get('Items', [])
    
    # Filter for predictions that need verification
    predictions = []
    for prediction in all_predictions:
        # Include if:
        # 1. Status is pending, OR
        # 2. No verification status exists, OR  
        # 3. Previous verification failed/errored
        status = prediction.get('initial_status', '').lower()
        verification_status = prediction.get('verification_status', '').lower()
        
        if (status == 'pending' or 
            not verification_status or 
            verification_status in ['error', 'failed']):
            predictions.append(prediction)
    
    if limit:
        predictions = predictions[:limit]
    
    logger.info(f"Found {len(predictions)} predictions to verify")
    
    # Initialize verification agent
    agent = PredictionVerificationAgent()
    
    # Process predictions
    results = []
    stats = {
        'total_processed': 0,
        'verified_true': 0,
        'verified_false': 0,
        'inconclusive': 0,
        'tool_gaps': 0,
        'errors': 0,
        'notifications_sent': 0
    }
    
    for prediction in predictions:
        try:
            # Verify prediction
            result = agent.verify_prediction(prediction)
            results.append(result)
            
            # Update statistics
            stats['total_processed'] += 1
            if result.status == VerificationStatus.TRUE:
                stats['verified_true'] += 1
            elif result.status == VerificationStatus.FALSE:
                stats['verified_false'] += 1
            elif result.status == VerificationStatus.INCONCLUSIVE:
                stats['inconclusive'] += 1
            elif result.status == VerificationStatus.TOOL_GAP:
                stats['tool_gaps'] += 1
            elif result.status == VerificationStatus.ERROR:
                stats['errors'] += 1
            
            # Log to S3
            log_to_s3(prediction, result)
            
            # Update DynamoDB
            update_prediction_status(prediction, result)
            
            # Send notification if verified TRUE
            if result.status == VerificationStatus.TRUE:
                send_sns_notification(prediction, result)
                stats['notifications_sent'] += 1
                
        except Exception as e:
            logger.error(f"Error processing prediction {prediction.get('SK', 'unknown')}: {str(e)}")
            stats['errors'] += 1
    
    logger.info(f"Batch verification complete: {stats}")
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Batch verification completed',
            'statistics': stats
        })
    }

def handle_single_verification(prediction_id: str) -> Dict[str, Any]:
    """Handle verification of a single prediction"""
    
    if not prediction_id:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'prediction_id required'})
        }
    
    # Get prediction from DynamoDB
    table = dynamodb.Table(TABLE_NAME)
    
    # Note: This is simplified - you'd need proper key structure
    response = table.get_item(Key={'SK': prediction_id})
    
    if 'Item' not in response:
        return {
            'statusCode': 404,
            'body': json.dumps({'error': 'Prediction not found'})
        }
    
    prediction = response['Item']
    
    # Verify prediction
    agent = PredictionVerificationAgent()
    result = agent.verify_prediction(prediction)
    
    # Log and update
    log_to_s3(prediction, result)
    update_prediction_status(prediction, result)
    
    if result.status == VerificationStatus.TRUE:
        send_sns_notification(prediction, result)
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Single verification completed',
            'result': {
                'prediction_id': result.prediction_id,
                'status': result.status.value,
                'confidence': result.confidence,
                'reasoning': result.reasoning
            }
        })
    }

def log_to_s3(prediction: Dict[str, Any], result: VerificationResult):
    """Log verification result to S3"""
    try:
        from datetime import datetime
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "prediction_id": result.prediction_id,
            "original_statement": prediction.get('prediction_statement', ''),
            "verification_category": prediction.get('verifiable_category', 'unknown'),
            "verification_result": result.status.value,
            "confidence": result.confidence,
            "reasoning": result.reasoning,
            "processing_time_ms": result.processing_time_ms,
            "tools_used": result.tools_used
        }
        
        if result.tool_gap:
            log_entry["tool_gap"] = {
                "missing_tool": result.tool_gap.missing_tool,
                "suggested_mcp_tool": result.tool_gap.suggested_mcp_tool,
                "priority": result.tool_gap.priority
            }
        
        # Generate S3 key
        date_str = datetime.now().strftime('%Y/%m/%d')
        timestamp = datetime.now().strftime('%H%M%S')
        s3_key = f"verification-logs/{date_str}/{result.prediction_id}_{timestamp}.json"
        
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=json.dumps(log_entry, indent=2),
            ContentType='application/json'
        )
        
        logger.info(f"Logged to S3: {s3_key}")
        
    except Exception as e:
        logger.error(f"Failed to log to S3: {str(e)}")

def update_prediction_status(prediction: Dict[str, Any], result: VerificationResult):
    """Update prediction status in DynamoDB"""
    try:
        from decimal import Decimal
        
        table = dynamodb.Table(TABLE_NAME)
        
        table.update_item(
            Key={
                'PK': prediction['PK'],
                'SK': prediction['SK']
            },
            UpdateExpression="SET verification_status = :status, verification_confidence = :confidence, verification_reasoning = :reasoning, verification_completed_at = :completed",
            ExpressionAttributeValues={
                ':status': result.status.value.lower(),
                ':confidence': Decimal(str(result.confidence)),
                ':reasoning': result.reasoning,
                ':completed': result.verification_date.isoformat()
            }
        )
        
        logger.info(f"Updated DynamoDB status: {result.status.value}")
        
    except Exception as e:
        logger.error(f"Failed to update DynamoDB: {str(e)}")

def send_sns_notification(prediction: Dict[str, Any], result: VerificationResult):
    """Send SNS notification for verified TRUE prediction"""
    try:
        if not SNS_TOPIC:
            logger.warning("No SNS topic configured")
            return
        
        message = {
            "prediction": prediction.get('prediction_statement', 'Unknown'),
            "status": result.status.value,
            "confidence": result.confidence,
            "reasoning": result.reasoning
        }
        
        sns_client.publish(
            TopicArn=SNS_TOPIC,
            Subject=f"🎯 Prediction Verified TRUE: {prediction.get('prediction_statement', 'Unknown')[:50]}...",
            Message=json.dumps(message, indent=2)
        )
        
        logger.info("SNS notification sent")
        
    except Exception as e:
        logger.error(f"Failed to send SNS notification: {str(e)}")