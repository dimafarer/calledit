# CalledIt Documentation

This directory contains all documentation for the CalledIt project, organized by status and purpose.

## 📁 Directory Structure

### `/current/` - Active Documentation
**Status**: ✅ Up-to-date with v1.5.1

- **`API.md`** - REST and WebSocket API documentation
- **`TRD.md`** - Technical Requirements Document
- **`TESTING.md`** - Testing strategy and coverage
- **`infra.svg`** - Current system architecture diagram
- **`VPSS_COMPLETE.md`** - Verifiable Prediction Structuring System guide (ACTIVE FEATURE)
- **`streaming_implementation_guide.md`** - WebSocket streaming implementation (CORE ARCHITECTURE)
- **`SECURITY_CLEANUP.md`** - Security practices and cleanup checklist
- **`VERIFICATION_SYSTEM.md`** - Automated verification system operational guide

### `/implementation-plans/` - Development Guides
**Status**: 🚧 Mixed (active and completed plans)

#### `/v1.0-verifiability/` - Verifiability System (COMPLETED)
- **Git Commits**: `de35420` - `4153409` (Jan 2025)
- **Key Commits**: Verifiability categories implementation → DynamoDB integration → automated testing
- **`verifiability_integration_plan.md`** - 5-category classification system
- **`implementation_steps.md`** - Step-by-step implementation guide

#### `/v1.2-verification/` - Automated Verification (COMPLETED)  
- **Git Commits**: `fb31057` - `507fe0f` (Jan 2025)
- **Key Commits**: Phase 1 verification → EventBridge integration → "Crying" notifications
- **`VERIFICATION_SYSTEM.md`** - EventBridge + Strands verification agent

#### `/v1.5-vpss/` - Verifiable Prediction Structuring System (COMPLETED)
- **Git Commits**: `29929da` - `3fb77b8` (Jan 2025)
- **Key Commits**: Frontend plan → Backend fixes → Complete documentation
- **`VPSS_FRONTEND_PLAN.md`** - Frontend implementation plan
- **`STRANDS_REVIEW_FEATURE.md`** - Review agent specification
- **`BACKEND_MULTIPLE_FIELD_FIX.md`** - Multiple field update solution

#### `/testing-improvements/` - Testing Enhancement (ACTIVE)
- **Git Commits**: `c1846d1` - `70fd81f` (Aug 2025)
- **`TESTING_IMPROVEMENTS.md`** - Current testing improvement plan
- **`TESTING_PHASE_PLAN.md`** - Phased testing strategy
- **`TESTING_REVIEW.md`** - Test suite analysis

### `/historical/` - Completed/Deprecated Documentation
**Status**: 📚 Reference only

- **`PHASE_3_SUMMARY.md`** - Phase 3 completion report (milestone documentation)

#### `/deprecated/`
- *(Currently empty - truly deprecated docs go here)*

#### `/q-dev-chats/`
- **`q-dev-chat-2025-06-27.md`** - Development conversation logs
- **`q-dev-chat-2025-06-27-2.md`** - Additional dev discussions

#### `/old-readme/`
- Previous README versions for reference

### `/archive/` - Rarely Accessed Historical Docs
**Status**: 🗄️ Archive

- **`UI_IMPROVEMENTS.md`** - UI enhancement plans (superseded)

## 🔄 Documentation Lifecycle

### Active Documents (current/)
- **Updated**: With each release
- **Reviewed**: Before major version releases
- **Status**: Always reflects current codebase

### Implementation Plans (implementation-plans/)
- **Created**: During feature planning
- **Updated**: During development
- **Moved to historical/**: When feature is complete

### Historical Documents (historical/)
- **Purpose**: Reference and development history
- **Status**: Frozen at completion
- **Access**: Read-only for historical context

## 📋 Maintenance Guidelines

### When to Update Current Docs
- ✅ API changes or new endpoints
- ✅ Architecture modifications
- ✅ New testing strategies
- ✅ Version releases

### When to Move Implementation Plans
- ✅ Feature development complete
- ✅ All related git commits merged
- ✅ Documentation reflects final implementation

### When to Archive Documents
- ✅ Plans superseded by newer approaches
- ✅ Documents no longer relevant
- ✅ Historical reference only

## 🎯 Quick Navigation

### For Developers
- **API Reference**: `current/API.md`
- **System Architecture**: `current/infra.svg`
- **Testing Guide**: `current/TESTING.md`

### For Project Managers
- **Requirements**: `current/TRD.md`
- **Implementation History**: `implementation-plans/`
- **Completion Reports**: `historical/deprecated/`

### For New Contributors
1. Start with `current/TRD.md` for system overview
2. Review `current/API.md` for integration details
3. Check `implementation-plans/testing-improvements/` for active work

## 📊 Documentation Status

| Document | Version | Last Updated | Status |
|----------|---------|--------------|--------|
| API.md | v1.5.1 | 2025-08-28 | ✅ Current |
| TRD.md | v1.5.1 | 2025-08-28 | ✅ Current |
| TESTING.md | v1.5.1 | 2025-08-23 | ✅ Current |
| Testing Improvements | Phase 1 | 2025-08-23 | 🚧 Active |

---

**Last Updated**: August 28, 2025  
**Maintained By**: Development Team  
**Review Cycle**: Each major release