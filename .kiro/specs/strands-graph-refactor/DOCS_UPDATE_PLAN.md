# docs/current/ Update Plan

## Date: 2025-01-19

## Files Requiring Updates

### 1. APPLICATION_FLOW.md - NEEDS MAJOR UPDATES
**Status:** References old monolith architecture

**Issues Found:**
- Line 115: References `strands_make_call_stream.py` as handler
- Line 192: Code example shows `strands_make_call_stream.py`
- Line 959: Architecture diagram shows `strands_make_call_stream.py`
- Line 962: References `error_handling.py`
- Describes single "Strands Agent" instead of 3-agent graph
- No mention of Parser, Categorizer, Verification Builder agents

**Required Updates:**
1. Update handler references to `strands_make_call_graph.py`
2. Update "STRANDS AGENT EXECUTION" section to "3-AGENT GRAPH EXECUTION"
3. Add Parser → Categorizer → Verification Builder flow
4. Remove error_handling.py references
5. Update code examples to show graph execution
6. Update architecture diagrams

**Priority:** HIGH (core system documentation)

### 2. VPSS_COMPLETE.md - NEEDS CLARIFICATION
**Status:** References old handler, needs future enhancement note

**Issues Found:**
- Line 47: References `strands_make_call_stream.py`
- Marked as "FULLY OPERATIONAL" but not integrated into 3-agent graph
- No mention that it's a future enhancement (Task 10)

**Required Updates:**
1. Add prominent note: "Future Enhancement - Not Yet Integrated"
2. Update handler reference to note it's for future integration
3. Clarify that review_agent.py exists but not in production graph
4. Keep all VPSS details for future reference

**Priority:** MEDIUM (clarification needed)

### 3. STRANDS_GRAPH_FLOW.md - ALREADY UPDATED ✅
**Status:** Complete rewrite done on 2025-01-18
**No action needed**

## Files to Check (May Not Need Updates)

### 4. API.md
**Check for:**
- WebSocket route documentation
- Handler references
- Endpoint descriptions

### 5. TRD.md
**Check for:**
- Technical architecture section
- Agent descriptions
- System requirements

### 6. TESTING.md
**Check for:**
- Test structure descriptions
- Integration test documentation
- Handler references

### 7. VERIFICATION_SYSTEM.md
**Check for:**
- Verification agent references
- System architecture
- May be OK (separate from prediction processing)

### 8. streaming_implementation_guide.md
**Check for:**
- Streaming implementation details
- Handler references
- May reference old architecture

## Files to Archive

### 9. DEPLOYMENT_MANAGEMENT.md
**Check:** May be outdated or one-time documentation

### 10. SECURITY_CLEANUP.md
**Archive:** One-time cleanup documentation

## Update Strategy

### Phase 2A: APPLICATION_FLOW.md (30 min)
1. Update version and date
2. Replace handler references
3. Update "STRANDS AGENT EXECUTION" to "3-AGENT GRAPH EXECUTION"
4. Add 3-agent flow diagram
5. Update code examples
6. Remove error_handling.py references

### Phase 2B: VPSS_COMPLETE.md (10 min)
1. Add "Future Enhancement" banner at top
2. Update handler references with future note
3. Clarify integration status
4. Keep all technical details

### Phase 2C: Quick Audits (30 min)
1. Check API.md, TRD.md, TESTING.md
2. Update any outdated references
3. Mark files as reviewed

### Phase 2D: Archive (10 min)
1. Move SECURITY_CLEANUP.md to archive/
2. Check DEPLOYMENT_MANAGEMENT.md relevance
3. Update doc index if needed

## Success Criteria

- [ ] APPLICATION_FLOW.md reflects 3-agent graph
- [ ] VPSS_COMPLETE.md clarified as future enhancement
- [ ] All docs checked for outdated references
- [ ] No references to deleted files
- [ ] Clear distinction between current and future

## Total Estimated Time: 1.5 hours

Ready to proceed with Phase 2A (APPLICATION_FLOW.md)?
