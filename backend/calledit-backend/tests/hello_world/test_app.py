import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from handlers.hello_world.app import lambda_handler
from unittest.mock import patch, MagicMock
import json
import unittest

class TestApp(unittest.TestCase):

    def test_lambda_handler_empty_prompt(self):
        """
        Test the lambda_handler function when the 'prompt' parameter is an empty string.
        This should return a 400 status code with an error message since empty prompts are invalid.
        """
        event = {'queryStringParameters': {'prompt': ''}}
        context = MagicMock()

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 400)
        self.assertIn('error', json.loads(response['body']))
        self.assertEqual(json.loads(response['body'])['error'], 'No prompt provided')

    def test_lambda_handler_missing_prompt(self):
        """
        Test the lambda_handler function when the 'prompt' parameter is missing from the event.
        This should trigger the error handling in the get_event_property function.
        """
        event = {}
        context = MagicMock()

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 400)
        self.assertIn('error', json.loads(response['body']))
        self.assertEqual(json.loads(response['body'])['error'], 'No prompt provided')

    def test_lambda_handler_successful_response(self):
        """
        Test the lambda_handler function with a valid 'prompt' in the event.

        This test verifies that the lambda_handler returns a successful response
        with the correct status code, headers, and body when given a valid prompt.
        """
        event = {'prompt': 'test'}
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 200)
        self.assertEqual(response['headers'], {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
        })

        body = json.loads(response['body'])
        self.assertEqual(body['message'], 'hello world test')

if __name__ == '__main__':
    unittest.main()