#!/usr/bin/env python3
"""
Modernize legacy DynamoDB predictions to match current data structure
"""

import boto3
from typing import Dict, Any
import logging
from datetime import datetime, timezone
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataModernizer:
    def __init__(self, table_name: str = "calledit-db", region: str = "us-west-2"):
        self.table_name = table_name
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.table = self.dynamodb.Table(table_name)
    
    def get_all_predictions(self):
        """Get all predictions to analyze structure"""
        response = self.table.scan()
        return response.get('Items', [])
    
    def categorize_prediction(self, statement: str) -> str:
        """
        Intelligently categorize prediction based on content
        """
        statement_lower = statement.lower()
        
        # Agent verifiable - natural laws, facts, certainties
        if any(word in statement_lower for word in ['sun', 'rise', 'tomorrow', 'earth', 'gravity', 'christmas', 'thursday']):
            return 'agent_verifiable'
        
        # Current tool verifiable - time/date based
        if any(word in statement_lower for word in ['today', 'tonight', 'now', 'currently', 'this morning', 'this evening']):
            return 'current_tool_verifiable'
        
        # API tool verifiable - external data needed
        if any(word in statement_lower for word in ['bitcoin', 'stock', 'price', 'weather', 'rain', 'nba', 'nuggets', 'thunder', 'nicks', 'win', 'championship']):
            return 'api_tool_verifiable'
        
        # Strands tool verifiable - calculations
        if any(word in statement_lower for word in ['calculate', 'math', 'percent', 'compound', 'interest', '+']):
            return 'strands_tool_verifiable'
        
        # Human verifiable only - personal/subjective
        if any(word in statement_lower for word in ['i will', 'feel', 'happy', 'love', 'bore', 'fall asleep', 'snore', 'drinks']):
            return 'human_verifiable_only'
        
        # Default to human verifiable for personal predictions
        return 'human_verifiable_only'
    
    def generate_verification_date(self, statement: str, created_at: str) -> str:
        """
        Generate appropriate verification date based on prediction content
        """
        statement_lower = statement.lower()
        
        try:
            # Parse creation date
            if 'T' in created_at:
                base_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            else:
                base_date = datetime.strptime(created_at[:10], '%Y-%m-%d').replace(tzinfo=timezone.utc)
        except:
            base_date = datetime.now(timezone.utc)
        
        # Sports events - end of season
        if 'nba' in statement_lower or 'championship' in statement_lower:
            return '2025-06-30T23:59:59Z'
        
        # Tonight/today predictions
        if 'tonight' in statement_lower:
            return base_date.replace(hour=23, minute=59, second=59).isoformat()
        elif 'today' in statement_lower:
            return base_date.replace(hour=23, minute=59, second=59).isoformat()
        
        # Tomorrow predictions
        elif 'tomorrow' in statement_lower:
            next_day = base_date.replace(hour=23, minute=59, second=59)
            return next_day.isoformat()
        
        # Default: 30 days from creation
        else:
            from datetime import timedelta
            future_date = base_date + timedelta(days=30)
            return future_date.isoformat()
    
    def generate_category_reasoning(self, category: str, statement: str) -> str:
        """Generate reasoning for category assignment"""
        reasoning_map = {
            'agent_verifiable': f"This prediction about '{statement}' can be verified through pure reasoning and established knowledge without requiring external tools or real-time data.",
            'current_tool_verifiable': f"This prediction about '{statement}' requires checking current time/date information to verify.",
            'api_tool_verifiable': f"This prediction about '{statement}' requires external data sources or APIs to verify the outcome.",
            'strands_tool_verifiable': f"This prediction about '{statement}' involves calculations or computational verification.",
            'human_verifiable_only': f"This prediction about '{statement}' is subjective or personal and can only be verified by human assessment."
        }
        return reasoning_map.get(category, f"Category reasoning for '{statement}'")
    
    def modernize_prediction(self, prediction: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a single prediction to modern structure
        """
        statement = prediction.get('prediction_statement', '')
        created_at = prediction.get('createdAt', '')
        
        # Generate missing fields
        category = self.categorize_prediction(statement)
        
        updates = {}
        
        # Add verifiable_category if missing
        if 'verifiable_category' not in prediction:
            updates['verifiable_category'] = category
        
        # Add category_reasoning if missing
        if 'category_reasoning' not in prediction:
            updates['category_reasoning'] = self.generate_category_reasoning(category, statement)
        
        # Fix verification_date if it's placeholder text
        current_date = prediction.get('verification_date', '')
        if current_date in ['YYYY-MM-DD', 'To be determined after the NBA season concludes', 'The upcoming Saturday after the prediction was made']:
            updates['verification_date'] = self.generate_verification_date(statement, created_at)
        
        # Add prediction_date if missing (use createdAt)
        if 'prediction_date' not in prediction:
            try:
                if 'T' in created_at:
                    updates['prediction_date'] = created_at[:10]  # Extract date part
                else:
                    updates['prediction_date'] = created_at[:10]
            except:
                updates['prediction_date'] = '2025-01-27'
        
        # Add date_reasoning if missing
        if 'date_reasoning' not in prediction:
            updates['date_reasoning'] = f"Verification date set based on prediction content and timeline requirements."
        
        return updates
    
    def update_prediction_in_db(self, prediction: Dict[str, Any], updates: Dict[str, Any]):
        """Update prediction in DynamoDB"""
        if not updates:
            return
        
        # Build update expression
        update_expr = "SET "
        expr_values = {}
        expr_names = {}
        
        for i, (key, value) in enumerate(updates.items()):
            if i > 0:
                update_expr += ", "
            
            attr_name = f"#{key}"
            attr_value = f":{key}"
            
            update_expr += f"{attr_name} = {attr_value}"
            expr_names[attr_name] = key
            expr_values[attr_value] = value
        
        try:
            self.table.update_item(
                Key={
                    'PK': prediction['PK'],
                    'SK': prediction['SK']
                },
                UpdateExpression=update_expr,
                ExpressionAttributeNames=expr_names,
                ExpressionAttributeValues=expr_values
            )
            logger.info(f"Updated prediction: {prediction.get('prediction_statement', 'Unknown')[:50]}...")
        except Exception as e:
            logger.error(f"Failed to update prediction: {str(e)}")
    
    def modernize_all_predictions(self, dry_run: bool = True):
        """
        Modernize all predictions in the database
        """
        predictions = self.get_all_predictions()
        logger.info(f"Found {len(predictions)} predictions to analyze")
        
        updated_count = 0
        
        for prediction in predictions:
            updates = self.modernize_prediction(prediction)
            
            if updates:
                if dry_run:
                    logger.info(f"Would update: {prediction.get('prediction_statement', 'Unknown')[:50]}...")
                    logger.info(f"  Updates: {updates}")
                else:
                    self.update_prediction_in_db(prediction, updates)
                updated_count += 1
        
        logger.info(f"{'Would update' if dry_run else 'Updated'} {updated_count} predictions")
        return updated_count

def main():
    modernizer = DataModernizer()
    
    print("🔍 Analyzing predictions for modernization...")
    
    # First run in dry-run mode
    count = modernizer.modernize_all_predictions(dry_run=True)
    
    if count > 0:
        response = input(f"\nFound {count} predictions to update. Proceed with actual updates? (y/N): ")
        if response.lower() == 'y':
            print("🚀 Updating predictions...")
            modernizer.modernize_all_predictions(dry_run=False)
            print("✅ Modernization complete!")
        else:
            print("❌ Cancelled - no changes made")
    else:
        print("✅ All predictions are already up to date!")

if __name__ == "__main__":
    main()