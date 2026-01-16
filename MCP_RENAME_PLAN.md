# MCP → Prediction Refinement System Rename Plan

**Date**: January 16, 2026  
**Status**: Ready to Execute  
**Verified**: ✅ Local dev working, ✅ AWS deployment working

---

## 🎯 Objective

Rename "MCP Sampling" to "Verifiable Prediction Structuring System" (VPSS) throughout the codebase to avoid confusion with the actual Model Context Protocol (MCP) which is used elsewhere in the project for tool gap detection.

The new name accurately reflects the feature's purpose: transforming natural language predictions into structured JSON format with all necessary fields for automated verification.

---

## 📋 Terminology Changes

| Old Term | New Term |
|----------|----------|
| MCP Sampling | Verifiable Prediction Structuring System (VPSS) |
| MCP Sampling pattern | VPSS pattern / Prediction Structuring pattern |
| MCP Sampling workflow | VPSS workflow / Prediction Structuring workflow |
| MCP Sampling feature | VPSS feature / Prediction Structuring feature |

**Note**: Keep "MCP" when referring to actual Model Context Protocol tools (mcp-weather, mcp-finance, etc.)

---

## 📁 Files to Update (Organized by Priority)

### **Phase 1: Documentation** (High Priority - User Facing)

#### Main Documentation
- [ ] `README.md` - Multiple references in features list and status
- [ ] `docs/README.md` - Documentation index references
- [ ] `docs/current/MCP_SAMPLING_COMPLETE.md` - Rename file and update content
- [ ] `CHANGELOG.md` - Update version history entries

#### Implementation Plans
- [ ] `docs/implementation-plans/v1.5-mcp-sampling/` - Rename folder to `v1.5-vpss/`
- [ ] `docs/implementation-plans/v1.5-mcp-sampling/MCP_SAMPLING_FRONTEND_PLAN.md` - Rename to `VPSS_FRONTEND_PLAN.md` and update
- [ ] `docs/implementation-plans/v1.5-mcp-sampling/STRANDS_REVIEW_FEATURE.md` - Update content
- [ ] `docs/implementation-plans/v1.5-mcp-sampling/BACKEND_MULTIPLE_FIELD_FIX.md` - Update content

#### Other Documentation
- [ ] `docs/historical/PHASE_3_SUMMARY.md` - Update references
- [ ] `docs/current/DEPLOYMENT_MANAGEMENT.md` - Update references

---

### **Phase 2: Backend Code Comments** (Medium Priority - Internal)

#### Lambda Handlers
- [ ] `backend/calledit-backend/handlers/strands_make_call/review_agent.py`
  - Class docstring: Line 14-16
  - Method docstrings: Lines 50-52, 117-119
  
- [ ] `backend/calledit-backend/handlers/strands_make_call/strands_make_call_stream.py`
  - Function docstrings: Lines 47-49, 135-137, 179-181, 481-483, 497-499

#### Tests
- [ ] `backend/calledit-backend/tests/strands_make_call/test_review_agent.py`
  - Class docstring: Line 14-16

---

### **Phase 3: Frontend Code Comments** (Low Priority - Internal)

- [ ] `frontend/src/utils/autoTest.js`
  - File header comment: Line 1
  - Console log: Line 5

---

### **Phase 4: Testing Files** (Low Priority - Deprecated/Archive)

#### Active Tests
- [ ] `testing/README.md` - Update test descriptions
- [ ] `testing/active/test_improvement_updated.py` - Update comments if any

#### Deprecated Tests (Optional - these are archived)
- [ ] `testing/deprecated/old_tests/test_review_feature.py`
- [ ] `testing/deprecated/old_tests/test_review_detailed.py`
- [ ] `testing/deprecated/complex_e2e/test_mcp_sampling_e2e.py`
- [ ] `testing/deprecated/complex_e2e/test_mcp_sampling_integration.py`

---

## 🔄 Execution Strategy

