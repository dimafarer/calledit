"""
Web Search Tool — First registered tool in the CalledIt tool registry.

Custom Strands @tool using Python requests to search the web for
factual verification of predictions (weather, sports, stocks, news, etc.).

Uses DuckDuckGo Instant Answer API (free, no API key required).
"""

import json
import logging
import requests
from strands import tool

logger = logging.getLogger(__name__)

SEARCH_TIMEOUT = 10  # seconds
DDG_API_URL = "https://api.duckduckgo.com/"


@tool
def web_search(query: str) -> str:
    """
    Search the web for information to verify factual claims.

    Args:
        query: Search query string describing what to look up.

    Returns:
        JSON string with search results or structured error.
    """
    if not query or not query.strip():
        return json.dumps({"status": "error", "error": "Empty query", "query": query})

    try:
        response = requests.get(
            DDG_API_URL,
            params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            timeout=SEARCH_TIMEOUT,
            headers={"User-Agent": "CalledIt-Verification/1.0"}
        )
        response.raise_for_status()
        data = response.json()

        # Extract useful fields from DuckDuckGo response
        results = []
        # Abstract (main answer)
        if data.get("Abstract"):
            results.append({
                "type": "abstract",
                "text": data["Abstract"],
                "source": data.get("AbstractSource", ""),
                "url": data.get("AbstractURL", "")
            })
        # Answer (instant answer)
        if data.get("Answer"):
            results.append({
                "type": "answer",
                "text": data["Answer"]
            })
        # Related topics
        for topic in data.get("RelatedTopics", [])[:5]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append({
                    "type": "related",
                    "text": topic["Text"],
                    "url": topic.get("FirstURL", "")
                })

        return json.dumps({
            "status": "success",
            "query": query,
            "results": results,
            "result_count": len(results)
        })

    except requests.Timeout:
        logger.warning(f"Web search timed out for query: {query}")
        return json.dumps({"status": "error", "error": "Request timed out", "query": query})
    except requests.HTTPError as e:
        logger.warning(f"Web search HTTP error for query: {query}: {e}")
        return json.dumps({"status": "error", "error": f"HTTP {e.response.status_code}", "query": query})
    except requests.ConnectionError:
        logger.warning(f"Web search connection failed for query: {query}")
        return json.dumps({"status": "error", "error": "Connection failed", "query": query})
    except Exception as e:
        logger.error(f"Web search unexpected error for query: {query}: {e}")
        return json.dumps({"status": "error", "error": str(e), "query": query})
