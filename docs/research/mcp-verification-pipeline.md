# MCP Verification Pipeline — Ecosystem Research

**Date:** March 18, 2026
**Purpose:** Research how to implement CalledIt's verification pipeline using MCP tools, covering ecosystem options, integration patterns, security, and a recommended starting stack.

---

## The Core Architecture

The Verification Builder writes verification plans. The verification pipeline executes them. Both need to see the same set of tools. MCP (Model Context Protocol) solves this by providing a standard interface for tool discovery and invocation.

Strands has native MCP support via `MCPClient`. The pattern:

```python
from strands.mcp import MCPClient
from strands import Agent

# Connect to MCP servers
fetch_mcp = MCPClient(lambda: streamablehttp_client("https://fetch-server/mcp/"))
search_mcp = MCPClient(lambda: streamablehttp_client("https://search-server/mcp/"))

with fetch_mcp, search_mcp:
    # Dynamic tool discovery — agent sees all available tools
    tools = fetch_mcp.list_tools_sync() + search_mcp.list_tools_sync()

    # SAME tools go to both the Verification Builder and the execution pipeline
    vb_agent = Agent(model=bedrock_model, tools=tools, system_prompt=vb_prompt)
    verify_agent = Agent(model=bedrock_model, tools=tools, system_prompt=verify_prompt)
```

Key point: `list_tools_sync()` returns tool names, descriptions, and input schemas. If a server adds a new tool, the agent sees it on the next call. No code changes needed.

---

## The MCP Ecosystem — Three Tiers

### Tier 1: Individual Open-Source MCP Servers

These are standalone servers you run yourself via `npx` or `uvx`. Open-source (MIT/Apache), free, and you control the deployment.

**Most relevant for CalledIt verification:**

| Server | License | API Key? | What It Does | Verification Use Case |
|---|---|---|---|---|
| `@modelcontextprotocol/server-fetch` | MIT | No | Fetches any URL, converts HTML to clean markdown | Check news articles, Wikipedia, official sources, API endpoints |
| `@nicobailon/mcp-brave-search` | MIT | Yes (free) | Web search via Brave Search API | Search for verification evidence across the web |
| `@nicobailon/mcp-playwright` | Apache 2.0 | No | Full browser automation (Chromium, Firefox, WebKit) | Navigate dynamic sites, read JavaScript-rendered content |
| `@modelcontextprotocol/server-github` | MIT | Yes (free PAT) | Full GitHub API access | Verify tech predictions (repo stats, releases, etc.) |

**Additional servers for specific prediction categories:**

| Server | License | API Key? | Prediction Category |
|---|---|---|---|
| OpenWeatherMap MCP (build custom) | — | Yes (free, 1000 calls/day) | Weather predictions |
| Sports API MCP (build custom) | — | Varies | Sports outcome predictions |
| Alpha Vantage MCP (build custom) | — | Yes (free, 25 calls/day) | Financial/stock predictions |

### Tier 2: Aggregator Platforms

These bundle many APIs behind a single MCP server, handling auth, rate limiting, and API normalization.

