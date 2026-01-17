# Implementation Plan: Strands Graph Refactor

## Overview

This implementation plan refactors the CalledIt prediction verification system from a monolithic single-agent architecture to a Strands Graph-based multi-agent workflow. The approach is iterative: build and test each agent in isolation before integrating into the graph, ensuring progressive validation at each milestone.

## Tasks

- [x] 1. Set up graph infrastructure and shared utilities
  - Create graph state TypedDict definition
  - Set up logging configuration
  - Create utility functions for timezone handling
  - Set up test infrastructure with pytest and hypothesis
  - _Requirements: 1.1, 14.2_

- [-] 2. Implement Parser Agent
  - [x] 2.1 Create Parser Agent with focused system prompt (~25 lines)
    - Define agent with explicit name "parser_agent"
    - Specify model "claude-3-5-sonnet-20241022"
    - Include parse_relative_date and current_time tools
    - Write system prompt for prediction extraction and time parsing
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 9.1_
  
  - [x] 2.2 Implement parser node function
    - Create parser_node_function that invokes Parser Agent
    - Parse JSON response with single json.loads call
    - Update graph state with prediction_statement, verification_date, date_reasoning
    - _Requirements: 2.5, 8.3_
  
  - [x] 2.3 Write unit tests for Parser Agent
    - Test exact text preservation (specific examples)
    - Test 12-hour to 24-hour conversion (3:00pm → 15:00, this morning → 09:00)
    - Test timezone handling (America/New_York, Europe/London, UTC)
    - Test invalid timezone fallback to UTC
    - _Requirements: 2.1, 2.3, 2.4, 11.5_
  
  - [ ] 2.4 Write property test for Parser Agent
    - **Property 2: Parser preserves exact prediction text**
    - **Validates: Requirements 2.1**
  
  - [ ] 2.5 Write property test for time conversion
    - **Property 3: Parser converts 12-hour to 24-hour format**
    - **Validates: Requirements 2.3**
  
  - [ ] 2.6 Write property test for timezone handling
    - **Property 4: Parser respects user timezone**
    - **Validates: Requirements 2.4, 11.2**

- [ ] 3. Checkpoint - Verify Parser Agent works in isolation
  - Run all Parser Agent tests
  - Verify property tests pass with 100+ iterations
  - Ensure all tests pass, ask the user if questions arise

- [ ] 4. Implement Categorizer Agent
  - [ ] 4.1 Create Categorizer Agent with focused system prompt (~30 lines)
    - Define agent with explicit name "categorizer_agent"
    - Specify model "claude-3-5-sonnet-20241022"
    - Write system prompt with 5 verifiability categories and examples
    - _Requirements: 3.1, 3.2, 9.2_
  
  - [ ] 4.2 Implement categorizer node function
    - Create categorizer_node_function that invokes Categorizer Agent
    - Parse JSON response with single json.loads call
    - Validate category is in valid set
    - Update graph state with verifiable_category, category_reasoning
    - _Requirements: 3.1, 3.2, 3.5, 8.3_
  
  - [ ] 4.3 Write unit tests for Categorizer Agent
    - Test each of 5 categories with specific examples
    - Test category validation (reject invalid categories)
    - Test reasoning field is non-empty
    - _Requirements: 3.1, 3.2, 3.3_
  
  - [ ] 4.4 Write property test for Categorizer Agent
    - **Property 6: Categorizer returns valid category**
    - **Validates: Requirements 3.1, 3.2**
  
  - [ ] 4.5 Write property test for reasoning
    - **Property 7: Categorizer provides reasoning**
    - **Validates: Requirements 3.3**

- [ ] 5. Checkpoint - Verify Categorizer Agent works in isolation
  - Run all Categorizer Agent tests
  - Verify property tests pass with 100+ iterations
  - Ensure all tests pass, ask the user if questions arise

- [ ] 6. Implement Verification Builder Agent
  - [ ] 6.1 Create Verification Builder Agent with focused system prompt (~25 lines)
    - Define agent with explicit name "verification_builder_agent"
    - Specify model "claude-3-5-sonnet-20241022"
    - Write system prompt for building verification methods
    - _Requirements: 4.1, 9.3_
  
  - [ ] 6.2 Implement verification builder node function
    - Create verification_builder_node_function that invokes Verification Builder Agent
    - Parse JSON response with single json.loads call
    - Validate verification_method has source, criteria, steps fields
    - Ensure each field is a list
    - Update graph state with verification_method
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 8.3_
  
  - [ ] 6.3 Write unit tests for Verification Builder Agent
    - Test output structure (source, criteria, steps present)
    - Test each field is a list
    - Test with different verifiability categories
    - _Requirements: 4.1, 4.2, 4.3, 4.4_
  
  - [ ] 6.4 Write property test for Verification Builder Agent
    - **Property 9: Verification Builder output structure completeness**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4**

- [ ] 7. Checkpoint - Verify Verification Builder Agent works in isolation
  - Run all Verification Builder Agent tests
  - Verify property tests pass with 100+ iterations
  - Ensure all tests pass, ask the user if questions arise

