"""
Prediction Verification Graph

This module implements the 3-agent graph workflow for prediction verification:
Parser → Categorizer → Verification Builder

Following Strands best practices and official documentation:
- GraphBuilder for sequential workflow
- Plain Agent nodes (Graph handles text propagation automatically)
- Agents return JSON that gets passed to next agents
- Simple JSON parsing with fallbacks

Based on official Strands Graph documentation:
https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/graph/

Key insight: The Graph automatically propagates outputs between nodes.
Entry nodes receive the original task, dependent nodes receive the original task
plus results from all completed dependencies. No custom state management needed!
"""

import logging
import json
from typing import Dict, Any
from strands.multiagent import GraphBuilder

from parser_agent import create_parser_agent
from categorizer_agent import create_categorizer_agent
from verification_builder_agent import create_verification_builder_agent

logger = logging.getLogger(__name__)


def extract_json_from_text(text: str) -> str:
    """
    Extract JSON from text that might be wrapped in markdown code blocks or have extra text.
    
    Tries multiple strategies:
    1. Direct JSON parse (if text is already clean JSON)
    2. Extract from ```json ... ``` markdown blocks
    3. Extract from ``` ... ``` code blocks
    4. Find JSON object/array in text
    
    Args:
        text: Text that contains JSON (possibly with markdown or extra text)
        
    Returns:
        Extracted JSON string (still needs to be parsed with json.loads)
    """
    import re
    
    # Strategy 1: Try direct parse (text is already clean JSON)
    text = text.strip()
    if text.startswith('{') or text.startswith('['):
        return text
    
    # Strategy 2: Extract from ```json ... ``` blocks
    json_block_match = re.search(r'```json\s*\n(.*?)\n```', text, re.DOTALL)
    if json_block_match:
        return json_block_match.group(1).strip()
    
    # Strategy 3: Extract from ``` ... ``` blocks (no language specified)
    code_block_match = re.search(r'```\s*\n(.*?)\n```', text, re.DOTALL)
    if code_block_match:
        potential_json = code_block_match.group(1).strip()
        if potential_json.startswith('{') or potential_json.startswith('['):
            return potential_json
    
    # Strategy 4: Find JSON object in text (look for { ... })
    json_obj_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_obj_match:
        return json_obj_match.group(0)
    
    # Strategy 5: Find JSON array in text (look for [ ... ])
    json_arr_match = re.search(r'\[.*\]', text, re.DOTALL)
    if json_arr_match:
        return json_arr_match.group(0)
    
    # If all strategies fail, return original text
    return text


def create_prediction_graph():
    """
    Create the 3-agent prediction verification graph.
    
    Graph structure:
    Parser → Categorizer → Verification Builder
    
    The Graph automatically handles input propagation:
    - Parser receives the original task (user prompt with context)
    - Categorizer receives original task + Parser's output
    - Verification Builder receives original task + Parser's output + Categorizer's output
    
    Each agent returns JSON, which the Graph passes to dependent nodes.
    
    Returns:
        Compiled graph ready for execution
    """
    # Create the agents
    parser_agent = create_parser_agent()
    categorizer_agent = create_categorizer_agent()
    verification_builder_agent = create_verification_builder_agent()
    
    # Create GraphBuilder
    builder = GraphBuilder()
    
    # Add agents as nodes (agent first, then node ID)
    builder.add_node(parser_agent, "parser")
    builder.add_node(categorizer_agent, "categorizer")
    builder.add_node(verification_builder_agent, "verification_builder")
    
    # Add edges (define sequential flow)
    builder.add_edge("parser", "categorizer")
    builder.add_edge("categorizer", "verification_builder")
    
    # Set entry point
    builder.set_entry_point("parser")
    
    # Build graph
    graph = builder.build()
    
    logger.info("Prediction graph created with 3 agent nodes")
    
    return graph


# Create the graph instance (singleton)
prediction_graph = create_prediction_graph()


