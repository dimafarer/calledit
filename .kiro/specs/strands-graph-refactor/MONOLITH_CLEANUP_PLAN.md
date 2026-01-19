# Monolith Agent Code Cleanup Plan

## Overview

After successfully implementing the 3-agent graph architecture, we still have legacy code from the original monolith agent design. This plan identifies all legacy files and provides a safe cleanup strategy with testing at each step.

## Current State Analysis

### Active Production Code (3-Agent Graph)
✅ **KEEP - Currently in use:**
- `strands_make_call_graph.py` - **ACTIVE HANDLER** (configured in template.yaml)
- `prediction_graph.py` - Graph orchestration
- `parser_agent.py` - Parser Agent definition
- `categorizer_agent.py` - Categorizer Agent definition
- `verification_builder_agent.py` - Verification Builder Agent definition
- `graph_state.py` - Graph state TypedDict
- `utils.py` - Shared utilities (timezone handling, JSON extraction)
- `requirements.txt` - Dependencies

### Legacy Monolith Code
❌ **DELETE - No longer used:**
- `strands_make_call.py` - Original monolith agent (non-streaming)
- `strands_make_call_stream.py` - Monolith agent with streaming
- `review_agent.py` - Future enhancement (not yet implemented in graph)

### Analysis

**strands_make_call.py:**
- Original monolith design with single agent
- No streaming support
- Handles everything in one agent (parsing, categorization, verification)
- NOT referenced in template.yaml
- NOT imported by any active code

**strands_make_call_stream.py:**
- Monolith design with streaming added
- Still uses single agent for all tasks
- Includes VPSS/review code that's not yet implemented
- References `error_handling.py` (already deleted)
- References `review_agent.py` (future enhancement)
- NOT referenced in template.yaml
- NOT imported by any active code

**review_agent.py:**
- Future enhancement for VPSS feedback loop
- Not yet integrated into 3-agent graph
- Part of Task 10 (future work)
- Keep for now, but mark as future enhancement

## Cleanup Strategy

### Phase 1: Verify No Dependencies
**Goal:** Confirm legacy files are not imported anywhere

**Actions:**
1. Search codebase for imports of `strands_make_call`
2. Search codebase for imports of `strands_make_call_stream`
3. Verify template.yaml only references `strands_make_call_graph`
4. Check if any tests reference legacy files

**Expected Result:** No active code depends on legacy files

### Phase 2: Delete Legacy Monolith Files
**Goal:** Remove unused monolith agent code

**Files to Delete:**
- `backend/calledit-backend/handlers/strands_make_call/strands_make_call.py`
- `backend/calledit-backend/handlers/strands_make_call/strands_make_call_stream.py`

**Rationale:**
- Not referenced in template.yaml (production uses `strands_make_call_graph`)
- Not imported by any active code
- Replaced by 3-agent graph architecture
- Keeping them creates confusion about which code is active

### Phase 3: Handle review_agent.py
**Goal:** Decide what to do with future enhancement code

**Options:**
1. **Keep it** - It's part of Task 10 (future enhancement)
2. **Move it** - Relocate to a "future" directory
3. **Delete it** - Remove and recreate when implementing Task 10

**Recommendation:** Keep it for now, but add clear documentation that it's not yet integrated

### Phase 4: Run Tests
**Goal:** Verify cleanup didn't break anything

**Actions:**
1. Run all 18 integration tests
2. Verify all tests still pass
3. Check for any import errors

**Expected Result:** All tests pass, no regressions

### Phase 5: Update Documentation
**Goal:** Document the cleanup

**Actions:**
1. Update CLEANUP_LOG.md with monolith removal
2. Update tasks.md to reflect cleanup completion
3. Add note about review_agent.py being future work

## Safety Checks

Before deleting each file:
- ✅ Verify not referenced in template.yaml
- ✅ Verify not imported by active code
- ✅ Verify not used by tests
- ✅ Run tests after deletion

## Rollback Plan

If tests fail after cleanup:
1. Git revert the deletion commit
2. Investigate which code was actually using the legacy files
3. Update the cleanup plan
4. Try again with more targeted approach

## Expected Outcome

After cleanup:
- Only 3-agent graph code remains
- No confusion about which handler is active
- Cleaner codebase
- All tests still passing
- Clear separation between current code and future enhancements

## Files Summary

### Keep (Active Production Code)
```
backend/calledit-backend/handlers/strands_make_call/
├── strands_make_call_graph.py      ✅ ACTIVE HANDLER
├── prediction_graph.py              ✅ Graph orchestration
├── parser_agent.py                  ✅ Parser Agent
├── categorizer_agent.py             ✅ Categorizer Agent
├── verification_builder_agent.py    ✅ Verification Builder Agent
├── graph_state.py                   ✅ State definition
├── utils.py                         ✅ Shared utilities
├── requirements.txt                 ✅ Dependencies
└── review_agent.py                  ⏳ Future enhancement (Task 10)
```

### Delete (Legacy Monolith)
```
backend/calledit-backend/handlers/strands_make_call/
├── strands_make_call.py            ❌ DELETE - Original monolith
└── strands_make_call_stream.py     ❌ DELETE - Monolith with streaming
```

## Implementation Steps

1. **Verify dependencies** - Search for imports
2. **Delete legacy files** - Remove monolith code
3. **Run tests** - Verify no regressions
4. **Update docs** - Document cleanup
5. **Commit** - Clean commit message

Ready to proceed?
