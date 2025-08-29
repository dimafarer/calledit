#!/usr/bin/env python3
from verify_predictions import PredictionVerificationRunner

def lambda_handler(event, context):
    runner = PredictionVerificationRunner()
    stats = runner.run_verification_batch()
    return {
        'statusCode': 200,
        'body': stats
    }