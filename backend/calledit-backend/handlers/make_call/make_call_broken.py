import json
import boto3
from datetime import datetime, timedelta
import logging
import traceback

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
    }
    
    # Handle OPTIONS request for CORS
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({})
        }
    
    if not event.get('queryStringParameters') or 'prompt' not in event['queryStringParameters']:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'error': 'No prompt provided'})
        }
    
    prompt = event['queryStringParameters']['prompt']
    logger.info(f"Processing prompt: {prompt}")
    
    try:
        # Create a simple default response structure
        default_response = {
            "prediction_statement": prompt,
            "verification_date": datetime.now().strftime('%Y-%m-%d'),
            "verification_method": {
                "source": ["Personal verification"],
                "criteria": ["Task completion"],
                "steps": ["Check if the task was completed"]
            },
            "initial_status": "pending"
        }
        
        # Initialize Bedrock client
        bedrock = boto3.client('bedrock-runtime')
        
        # Enhanced system prompt with explicit array format instructions
        system_prompt = [
            {
                "text": """You are an expert in creating structured verification criteria for predictions.

Your goals are to:
1. Analyze natural language predictions
2. Extract key verifiable claims
3. Generate precise verification parameters

Follow these rules:
- Use the datetime_resolver tool for all date references
- Maintain strict JSON formatting with exact keys
- Include measurable criteria where possible
- Specify verification sources explicitly
- ALWAYS format source, criteria, and steps as ARRAYS even if there's only one item


Example input: "miriam will have 2 drinks tonight"
Example Output:
{
 "prediction_statement": "miriam will have 2 drinks tonight",
 "verification_date": "YYYY-MM-DD",
 "verification_method": {
  "criteria": [
   "Miriam consumes exactly 2 drinks",
   "Drinks must be consumed within the timeframe defined as 'tonight'",
   "A drink is defined as a standard serving of an alcoholic beverage (e.g., one glass of wine, one cocktail, one bottle of beer)"
  ],
  "source": [
   "Direct observation by a trusted individual",
   "Self-reporting by Miriam",
   "Counting empty drink containers (e.g., glasses, bottles)"
  ],
  "steps": [
   "Identify a trusted individual to observe Miriam tonight",
   "Define the specific timeframe for 'tonight' (e.g., 6 PM to midnight)",
   "Ensure the observer notes the number of drinks Miriam consumes",
   "Alternatively, ask Miriam to self-report the number of drinks she has had by the end of the night",
   "Count any empty drink containers as additional verification"
  ]
 }
}
.k
Begin every response with proper JSON structure."""
            }
        ]
        
        tool_config = {
            "toolChoice": {"auto": {}},
            "tools": [
                {
                    "toolSpec": {
                        "name": "datetime_resolver",
                        "description": "Converts natural language dates to ISO format",
                        "inputSchema": {
                            "json": {
                                "type": "object",
                                "properties": {
                                    "date_expression": {"type": "string"}
                                },
                                "required": ["date_expression"]
                            }
                        }
                    }
                }
            ]
        }
        
        messages = [
            {
                "role": "user",
                "content": [{"text": f"Create verification format for: {prompt}"}]
            }
        ]
        
        inf_params = {
            "temperature": 0.5,
            "top_p": 0.9,
            "top_k": 50,
            "max_new_tokens": 1000
        }
        
        # First pass - let model potentially call tools
        logger.info("Making initial call to Bedrock")
        response = bedrock.converse(
            modelId='us.amazon.nova-pro-v1:0',
            system=system_prompt,
            messages=messages,
            toolConfig=tool_config,
            inferenceConfig=inf_params
        )
        
        response_body_str = response['body'].read().decode('utf-8')
        logger.info(f"Raw response from Bedrock: {response_body_str[:200]}...")
        
        response_body = json.loads(response_body_str)
        logger.info("Successfully parsed JSON response")
        
        # Handle potential tool calls
        tool_calls = []
        for block in response_body['output']['message']['content']:
            if 'toolUse' in block:
                tool_calls.append(block['toolUse'])
        
        if tool_calls:
            logger.info(f"Tool calls detected: {len(tool_calls)}")
            # Resolve dates and re-run
            for tool_call in tool_calls:
                if tool_call['name'] == 'datetime_resolver':
                    date_expression = tool_call['parameters']['date_expression']
                    resolved_date = resolve_date(date_expression)
                    logger.info(f"Resolved date: '{date_expression}' -> '{resolved_date}'")
                    prompt = prompt.replace(date_expression, resolved_date)
            
            # Second pass with resolved dates
            logger.info(f"Making second pass with resolved dates: {prompt}")
            final_response = bedrock.converse(
                modelId='us.amazon.nova-pro-v1:0',
                system=system_prompt,
                messages=[{
                    "role": "user",
                    "content": [{"text": f"Final verification for: {prompt}"}]
                }],
                inferenceConfig=inf_params
            )
            final_response_body_str = final_response['body'].read().decode('utf-8')
            logger.info(f"Raw final response from Bedrock: {final_response_body_str[:200]}...")
            response_body = json.loads(final_response_body_str)
        
        # Extract JSON content
        text_blocks = []
        for block in response_body['output']['message']['content']:
            if 'text' in block:
                text_blocks.append(block)
        
        if not text_blocks:
            logger.warning("No text content found in the response, using default response")
            prediction_json = default_response
        else:
            text_content = text_blocks[0]['text']
            logger.info(f"Raw text content: {text_content[:200]}...")
            
            # Extract JSON from the text (handle markdown code blocks if present)
            json_str = ""
            try:
                if '```json' in text_content:
                    json_str = text_content.split('```json')[1].split('```')[0].strip()
                    logger.info("Extracted JSON from ```json``` block")
                elif '```' in text_content:
                    json_str = text_content.split('```')[1].strip()
                    logger.info("Extracted JSON from ``` block")
                else:
                    # Try to find JSON content directly
                    start_idx = text_content.find('{')
                    end_idx = text_content.rfind('}') + 1
                    if start_idx >= 0 and end_idx > start_idx:
                        json_str = text_content[start_idx:end_idx]
                        logger.info(f"Extracted JSON using braces: start={start_idx}, end={end_idx}")
                    else:
                        json_str = text_content.strip()
                        logger.info("Using full text content as JSON")
                
                logger.info(f"Extracted JSON string: {json_str[:200]}...")
                
                try:
                    prediction_json = json.loads(json_str)
                    logger.info("Successfully parsed extracted JSON")
                except json.JSONDecodeError as json_err:
                    logger.error(f"JSON parsing error: {str(json_err)}")
                    logger.error(f"Problematic JSON string: {json_str}")
                    # Fall back to default response
                    prediction_json = default_response
            except Exception as extract_err:
                logger.error(f"Error extracting JSON: {str(extract_err)}")
                # Fall back to default response
                prediction_json = default_response
        
        # Ensure verification_method exists
        if "verification_method" not in prediction_json:
            prediction_json["verification_method"] = {
                "source": ["Personal verification"],
                "criteria": ["Task completion"],
                "steps": ["Check if the task was completed"]
            }
        
        verification_method = prediction_json["verification_method"]
        
        # Convert source to array if it's not already
        if "source" in verification_method and not isinstance(verification_method["source"], list):
            verification_method["source"] = [verification_method["source"]]
        elif "source" not in verification_method:
            verification_method["source"] = ["Not specified"]
            
        # Convert criteria to array if it's not already
        if "criteria" in verification_method and not isinstance(verification_method["criteria"], list):
            verification_method["criteria"] = [verification_method["criteria"]]
        elif "criteria" not in verification_method:
            verification_method["criteria"] = ["Not specified"]
            
        # Convert steps to array if it's not already
        if "steps" in verification_method and not isinstance(verification_method["steps"], list):
            verification_method["steps"] = [verification_method["steps"]]
        elif "steps" not in verification_method:
            verification_method["steps"] = ["Not specified"]
        
        # Ensure all required fields exist
        if "prediction_statement" not in prediction_json or not prediction_json["prediction_statement"]:
            prediction_json["prediction_statement"] = prompt
            
        if "verification_date" not in prediction_json or not prediction_json["verification_date"]:
            # Default to tomorrow if no date specified
            prediction_json["verification_date"] = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            
        if "initial_status" not in prediction_json:
            prediction_json["initial_status"] = "pending"
        
        # Create the final response
        result = {
            "prediction_statement": prediction_json["prediction_statement"],
            "verification_date": prediction_json["verification_date"],
            "verification_method": verification_method,
            "initial_status": prediction_json["initial_status"]
        }
        
        logger.info(f"Final result structure: {json.dumps(result)}")
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'results': [result]
            })
        }
    
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Create a fallback response for any error case
        fallback_result = {
            "prediction_statement": prompt,
            "verification_date": datetime.now().strftime('%Y-%m-%d'),
            "verification_method": {
                "source": ["Personal verification"],
                "criteria": ["Task completion"],
                "steps": ["Check if the task was completed"]
            },
            "initial_status": "pending"
        }
        
        # Return a 200 with fallback data instead of 500 error
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'results': [fallback_result],
                'note': 'Using fallback response due to processing error'
            })
        }


def resolve_date(expression):
    """Convert natural language dates to ISO format"""
    today = datetime.now()
    
    expression = expression.lower()
    
    if expression == 'today':
        return today.strftime('%Y-%m-%d')
    elif expression == 'tomorrow':
        return (today + timedelta(days=1)).strftime('%Y-%m-%d')
    elif expression == 'next week':
        return (today + timedelta(weeks=1)).strftime('%Y-%m-%d')
    elif expression == 'next month':
        # Add approximately 30 days
        return (today + timedelta(days=30)).strftime('%Y-%m-%d')
    elif expression == 'yesterday':
        return (today - timedelta(days=1)).strftime('%Y-%m-%d')
    elif 'day' in expression and 'after' in expression:
        # Handle "X days after today" or similar expressions
        try:
            days = int(''.join(filter(str.isdigit, expression)))
            return (today + timedelta(days=days)).strftime('%Y-%m-%d')
        except ValueError:
            return (today + timedelta(days=1)).strftime('%Y-%m-%d')
    else:
        return expression