**Jentic** (most promising for CalledIt)
- Single MCP server that provides access to thousands of APIs
- You search their API directory, add APIs to your registry, and your agent calls them
- Free beta tier available
- Pattern: one MCP connection instead of 10+ individual servers
- Worth evaluating after the initial 3-server stack is working
- Docs: [docs.jentic.com](https://docs.jentic.com)

**Composio**
- 200+ pre-built integrations with managed OAuth
- More enterprise-focused, handles token refresh and rate limiting
- Free tier exists but more limited than Jentic
- MCP support added alongside their native spec

**Pica**
- Unified integration layer, 200+ platforms
- Handles OAuth, token refresh, rate limiting, API normalization
- Used by some OpenClaw skills for broad API access

### Tier 3: The Official MCP Registry

`registry.modelcontextprotocol.io` — a read-only REST API for discovering publicly available MCP servers.

- `GET /v0/servers` — list/search servers with pagination
- `GET /v0/servers/{id}` — get server details
- Launched preview September 2025
- Community-maintained, open-source at `github.com/modelcontextprotocol/registry`
- Use this to find new servers, not to execute tools

---

## Tool Discovery: How It Actually Works

Two levels of discovery:

### Level 1: Finding MCP Servers (Registry)
Query the MCP Registry REST API or browse aggregator catalogs to find servers that offer the capabilities you need. This is a design-time activity.

### Level 2: Discovering Tools Within a Server (Runtime)
Once connected to an MCP server, call `list_tools_sync()` (or the MCP `tools/list` method). The server returns every tool it exposes with name, description, and JSON Schema for inputs. This happens at runtime.

```python
# Runtime tool discovery
with mcp_client:
    tools = mcp_client.list_tools_sync()
    # tools is a list of tool definitions the agent can use
    # Each tool has: name, description, inputSchema
```

### Dynamic Updates
MCP supports `notifications/tools/list_changed` — servers can notify clients when their tool list changes. This means if you add a new tool to a running server, connected agents can pick it up without reconnecting.

### Can You Use Any Tool on the Fly?

Not exactly. The flow is:
1. Pre-configure which MCP servers to connect to (config-level decision)
2. Tools within those servers are discovered dynamically at runtime
3. Adding a new tool to an existing server = zero code changes
4. Adding a new MCP server = config change (add the server URL)

You can't just "discover and use" arbitrary servers at runtime without pre-registering the connection. This is by design — it's a security boundary.

---

## Integration with CalledIt's Existing Architecture

### Current State
- Tool registry in DynamoDB (Decision 19) with PK `TOOL#{tool_id}`
- Web search exists as a custom Strands `@tool` (Decision 20)
- Categorizer reads the tool registry to determine `auto_verifiable` vs `automatable`
- Verification Builder writes plans referencing tools it doesn't actually have access to

### Target State
- MCP servers replace the DDB tool registry as the source of truth for available tools
- `MCPClient.list_tools_sync()` replaces DDB reads for tool discovery
- The Verification Builder agent receives MCP tools directly — plans reference real tools
- The verification execution agent receives the same MCP tools — plans are directly executable
- The categorizer receives the tool list to make accurate routing decisions
- DDB tool registry becomes metadata/config (which MCP servers to connect to, not what tools exist)

### Migration Path
1. Keep the existing DDB tool registry for metadata (server URLs, descriptions, status)
2. At runtime, connect to MCP servers listed in the registry
3. Discover tools via `list_tools_sync()`
4. Pass discovered tools to Verification Builder, categorizer, and verification pipeline agents
5. Retire the custom `@tool` web_search in favor of the MCP brave-search or fetch server

---

## Prediction Category Coverage

How the recommended MCP servers map to prediction types:

| Prediction Type | Example | MCP Server | Coverage |
|---|---|---|---|
| Weather | "It will rain tomorrow in Seattle" | fetch (weather API) or custom weather MCP | High — free weather APIs available |
| Sports | "Lakers will beat Celtics tonight" | fetch + brave-search (scrape scores) | Medium — may need custom sports MCP |
| News/Current Events | "Congress will pass the bill this week" | brave-search + fetch | High — web search covers most |
| Financial | "Tesla stock will hit $300 by Friday" | fetch (financial API) | Medium — free tier rate limits |
| Tech | "Python 4.0 will release this year" | github + fetch + brave-search | High |
| Personal/Subjective | "I'll feel better tomorrow" | None | human_only — no tool helps |
| Location/Private | "Miriam will be home before 3pm" | None | human_only — private data |

The first 3 MCP servers (fetch, brave-search, playwright) cover weather, sports, news, financial, and tech predictions — roughly 70-80% of `automatable` predictions could become `auto_verifiable`.

---

## Security Considerations

Sources: OWASP GenAI Security Project MCP guide, defense-first architecture guides.

### Risks and Mitigations

| Risk | Description | Mitigation |
|---|---|---|
| Tool injection / rug pull | Malicious server changes tool descriptions to trick the agent | Pin to trusted servers, validate tool schemas, use signed manifests |
| Excessive permissions | Tools that can write data, execute code, or modify state | Use read-only tools for verification (checking scores, weather, prices) |
| Prompt injection via tool responses | Tool returns data that manipulates the agent's behavior | Treat tool output as untrusted, validate/sanitize responses |
| Credential exposure | API keys for third-party services leaked through agent context | Store in AWS Secrets Manager, let MCP server handle auth, never pass through agent |
| Transport security | Unencrypted communication between agent and MCP server | TLS everywhere, mTLS for sensitive servers |
| Model spoofing | Malicious service impersonates a legitimate MCP tool | Verify server identity, use allowlists |

### CalledIt-Specific Security Profile

Verification tools are read-only by nature — they check scores, weather, prices, news. This significantly reduces the attack surface compared to general-purpose MCP (no file writes, no code execution, no database mutations).

The main CalledIt-specific risk is a tool returning manipulated data that causes a wrong verification result. Mitigations:
- Use multiple sources for verification (cross-reference)
- Log all tool responses for audit
- Human-in-the-loop for high-stakes verifications
- Rate limit tool calls to prevent abuse

### Recommended Security Defaults
- All MCP servers run locally or on your own infrastructure (not third-party hosted)
- TLS for all remote connections
- API keys stored in Secrets Manager, injected as environment variables
- Tool allowlist — only pre-approved tools can be invoked
- Response size limits to prevent context flooding
- Audit logging of all tool invocations and responses

---

## Recommended Implementation Plan

### Phase 1: Starter Stack (3 free MCP servers)
1. `server-fetch` — no API key, covers URL-based verification
2. `mcp-brave-search` — free API key from brave.com, covers web search
3. `mcp-playwright` — no API key, covers dynamic web content

Wire these into the Verification Builder and categorizer via Strands `MCPClient`. Build a basic verification execution agent that receives a plan and executes it.

### Phase 2: Expand Coverage
4. Custom weather MCP server wrapping OpenWeatherMap free tier
5. Custom sports MCP server wrapping a free sports API
6. Evaluate Jentic as a single-server replacement for scaling

### Phase 3: Production Hardening
7. Move MCP server configs to DDB (which servers to connect to)
8. Add security controls (allowlists, audit logging, response validation)
9. Integrate with the eval framework — score verification execution accuracy
10. Build the verification scheduling pipeline (check predictions at the right time)

---

## Key Sources

- [Strands + MCP Integration (AWS Blog)](https://aws.amazon.com/blogs/opensource/open-protocols-for-agent-interoperability-part-3-strands-agents-mcp/) — Strands MCPClient pattern
- [Official MCP Registry](https://registry.modelcontextprotocol.io) — server discovery API
- [MCP Server Spot — Free Servers Guide](https://www.mcpserverspot.com/learn/ecosystem/best-free-mcp-servers) — comprehensive free server list
- [Jentic Docs](https://docs.jentic.com) — aggregator platform documentation
- [OWASP MCP Security Guide](https://www.aigl.blog/a-practical-guide-for-securely-using-third-party-mcp-servers-owasp-genai-security-project-v1-0-oct-23-2025/) — security best practices
- [MCP Security Defense-First Architecture](https://christian-schneider.net/blog/securing-mcp-defense-first-architecture/) — defense in depth guide

Content was rephrased for compliance with licensing restrictions. Sources linked inline.