- [ ] 8. Integrate Parser, Categorizer, and Verification Builder into Graph
  - [ ] 8.1 Create GraphBuilder with state schema
    - Define PredictionGraphState TypedDict
    - Initialize GraphBuilder with state schema
    - _Requirements: 1.1_
  
  - [ ] 8.2 Add nodes to graph
    - Add parser node
    - Add categorizer node
    - Add verification_builder node
    - _Requirements: 1.1_
  
  - [ ] 8.3 Add edges to graph
    - Add edge from parser to categorizer
    - Add edge from categorizer to verification_builder
    - Set entry point to parser
    - _Requirements: 1.1_
  
  - [ ] 8.4 Compile graph
    - Compile graph with GraphBuilder
    - _Requirements: 1.1_
  
  - [ ] 8.5 Write unit tests for graph structure
    - Test graph has 3 nodes (parser, categorizer, verification_builder)
    - Test edges are correct
    - Test entry point is parser
    - _Requirements: 1.1_
  
  - [ ] 8.6 Write integration test for 3-agent graph
    - Test end-to-end execution with sample input
    - Verify state flows through all nodes
    - Verify final state has all expected fields
    - _Requirements: 1.2_
  
  - [ ] 8.7 Write property test for state flow
    - **Property 1: State flows through graph nodes**
    - **Validates: Requirements 1.2**

- [ ] 9. Checkpoint - Verify 3-agent graph works end-to-end
  - Run all graph integration tests
  - Test with various prediction types
  - Ensure all tests pass, ask the user if questions arise

- [ ] 10. Implement Review Agent
  - [ ] 10.1 Create Review Agent with focused system prompt (~30 lines)
    - Define agent with explicit name "review_agent"
    - Specify model "claude-3-5-sonnet-20241022"
    - Write system prompt for identifying improvable sections
    - _Requirements: 5.1, 5.2, 5.3, 9.4_
  
  - [ ] 10.2 Implement review node function
    - Create review_node_function that invokes Review Agent
    - Parse JSON response with single json.loads call
    - Update graph state with reviewable_sections
    - Set initial_status to "pending"
    - _Requirements: 5.2, 8.3_
  
  - [ ] 10.3 Implement section regeneration method
    - Create regenerate_section function
    - Handle prediction_statement regeneration (update related fields)
    - Handle verification_method regeneration (return object structure)
    - Handle other section regeneration (return improved value)
    - _Requirements: 5.4, 5.5_
  
  - [ ] 10.4 Write unit tests for Review Agent
    - Test reviewable_sections structure
    - Test questions are generated for improvable sections
    - Test section regeneration for each field type
    - Test prediction_statement regeneration updates related fields
    - _Requirements: 5.2, 5.3, 5.4, 5.5_
  
  - [ ] 10.5 Write property test for Review Agent
    - **Property 10: Review Agent identifies improvable sections**
    - **Validates: Requirements 5.2**
  
  - [ ] 10.6 Write property test for questions generation
    - **Property 11: Review Agent generates questions for improvable sections**
    - **Validates: Requirements 5.3**
  
  - [ ] 10.7 Write property test for section regeneration
    - **Property 12: Review Agent regenerates sections**
    - **Validates: Requirements 5.4**

- [ ] 11. Integrate Review Agent into Graph
  - [ ] 11.1 Add review node to graph
    - Add review node to GraphBuilder
    - Add edge from verification_builder to review
    - Recompile graph
    - _Requirements: 5.1_
  
  - [ ] 11.2 Write unit test for complete graph structure
    - Test graph has 4 nodes
    - Test all edges are correct
    - Test review is final node
    - _Requirements: 5.1_
  
  - [ ] 11.3 Write integration test for complete graph
    - Test end-to-end execution with all 4 agents
    - Verify state flows through all nodes
    - Verify final state has all expected fields including reviewable_sections
    - _Requirements: 1.2, 5.2_

- [ ] 12. Checkpoint - Verify complete 4-agent graph works
  - Run all graph tests
  - Test with various prediction types
  - Ensure all tests pass, ask the user if questions arise

