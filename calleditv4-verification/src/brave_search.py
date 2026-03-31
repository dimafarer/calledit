"""Brave Search tool for the verification agent.

Simple HTTP-based web search using the Brave Search API. This bypasses
the AgentCore Browser tool (which has runtime permission issues) and
provides reliable web search for fact verification.

Decision 145: Brave Search as primary web search tool for verification.

Usage:
    from brave_search import brave_web_search
    agent = Agent(tools=[brave_web_search, ...])

Requires BRAVE_API_KEY environment variable.
"""

import json
import logging
import os

import requests
from strands import tool

logger = logging.getLogger(__name__)

BRAVE_API_KEY = os.environ.get("BRAVE_API_KEY", "")
BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"


@tool
def brave_web_search(query: str, count: int = 5) -> str:
    """Search the web using Brave Search API and return results.

    Use this tool to find current facts, news, data, and information
    from the web. Returns titles, URLs, and descriptions of matching
    web pages.

    Args:
        query: The search query string.
        count: Number of results to return (1-20, default 5).

    Returns:
        JSON string with search results, each containing title, url,
        and description. Returns an error message if the search fails.
    """
    if not BRAVE_API_KEY:
        return json.dumps({
            "error": "BRAVE_API_KEY not configured",
            "results": [],
        })

    count = max(1, min(20, count))

    try:
        response = requests.get(
            BRAVE_SEARCH_URL,
            params={"q": query, "count": count},
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": BRAVE_API_KEY,
            },
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()

        results = []
        for item in data.get("web", {}).get("results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "description": item.get("description", ""),
            })

        return json.dumps({"results": results, "query": query})

    except requests.exceptions.Timeout:
        logger.warning(f"Brave search timed out for query: {query}")
        return json.dumps({"error": "Search timed out", "results": []})
    except requests.exceptions.HTTPError as e:
        logger.error(f"Brave search HTTP error: {e}")
        return json.dumps({"error": f"HTTP {e.response.status_code}", "results": []})
    except Exception as e:
        logger.error(f"Brave search failed: {e}")
        return json.dumps({"error": str(e), "results": []})