### Option A: Complete Rename (Recommended)
Update everything in one go for consistency.

**Pros:**
- Complete consistency across codebase
- No confusion in future
- Clean git history with single "rename" commit

**Cons:**
- More files to touch
- Slightly longer to complete

### Option B: Phased Approach
Do Phase 1 (docs) now, defer code comments to later.

**Pros:**
- Faster initial completion
- User-facing content fixed immediately

**Cons:**
- Inconsistency between docs and code
- Need to remember to finish later

---

## 🚀 Recommended Execution Order

### Step 1: Rename Folder Structure
```bash
cd docs/implementation-plans
mv v1.5-mcp-sampling v1.5-vpss
```

### Step 2: Rename Key Documentation Files
```bash
cd docs/current
mv MCP_SAMPLING_COMPLETE.md VPSS_COMPLETE.md

cd ../implementation-plans/v1.5-vpss
mv MCP_SAMPLING_FRONTEND_PLAN.md VPSS_FRONTEND_PLAN.md
```

### Step 3: Update File Contents
Use find/replace in each file:
- Find: `MCP Sampling`
- Replace: `Verifiable Prediction Structuring System` (or `VPSS` where appropriate)
- Find: `MCP sampling`
- Replace: `Prediction Structuring` (or `VPSS` where appropriate)

### Step 4: Update Backend Code Comments
Update docstrings in:
- `review_agent.py`
- `strands_make_call_stream.py`
- `test_review_agent.py`

### Step 5: Update Frontend Code Comments
Update comments in:
- `autoTest.js`

### Step 6: Update Testing Documentation
Update references in:
- `testing/README.md`

### Step 7: Verify & Test
```bash
# Search for any remaining "MCP Sampling" references
grep -r "MCP Sampling" --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=venv

# Run tests to ensure nothing broke
cd frontend
npm run test

cd ../backend/calledit-backend
pytest
```

### Step 8: Commit Changes
```bash
git add .
git commit -m "Rename MCP Sampling to Verifiable Prediction Structuring System (VPSS)

- Clarify terminology to avoid confusion with Model Context Protocol
- MCP Sampling was a misnomer for the prediction structuring workflow
- VPSS accurately describes transformation of predictions into verifiable JSON
- Actual MCP (Model Context Protocol) is used for tool gap detection
- Updated all documentation, code comments, and test files"

git push origin main
```

---

## ⚠️ Important Notes

### DO NOT Change:
- ✅ `MCPToolSuggestions` class name (this IS about Model Context Protocol)
- ✅ `suggested_mcp_tool` field names (these ARE MCP tools)
- ✅ References to `mcp-weather`, `mcp-finance`, etc. (actual MCP tools)
- ✅ Any API endpoint names or WebSocket actions (would break compatibility)

### DO Change:
- ✅ "MCP Sampling" in documentation → "Verifiable Prediction Structuring System" or "VPSS"
- ✅ "MCP Sampling" in code comments → "Prediction Structuring" or "VPSS"
- ✅ File names with "MCP_SAMPLING" → "VPSS"
- ✅ Folder names with "mcp-sampling" → "vpss"

---

## 📊 Impact Assessment

### Breaking Changes: **NONE** ✅
- No API changes
- No database schema changes
- No configuration changes
- No user-facing UI text changes

### Risk Level: **LOW** ✅
- Only documentation and comments affected
- No functional code changes
- Easy to revert if needed

### Testing Required: **MINIMAL** ✅
- Verify docs render correctly
- Run existing test suite
- No new tests needed

---

## ✅ Success Criteria

- [ ] All documentation uses "Verifiable Prediction Structuring System" or "VPSS"
- [ ] No references to "MCP Sampling" remain (except in git history)
- [ ] All tests still pass
- [ ] Application still runs locally
- [ ] Can still deploy to AWS successfully
- [ ] README clearly explains the VPSS feature

---

**Ready to Execute**: All prerequisites met, plan reviewed, ready to proceed.
