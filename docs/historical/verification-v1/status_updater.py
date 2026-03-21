#!/usr/bin/env python3
"""
Status Updater for DynamoDB
Updates prediction verification status in database
"""

import boto3
from typing import Dict, Any
import logging
from datetime import datetime
from decimal import Decimal

from verification_result import VerificationResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StatusUpdater:
    def __init__(self, table_name: str = "calledit-db", region: str = "us-west-2"):
        self.table_name = table_name
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.table = self.dynamodb.Table(table_name)
    
    def update_prediction_status(self, prediction: Dict[str, Any], result: VerificationResult):
        """Update prediction verification status in DynamoDB"""
        try:
            # Prepare update attributes
            update_expr = "SET verification_status = :status, verification_confidence = :confidence, verification_date_completed = :completed, verification_reasoning = :reasoning, verification_method = :method"
            
            expr_values = {
                ':status': result.status.value.lower(),
                ':confidence': Decimal(str(result.confidence)),
                ':completed': result.verification_date.isoformat(),
                ':reasoning': result.reasoning,
                ':method': result.verification_method or 'unknown'
            }
            
            # Add tool gap information if present
            if result.tool_gap:
                update_expr += ", tool_gap_info = :tool_gap"
                expr_values[':tool_gap'] = {
                    'missing_tool': result.tool_gap.missing_tool,
                    'suggested_mcp_tool': result.tool_gap.suggested_mcp_tool,
                    'tool_specification': result.tool_gap.tool_specification,
                    'priority': result.tool_gap.priority
                }
            
            # Add error information if present
            if result.error_message:
                update_expr += ", verification_error = :error"
                expr_values[':error'] = result.error_message
            
            # Add processing metrics
            update_expr += ", processing_time_ms = :processing_time, tools_used = :tools"
            expr_values[':processing_time'] = result.processing_time_ms
            expr_values[':tools'] = result.tools_used
            
            # Update the item
            self.table.update_item(
                Key={
                    'PK': prediction['PK'],
                    'SK': prediction['SK']
                },
                UpdateExpression=update_expr,
                ExpressionAttributeValues=expr_values
            )
            
            logger.info(f"📝 Updated prediction status: {result.status.value} (confidence: {result.confidence})")
            
        except Exception as e:
            logger.error(f"Failed to update prediction status: {str(e)}")
            # Don't raise - status update failure shouldn't stop verification
    
    def get_verification_statistics(self) -> Dict[str, int]:
        """Get verification statistics from database"""
        try:
            response = self.table.scan()
            predictions = response.get('Items', [])
            
            stats = {
                'total': len(predictions),
                'pending': 0,
                'verified_true': 0,
                'verified_false': 0,
                'inconclusive': 0,
                'tool_gaps': 0,
                'errors': 0
            }
            
            for prediction in predictions:
                verification_status = prediction.get('verification_status', '').lower()
                initial_status = prediction.get('initial_status', '').lower()
                
                if initial_status == 'pending' and not verification_status:
                    stats['pending'] += 1
                elif verification_status == 'true':
                    stats['verified_true'] += 1
                elif verification_status == 'false':
                    stats['verified_false'] += 1
                elif verification_status == 'inconclusive':
                    stats['inconclusive'] += 1
                elif verification_status == 'tool_gap':
                    stats['tool_gaps'] += 1
                elif verification_status == 'error':
                    stats['errors'] += 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting verification statistics: {str(e)}")
            return {}

def main():
    """Test status updater"""
    from verification_result import VerificationResult, VerificationStatus, ToolGap
    from datetime import datetime
    
    updater = StatusUpdater()
    
    # Get current statistics
    stats = updater.get_verification_statistics()
    print("📊 Current Verification Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n🧪 Status updater ready for use")

if __name__ == "__main__":
    main()