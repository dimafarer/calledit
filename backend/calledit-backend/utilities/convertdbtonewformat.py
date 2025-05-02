import boto3
from datetime import datetime
import time
from typing import Dict, Any
import os

def is_old_format(item: Dict[str, Any]) -> bool:
    """
    Check if the item is in the old format by looking at the PK structure
    """
    if 'PK' not in item:
        return False
    
    pk_value = item['PK']['S']
    return ':Call:' in pk_value

def convert_to_new_format(old_item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert an item from the old format to the new format
    """
    # Extract timestamp and userId from the old PK
    old_pk = old_item['PK']['S']
    user_id = old_pk.split(':')[1]
    timestamp = old_pk.split(':')[3]

    new_item = {
        'PK': {'S': f'USER:{user_id}'},
        'SK': {'S': f'PREDICTION#{timestamp}'},
        'createdAt': {'S': timestamp},
        'updatedAt': {'S': timestamp},
        'userId': {'S': user_id},
        'status': {'S': old_item['initial_status']['S'].upper()},
    }

    # Copy over common fields
    for field in ['initial_status', 'prediction_statement', 
                 'verification_date', 'verification_method']:
        if field in old_item:
            new_item[field] = old_item[field]

    return new_item

def migrate_table(table_name: str, dry_run: bool = True):
    """
    Migrate items from old format to new format
    """
    dynamodb = boto3.client('dynamodb')
    
    # Use paginator for handling large tables
    paginator = dynamodb.get_paginator('scan')
    page_iterator = paginator.paginate(TableName=table_name)
    
    items_to_update = 0
    items_processed = 0

    for page in page_iterator:
        for item in page['Items']:
            items_processed += 1
            
            if is_old_format(item):
                items_to_update += 1
                
                if not dry_run:
                    new_item = convert_to_new_format(item)
                    
                    # Delete old item
                    dynamodb.delete_item(
                        TableName=table_name,
                        Key={
                            'PK': item['PK'],
                            'SK': item['SK']
                        }
                    )
                    
                    # Put new item
                    dynamodb.put_item(
                        TableName=table_name,
                        Item=new_item
                    )
                    
                    # Add small delay to avoid exceeding throughput
                    time.sleep(0.1)
            
            if items_processed % 100 == 0:
                print(f"Processed {items_processed} items...")

    print(f"\nMigration Summary:")
    print(f"Total items processed: {items_processed}")
    print(f"Items requiring update: {items_to_update}")
    print(f"Dry run: {dry_run}")

if __name__ == "__main__":
    TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')
    
    if not TABLE_NAME:
        raise ValueError("DYNAMODB_TABLE_NAME environment variable must be set")

    # First do a dry run to see how many items would be affected
    print("Performing dry run...")
    migrate_table(TABLE_NAME, dry_run=True)
    
    # Ask for confirmation before actual migration
    response = input("\nDo you want to proceed with the actual migration? (yes/no): ")
    
    if response.lower() == 'yes':
        print("\nStarting actual migration...")
        migrate_table(TABLE_NAME, dry_run=False)
        print("Migration completed!")
    else:
        print("\nMigration cancelled.")