- [ ] 13. Implement comprehensive callback handler
  - [ ] 13.1 Create callback handler function
    - Handle text generation events (data field)
    - Handle tool usage events (current_tool_use field)
    - Handle lifecycle events (init_event_loop, start_event_loop, complete, force_stop)
    - Handle message events (message field)
    - Implement graceful error handling (catch and log, don't re-raise)
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.7_
  
  - [ ] 13.2 Integrate callback with WebSocket streaming
    - Send text chunks to WebSocket
    - Send tool usage notifications to WebSocket
    - Send status updates to WebSocket
    - Maintain existing JSON message format
    - _Requirements: 7.6, 10.1, 10.2, 10.3, 10.4_
  
  - [ ] 13.3 Write unit tests for callback handler
    - Test each event type is handled without errors
    - Test WebSocket messages are sent with correct format
    - Test callback errors don't crash agent
    - Mock WebSocket client for testing
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.7_
  
  - [ ] 13.4 Write property test for callback error handling
    - **Property 14: Callback handles all event types without crashing**
    - **Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 7.7**

- [ ] 14. Implement Lambda handler with graph integration
  - [ ] 14.1 Create Lambda handler function
    - Extract connection_id, domain_name, stage from event
    - Create API Gateway Management API client
    - Parse request body (prompt, timezone, action)
    - Handle makecall action with graph execution
    - Return proper Lambda response format (statusCode, body)
    - _Requirements: 14.3, 14.4, 14.5_
  
  - [ ] 14.2 Integrate graph execution in Lambda handler
    - Initialize graph state with user inputs
    - Execute graph with callback handler
    - Convert graph output to response format
    - Send response via WebSocket
    - _Requirements: 1.1, 10.5_
  
  - [ ] 14.3 Implement timezone handling
    - Get current datetime in UTC
    - Convert to user's local timezone
    - Handle invalid timezones (fallback to UTC)
    - Provide both UTC and local time in response
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_
  
  - [ ] 14.4 Implement JSON parsing with simple fallback
    - Parse agent responses with single json.loads call
    - Use simple fallback response on parsing failure
    - Remove all regex-based JSON extraction
    - _Requirements: 8.1, 8.2, 8.3, 8.4_
  
  - [ ] 14.5 Write unit tests for Lambda handler
    - Test with valid Lambda event
    - Test connection parameter extraction
    - Test timezone handling
    - Test invalid timezone fallback
    - Test Lambda response format
    - Mock API Gateway client
    - _Requirements: 14.3, 14.4, 14.5, 11.5_
  
  - [ ] 14.6 Write property test for timezone conversion
    - **Property 21: UTC conversion correctness**
    - **Validates: Requirements 11.3**
  
  - [ ] 14.7 Write property test for response format
    - **Property 28: Output format compatibility**
    - **Validates: Requirements 13.2, 13.5**

- [ ] 15. Implement VPSS feedback loop
  - [ ] 15.1 Handle improve_section action
    - Parse section name from request
    - Generate questions using Review Agent
    - Send questions via WebSocket
    - _Requirements: 12.1_
  
  - [ ] 15.2 Handle improvement_answers action
    - Parse section, answers, original_value, full_context from request
    - Regenerate section using Review Agent
    - Handle multiple field updates (for prediction_statement)
    - Send improved response via WebSocket
    - _Requirements: 12.2, 12.3, 12.4_
  
  - [ ] 15.3 Write unit tests for VPSS workflow
    - Test improve_section generates questions
    - Test improvement_answers regenerates section
    - Test prediction_statement updates related fields
    - Test all improvable fields (prediction_statement, verification_date, verification_method, verifiable_category)
    - _Requirements: 12.1, 12.2, 12.3, 12.4_
  
  - [ ] 15.4 Write integration test for VPSS feedback loop
    - Test complete workflow: initial prediction → review → improve_section → improvement_answers → regenerated prediction
    - _Requirements: 12.1, 12.2, 12.3_

- [ ] 16. Remove legacy error handling code
  - [ ] 16.1 Delete error_handling.py file
    - Remove safe_agent_call function
    - Remove with_agent_fallback decorator
    - Remove safe_streaming_callback function
    - Remove ToolFallbackManager class
    - _Requirements: 6.1, 6.2, 6.3_
  
  - [ ] 16.2 Verify error handling removal
    - Verify safe_agent_call is not used anywhere
    - Verify with_agent_fallback is not used anywhere
    - Verify safe_streaming_callback is not used anywhere
    - _Requirements: 6.1, 6.2, 6.3_

- [ ] 17. Verify backward compatibility
  - [ ] 17.1 Write property test for input format compatibility
    - **Property 27: Input format compatibility**
    - **Validates: Requirements 13.1**
  
  - [ ] 17.2 Write property test for action type support
    - **Property 29: Action type support**
    - **Validates: Requirements 13.3**
  
  - [ ] 17.3 Write property test for event type consistency
    - **Property 30: Event type consistency**
    - **Validates: Requirements 13.4**
  
  - [ ] 17.4 Write integration test comparing old and new outputs
    - Test same inputs produce same output structure
    - Test all response fields are present
    - Test WebSocket event types match
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5_

- [ ] 18. Final checkpoint - Complete system verification
  - Run all unit tests
  - Run all property tests (verify 100+ iterations each)
  - Run all integration tests
  - Test in Lambda environment with real WebSocket connections
  - Verify backward compatibility with frontend
  - Ensure all tests pass, ask the user if questions arise

## Notes

- All tasks are required for comprehensive testing from the start
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at each milestone
- Property tests validate universal correctness properties with 100+ iterations
- Unit tests validate specific examples, edge cases, and integration points
- The iterative approach builds and tests each agent in isolation before integration
- Error handling is simplified by removing custom wrappers and using Strands built-in mechanisms
- Backward compatibility is maintained throughout to ensure frontend continues working