def parse_graph_results(result) -> Dict[str, Any]:
    """
    Parse the graph results and extract all agent outputs.
    
    The Graph returns a MultiAgentResult with results from each node.
    We need to extract and parse the JSON from each agent.
    
    Args:
        result: MultiAgentResult from graph execution
        
    Returns:
        Dictionary with all parsed outputs
    """
    parsed_data = {}
    
    # Parse parser output
    if "parser" in result.results:
        parser_result_obj = result.results["parser"]
        # Get the actual text content from the AgentResult
        parser_result = str(parser_result_obj.result) if hasattr(parser_result_obj, 'result') else str(parser_result_obj)
        
        logger.info(f"Parser raw output (first 200 chars): {parser_result[:200]}")
        
        try:
            # Extract JSON from potentially wrapped text
            json_text = extract_json_from_text(parser_result)
            parser_data = json.loads(json_text)
            parsed_data["prediction_statement"] = parser_data.get("prediction_statement", "")
            parsed_data["verification_date"] = parser_data.get("verification_date", "")
            parsed_data["date_reasoning"] = parser_data.get("date_reasoning", "")
            logger.info("Parser JSON parsed successfully")
        except json.JSONDecodeError as e:
            logger.error(f"Parser JSON decode error: {str(e)}")
            logger.error(f"Parser raw output: {parser_result}")
            parsed_data["prediction_statement"] = ""
            parsed_data["verification_date"] = ""
            parsed_data["date_reasoning"] = "Fallback: Could not parse parser response"
    
    # Parse categorizer output
    if "categorizer" in result.results:
        categorizer_result_obj = result.results["categorizer"]
        categorizer_result = str(categorizer_result_obj.result) if hasattr(categorizer_result_obj, 'result') else str(categorizer_result_obj)
        
        logger.info(f"Categorizer raw output (first 200 chars): {categorizer_result[:200]}")
        
        try:
            # Extract JSON from potentially wrapped text
            json_text = extract_json_from_text(categorizer_result)
            categorizer_data = json.loads(json_text)
            parsed_data["verifiable_category"] = categorizer_data.get("verifiable_category", "human_verifiable_only")
            parsed_data["category_reasoning"] = categorizer_data.get("category_reasoning", "")
            logger.info("Categorizer JSON parsed successfully")
        except json.JSONDecodeError as e:
            logger.error(f"Categorizer JSON decode error: {str(e)}")
            logger.error(f"Categorizer raw output: {categorizer_result}")
            parsed_data["verifiable_category"] = "human_verifiable_only"
            parsed_data["category_reasoning"] = "Fallback: Could not parse categorizer response"
    
    # Parse verification builder output
    if "verification_builder" in result.results:
        verification_result_obj = result.results["verification_builder"]
        verification_result = str(verification_result_obj.result) if hasattr(verification_result_obj, 'result') else str(verification_result_obj)
        
        logger.info(f"Verification builder raw output (first 200 chars): {verification_result[:200]}")
        
        try:
            # Extract JSON from potentially wrapped text
            json_text = extract_json_from_text(verification_result)
            verification_data = json.loads(json_text)
            verification_method = verification_data.get("verification_method", {})
            
            # Ensure all fields are lists
            if not isinstance(verification_method.get("source"), list):
                verification_method["source"] = [verification_method.get("source", "Manual verification")]
            if not isinstance(verification_method.get("criteria"), list):
                verification_method["criteria"] = [verification_method.get("criteria", "Human judgment required")]
            if not isinstance(verification_method.get("steps"), list):
                verification_method["steps"] = [verification_method.get("steps", "Manual review needed")]
            
            parsed_data["verification_method"] = verification_method
            logger.info("Verification builder JSON parsed successfully")
        except json.JSONDecodeError as e:
            logger.error(f"Verification builder JSON decode error: {str(e)}")
            logger.error(f"Verification builder raw output: {verification_result}")
            parsed_data["verification_method"] = {
                "source": ["Manual verification"],
                "criteria": ["Human judgment required"],
                "steps": ["Manual review needed"]
            }
    
    return parsed_data


def execute_prediction_graph(
    user_prompt: str,
    user_timezone: str,
    current_datetime_utc: str,
    current_datetime_local: str,
    callback_handler=None
) -> Dict[str, Any]:
    """
    Execute the prediction verification graph with user inputs.
    
    This is the main entry point for processing predictions through
    the 3-agent workflow.
    
    The Graph automatically propagates outputs between agents:
    - Parser receives the initial prompt
    - Categorizer receives Parser's JSON output
    - Verification Builder receives both Parser and Categorizer outputs
    
    Args:
        user_prompt: User's prediction text
        user_timezone: User's timezone (e.g., "America/New_York")
        current_datetime_utc: Current datetime in UTC
        current_datetime_local: Current datetime in user's local timezone
        callback_handler: Optional callback for streaming events
        
    Returns:
        Final state with all agent outputs
    """
    # Build the initial prompt with context for the parser
    initial_prompt = f"""PREDICTION: {user_prompt}
CURRENT DATE: {current_datetime_local}
TIMEZONE: {user_timezone}

Extract the prediction and parse the verification date."""
    
    logger.info(f"Executing prediction graph for: {user_prompt[:50]}...")
    
    try:
        # Execute graph with initial prompt
        # The Graph will automatically propagate outputs between nodes
        if callback_handler:
            result = prediction_graph(initial_prompt, callback_handler=callback_handler)
        else:
            result = prediction_graph(initial_prompt)
        
        logger.info(f"Prediction graph execution completed with status: {result.status}")
        
        # Parse all agent outputs from the graph results
        parsed_data = parse_graph_results(result)
        
        # Add metadata
        parsed_data["user_timezone"] = user_timezone
        parsed_data["current_datetime_utc"] = current_datetime_utc
        parsed_data["current_datetime_local"] = current_datetime_local
        
        # Ensure all required fields are present
        if not parsed_data.get("prediction_statement"):
            parsed_data["prediction_statement"] = user_prompt
        if not parsed_data.get("verification_date"):
            parsed_data["verification_date"] = current_datetime_local
        if not parsed_data.get("verifiable_category"):
            parsed_data["verifiable_category"] = "human_verifiable_only"
        if not parsed_data.get("verification_method"):
            parsed_data["verification_method"] = {
                "source": ["Manual verification"],
                "criteria": ["Human judgment required"],
                "steps": ["Manual review needed"]
            }
        
        logger.debug(f"Final parsed data keys: {list(parsed_data.keys())}")
        return parsed_data
        
    except Exception as e:
        logger.error(f"Prediction graph execution failed: {str(e)}", exc_info=True)
        
        # Return error state
        return {
            "error": f"Graph execution failed: {str(e)}",
            "prediction_statement": user_prompt,
            "verification_date": current_datetime_local,
            "date_reasoning": "Error during processing",
            "verifiable_category": "human_verifiable_only",
            "category_reasoning": "Error during processing",
            "verification_method": {
                "source": ["Manual verification"],
                "criteria": ["Human judgment required"],
                "steps": ["Manual review needed due to error"]
            },
            "user_timezone": user_timezone,
            "current_datetime_utc": current_datetime_utc,
            "current_datetime_local": current_datetime_local
        }
