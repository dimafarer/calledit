"""
MCP Manager — Manages MCP server connections and tool discovery.

Replaces the DynamoDB-based tool_registry.py with MCP-native tool discovery.
Connections are established at module level (Lambda INIT) and reused across
warm Lambda invocations. Same singleton pattern as prediction_graph.

Three MCP servers are configured:
  - fetch: URL fetching + HTML-to-markdown conversion (no API key)
  - brave_search: Web search via Brave Search API (needs BRAVE_API_KEY)
  - playwright: Browser automation for dynamic content (no API key)

Graceful degradation: if any server fails, the remaining servers still
contribute tools. If ALL servers fail, the pipeline operates in reasoning-only
mode (empty manifest) — same behavior as before MCP integration.

References:
  - Decision 64: Spec split (A1 infrastructure, A2 application logic)
  - Decision 65: Docker Lambda for MCP subprocess support
  - Decision 57: Tools should be architecture-agnostic
"""

import os
import logging
from typing import List, Dict, Any

from strands.tools.mcp import MCPClient
from mcp import StdioServerParameters

logger = logging.getLogger(__name__)

# Static MCP server configurations.
# Each entry maps to an npx-invoked MCP server subprocess.
# Node.js + npm are available in the Docker Lambda image (Spec A1).
MCP_SERVERS: Dict[str, Dict[str, Any]] = {
    "fetch": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-fetch"],
        "env": None,
    },
    "brave_search": {
        "command": "npx",
        "args": ["-y", "@nicobailon/mcp-brave-search"],
        "env": {"BRAVE_API_KEY": os.environ.get("BRAVE_API_KEY", "")},
    },
    "playwright": {
        "command": "npx",
        "args": ["-y", "@nicobailon/mcp-playwright"],
        "env": None,
    },
}


class MCPManager:
    """Manages MCP server connections and provides tool discovery.

    Connects to configured MCP servers via stdio transport (npx subprocesses),
    discovers tools via list_tools_sync(), and builds a human-readable manifest
    for injection into agent system prompts.

    Usage:
        from mcp_manager import mcp_manager
        manifest = mcp_manager.get_tool_manifest()  # for agent prompts
        clients = mcp_manager.get_mcp_clients()      # for future Agent(tools=[...])
    """

    def __init__(self):
        self._clients: Dict[str, MCPClient] = {}
        self._tool_list: list = []
        self._manifest: str = ""
        self._initialize()

    def _initialize(self):
        """Connect to all configured MCP servers, discover tools."""
        for name, config in MCP_SERVERS.items():
            try:
                env = {**os.environ, **(config["env"] or {})}
                client = MCPClient(
                    lambda c=config, e=env: StdioServerParameters(
                        command=c["command"],
                        args=c["args"],
                        env=e,
                    )
                )
                client.start()
                tools = client.list_tools_sync()
                self._clients[name] = client
                self._tool_list.extend(tools)
                logger.info(f"MCP server '{name}' connected: {len(tools)} tools")
            except Exception as e:
                logger.error(f"MCP server '{name}' failed to connect: {e}")

        if not self._clients:
            logger.warning(
                "All MCP servers failed — operating in reasoning-only mode"
            )

        self._manifest = self._build_manifest()
        logger.info(
            f"MCP Manager initialized: {len(self._clients)} servers, "
            f"{len(self._tool_list)} tools"
        )

    def _build_manifest(self) -> str:
        """Build human-readable tool manifest from discovered tools."""
        if not self._tool_list:
            return ""
        lines = []
        for tool in self._tool_list:
            name = getattr(tool, "name", str(tool))
            desc = getattr(tool, "description", "No description")
            lines.append(f"- {name}: {desc}")
        return "\n".join(lines)

    def get_tool_manifest(self) -> str:
        """Return human-readable tool manifest for agent prompts."""
        return self._manifest

    def get_mcp_clients(self) -> List[MCPClient]:
        """Return MCPClient instances for future Agent(tools=[...]) wiring (Spec B)."""
        return list(self._clients.values())

    def get_mcp_tools(self) -> list:
        """Return raw MCP tool objects from aggregated tool list."""
        return list(self._tool_list)

    def shutdown(self):
        """Stop all MCP client connections."""
        for name, client in self._clients.items():
            try:
                client.stop(None, None, None)
                logger.info(f"MCP server '{name}' stopped")
            except Exception as e:
                logger.error(f"Failed to stop MCP server '{name}': {e}")


# Module-level singleton — initialized at Lambda INIT, reused across warm invocations.
mcp_manager = MCPManager()
