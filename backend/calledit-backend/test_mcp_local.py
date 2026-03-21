"""
Local test for MCP server connections.
Run from backend/calledit-backend/:
  /home/wsluser/projects/calledit/venv/bin/python test_mcp_local.py
"""
import os
import subprocess
import shutil

# Step 1: Check npx/node are available
print("=== Step 1: Check npx/node ===")
npx_path = shutil.which("npx")
node_path = shutil.which("node")
print(f"npx: {npx_path}")
print(f"node: {node_path}")

if not npx_path:
    print("ERROR: npx not found on PATH")
    exit(1)

# Step 2: Test npx can download and run a package
print("\n=== Step 2: Test npx subprocess ===")
try:
    result = subprocess.run(
        ["npx", "-y", "@modelcontextprotocol/server-brave-search"],
        capture_output=True, text=True, timeout=30,
        env={**os.environ, "HOME": "/tmp", "NPM_CONFIG_CACHE": "/tmp/.npm",
             "BRAVE_API_KEY": os.environ.get("BRAVE_API_KEY", "test")}
    )
    print(f"returncode: {result.returncode}")
    print(f"stdout: {result.stdout[:500]}")
    print(f"stderr: {result.stderr[:500]}")
except subprocess.TimeoutExpired:
    print("Process started and ran for 30s (good — means it's running as a server)")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")

# Step 3: Test MCPClient connection with brave-search (known good npm package)
print("\n=== Step 3: Test MCPClient with brave-search ===")
try:
    from strands.tools.mcp import MCPClient
    from mcp import StdioServerParameters
    from mcp.client.stdio import stdio_client

    env = {**os.environ, "HOME": "/tmp", "NPM_CONFIG_CACHE": "/tmp/.npm"}

    client = MCPClient(
        lambda: stdio_client(
            StdioServerParameters(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-brave-search"],
                env=env,
            )
        ),
        startup_timeout=60,
    )
    print("Starting MCPClient...")
    client.start()
    print("MCPClient started!")

    tools = client.list_tools_sync()
    print(f"Tools discovered: {len(tools)}")
    for tool in tools:
        print(f"  tool_name={tool.tool_name}")
        # Check tool_spec for description
        spec = getattr(tool, "tool_spec", {})
        print(f"    tool_spec keys: {list(spec.keys()) if isinstance(spec, dict) else type(spec)}")
        if isinstance(spec, dict):
            print(f"    description: {spec.get('description', 'N/A')[:100]}")
        # Also check mcp_tool
        mcp_tool = getattr(tool, "mcp_tool", None)
        if mcp_tool:
            print(f"    mcp_tool.name: {getattr(mcp_tool, 'name', 'N/A')}")
            print(f"    mcp_tool.description: {str(getattr(mcp_tool, 'description', 'N/A'))[:100]}")

    client.stop(None, None, None)
    print("MCPClient stopped cleanly.")

except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
