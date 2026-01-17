# Requirements Document: Strands Graph Refactor

## Introduction

This specification defines the requirements for refactoring the CalledIt prediction verification system to use Strands Graph pattern with specialized agents. The current implementation uses a single monolithic agent with complex manual parsing and custom error handling. The refactored system will leverage Strands best practices including GraphBuilder for sequential workflows, focused agent prompts, built-in error handling, and proper streaming callbacks.

## Glossary

- **Strands**: An AI agent framework providing tools, streaming, and graph-based workflows
- **Graph**: A Strands pattern for orchestrating multiple agents in sequential or conditional workflows
- **GraphBuilder**: Strands API for constructing agent graphs with nodes and edges
- **Parser_Agent**: Specialized agent that extracts predictions and parses time references
- **Categorizer_Agent**: Specialized agent that determines verifiability category (5 categories)
- **Verification_Builder_Agent**: Specialized agent that builds verification methods (source, criteria, steps) - distinct from the verification system that executes verification
- **Review_Agent**: Specialized agent that identifies improvements using VPSS
- **VPSS**: Verifiable Prediction Structuring System - workflow for improving predictions with user feedback
- **Verifiability_Category**: Classification of how a prediction can be verified (agent_verifiable, current_tool_verifiable, strands_tool_verifiable, api_tool_verifiable, human_verifiable_only)
- **WebSocket_Stream**: Real-time bidirectional communication channel between Lambda and frontend
- **Callback_Handler**: Function that receives agent lifecycle events for streaming to frontend
- **Lambda_Handler**: AWS Lambda entry point function that processes WebSocket messages

## Requirements

### Requirement 1: Graph-Based Architecture

**User Story:** As a system architect, I want to use Strands Graph pattern with specialized agents, so that the system is maintainable and follows best practices.

#### Acceptance Criteria

1. THE System SHALL use GraphBuilder to create a sequential workflow with 4 specialized agents
2. WHEN the graph executes, THE System SHALL pass state between agents using graph state management
3. THE System SHALL define explicit agent names for all agents in the graph
4. THE System SHALL specify explicit model selection for all agents in the graph
5. THE System SHALL support conditional edges for optimization paths in the graph

### Requirement 2: Parser Agent

**User Story:** As a developer, I want a specialized Parser Agent, so that prediction extraction and time parsing are handled separately from other concerns.

#### Acceptance Criteria

1. THE Parser_Agent SHALL extract the user's exact prediction statement without modification
2. WHEN a time reference is provided, THE Parser_Agent SHALL parse it using the parse_relative_date tool
3. THE Parser_Agent SHALL convert 12-hour time formats to 24-hour formats
4. THE Parser_Agent SHALL work in the user's local timezone context
5. THE Parser_Agent SHALL return structured output with prediction_statement and verification_date fields

### Requirement 3: Categorizer Agent

**User Story:** As a developer, I want a specialized Categorizer Agent, so that verifiability categorization logic is isolated and focused.

#### Acceptance Criteria

1. THE Categorizer_Agent SHALL classify predictions into exactly one of 5 verifiability categories
2. THE Categorizer_Agent SHALL validate that the category is one of: agent_verifiable, current_tool_verifiable, strands_tool_verifiable, api_tool_verifiable, human_verifiable_only
3. THE Categorizer_Agent SHALL provide reasoning for the chosen category
4. THE Categorizer_Agent SHALL receive parsed prediction data from Parser_Agent
5. THE Categorizer_Agent SHALL return verifiable_category and category_reasoning fields

### Requirement 4: Verification Builder Agent

**User Story:** As a developer, I want a specialized Verification Builder Agent, so that verification method construction is handled independently from the verification system that executes verification.

#### Acceptance Criteria

1. THE Verification_Builder_Agent SHALL build verification methods with source, criteria, and steps fields
2. THE Verification_Builder_Agent SHALL ensure source is a list of reliable verification sources
3. THE Verification_Builder_Agent SHALL ensure criteria is a list of measurable verification criteria
4. THE Verification_Builder_Agent SHALL ensure steps is a list of detailed verification steps
5. THE Verification_Builder_Agent SHALL receive categorized prediction data from Categorizer_Agent

### Requirement 5: Review Agent Integration

**User Story:** As a developer, I want the Review Agent integrated into the graph, so that VPSS workflow is part of the sequential pipeline.

#### Acceptance Criteria

1. THE Review_Agent SHALL be integrated as the final node in the graph
2. THE Review_Agent SHALL identify improvable sections in the prediction response
3. THE Review_Agent SHALL generate specific questions for each improvable section
4. THE Review_Agent SHALL support regenerating sections with user clarifications
5. WHEN prediction_statement is regenerated, THE Review_Agent SHALL update related fields (verification_date, verification_method)

### Requirement 6: Simplified Error Handling

**User Story:** As a developer, I want to remove custom error wrappers, so that the system uses Strands built-in error handling.

#### Acceptance Criteria

