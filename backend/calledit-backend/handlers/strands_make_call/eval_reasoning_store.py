"""
Eval Reasoning Store — DynamoDB capture of full model reasoning traces.

Fire-and-forget pattern: DDB failures are logged at WARN level and never
block or abort an evaluation run. The local score history file is always
written regardless of DDB status.

TABLE: calledit-eval-reasoning
  PK: eval_run_id (S) — UUID per eval run
  SK: record_key (S) — record_type#test_case_id

RECORD TYPES:
  run_metadata#SUMMARY — overall run info
  agent_output#<test_case_id> — full text output from all 4 agents
  judge_reasoning#<test_case_id>#<agent_name> — judge score + reasoning
  token_counts#<test_case_id> — input/output tokens per agent

TTL: 90 days from creation (eval data is ephemeral R&D data).
"""

import logging
import time
import uuid
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

TABLE_NAME = "calledit-eval-reasoning"
TTL_DAYS = 90


class EvalReasoningStore:
    """Write eval reasoning traces to DynamoDB. Fire-and-forget on failure."""

    def __init__(self, table_name: str = TABLE_NAME):
        self.table_name = table_name
        self.eval_run_id = str(uuid.uuid4())
        self._table = None
        try:
            import boto3
            self._table = boto3.resource("dynamodb").Table(table_name)
        except Exception as e:
            logger.warning(f"DynamoDB unavailable, reasoning store disabled: {e}")

    def write_run_metadata(
        self,
        manifest: dict,
        dataset_version: str,
        schema_version: str,
        total_tests: int,
        pass_rate: float,
        duration_s: float,
    ):
        """Write overall run metadata."""
        self._put_item("run_metadata#SUMMARY", {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "prompt_version_manifest": manifest,
            "dataset_version": dataset_version,
            "schema_version": schema_version,
            "total_tests": total_tests,
            "pass_rate": str(pass_rate),  # DDB doesn't support float
            "duration_s": str(duration_s),
        })

    def write_agent_outputs(self, test_case_id: str, agent_outputs: Dict[str, str]):
        """Write full text outputs from all 4 agents for a test case."""
        self._put_item(f"agent_output#{test_case_id}", {
            "parser_output": agent_outputs.get("parser", ""),
            "categorizer_output": agent_outputs.get("categorizer", ""),
            "verification_builder_output": agent_outputs.get("verification_builder", ""),
            "review_output": agent_outputs.get("review", ""),
        })

    def write_judge_reasoning(
        self,
        test_case_id: str,
        agent_name: str,
        score: float,
        reasoning: str,
        judge_model: str,
    ):
        """Write judge reasoning for a specific agent evaluation."""
        self._put_item(f"judge_reasoning#{test_case_id}#{agent_name}", {
            "agent_name": agent_name,
            "score": str(score),
            "judge_reasoning": reasoning,
            "judge_model": judge_model,
        })

    def write_token_counts(self, test_case_id: str, counts: Dict[str, Dict[str, int]]):
        """Write token counts per agent.

        Args:
            test_case_id: e.g. "base-001"
            counts: {agent_name: {"input_tokens": N, "output_tokens": N}}
        """
        data = {}
        for agent, tokens in counts.items():
            data[f"{agent}_input_tokens"] = tokens.get("input_tokens", 0)
            data[f"{agent}_output_tokens"] = tokens.get("output_tokens", 0)
        self._put_item(f"token_counts#{test_case_id}", data)

    def _put_item(self, record_key: str, data: dict):
        """Fire-and-forget DDB write. Logs warning on failure, never raises."""
        if not self._table:
            return
        try:
            item = {
                "eval_run_id": self.eval_run_id,
                "record_key": record_key,
                "ttl": int(time.time()) + (TTL_DAYS * 86400),
                **data,
            }
            self._table.put_item(Item=item)
        except Exception as e:
            logger.warning(f"DDB write failed for {record_key}: {e}")
