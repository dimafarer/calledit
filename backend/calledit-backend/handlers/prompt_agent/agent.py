import json
import urllib.parse
from strands import Agent, tool
from strands_tools import calculator, current_time
# Skip python_repl which requires filesystem access

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


def lambda_handler(event, context):
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
        except:
            pass
    
    if not prompt:
        return {
            'statusCode': 400,
            'body': json.dumps('Missing prompt parameter'),
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
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