1. THE System SHALL remove the safe_agent_call wrapper function
2. THE System SHALL remove the with_agent_fallback decorator
3. THE System SHALL remove the safe_streaming_callback wrapper function
4. THE System SHALL use try/except blocks only where custom fallback logic is needed
5. THE System SHALL leverage Strands' built-in retry and error handling mechanisms

### Requirement 7: Improved Callback Handler

**User Story:** As a developer, I want a comprehensive callback handler, so that all agent lifecycle events are properly streamed to the frontend.

#### Acceptance Criteria

1. THE Callback_Handler SHALL handle text generation events (data field)
2. THE Callback_Handler SHALL handle tool usage events (current_tool_use field)
3. THE Callback_Handler SHALL handle lifecycle events (init_event_loop, start_event_loop, complete, force_stop)
4. THE Callback_Handler SHALL handle message events (message field)
5. THE Callback_Handler SHALL implement graceful error handling without crashing agent execution
6. THE Callback_Handler SHALL stream events to WebSocket connection in real-time
7. WHEN an error occurs in the callback, THE System SHALL log the error and continue agent execution

### Requirement 8: Simplified JSON Parsing

**User Story:** As a developer, I want to remove manual JSON parsing logic, so that the system trusts Strands to handle structured output.

#### Acceptance Criteria

1. THE System SHALL remove regex-based JSON extraction from markdown code blocks
2. THE System SHALL remove fallback JSON parsing logic
3. THE System SHALL parse agent responses with a single json.loads call
4. WHEN JSON parsing fails, THE System SHALL use a simple fallback response
5. THE System SHALL specify JSON format requirements in agent system prompts

### Requirement 9: Focused Agent Prompts

**User Story:** As a developer, I want concise agent prompts (20-30 lines each), so that agents are focused and maintainable.

#### Acceptance Criteria

1. THE Parser_Agent SHALL have a system prompt of approximately 20-30 lines
2. THE Categorizer_Agent SHALL have a system prompt of approximately 20-30 lines
3. THE Verification_Agent SHALL have a system prompt of approximately 20-30 lines
4. THE Review_Agent SHALL have a system prompt of approximately 20-30 lines
5. THE System SHALL move detailed instructions from system prompts to user prompts where appropriate

### Requirement 10: WebSocket Streaming Compatibility

**User Story:** As a frontend developer, I want the refactored system to maintain WebSocket streaming, so that the user experience is unchanged.

#### Acceptance Criteria

1. THE System SHALL stream text chunks to the frontend via WebSocket
2. THE System SHALL stream tool usage notifications to the frontend via WebSocket
3. THE System SHALL stream status updates to the frontend via WebSocket
4. THE System SHALL maintain the existing JSON message format for frontend compatibility
5. THE System SHALL send completion notifications when processing finishes

### Requirement 11: Timezone Handling Preservation

**User Story:** As a user, I want timezone handling to work correctly, so that my predictions are interpreted in my local time.

#### Acceptance Criteria

1. THE System SHALL accept user_timezone as input from the frontend
2. THE System SHALL interpret time references in the user's local timezone
3. THE System SHALL convert verification dates from local time to UTC for storage
4. THE System SHALL provide both UTC and local time representations in responses
5. THE System SHALL handle invalid timezones by falling back to UTC

### Requirement 12: VPSS Feedback Loop Support

**User Story:** As a user, I want to improve my predictions with clarifications, so that verification is more accurate.

#### Acceptance Criteria

1. WHEN a user requests section improvement, THE System SHALL generate specific questions
2. WHEN a user provides answers, THE System SHALL regenerate the section with clarifications
3. THE System SHALL support improving prediction_statement, verification_date, verification_method, and category fields
4. WHEN prediction_statement changes, THE System SHALL update related fields automatically
5. THE System SHALL use graph cycles to enable iterative improvement workflow

### Requirement 13: Backward Compatibility

**User Story:** As a frontend developer, I want the API contract to remain unchanged, so that the frontend continues to work without modifications.

#### Acceptance Criteria

1. THE System SHALL accept the same WebSocket message format as the current implementation
2. THE System SHALL return the same JSON structure in responses as the current implementation
3. THE System SHALL support the same action types (makecall, improve_section, improvement_answers)
4. THE System SHALL maintain the same WebSocket event types (text, tool, status, call_response, review_complete, complete)
5. THE System SHALL preserve all existing response fields (prediction_statement, verification_date, verifiable_category, verification_method, etc.)

### Requirement 14: AWS Lambda Environment Compatibility

**User Story:** As a DevOps engineer, I want the refactored system to work in AWS Lambda, so that deployment is seamless.

#### Acceptance Criteria

1. THE System SHALL work within AWS Lambda execution time limits
2. THE System SHALL use boto3 for API Gateway Management API calls
3. THE System SHALL handle Lambda context and event objects correctly
4. THE System SHALL manage WebSocket connections using connection_id, domain_name, and stage
5. THE System SHALL return proper Lambda response format with statusCode and body fields
