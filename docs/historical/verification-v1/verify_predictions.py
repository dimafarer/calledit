#!/usr/bin/env python3
"""
Main Prediction Verification Script
Processes all pending predictions using Strands agent
"""

import json
import logging
from datetime import datetime
from typing import List

from ddb_scanner import DynamoDBScanner
from verification_agent import PredictionVerificationAgent
from verification_result import VerificationResult, VerificationStatus
from s3_logger import S3Logger
from email_notifier import EmailNotifier
from status_updater import StatusUpdater

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PredictionVerificationRunner:
    def __init__(self):
        self.scanner = DynamoDBScanner()
        self.agent = PredictionVerificationAgent()
        self.s3_logger = S3Logger()
        self.email_notifier = EmailNotifier()
        self.status_updater = StatusUpdater()
    
    def run_verification_batch(self, limit: int = None) -> dict:
        """
        Run verification on all pending predictions
        
        Args:
            limit: Maximum number of predictions to process (None for all)
            
        Returns:
            Summary statistics
        """
        logger.info("🚀 Starting prediction verification batch")
        
        # Get pending predictions
        predictions = self.scanner.query_pending_predictions()
        
        if limit:
            predictions = predictions[:limit]
        
        logger.info(f"Found {len(predictions)} predictions to verify")
        
        # Process each prediction
        results = []
        stats = {
            'total_processed': 0,
            'verified_true': 0,
            'verified_false': 0,
            'inconclusive': 0,
            'tool_gaps': 0,
            'errors': 0,
            'emails_sent': 0
        }
        
        for i, prediction in enumerate(predictions, 1):
            logger.info(f"Processing {i}/{len(predictions)}: {prediction.get('prediction_statement', 'Unknown')[:50]}...")
            
            try:
                # Verify the prediction
                result = self.agent.verify_prediction(prediction)
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
                self.s3_logger.log_verification_result(prediction, result)
                
                # Update DynamoDB status
                self.status_updater.update_prediction_status(prediction, result)
                
                # Send email if verified TRUE
                if result.status == VerificationStatus.TRUE:
                    self.email_notifier.send_verification_email(prediction, result)
                    stats['emails_sent'] += 1
                
                logger.info(f"✅ Completed: {result.status.value} (confidence: {result.confidence})")
                
            except Exception as e:
                logger.error(f"❌ Error processing prediction: {str(e)}")
                stats['errors'] += 1
        
        # Log summary
        self._log_batch_summary(stats, results)
        
        return stats
    
    def _log_batch_summary(self, stats: dict, results: List[VerificationResult]):
        """Log batch processing summary"""
        logger.info("\n" + "="*60)
        logger.info("📊 VERIFICATION BATCH SUMMARY")
        logger.info("="*60)
        
        for key, value in stats.items():
            logger.info(f"{key.replace('_', ' ').title()}: {value}")
        
        # Tool gap analysis
        tool_gaps = [r for r in results if r.status == VerificationStatus.TOOL_GAP]
        if tool_gaps:
            logger.info(f"\n🔧 Tool Gaps Identified ({len(tool_gaps)}):")
            gap_summary = {}
            for result in tool_gaps:
                if result.tool_gap:
                    tool = result.tool_gap.missing_tool
                    gap_summary[tool] = gap_summary.get(tool, 0) + 1
            
            for tool, count in gap_summary.items():
                logger.info(f"  {tool}: {count} predictions")
        
        logger.info("="*60)

def main():
    """Main verification script"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Verify pending predictions')
    parser.add_argument('--limit', type=int, help='Limit number of predictions to process')
    parser.add_argument('--dry-run', action='store_true', help='Run without updating database or sending emails')
    
    args = parser.parse_args()
    
    if args.dry_run:
        logger.info("🧪 Running in DRY RUN mode - no database updates or emails")
    
    runner = PredictionVerificationRunner()
    
    try:
        stats = runner.run_verification_batch(limit=args.limit)
        
        print(f"\n✅ Verification complete!")
        print(f"Processed: {stats['total_processed']} predictions")
        print(f"Verified TRUE: {stats['verified_true']} (emails sent: {stats['emails_sent']})")
        print(f"Verified FALSE: {stats['verified_false']}")
        print(f"Tool gaps: {stats['tool_gaps']}")
        print(f"Errors: {stats['errors']}")
        
    except KeyboardInterrupt:
        logger.info("\n⏹️  Verification interrupted by user")
    except Exception as e:
        logger.error(f"❌ Verification failed: {str(e)}")
        raise

if __name__ == "__main__":
    main()