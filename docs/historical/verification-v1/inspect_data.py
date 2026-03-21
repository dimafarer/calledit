#!/usr/bin/env python3
"""
Inspect actual DynamoDB data structure
"""

from ddb_scanner import DynamoDBScanner
import json

def main():
    scanner = DynamoDBScanner()
    
    # Get one prediction to inspect its structure
    predictions = scanner.query_pending_predictions()
    
    if predictions:
        print("🔍 Sample Prediction Structure:")
        print("=" * 50)
        
        sample = predictions[0]
        
        # Pretty print the structure
        for key, value in sample.items():
            if isinstance(value, str) and len(value) > 100:
                print(f"{key}: {value[:100]}...")
            else:
                print(f"{key}: {value}")
        
        print("\n" + "=" * 50)
        print(f"📋 Available Fields: {list(sample.keys())}")
        
        # Look for category-related fields
        category_fields = [k for k in sample.keys() if 'category' in k.lower() or 'verif' in k.lower()]
        print(f"🏷️  Category-related fields: {category_fields}")
        
    else:
        print("No predictions found")

if __name__ == "__main__":
    main()