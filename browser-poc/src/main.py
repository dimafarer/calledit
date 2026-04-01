"""
Browser PoC Agent — Minimal diagnostic agent for AgentCore Browser tool.

Tests the Browser tool lifecycle layer by layer:
  1. Environment logging (AWS_ env vars, credential source)
  2. Layer 1: boto3 API call (start_browser_session)
  3. Layer 2: SigV4 WebSocket header generation
  4. Playwright CDP connection
  5. Page navigation + title extraction
  6. Session cleanup

No LLM, no Brave Search, no Code Interpreter, no DDB.
Every step is independently try/excepted with full stack traces.
"""

import asyncio
import json
import logging
import os
import sys
import traceback

# Ensure AWS region is set
if not os.environ.get("AWS_DEFAULT_REGION"):
    os.environ["AWS_DEFAULT_REGION"] = os.environ.get("AWS_REGION", "us-west-2")

import boto3
from bedrock_agentcore import RequestContext
from bedrock_agentcore.runtime import BedrockAgentCoreApp

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("browser-poc")

app = BedrockAgentCoreApp()

REGION = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-west-2"))


# ---------------------------------------------------------------------------
# Pure utility functions (testable)
# ---------------------------------------------------------------------------

SENSITIVE_PATTERNS = ("SECRET", "TOKEN", "SESSION", "PASSWORD", "KEY")


def filter_aws_env_vars(env_dict: dict) -> dict:
    """Filter env vars to AWS_-prefixed keys, masking sensitive values.

    Args:
        env_dict: Full environment dictionary.

    Returns:
        Dict with only AWS_-prefixed keys. Values containing sensitive
        patterns (SECRET, TOKEN, SESSION, PASSWORD, KEY) are replaced
        with '***MASKED***'.
    """
    result = {}
    for key, value in env_dict.items():
        if not key.startswith("AWS_"):
            continue
        upper_key = key.upper()
        if any(pat in upper_key for pat in SENSITIVE_PATTERNS):
            result[key] = "***MASKED***"
        else:
            result[key] = value
    return result


def detect_credential_source() -> str:
    """Detect how AWS credentials are being provided."""
    if os.environ.get("AWS_ACCESS_KEY_ID"):
        return "environment_variables"
    if os.environ.get("AWS_CONTAINER_CREDENTIALS_RELATIVE_URI"):
        return "container_credentials (ECS/AgentCore)"
    if os.environ.get("AWS_WEB_IDENTITY_TOKEN_FILE"):
        return "web_identity_token"
    try:
        session = boto3.Session()
        creds = session.get_credentials()
        if creds:
            return f"boto3_session ({creds.method})"
    except Exception:
        pass
    return "unknown"


# ---------------------------------------------------------------------------
# Layer test functions
# ---------------------------------------------------------------------------

def log_environment() -> dict:
    """Log AWS environment variables and credential source."""
    aws_vars = filter_aws_env_vars(dict(os.environ))
    cred_source = detect_credential_source()

    logger.info(f"=== ENVIRONMENT ===")
    logger.info(f"AWS Region: {REGION}")
    logger.info(f"Credential source: {cred_source}")
    for k, v in sorted(aws_vars.items()):
        logger.info(f"  {k} = {v}")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"=== END ENVIRONMENT ===")

    return {
        "aws_region": REGION,
        "credential_source": cred_source,
        "aws_env_vars": aws_vars,
    }


def test_layer1(region: str) -> dict:
    """Layer 1: Start a browser session via boto3 API.

    Tests IAM permissions and API connectivity.
    Returns dict with session_id and browser_identifier.
    """
    from bedrock_agentcore.tools.browser_client import BrowserClient

    logger.info("=== LAYER 1: Starting browser session via boto3 API ===")
    client = BrowserClient(region)
    session_id = client.start()
    identifier = client.identifier

    logger.info(f"Layer 1 SUCCESS: session_id={session_id}, identifier={identifier}")
    return {
        "session_id": session_id,
        "identifier": identifier,
        "_client": client,  # pass client for cleanup
    }


def test_layer2(client) -> dict:
    """Layer 2: Generate SigV4 WebSocket headers and connect via Playwright CDP.

    Tests credential signing and WebSocket/Playwright connectivity.
    Returns dict with ws_url and browser/page objects.
    """
    logger.info("=== LAYER 2: Generating WebSocket headers (SigV4) ===")
    ws_url, headers = client.generate_ws_headers()
    logger.info(f"WebSocket URL: {ws_url}")
    logger.info(f"Headers generated: {list(headers.keys())}")

    # Check if playwright is importable
    logger.info("Checking playwright import...")
    from playwright.async_api import async_playwright
    logger.info("playwright imported successfully")

    return {
        "ws_url": ws_url,
        "headers": headers,
    }


async def test_cdp_connect(ws_url: str, headers: dict) -> dict:
    """Connect to the browser via Playwright CDP over WebSocket.

    This is the step most likely to fail in the deployed runtime.
    """
    from playwright.async_api import async_playwright

    logger.info("=== CDP CONNECT: Connecting via Playwright CDP ===")
    logger.info(f"Connecting to: {ws_url[:80]}...")

    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp(ws_url, headers=headers)
    context = browser.contexts[0]
    page = context.pages[0]

    logger.info(f"CDP connect SUCCESS: browser connected, page available")
    return {
        "browser": browser,
        "page": page,
        "_pw": pw,
    }


async def test_navigation(page, url: str) -> dict:
    """Navigate to a URL and extract the page title."""
    logger.info(f"=== NAVIGATION: Navigating to {url} ===")
    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    title = await page.title()
    logger.info(f"Navigation SUCCESS: title='{title}'")
    return {"title": title}


