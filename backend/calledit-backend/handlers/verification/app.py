#!/usr/bin/env python3
import sys
import os
import logging

from error_handling import with_agent_fallback, safe_agent_call
from verify_predictions import PredictionVerificationRunner

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

@with_agent_fallback({
    'statusCode': 500,
    'body': {
        'error': 'Verification batch failed',
        'processed': 0,
        'verified': 0,
        'failed': 1
    }
})
def lambda_handler(event, context):
    """
    Lambda handler for scheduled prediction verification with error handling
    """
    try:
        logger.info("Starting verification batch")
        runner = PredictionVerificationRunner()
        stats = runner.run_verification_batch()
        
        logger.info(f"Verification batch completed: {stats}")
        return {
            'statusCode': 200,
            'body': stats
        }
    except Exception as e:
        logger.error(f"Verification batch failed: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': {
                'error': str(e),
                'processed': 0,
                'verified': 0,
                'failed': 1
            }
        }