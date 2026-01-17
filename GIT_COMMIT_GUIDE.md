# Git Commit Guide - Handler Cleanup

## Step 1: Check Status

```bash
cd /home/wsluser/projects/calledit
git status
```

Expected changes:
- Deleted: `backend/calledit-backend/handlers/hello_world/`
- Deleted: `backend/calledit-backend/handlers/make_call/`
- Deleted: `backend/calledit-backend/handlers/prompt_bedrock/`
- Deleted: `backend/calledit-backend/handlers/prompt_agent/`
- Deleted: `backend/calledit-backend/handlers/shared/`
- Deleted: `backend/calledit-backend/tests/hello_world/`
- Deleted: `backend/calledit-backend/tests/make_call/`
- Modified: `backend/calledit-backend/template.yaml`
- New: Documentation files

## Step 2: Stage Changes

```bash
# Stage deleted handlers
git rm -r backend/calledit-backend/handlers/hello_world/
git rm -r backend/calledit-backend/handlers/make_call/
git rm -r backend/calledit-backend/handlers/prompt_bedrock/
git rm -r backend/calledit-backend/handlers/prompt_agent/
git rm -r backend/calledit-backend/handlers/shared/

# Stage deleted tests
git rm -r backend/calledit-backend/tests/hello_world/
git rm -r backend/calledit-backend/tests/make_call/

# Stage modified template
git add backend/calledit-backend/template.yaml

# Stage documentation
git add HANDLER_CLEANUP_COMPLETE.md
git add HANDLER_CLEANUP_ANALYSIS.md
git add TEMPLATE_CLEANUP_GUIDE.md
git add cleanup_unused_handlers.sh
git add COMMIT_MESSAGE.txt
git add GIT_COMMIT_GUIDE.md
```

## Step 3: Commit

```bash
# Use the prepared commit message
git commit -F COMMIT_MESSAGE.txt
```

Or commit with inline message:

```bash
git commit -m "chore: Remove unused Lambda handlers before Strands refactoring

Remove 5 deprecated Lambda handlers and their tests to clean up codebase
before implementing Strands best practices improvements.

Deleted Handlers:
- hello_world/ - Demo function
- make_call/ - Old non-streaming handler
- prompt_bedrock/ - Direct Bedrock (superseded)
- prompt_agent/ - Early agent (superseded)
- shared/ - Unused utilities

Benefits:
- 38% reduction in Lambda functions (13 → 8)
- Cleaner codebase for Strands refactoring
- Faster deployments

Verification:
- ✅ Deployment successful
- ✅ No behavioral changes detected"
```

## Step 4: Push

```bash
# Push to origin (EC2 server)
git push origin main

# Push to github (public)
git push github main
```

## Step 5: Clean Up Temporary Files (Optional)

After committing, you can optionally remove the temporary documentation files:

```bash
# Keep these for reference:
# - HANDLER_CLEANUP_COMPLETE.md
# - STRANDS_BEST_PRACTICES_REVIEW.md

# Remove these temporary files:
rm COMMIT_MESSAGE.txt
rm GIT_COMMIT_GUIDE.md
rm HANDLER_CLEANUP_ANALYSIS.md
rm TEMPLATE_CLEANUP_GUIDE.md
rm cleanup_unused_handlers.sh
```

Or keep them all for historical reference - they're useful documentation!

## Verification

After pushing, verify:

```bash
# Check commit history
git log --oneline -5

# Verify remote has the changes
git log origin/main --oneline -5
```

---

**Ready to commit!** 🚀