def cleanup(client) -> None:
    """Stop the browser session."""
    try:
        logger.info("=== CLEANUP: Stopping browser session ===")
        client.stop()
        logger.info("Cleanup SUCCESS")
    except Exception as e:
        logger.error(f"Cleanup failed (non-fatal): {e}", exc_info=True)


# ---------------------------------------------------------------------------
# Also test the Strands AgentCoreBrowser wrapper (what the real agent uses)
# ---------------------------------------------------------------------------

def test_strands_wrapper(region: str, url: str) -> dict:
    """Test the Strands AgentCoreBrowser wrapper directly.

    This is what the verification agent actually uses. If the raw
    layer tests pass but this fails, the issue is in the Strands wrapper.
    """
    logger.info("=== STRANDS WRAPPER: Testing AgentCoreBrowser ===")
    from strands_tools.browser import AgentCoreBrowser

    browser_tool = AgentCoreBrowser(region=region)
    logger.info(f"AgentCoreBrowser initialized (region={region})")

    # The .browser attribute is the Strands tool callable
    tool_fn = browser_tool.browser
    logger.info(f"Browser tool callable: {tool_fn}")
    logger.info(f"Tool name: {getattr(tool_fn, '__name__', 'unknown')}")

    return {"wrapper_initialized": True, "tool_name": getattr(tool_fn, "__name__", "unknown")}


# ---------------------------------------------------------------------------
# Main handler
# ---------------------------------------------------------------------------

@app.entrypoint
def handler(payload: dict, context: RequestContext) -> str:
    """Browser PoC diagnostic handler.

    Payload: {"url": "https://..."}
    Returns JSON with step-by-step results.
    """
    import nest_asyncio
    nest_asyncio.apply()

    url = payload.get("url", "https://en.wikipedia.org/wiki/Main_Page")
    logger.info(f"Browser PoC invoked with url={url}")

    result = {
        "success": False,
        "title": None,
        "steps_completed": [],
        "failed_step": None,
        "error": None,
        "error_detail": None,
        "env_info": None,
        "strands_wrapper": None,
    }

    client = None

    # Step 1: Environment
    try:
        result["env_info"] = log_environment()
        result["steps_completed"].append("env_log")
    except Exception as e:
        result["failed_step"] = "env_log"
        result["error"] = str(e)
        result["error_detail"] = traceback.format_exc()
        logger.error(f"env_log FAILED: {e}", exc_info=True)
        return json.dumps(result)

    # Step 2: Layer 1 (boto3 API)
    try:
        l1 = test_layer1(REGION)
        client = l1["_client"]
        result["steps_completed"].append("layer1")
        logger.info(f"Layer 1 passed: session_id={l1['session_id']}")
    except Exception as e:
        result["failed_step"] = "layer1"
        result["error"] = str(e)
        result["error_detail"] = traceback.format_exc()
        logger.error(f"layer1 FAILED: {e}", exc_info=True)
        return json.dumps(result)

    # Step 3: Layer 2 (SigV4 WebSocket headers)
    try:
        l2 = test_layer2(client)
        result["steps_completed"].append("sigv4_headers")
        logger.info("SigV4 headers generated successfully")
    except Exception as e:
        result["failed_step"] = "sigv4_headers"
        result["error"] = str(e)
        result["error_detail"] = traceback.format_exc()
        logger.error(f"sigv4_headers FAILED: {e}", exc_info=True)
        cleanup(client)
        return json.dumps(result)

    # Step 4: Playwright CDP connect
    try:
        loop = asyncio.get_event_loop()
        cdp = loop.run_until_complete(test_cdp_connect(l2["ws_url"], l2["headers"]))
        result["steps_completed"].append("cdp_connect")
        logger.info("CDP connect passed")
    except Exception as e:
        result["failed_step"] = "cdp_connect"
        result["error"] = str(e)
        result["error_detail"] = traceback.format_exc()
        logger.error(f"cdp_connect FAILED: {e}", exc_info=True)
        cleanup(client)
        return json.dumps(result)

    # Step 5: Navigation
    try:
        nav = loop.run_until_complete(test_navigation(cdp["page"], url))
        result["title"] = nav["title"]
        result["steps_completed"].append("navigate")
        logger.info(f"Navigation passed: title='{nav['title']}'")
    except Exception as e:
        result["failed_step"] = "navigate"
        result["error"] = str(e)
        result["error_detail"] = traceback.format_exc()
        logger.error(f"navigate FAILED: {e}", exc_info=True)

    # Step 6: Close playwright resources
    try:
        loop.run_until_complete(cdp["page"].close())
        loop.run_until_complete(cdp["browser"].close())
        result["steps_completed"].append("pw_cleanup")
    except Exception as e:
        logger.warning(f"Playwright cleanup failed (non-fatal): {e}")

    # Step 7: Cleanup browser session
    cleanup(client)
    result["steps_completed"].append("session_cleanup")

    # Step 8: Test Strands wrapper (bonus — tests what the real agent uses)
    try:
        wrapper_result = test_strands_wrapper(REGION, url)
        result["strands_wrapper"] = wrapper_result
        result["steps_completed"].append("strands_wrapper")
    except Exception as e:
        result["strands_wrapper"] = {"error": str(e), "detail": traceback.format_exc()}
        logger.error(f"strands_wrapper FAILED: {e}", exc_info=True)

    # If we got a title, it's a success
    if result["title"] and result["failed_step"] is None:
        result["success"] = True

    logger.info(f"=== FINAL RESULT: success={result['success']}, "
                f"steps={result['steps_completed']}, "
                f"failed={result['failed_step']} ===")

    return json.dumps(result, indent=2)


if __name__ == "__main__":
    app.run()
