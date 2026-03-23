import json
import logging
import os

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from strands.models.bedrock import BedrockModel
from strands_tools.browser import AgentCoreBrowser
from strands_tools.code_interpreter import AgentCoreCodeInterpreter

logger = logging.getLogger(__name__)

app = BedrockAgentCoreApp()

AWS_REGION = os.environ.get("AWS_REGION", "us-west-2")

SYSTEM_PROMPT = (
    "You are the CalledIt v4 agent. "
    "You have access to two tools:\n"
    "1. Browser — navigate URLs, search the web, extract content from web pages. "
    "Use this when you need to look up current information, verify facts, or read web content.\n"
    "2. Code Interpreter — execute Python code in a secure sandbox. "
    "Use this for calculations, date math, data analysis, or any task that benefits from running code.\n"
    "Use the appropriate tool when the user's request would benefit from it. "
    "Respond helpfully to any message."
)

MODEL_ID = "us.anthropic.claude-sonnet-4-20250514-v1:0"

# Tool instances — lightweight config objects, no connections until agent uses them
browser_tool = AgentCoreBrowser(region=AWS_REGION)
code_interpreter_tool = AgentCoreCodeInterpreter(region=AWS_REGION)

TOOLS = [browser_tool.browser, code_interpreter_tool.code_interpreter]


@app.entrypoint
def handler(payload: dict, context: dict) -> str:
    """Agent entrypoint — receives payload, returns response string."""
    if "prompt" not in payload:
        return json.dumps({"error": "Missing 'prompt' field in payload"})

    prompt = payload["prompt"]

    try:
        model = BedrockModel(model_id=MODEL_ID)
        agent = Agent(model=model, system_prompt=SYSTEM_PROMPT, tools=TOOLS)
        response = agent(prompt)
        return str(response)
    except Exception as e:
        logger.error(f"Agent invocation failed: {e}", exc_info=True)
        return json.dumps({"error": f"Agent invocation failed: {str(e)}"})


if __name__ == "__main__":
    app.run()
