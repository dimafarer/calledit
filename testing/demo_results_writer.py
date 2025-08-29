#!/usr/bin/env python3
"""
Write demo test results to DynamoDB
Uses the same structure as write_to_db Lambda
"""

import boto3
import json
import uuid
from datetime import datetime
from demo_prompts import get_all_prompts

# Known user partition key
USER_PARTITION_KEY = "USER:c8518370-f081-709f-07cd-41dbe3e756ee"
TABLE_NAME = "calledit-db"

def write_prediction_to_ddb(prediction_data):
    """Write a prediction to DynamoDB using same structure as Lambda"""
    
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(TABLE_NAME)
    
    # Generate unique call ID
    call_id = str(uuid.uuid4())
    
    # Create DynamoDB item (same structure as write_to_db Lambda)
    timestamp = datetime.utcnow().isoformat()
    
    item = {
        'PK': USER_PARTITION_KEY,  # USER:c8518370-f081-709f-07cd-41dbe3e756ee
        'SK': f'PREDICTION#{timestamp}',  # Organized hierarchy
        'userId': USER_PARTITION_KEY.split(':')[1],  # Extract just the UUID part
        'status': 'PENDING',
        'createdAt': timestamp,
        'updatedAt': timestamp,
        'call_id': call_id,
        'original_prompt': prediction_data['prompt'],
        'prediction_statement': prediction_data.get('statement', prediction_data['prompt']),
        'verification_date': prediction_data.get('verification_date', ''),
        'verifiable_category': prediction_data.get('category', 'unknown'),
        'category_reasoning': prediction_data.get('reasoning', ''),
        'verification_method': prediction_data.get('verification_method', {}),
        'date_reasoning': prediction_data.get('date_reasoning', ''),
        'verification_result': None,
        'verification_confidence': None,
        'verification_timestamp': None
    }
    
    try:
        table.put_item(Item=item)
        print(f"✅ Wrote prediction: {call_id}")
        return call_id
    except Exception as e:
        print(f"❌ Failed to write {call_id}: {e}")
        return None

def write_demo_results(results_file="demo_results.json"):
    """Write demo results from JSON file to DynamoDB"""
    
    try:
        with open(results_file, 'r') as f:
            results = json.load(f)
    except FileNotFoundError:
        print(f"❌ Results file {results_file} not found")
        return
    
    print(f"📝 Writing {len(results)} predictions to DynamoDB")
    print(f"User: {USER_PARTITION_KEY}")
    print(f"Table: {TABLE_NAME}\n")
    
    successful_writes = 0
    
    for result in results:
        if result.get('success'):
            call_id = write_prediction_to_ddb(result)
            if call_id:
                successful_writes += 1
    
    print(f"\n📊 Summary:")
    print(f"Total results: {len(results)}")
    print(f"Successful writes: {successful_writes}")

def create_sample_results():
    """Create sample results for testing (without API calls)"""
    print("🎯 Creating sample demo results...")
    from datetime import datetime
    
    all_prompts = get_all_prompts()
    sample_results = []
    
    category_map = {
        "agent_verifiable": "agent_verifiable",
        "current_tool_verifiable": "current_tool_verifiable", 
        "strands_tool_verifiable": "strands_tool_verifiable",
        "api_tool_verifiable": "api_tool_verifiable",
        "human_verifiable_only": "human_verifiable_only"
    }
    
    for category, prompts in all_prompts.items():
        # Take first 2 prompts from each category
        for prompt in prompts[:2]:
            result = {
                "prompt": prompt,
                "statement": f"Structured version: {prompt}",
                "category": category_map[category],
                "reasoning": f"This prediction is {category.replace('_', ' ')} because it requires {category.split('_')[0]} verification methods.",
                "verification_date": datetime.utcnow().isoformat() + "Z",
                "verification_method": {
                    "source": ["AI Agent", "Tools"],
                    "criteria": [f"Verify: {prompt}"],
                    "steps": ["Process prediction", "Determine truth value"]
                },
                "date_reasoning": "Set for tomorrow for verification testing",
                "success": True
            }
            sample_results.append(result)
    
    # Save sample results
    with open("demo_results.json", 'w') as f:
        json.dump(sample_results, f, indent=2)
    
    print(f"✅ Created {len(sample_results)} sample results")
    return sample_results

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--sample":
        # Create and write sample results
        create_sample_results()
        write_demo_results()
    else:
        # Write existing results file
        write_demo_results()