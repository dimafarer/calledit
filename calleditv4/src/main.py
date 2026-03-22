import json
import logging

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from strands.models.bedrock import BedrockModel

logger = logging.getLogger(__name__)

app = BedrockAgentCoreApp()

SYSTEM_PROMPT = (
    "You are the CalledIt v4 foundation agent. "
    "This is a placeholder prompt for infrastructure validation. "
    "Respond helpfully to any message."
)

MODEL_ID = "us.anthropic.claude-sonnet-4-20250514-v1:0"


@app.entrypoint
def handler(payload: dict, context: dict) -> str:
    """Agent entrypoint — receives payload, returns response string."""
    # Validate payload
    if "prompt" not in payload:
        return json.dumps({"error": "Missing 'prompt' field in payload"})

    prompt = payload["prompt"]

    try:
        model = BedrockModel(model_id=MODEL_ID)
        agent = Agent(model=model, system_prompt=SYSTEM_PROMPT)
        response = agent(prompt)
        return str(response)
    except Exception as e:
        logger.error(f"Agent invocation failed: {e}", exc_info=True)
        return json.dumps({"error": f"Agent invocation failed: {str(e)}"})


if __name__ == "__main__":
    app.run()
