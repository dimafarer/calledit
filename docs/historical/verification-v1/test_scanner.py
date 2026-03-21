#!/usr/bin/env python3
"""
Test script to examine predictions in detail
"""

from ddb_scanner import DynamoDBScanner
import json

def main():
    scanner = DynamoDBScanner()
    
    # Get all predictions ready for verification
    predictions = scanner.query_pending_predictions()
    
    print(f"📋 Found {len(predictions)} predictions ready for verification\n")
    
    # Group by category
    categories = {}
    for prediction in predictions:
        category = prediction.get('verifiable_category', 'unknown')
        if category not in categories:
            categories[category] = []
        categories[category].append(prediction)
    
    # Show breakdown by category
    print("📊 Breakdown by Verifiability Category:")
    for category, preds in categories.items():
        print(f"  {category}: {len(preds)} predictions")
    
    print("\n" + "="*80)
    
    # Show sample predictions from each category
    for category, preds in categories.items():
        print(f"\n🏷️  {category.upper()} ({len(preds)} predictions):")
        print("-" * 60)
        
        for i, pred in enumerate(preds[:3], 1):  # Show first 3 from each category
            statement = pred.get('prediction_statement', 'Unknown')
            verification_date = pred.get('verification_date', 'Unknown')
            date_error = pred.get('date_parse_error', False)
            
            print(f"  {i}. {statement}")
            print(f"     Verification Date: {verification_date}")
            if date_error:
                print(f"     ⚠️  Date parsing issue")
            print()
        
        if len(preds) > 3:
            print(f"     ... and {len(preds) - 3} more")
            print()

if __name__ == "__main__":
    main()