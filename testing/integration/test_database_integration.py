#!/usr/bin/env python3
"""
Database Integration Tests - Testing Phase C
Tests CRUD operations, error handling, and data consistency
"""

import json
import boto3
import pytest
from decimal import Decimal
from moto import mock_aws
from datetime import datetime, timezone

# Mock DynamoDB for testing
@mock_aws
class TestDatabaseIntegration:
    
    def setup_method(self):
        """Setup test DynamoDB table"""
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        # Create test table
        self.table = self.dynamodb.create_table(
            TableName='calledit-db-test',
            KeySchema=[
                {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                {'AttributeName': 'prediction_id', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'prediction_id', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        self.test_prediction = {
            'user_id': 'test-user-123',
            'prediction_id': 'pred-456',
            'prediction_statement': 'Bitcoin will hit $100k by end of year',
            'verification_date': '2025-12-31T23:59:59Z',
            'verifiable_category': 'api_tool_verifiable',
            'category_reasoning': 'Requires external price data',
            'verification_status': 'PENDING',
            'created_at': datetime.now(timezone.utc).isoformat()
        }
    
    def test_create_prediction_success(self):
        """Test successful prediction creation"""
        response = self.table.put_item(Item=self.test_prediction)
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200
        
        # Verify item was created
        item = self.table.get_item(
            Key={'user_id': 'test-user-123', 'prediction_id': 'pred-456'}
        )
        assert 'Item' in item
        assert item['Item']['prediction_statement'] == 'Bitcoin will hit $100k by end of year'
    
    def test_read_prediction_success(self):
        """Test successful prediction retrieval"""
        # Insert test data
        self.table.put_item(Item=self.test_prediction)
        
        # Read data
        response = self.table.get_item(
            Key={'user_id': 'test-user-123', 'prediction_id': 'pred-456'}
        )
        
        assert 'Item' in response
        item = response['Item']
        assert item['verifiable_category'] == 'api_tool_verifiable'
        assert item['verification_status'] == 'PENDING'
    
    def test_update_prediction_success(self):
        """Test successful prediction update"""
        # Insert test data
        self.table.put_item(Item=self.test_prediction)
        
        # Update verification status
        response = self.table.update_item(
            Key={'user_id': 'test-user-123', 'prediction_id': 'pred-456'},
            UpdateExpression='SET verification_status = :status, verification_confidence = :conf',
            ExpressionAttributeValues={
                ':status': 'VERIFIED_TRUE',
                ':conf': Decimal('0.95')
            },
            ReturnValues='ALL_NEW'
        )
        
        assert response['Attributes']['verification_status'] == 'VERIFIED_TRUE'
        assert response['Attributes']['verification_confidence'] == Decimal('0.95')
    
    def test_delete_prediction_success(self):
        """Test successful prediction deletion"""
        # Insert test data
        self.table.put_item(Item=self.test_prediction)
        
        # Delete item
        response = self.table.delete_item(
            Key={'user_id': 'test-user-123', 'prediction_id': 'pred-456'}
        )
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200
        
        # Verify deletion
        item = self.table.get_item(
            Key={'user_id': 'test-user-123', 'prediction_id': 'pred-456'}
        )
        assert 'Item' not in item
    
    def test_query_user_predictions(self):
        """Test querying all predictions for a user"""
        # Insert multiple predictions
        predictions = [
            {**self.test_prediction, 'prediction_id': 'pred-1'},
            {**self.test_prediction, 'prediction_id': 'pred-2'},
            {**self.test_prediction, 'prediction_id': 'pred-3'}
        ]
        
        for pred in predictions:
            self.table.put_item(Item=pred)
        
        # Query user predictions
        response = self.table.query(
            KeyConditionExpression='user_id = :uid',
            ExpressionAttributeValues={':uid': 'test-user-123'}
        )
        
        assert response['Count'] == 3
        assert len(response['Items']) == 3
    
    def test_data_consistency_decimal_handling(self):
        """Test Decimal type handling for confidence scores"""
        prediction_with_decimal = {
            **self.test_prediction,
            'verification_confidence': Decimal('0.87'),
            'processing_time': Decimal('2.5')
        }
        
        # Insert with Decimal values
        self.table.put_item(Item=prediction_with_decimal)
        
        # Retrieve and verify Decimal preservation
        item = self.table.get_item(
            Key={'user_id': 'test-user-123', 'prediction_id': 'pred-456'}
        )['Item']
        
        assert isinstance(item['verification_confidence'], Decimal)
        assert item['verification_confidence'] == Decimal('0.87')
    
    def test_error_handling_missing_key(self):
        """Test error handling for missing required keys"""
        with pytest.raises(Exception):
            self.table.put_item(Item={'prediction_statement': 'Missing keys'})
    
    def test_error_handling_nonexistent_item(self):
        """Test handling of nonexistent item retrieval"""
        response = self.table.get_item(
            Key={'user_id': 'nonexistent', 'prediction_id': 'fake'}
        )
        assert 'Item' not in response


if __name__ == '__main__':
    # Run tests
    test_suite = TestDatabaseIntegration()
    
    print("🧪 Starting Database Integration Tests...")
    
    tests = [
        'test_create_prediction_success',
        'test_read_prediction_success', 
        'test_update_prediction_success',
        'test_delete_prediction_success',
        'test_query_user_predictions',
        'test_data_consistency_decimal_handling',
        'test_error_handling_missing_key',
        'test_error_handling_nonexistent_item'
    ]
    
    passed = 0
    for test_name in tests:
        try:
            test_suite.setup_method()
            getattr(test_suite, test_name)()
            print(f"✅ {test_name}")
            passed += 1
        except Exception as e:
            print(f"❌ {test_name}: {e}")
    
    print(f"\n📊 Database Integration Tests: {passed}/{len(tests)} passed ({passed/len(tests)*100:.1f}%)")