# Documentation Audit & Update Plan

## Date: 2025-01-19

## Overview

After completing the 3-agent graph refactor and monolith cleanup, we need to audit and update all documentation to reflect the current architecture.

## Current State Analysis

### README.md Issues

**MAJOR OUTDATED SECTIONS:**

1. **Handler Structure (Lines ~50-80)**
   - ❌ References `strands_make_call_stream.py` as main handler
   - ❌ Lists components: review_agent.py, parser_agent.py, utils.py, error_handling.py, graph_state.py
   - ✅ SHOULD reference `strands_make_call_graph.py` as main handler
   - ✅ SHOULD list: prediction_graph.py, parser_agent.py, categorizer_agent.py, verification_builder_agent.py, graph_state.py, utils.py

2. **Lambda Functions Section (Lines ~300-400)**
   - ❌ References `strands_make_call_stream.py` as main handler
   - ❌ Lists old components (error_handling.py, review_agent.py)
   - ✅ SHOULD describe 3-agent graph architecture
   - ✅ SHOULD list current components

3. **Data Flow Section (Lines ~450-500)**
   - ❌ Describes single "Strands agent"
   - ✅ SHOULD describe 3-agent graph flow: Parser → Categorizer → Verification Builder

4. **Example Code (Lines ~200-250)**
   - ❌ Shows monolith agent output structure
   - ✅ SHOULD show 3-agent graph output structure

### docs/current/ Files to Audit

#### ✅ Already Updated (Recent Work)
1. **STRANDS_GRAPH_FLOW.md** - ✅ Complete rewrite (2025-01-18)
   - Reflects plain Agent pattern
   - Documents 3-agent graph
   - No custom nodes references

#### ❓ Need to Check
2. **APPLICATION_FLOW.md** - Need to verify
   - Check if it references old monolith architecture
   - Verify 3-agent graph flow is documented

3. **API.md** - Need to verify
   - Check WebSocket route documentation
   - Verify handler references

4. **TRD.md** - Need to verify
   - Check technical architecture section
   - Verify agent descriptions

5. **TESTING.md** - Need to verify
   - Check if test structure matches current tests
   - Verify integration test documentation

6. **VERIFICATION_SYSTEM.md** - Probably OK
   - Verification system is separate from prediction processing
   - May not need updates

7. **VPSS_COMPLETE.md** - Probably OK
   - VPSS is future enhancement
   - May reference old architecture

8. **streaming_implementation_guide.md** - Need to check
   - May reference old monolith streaming
   - Should describe 3-agent graph streaming

#### 🗑️ Potentially Archive
9. **DEPLOYMENT_MANAGEMENT.md** - Check relevance
10. **SECURITY_CLEANUP.md** - Probably archive (one-time cleanup doc)

## Update Strategy

### Phase 1: README.md Update (HIGH PRIORITY)
**Goal:** Update main README to reflect 3-agent graph architecture

**Sections to Update:**
1. Repository Structure (lines ~50-80)
   - Update strands_make_call/ handler description
   - List current files: strands_make_call_graph.py, prediction_graph.py, 3 agent files
   - Remove references to error_handling.py

2. Lambda Functions Section (lines ~300-400)
   - Update MakeCallStreamFunction description
   - Describe 3-agent graph architecture
   - List current components

3. Data Flow Section (lines ~450-500)
   - Update to show: Parser → Categorizer → Verification Builder
   - Describe graph orchestration

4. Example Code (lines ~200-250)
   - Update to show 3-agent graph output
   - Include all fields from final_state

**Estimated Time:** 30 minutes

### Phase 2: docs/current/ Audit (MEDIUM PRIORITY)
**Goal:** Verify and update all current documentation

**Process:**
1. Read each file
2. Identify outdated sections
3. Update or mark for archival
4. Create update checklist

**Files to Audit:**
- APPLICATION_FLOW.md
- API.md
- TRD.md
- TESTING.md
- streaming_implementation_guide.md
- VPSS_COMPLETE.md

**Estimated Time:** 1-2 hours

### Phase 3: Archive Old Docs (LOW PRIORITY)
**Goal:** Move outdated documentation to archive

**Candidates:**
- DEPLOYMENT_MANAGEMENT.md (if outdated)
- SECURITY_CLEANUP.md (one-time cleanup)
- Any other docs that are no longer relevant

**Estimated Time:** 15 minutes

## Documentation Standards

### What to Include
- ✅ Current 3-agent graph architecture
- ✅ Plain Agent pattern (no custom nodes)
- ✅ Actual file names and structure
- ✅ Production handler: strands_make_call_graph.py
- ✅ Graph components: prediction_graph.py, 3 agent files
- ✅ Supporting files: graph_state.py, utils.py
- ✅ Future enhancements: review_agent.py (Task 10)

### What to Remove
- ❌ References to strands_make_call.py (deleted)
- ❌ References to strands_make_call_stream.py (deleted)
- ❌ References to error_handling.py (deleted)
- ❌ References to custom_node.py (deleted)
- ❌ Monolith agent architecture
- ❌ Manual state management patterns

### What to Clarify
- ⚠️ review_agent.py is future enhancement (Task 10)
- ⚠️ VPSS is not yet integrated into graph
- ⚠️ Current production: 3-agent graph only

## Success Criteria

### README.md
- [ ] All handler references point to strands_make_call_graph.py
- [ ] 3-agent graph architecture clearly described
- [ ] No references to deleted files
- [ ] Example code shows current output structure
- [ ] Data flow diagram reflects 3-agent graph

### docs/current/
- [ ] All files audited
- [ ] Outdated sections updated or archived
- [ ] 3-agent graph architecture documented
- [ ] No references to deleted files
- [ ] Clear distinction between current and future features

### Overall
- [ ] Documentation matches codebase
- [ ] New developers can understand architecture
- [ ] No confusion about which code is active
- [ ] Future enhancements clearly marked

## Implementation Order

1. **README.md** (30 min) - Highest visibility, most important
2. **APPLICATION_FLOW.md** (20 min) - Core system documentation
3. **API.md** (15 min) - API reference
4. **TRD.md** (15 min) - Technical requirements
5. **streaming_implementation_guide.md** (10 min) - Implementation guide
6. **TESTING.md** (10 min) - Testing documentation
7. **Archive old docs** (15 min) - Cleanup

**Total Estimated Time:** 2 hours

## Next Steps

1. Start with README.md update
2. Test changes by having someone unfamiliar read it
3. Move to docs/current/ audit
4. Archive outdated documentation
5. Commit all changes together

Ready to proceed?
