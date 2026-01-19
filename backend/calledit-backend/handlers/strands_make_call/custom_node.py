"""
Custom Node Wrapper for Strands Graph

This module provides a wrapper to use our JSON-based agents as graph nodes
by implementing the MultiAgentBase interface.

Our agents return structured JSON, but Strands Graph expects nodes to handle
state management. This wrapper bridges that gap.

Based on official Strands documentation:
https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/graph/
"""

import logging
import json
from typing import Callable, Dict, Any
from strands.multiagent.base import MultiAgentBase, Status, MultiAgentResult, NodeResult
from strands import Agent

logger = logging.getLogger(__name__)


class StateManagingAgentNode(MultiAgentBase):
    """
    Wraps an Agent with state management for use in a Strands Graph.
    
    This node:
    1. Receives state from previous nodes
    2. Builds a prompt for the agent based on state
    3. Invokes the agent
    4. Parses JSON response
    5. Updates state with agent outputs
    6. Returns updated state for next nodes
    """
    
    def __init__(
        self,
        agent: Agent,
        name: str,
        prompt_builder: Callable[[Dict], str],
        response_parser: Callable[[str, Dict], Dict]
    ):
        """
        Initialize the state-managing agent node.
        
        Args:
            agent: The Strands Agent to execute
            name: Name of the node for identification
            prompt_builder: Function that builds prompt from state
            response_parser: Function that parses agent response and updates state
        """
        super().__init__()
        self.agent = agent
        self.name = name
        self.prompt_builder = prompt_builder
        self.response_parser = response_parser
    
    async def invoke_async(self, task, invocation_state, **kwargs):
        """
        Execute the agent with state management.
        
        Args:
            task: Input (either initial prompt or state from previous nodes)
            invocation_state: Shared invocation state (used to pass state between nodes)
            **kwargs: Additional arguments including callback_handler
            
        Returns:
            MultiAgentResult with results dict
        """
        try:
            # Extract state from invocation_state (where previous nodes stored it)
            # or from task if this is the first node
            if invocation_state and "_graph_state" in invocation_state:
                state = invocation_state["_graph_state"]
            elif isinstance(task, dict):
                state = task
            elif isinstance(task, str):
                # Initial input - create state
                state = {"user_prompt": task}
            else:
                state = {}
            
            # Build prompt for this agent based on current state
            prompt = self.prompt_builder(state)
            
            logger.info(f"Executing agent node: {self.name}")
            logger.debug(f"Prompt: {prompt[:100]}...")
            
            # Get callback handler if provided
            callback_handler = kwargs.get("callback_handler")
            
            # Invoke the agent
            if callback_handler:
                agent_result = self.agent(prompt, callback_handler=callback_handler)
            else:
                agent_result = self.agent(prompt)
            
            # Parse response and update state
            updated_state = self.response_parser(str(agent_result), state)
            
            logger.info(f"Node {self.name} completed successfully")
            logger.debug(f"Updated state keys: {list(updated_state.keys())}")
            
            # Store updated state in invocation_state for next nodes
            # The graph will pass invocation_state to subsequent nodes
            if invocation_state is not None:
                invocation_state["_graph_state"] = updated_state
            
            # Create NodeResult for this node
            # NodeResult wraps the agent's result with execution metadata
            node_result = NodeResult(
                result=agent_result,
                status=Status.COMPLETED
            )
            
            # Return MultiAgentResult following official Strands pattern
            # Note: MultiAgentResult does NOT have a 'state' field
            # State is managed via invocation_state and passed between nodes
            return MultiAgentResult(
                status=Status.COMPLETED,
                results={self.name: node_result}
            )
            
        except Exception as e:
            logger.error(f"Node {self.name} failed: {str(e)}", exc_info=True)
            
            # Add error to state
            if invocation_state and "_graph_state" in invocation_state:
                error_state = invocation_state["_graph_state"].copy()
            elif isinstance(task, dict):
                error_state = task.copy()
            else:
                error_state = {"user_prompt": str(task)}
            
            error_state["error"] = f"{self.name} error: {str(e)}"
            
            # Store error state in invocation_state
            if invocation_state is not None:
                invocation_state["_graph_state"] = error_state
            
            # Return failed result
            return MultiAgentResult(
                status=Status.FAILED
            )

