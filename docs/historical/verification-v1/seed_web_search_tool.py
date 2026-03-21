#!/usr/bin/env python3
"""
Seed the web_search tool record into the DynamoDB tool registry.

Run after deploying the web_search_tool.py module to register it
so the categorizer and verification agent can discover it.

Usage:
    python seed_web_search_tool.py
"""

import boto3
from datetime import datetime, timezone

TABLE_NAME = "calledit-db"
REGION = "us-west-2"


def seed_web_search_tool():
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(TABLE_NAME)

    tool_record = {
        "PK": "TOOL#web_search",
        "SK": "METADATA",
        "name": "web_search",
        "description": "Searches the web to verify factual claims about current events, weather, sports, stocks, and other publicly available data.",
        "capabilities": [
            "weather",
            "sports scores",
            "stock prices",
            "news",
            "factual claims",
            "current events",
            "public data"
        ],
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"}
            },
            "required": ["query"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["success", "error"]},
                "query": {"type": "string"},
                "results": {"type": "array"},
                "result_count": {"type": "integer"}
            }
        },
        "status": "active",
        "added_date": datetime.now(timezone.utc).isoformat()
    }

    table.put_item(Item=tool_record)
    print(f"Seeded web_search tool record in {TABLE_NAME}")
    print(f"  PK: {tool_record['PK']}")
    print(f"  Status: {tool_record['status']}")
    print(f"  Capabilities: {', '.join(tool_record['capabilities'])}")


if __name__ == "__main__":
    seed_web_search_tool()
