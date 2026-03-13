"""
Tool Registry Reader

Reads tool records from DynamoDB and builds a tool manifest string
for injection into the categorizer agent's system prompt.

Tool records use PK=TOOL#{tool_id}, SK=METADATA in the calledit-db table.
Called at module level in prediction_graph.py (cached by SnapStart).
"""

import boto3
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = {"name", "description", "capabilities", "input_schema", "output_schema", "status", "added_date"}


def read_active_tools(table_name: str = "calledit-db", region: str = "us-west-2") -> List[Dict]:
    """
    Read all active tool records from DynamoDB.

    Returns list of tool dicts with: name, description, capabilities,
    input_schema, output_schema, status, added_date.
    Filters on status='active' and PK starting with 'TOOL#'.
    """
    try:
        dynamodb = boto3.resource("dynamodb", region_name=region)
        table = dynamodb.Table(table_name)

        tools = []
        scan_kwargs = {}

        while True:
            response = table.scan(**scan_kwargs)
            for item in response.get("Items", []):
                pk = item.get("PK", "")
                if pk.startswith("TOOL#") and item.get("status") == "active":
                    tools.append(item)
            if "LastEvaluatedKey" not in response:
                break
            scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

        logger.info(f"Loaded {len(tools)} active tools from registry")
        return tools

    except Exception as e:
        logger.error(f"Failed to read tool registry: {e}", exc_info=True)
        return []


def build_tool_manifest(tools: List[Dict]) -> str:
    """
    Build a human-readable tool manifest string from tool records.

    Format per tool:
      - {name}: {description}
        Capabilities: {comma-separated capabilities}

    Returns empty string if no tools.
    """
    if not tools:
        return ""

    lines = []
    for tool in tools:
        name = tool.get("name", "unknown")
        desc = tool.get("description", "No description")
        caps = tool.get("capabilities", [])
        caps_str = ", ".join(caps) if caps else "general"
        lines.append(f"- {name}: {desc}")
        lines.append(f"  Capabilities: {caps_str}")

    return "\n".join(lines)
