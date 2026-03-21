#!/usr/bin/env python3
"""
DynamoDB Scanner for Prediction Verification
Queries pending predictions from CalledIt database
"""

import boto3
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import logging
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DynamoDBScanner:
    def __init__(self, table_name: str = "calledit-db", region: str = "us-west-2"):
        self.table_name = table_name
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.table = self.dynamodb.Table(table_name)
    
    def query_pending_predictions(self) -> List[Dict[str, Any]]:
        """
        Query all predictions with status='PENDING' that are ready for verification
        
        Returns:
            List of prediction dictionaries ready for verification
        """
        try:
            logger.info(f"Querying pending predictions from {self.table_name}")
            
            # Scan for predictions with PENDING status
            response = self.table.scan(
                FilterExpression="initial_status = :status",
                ExpressionAttributeValues={
                    ":status": "pending"
                }
            )
            
            predictions = response.get('Items', [])
            
            # Filter for predictions past their verification date
            current_time = datetime.now(timezone.utc)
            ready_predictions = []
            
            for prediction in predictions:
                verification_date = self._parse_verification_date(prediction.get('verification_date'))
                
                if verification_date and verification_date <= current_time:
                    # Add metadata for verification
                    prediction['ready_for_verification'] = True
                    prediction['current_time'] = current_time.isoformat()
                elif not verification_date:
                    # Include predictions with unparseable dates for manual review
                    prediction['ready_for_verification'] = True
                    prediction['current_time'] = current_time.isoformat()
                    prediction['date_parse_error'] = True
                    ready_predictions.append(prediction)
                    
                    logger.info(f"Found prediction with unparseable date: {prediction.get('prediction_statement', 'Unknown')[:50]}...")
                    ready_predictions.append(prediction)
                    
                    logger.info(f"Found ready prediction: {prediction.get('prediction_statement', 'Unknown')[:50]}...")
            
            logger.info(f"Found {len(ready_predictions)} predictions ready for verification")
            return ready_predictions
            
        except Exception as e:
            logger.error(f"Error querying pending predictions: {str(e)}")
            raise
    
    def get_prediction_by_id(self, prediction_id: str) -> Dict[str, Any]:
        """
        Get a specific prediction by ID for verification
        
        Args:
            prediction_id: The prediction ID to retrieve
            
        Returns:
            Prediction dictionary or None if not found
        """
        try:
            response = self.table.get_item(
                Key={'id': prediction_id}
            )
            
            return response.get('Item')
            
        except Exception as e:
            logger.error(f"Error getting prediction {prediction_id}: {str(e)}")
            raise
    
    def _parse_verification_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse verification date string to datetime object
        
        Args:
            date_str: Date string in various formats
            
        Returns:
            timezone-aware datetime object or None if parsing fails
        """
        if not date_str or date_str in ['YYYY-MM-DD', 'To be determined after the NBA season concludes', 'The upcoming Saturday after the prediction was made']:
            return None
            
        try:
            # Try ISO format first
            if 'T' in date_str:
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            
            # Handle EDT/EST timezone formats
            if 'EDT' in date_str or 'EST' in date_str:
                try:
                    # Remove timezone suffix and parse
                    clean_date = re.sub(r'\s+(EDT|EST)$', '', date_str)
                    dt = datetime.strptime(clean_date, '%Y-%m-%d %H:%M:%S')
                    return dt.replace(tzinfo=timezone.utc)  # Treat as UTC for simplicity
                except ValueError:
                    logger.warning(f"Failed to parse EDT/EST date: {date_str}")
                    return None
            
            # Try date-only format
            if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
                dt = datetime.strptime(date_str, '%Y-%m-%d')
                return dt.replace(tzinfo=timezone.utc)
            
            return None
            
        except (ValueError, TypeError) as e:
            logger.warning(f"Could not parse verification date '{date_str}': {str(e)}")
            return None
    
    def get_verification_stats(self) -> Dict[str, int]:
        """
        Get statistics about prediction verification status
        
        Returns:
            Dictionary with counts by status
        """
        try:
            response = self.table.scan()
            predictions = response.get('Items', [])
            
            stats = {
                'total': len(predictions),
                'pending': 0,
                'verified_true': 0,
                'verified_false': 0,
                'inconclusive': 0,
                'error': 0
            }
            
            for prediction in predictions:
                status = prediction.get('initial_status', 'unknown').lower()
                verification_status = prediction.get('verification_status', '').lower()
                
                if status == 'pending':
                    stats['pending'] += 1
                elif verification_status == 'true':
                    stats['verified_true'] += 1
                elif verification_status == 'false':
                    stats['verified_false'] += 1
                elif verification_status == 'inconclusive':
                    stats['inconclusive'] += 1
                elif verification_status == 'error':
                    stats['error'] += 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting verification stats: {str(e)}")
            raise

def main():
    """Test the DynamoDB scanner"""
    scanner = DynamoDBScanner()
    
    # Get verification statistics
    stats = scanner.get_verification_stats()
    print(f"📊 Verification Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Query pending predictions
    predictions = scanner.query_pending_predictions()
    print(f"\n🔍 Found {len(predictions)} predictions ready for verification:")
    
    for i, prediction in enumerate(predictions[:5], 1):  # Show first 5
        statement = prediction.get('prediction_statement', 'Unknown')
        category = prediction.get('verifiable_category', 'Unknown')
        verification_date = prediction.get('verification_date', 'Unknown')
        
        print(f"  {i}. {statement[:60]}...")
        print(f"     Category: {category}")
        print(f"     Verification Date: {verification_date}")
        print()

if __name__ == "__main__":
    main()