# Strands Agent Builder

A model-driven approach to building AI agents in just a few lines of code.

An interactive Strands agent toolkit designed to help you build, test, and extend your own custom AI agents and tools. With the Strands Agent Builder, you can create specialized agents, develop custom tools, and compose complex AI workflows—all from your terminal.

## Quick Start

Install:

```bash
pipx install strands-agents-builder
```

### Basic Usage Examples

Run interactive mode for agent development:

```bash
strands
```

Build a custom tool and use it immediately:

```bash
strands "Create a tool named sentiment_analyzer that analyzes text sentiment and test it with some examples"
```

Pipe content to build an agent based on specifications:

```bash
cat agent-spec.txt | strands "Build a specialized agent based on these specifications"
```

Use with knowledge base to extend existing tools:

```bash
strands --kb YOUR_KB_ID "Load my previous calculator tool and enhance it with scientific functions"
```

## Features

- 🏗️ Create and test custom tools with instant hot-reloading
- 🤖 Build specialized agents with focused capabilities
- 🔄 Extend existing tools and enhance their functionality
- 💬 Interactive command-line interface with rich output
- 🛠️ Powerful integrated tools (12+ tools including shell, editor, HTTP, Python)
- 🧠 Knowledge base integration for persisting and loading tools
- 🎮 Customizable system prompt for specialized agents
- 🪄 Nested agent capabilities with tool delegation
- 🔧 Dynamic tool loading for extending functionality
- 🖥️ Environment variable management and customization

## Integrated Tools

Strands comes with a comprehensive set of built-in tools:

- **agent_graph**: Create and manage graphs of agents
- **calculator**: Perform mathematical operations
- **cron**: Task scheduling with cron jobs
- **current_time**: Get the current date and time
- **editor**: File editing operations like line edits, search, and undo
- **environment**: Manage environment variables
- **generate_image**: Create AI generated images with Amazon Bedrock
- **http_request**: Make API calls, fetch web data, and call local HTTP servers
- **image_reader**: Process and analyze images
- **journal**: Create structured tasks and logs for agents to manage and work from
- **load_tool**: Dynamically load more tools at runtime
- **memory**: Agent memory persistence in Amazon Bedrock Knowledge Bases
- **nova_reels**: Create AI generated videos with Nova Reels on Amazon Bedrock
- **python_repl**: Run Python code
- **retrieve**: Semantically retrieve data from Amazon Bedrock Knowledge Bases for RAG, memory, and other purposes
- **shell**: Execute shell commands
- **slack**: Slack integration with real-time events, API access, and message sending
- **speak**: Generate speech from text using macOS say command or Amazon Polly
- **stop**: Force stop the agent event loop
- **store_in_kb**: Save content to knowledge bases for future reference
- **strand**: Create nested agent instances with specialized capabilities
- **swarm**: Coordinate multiple AI agents in a swarm / network of agents
- **think**: Perform deep thinking by creating parallel branches of agentic reasoning
- **use_aws**: Interact with AWS services
- **use_llm**: Run a new AI event loop with custom prompts
- **welcome**: Manage the Strands Agent Builder welcome text
- **workflow**: Orchestrate sequenced workflows

## Knowledge Base Integration

Strands Agent Builder leverages Amazon Bedrock Knowledge Bases to store and retrieve custom tools, agent configurations, and development history.

Load and extend tools from your knowledge base:

```bash
strands --kb YOUR_KB_ID "Load my data_visualizer tool and add 3D plotting capabilities"
```

Or set a default knowledge base via environment variable:

```bash
export STRANDS_KNOWLEDGE_BASE_ID="YOUR_KB_ID"
strands "Find my most recent agent configuration and make it more efficient"
```

Features:

- 🔄 Retrieve previously created tools and agent configurations
- 💾 Persistent storage for your custom tools and agents
- 🛠️ Ability to iteratively improve tools across sessions
- 🔍 Find and extend tools built in previous sessions

## Model Configuration

### Optimized Defaults

Strands comes with optimized, maxed-out configuration settings for the Bedrock model provider:

```json
{
    "model_id": "us.anthropic.claude-sonnet-4-20250514-v1:0",
    "max_tokens": 32767,
    "boto_client_config": {
        "read_timeout": 900,
        "connect_timeout": 900,
        "retries": {
            "max_attempts": 3,
            "mode": "adaptive"
        }
    },
    "additional_request_fields": {
        "anthropic_beta": ["interleaved-thinking-2025-05-14"],
        "thinking": {
            "type": "enabled",
            "budget_tokens": 2048
        }
    }
}
```

These settings provide:

- Claude Sonnet 4 (latest high-performance model)
- Maximum token output (32,768 tokens)
- Extended timeouts (15 minutes) for complex operations
- Automatic retries with adaptive backoff
- Interleaved thinking capability for real-time reasoning during responses
- Enabled thinking capability with 2,048 token budget for recursive reasoning

You can customize these values using environment variables:

```bash
# Maximum tokens for responses
export STRANDS_MAX_TOKENS=32000

# Budget for agent thinking/reasoning
export STRANDS_BUDGET_TOKENS=1024
```

### Custom Model Provider

You can configure strands to use a different model provider with specific settings by passing in the following arguments:

```bash
strands --model-provider <NAME> --model-config '<JSON_CONFIG>'
```

As an example, if you wanted to use the packaged Ollama provider with a specific model id, you would run:

```bash
strands --model-provider ollama --model-config '{"model_id": "llama2"}'
```

Strands Agent Builder is packaged with bedrock and ollama.

If you have implemented a custom model provider and would like to use it with strands, create a python module under the directory "$CWD/.models" and expose an instance function that returns an instance of your provider. As an example, assume you have:

```python
# ./.models/custom_model.py
from mymodels import CustomModel

def instance(**config):
    return CustomModel(**config)
```

You can then use it with strands by running:

```bash
strands --model-provider custom_model --model-config '{"custom_param": "value"}'
```

### Custom System Prompts

```bash
export STRANDS_SYSTEM_PROMPT="You are a Python expert."
```

Or local file:

```bash
echo "You are a security expert." > .prompt
```

## Exit

Type `exit`, `quit`, or press Ctrl+C/Ctrl+D to exit the Strands Agent Builder.
