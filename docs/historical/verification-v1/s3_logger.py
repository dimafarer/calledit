#!/usr/bin/env python3
"""
S3 Logger for Verification Results
Logs verification attempts and tool gaps to S3
"""

import json
import boto3
from datetime import datetime
from typing import Dict, Any
import logging

from verification_result import VerificationResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class S3Logger:
    def __init__(self, bucket_name: str = "calledit-verification-logs", region: str = "us-west-2"):
        self.bucket_name = bucket_name
        self.s3_client = boto3.client('s3', region_name=region)
    
    def log_verification_result(self, prediction: Dict[str, Any], result: VerificationResult):
        """Log verification result to S3"""
        try:
            # Create log entry
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "prediction_id": result.prediction_id,
                "original_statement": prediction.get('prediction_statement', ''),
                "verification_category": prediction.get('verifiable_category', 'unknown'),
                "agent_reasoning": result.reasoning,
                "tools_used": result.tools_used,
                "verification_result": result.status.value,
                "confidence": result.confidence,
                "verification_date": result.verification_date.isoformat(),
                "processing_time_ms": result.processing_time_ms,
                "agent_thoughts": result.agent_thoughts,
                "verification_method": result.verification_method,
                "actual_outcome": result.actual_outcome,
                "error_message": result.error_message
            }
            
            # Add tool gap information if present
            if result.tool_gap:
                log_entry["tool_gap"] = {
                    "missing_tool": result.tool_gap.missing_tool,
                    "suggested_mcp_tool": result.tool_gap.suggested_mcp_tool,
                    "tool_specification": result.tool_gap.tool_specification,
                    "priority": result.tool_gap.priority,
                    "examples": result.tool_gap.examples
                }
            else:
                log_entry["tool_gap"] = None
            
            # Generate S3 key
            date_str = datetime.now().strftime('%Y/%m/%d')
            timestamp = datetime.now().strftime('%H%M%S')
            s3_key = f"verification-logs/{date_str}/{result.prediction_id}_{timestamp}.json"
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=json.dumps(log_entry, indent=2),
                ContentType='application/json'
            )
            
            logger.info(f"📝 Logged verification result to S3: {s3_key}")
            
        except Exception as e:
            logger.error(f"Failed to log to S3: {str(e)}")
            # Don't raise - logging failure shouldn't stop verification
    
    def log_tool_gap_summary(self, tool_gaps: Dict[str, int]):
        """Log daily tool gap summary"""
        try:
            summary = {
                "date": datetime.now().strftime('%Y-%m-%d'),
                "timestamp": datetime.now().isoformat(),
                "tool_gaps": tool_gaps,
                "total_gaps": sum(tool_gaps.values())
            }
            
            date_str = datetime.now().strftime('%Y/%m/%d')
            s3_key = f"tool-gap-summaries/{date_str}/daily_summary.json"
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=json.dumps(summary, indent=2),
                ContentType='application/json'
            )
            
            logger.info(f"📊 Logged tool gap summary to S3: {s3_key}")
            
        except Exception as e:
            logger.error(f"Failed to log tool gap summary: {str(e)}")

def main():
    """Test S3 logging"""
    from verification_result import VerificationResult, VerificationStatus, ToolGap
    
    logger = S3Logger()
    
    # Mock prediction and result for testing
    mock_prediction = {
        'prediction_statement': 'Test prediction for S3 logging',
        'verifiable_category': 'agent_verifiable'
    }
    
    mock_result = VerificationResult(
        prediction_id="test_s3_log",
        status=VerificationStatus.TRUE,
        confidence=0.9,
        reasoning="Test verification for S3 logging",
        verification_date=datetime.now(),
        tools_used=['reasoning'],
        agent_thoughts="This is a test verification",
        processing_time_ms=1500
    )
    
    print("🧪 Testing S3 logging...")
    logger.log_verification_result(mock_prediction, mock_result)
    print("✅ S3 logging test complete")

if __name__ == "__main__":
    main()