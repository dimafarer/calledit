#!/usr/bin/env python3
"""
Verification Agent — Verifies predictions using the 3-category system.

Routes predictions by category:
- auto_verifiable: Verify with reasoning + all active registered tools
- automatable: Return inconclusive (tool gap — tool doesn't exist yet)
- human_only: Return inconclusive (requires human judgment)

Upgraded to Claude Sonnet 4 for consistency with prediction pipeline agents.
"""

import sys
import os
import time
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

from strands import Agent
from verification_result import (
    VerificationResult, VerificationStatus,
    create_tool_gap_result
)

# Try to import tool_registry — may not be available in all deployment contexts
try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'strands_make_call'))
    from tool_registry import read_active_tools
except ImportError:
    # Fallback: read tools directly from DDB if tool_registry module not available
    def read_active_tools(table_name="calledit-db", region="us-west-2"):
        """Inline fallback for reading active tools from DDB."""
        import boto3
        dynamodb = boto3.resource("dynamodb", region_name=region)
        table = dynamodb.Table(table_name)
        tools = []
        scan_kwargs = {}
        while True:
            response = table.scan(**scan_kwargs)
            for item in response.get("Items", []):
                if item.get("PK", "").startswith("TOOL#") and item.get("status") == "active":
                    tools.append(item)
            if "LastEvaluatedKey" not in response:
                break
            scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        return tools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PredictionVerificationAgent:
    """Verifies predictions using the 3-category routing system."""

    def __init__(self):
        # Load active tools from registry
        self.registered_tools = self._load_tools()

        # Build agent with registered tools
        agent_tools = self._build_tool_list()
        self.agent = Agent(
            name="prediction_verifier",
            model="us.anthropic.claude-sonnet-4-20250514-v1:0",
            tools=agent_tools if agent_tools else None
        )
        logger.info(f"Verification agent created with {len(agent_tools)} tools")

    def _load_tools(self) -> List[Dict]:
        """Load active tools from the DynamoDB tool registry."""
        try:
            tools = read_active_tools()
            logger.info(f"Loaded {len(tools)} active tools from registry")
            return tools
        except Exception as e:
            logger.error(f"Failed to load tools from registry: {e}")
            return []

    def _build_tool_list(self) -> list:
        """Build the Strands tool list from registered tools."""
        tools = []
        for tool_record in self.registered_tools:
            tool_name = tool_record.get("name", "")
            if tool_name == "web_search":
                try:
                    from web_search_tool import web_search
                    tools.append(web_search)
                    logger.info("Loaded web_search tool")
                except ImportError:
                    logger.warning("web_search tool registered but module not found")
        return tools

    def verify_prediction(self, prediction: Dict[str, Any]) -> VerificationResult:
        """Route prediction to appropriate verification method based on category."""
        start_time = time.time()

        prediction_id = prediction.get('SK', 'unknown')
        statement = prediction.get('prediction_statement', '')
        category = prediction.get('verifiable_category', 'unknown')
        verification_date = prediction.get('verification_date', '')

        logger.info(f"Verifying: {statement[:50]}... | Category: {category}")

        try:
            if category == 'auto_verifiable':
                result = self._verify_with_tools(prediction_id, statement, verification_date)
            elif category == 'automatable':
                result = self._mark_tool_gap(prediction_id, statement, verification_date)
            elif category == 'human_only':
                result = self._mark_human_required(prediction_id, statement, verification_date)
            else:
                result = self._handle_unknown_category(prediction_id, statement, verification_date)

            result.processing_time_ms = int((time.time() - start_time) * 1000)
            return result

        except Exception as e:
            logger.error(f"Verification error: {e}", exc_info=True)
            return VerificationResult(
                prediction_id=prediction_id,
                status=VerificationStatus.ERROR,
                confidence=0.0,
                reasoning=f"Verification failed: {str(e)}",
                verification_date=datetime.now(timezone.utc),
                tools_used=[],
                agent_thoughts=f"Error during verification: {str(e)}",
                error_message=str(e),
                processing_time_ms=int((time.time() - start_time) * 1000),
                verification_method="error_fallback"
            )

    def _verify_with_tools(self, prediction_id: str, statement: str, verification_date: str) -> VerificationResult:
        """Verify using reasoning + all active registered tools."""
        tool_names = [t.get("name", "unknown") for t in self.registered_tools]
        tools_desc = ", ".join(tool_names) if tool_names else "reasoning only"

        prompt = f"""Verify this prediction. Determine if it is TRUE, FALSE, or INCONCLUSIVE.

Prediction: "{statement}"
Verification Date: {verification_date}
Available tools: {tools_desc}

Use any available tools if they help verify the prediction.
If no tools are needed, use pure reasoning and established knowledge.

Respond with a clear verdict (TRUE, FALSE, or INCONCLUSIVE) and your reasoning.
Provide a confidence level from 0.0 to 1.0."""

        try:
            response = self.agent(prompt)
            agent_output = str(response)

            # Parse verdict from response
            output_lower = agent_output.lower()
            if 'true' in output_lower and 'false' not in output_lower:
                status = VerificationStatus.TRUE
                confidence = 0.85
            elif 'false' in output_lower and 'true' not in output_lower:
                status = VerificationStatus.FALSE
                confidence = 0.85
            else:
                status = VerificationStatus.INCONCLUSIVE
                confidence = 0.5

            return VerificationResult(
                prediction_id=prediction_id,
                status=status,
                confidence=confidence,
                reasoning=agent_output[:500],
                verification_date=datetime.now(timezone.utc),
                tools_used=tool_names or ['reasoning'],
                agent_thoughts=agent_output,
                verification_method='auto_verification'
            )
        except Exception as e:
            logger.error(f"Tool verification failed, falling back to reasoning: {e}")
            return VerificationResult(
                prediction_id=prediction_id,
                status=VerificationStatus.INCONCLUSIVE,
                confidence=0.3,
                reasoning=f"Tool verification failed, reasoning fallback: {str(e)}",
                verification_date=datetime.now(timezone.utc),
                tools_used=['reasoning_fallback'],
                agent_thoughts=str(e),
                verification_method='reasoning_fallback'
            )

    def _mark_tool_gap(self, prediction_id: str, statement: str, verification_date: str) -> VerificationResult:
        """Mark automatable predictions as inconclusive — tool doesn't exist yet."""
        return create_tool_gap_result(
            prediction_id=prediction_id,
            prediction_text=statement,
            category='automatable',
            reasoning="This prediction is automatable but requires a tool that hasn't been built yet."
        )

    def _mark_human_required(self, prediction_id: str, statement: str, verification_date: str) -> VerificationResult:
        """Mark human_only predictions as inconclusive — requires human judgment."""
        return VerificationResult(
            prediction_id=prediction_id,
            status=VerificationStatus.INCONCLUSIVE,
            confidence=0.0,
            reasoning="Requires human judgment — subjective or personal prediction.",
            verification_date=datetime.now(timezone.utc),
            tools_used=[],
            agent_thoughts=f"'{statement}' requires human assessment.",
            verification_method='human_assessment_required'
        )

    def _handle_unknown_category(self, prediction_id: str, statement: str, verification_date: str) -> VerificationResult:
        """Handle predictions with unrecognized categories."""
        return VerificationResult(
            prediction_id=prediction_id,
            status=VerificationStatus.INCONCLUSIVE,
            confidence=0.0,
            reasoning=f"Unknown verifiability category. Cannot determine verification method.",
            verification_date=datetime.now(timezone.utc),
            tools_used=[],
            agent_thoughts=f"Unrecognized category for: {statement}",
            verification_method='unknown_category_fallback'
        )


def main():
    """Test the verification agent."""
    agent = PredictionVerificationAgent()

    test_predictions = [
        {'SK': 'test_1', 'prediction_statement': 'The sun will rise tomorrow',
         'verifiable_category': 'auto_verifiable', 'verification_date': '2026-03-14T06:00:00Z'},
        {'SK': 'test_2', 'prediction_statement': 'It will rain in Seattle today',
         'verifiable_category': 'automatable', 'verification_date': '2026-03-13T23:59:59Z'},
        {'SK': 'test_3', 'prediction_statement': 'I will feel happy tomorrow',
         'verifiable_category': 'human_only', 'verification_date': '2026-03-14T00:00:00Z'},
    ]

    for p in test_predictions:
        print(f"\n{p['prediction_statement']} [{p['verifiable_category']}]")
        result = agent.verify_prediction(p)
        print(f"  → {result.status.value} (confidence: {result.confidence})")
        print(f"  → {result.reasoning[:100]}")


if __name__ == "__main__":
    main()
