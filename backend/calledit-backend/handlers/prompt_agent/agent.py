import json
import sys
import os
import logging
import urllib.parse
from strands import Agent, tool
from strands_tools import calculator, current_time

from error_handling import safe_agent_call, with_agent_fallback

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Define a custom tool as a Python function using the @tool decorator
@tool
def letter_counter(word: str, letter: str) -> int:
    """
    Count occurrences of a specific letter in a word.

    Args:
        word (str): The input word to search in
        letter (str): The specific letter to count

    Returns:
        int: The number of occurrences of the letter in the word
    """
    if not isinstance(word, str) or not isinstance(letter, str):
        return 0

    if len(letter) != 1:
        raise ValueError("The 'letter' parameter must be a single character")

    return word.lower().count(letter.lower())

@with_agent_fallback({
    'statusCode': 500,
    'body': json.dumps({'error': 'Agent processing failed', 'response': 'Unable to process request'})
})
def lambda_handler(event, context):
    # Create an agent with tools from the strands-tools example tools package
    try:
        # Create an agent with tools from the strands-tools example tools package
        # as well as our custom letter_counter tool
        agent = Agent(tools=[calculator, current_time, letter_counter])

        # Extract prompt from different possible locations in the event
        prompt = None
        if 'prompt' in event:
            # Direct Lambda invocation
            prompt = event['prompt']
        elif event.get('queryStringParameters') and 'prompt' in event['queryStringParameters']:
            # API Gateway GET request
            prompt = event['queryStringParameters']['prompt']
        elif 'body' in event and event['body']:
            # API Gateway POST request
            try:
                if isinstance(event['body'], dict):
                    prompt = event['body'].get('prompt')
                else:
                    body = json.loads(event['body'])
                    prompt = body.get('prompt')
            except Exception as e:
                logger.error(f"Error parsing request body: {str(e)}")
        
        if not prompt:
            logger.warning("No prompt provided in request")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'No prompt provided'}),
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
                }
            }

        # Use safe agent call with fallback
        fallback_response = "Unable to process your request due to a system error. Please try again."
        response = safe_agent_call(agent, prompt, fallback_response)
        
        logger.info(f"Agent response generated for prompt: {prompt[:50]}...")
        
        return {
            'statusCode': 200,
            'body': json.dumps({'response': str(response)}),
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            }
        }
        
    except Exception as e:
        logger.error(f"Error in prompt agent handler: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'}),
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            }
        }
            }
        }
    
    # URL decode the prompt if needed
    if isinstance(prompt, str) and '%' in prompt:
        prompt = urllib.parse.unquote(prompt)
    
    # Process the prompt through the agent
    response = agent(prompt)
    
    # Return the response in a proper Lambda format
    return {
        'statusCode': 200,
        'body': json.dumps(str(response)),
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
        }
    }