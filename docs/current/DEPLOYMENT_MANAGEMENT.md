# Deployment Management Guide

**CRITICAL:** This project has environment-specific configurations that must be managed carefully to prevent deployment breaks.

## 🚨 Problem Statement

- **Local deployment** has customized `template.yaml` (removed DDB, modified resources)
- **Production deployments** in other accounts need the original template structure
- **Code improvements** need to be shared without breaking deployments

## ✅ Solution: Environment-Specific Template Management

### Current Status
- Local `template.yaml` has been modified for this specific deployment
- Original template structure needed for other AWS accounts
- Code improvements (error handling, MCP sampling) ready to push

## 📋 Git Push/Pull Workflow

### Before Pushing Changes to GitHub

1. **Backup Local Configurations**
```bash
cd /home/wsluser/projects/calledit/backend/calledit-backend
cp template.yaml template.yaml.local
cp samconfig.toml samconfig.toml.local
```

2. **Restore Original Template Structure**
```bash
# Add back DDB table and other removed resources to template.yaml
# Ensure template.yaml matches what other accounts expect
```

3. **Commit and Push Code Changes**
```bash
git add .
git commit -m "Add error handling and MCP sampling improvements"
git push origin main
```

4. **Restore Local Configurations**
```bash
cp template.yaml.local template.yaml
cp samconfig.toml.local samconfig.toml
```

### When Pulling Changes from GitHub

1. **Backup Current Local Configurations**
```bash
cd /home/wsluser/projects/calledit/backend/calledit-backend
cp template.yaml template.yaml.local
cp samconfig.toml samconfig.toml.local
```

2. **Pull Changes**
```bash
git pull origin main
```

3. **Restore Local Configurations**
```bash
cp template.yaml.local template.yaml
cp samconfig.toml.local samconfig.toml
```

## 🔧 File Management

### Files to Keep Local (Never Commit)
- `template.yaml.local` - Your customized template
- `samconfig.toml.local` - Your deployment configuration
- `.env` files with account-specific values

### Files to Commit
- All code improvements in `/handlers/`
- Frontend changes in `/frontend/src/`
- Documentation updates
- Original `template.yaml` structure

## 🛡️ Safety Checklist

### Before Every Git Push:
- [ ] Local configurations backed up
- [ ] `template.yaml` restored to original structure
- [ ] No account-specific values in committed files
- [ ] Code changes tested and working

### After Every Git Pull:
- [ ] Local configurations restored
- [ ] Deployment still works with `sam deploy`
- [ ] No conflicts with local customizations

## 🚀 Quick Commands

### Push Workflow
```bash
# 1. Backup
cp template.yaml template.yaml.local
cp samconfig.toml samconfig.toml.local

# 2. Restore original (manual step - add back DDB)
# Edit template.yaml to match original structure

# 3. Push
git add . && git commit -m "Your changes" && git push

# 4. Restore local
cp template.yaml.local template.yaml
cp samconfig.toml.local samconfig.toml
```

### Pull Workflow
```bash
# 1. Backup
cp template.yaml template.yaml.local
cp samconfig.toml samconfig.toml.local

# 2. Pull
git pull origin main

# 3. Restore local
cp template.yaml.local template.yaml
cp samconfig.toml.local samconfig.toml
```

## 📝 Notes for Future Q Sessions

- **Always check** if `.local` backup files exist before git operations
- **Never commit** `template.yaml.local` or `samconfig.toml.local`
- **Test deployment** after restoring local configurations
- **Document any new** environment-specific changes in this file

## 🔍 Verification Commands

### Check Local Deployment Works
```bash
cd /home/wsluser/projects/calledit/backend/calledit-backend
sam build && sam deploy --no-confirm-changeset
```

### Check Git Status
```bash
git status
# Should NOT show template.yaml.local or samconfig.toml.local as tracked
```

## 🆘 Emergency Recovery

If deployment breaks after git operations:

1. **Restore from backup:**
```bash
cp template.yaml.local template.yaml
cp samconfig.toml.local samconfig.toml
```

2. **Redeploy:**
```bash
sam build && sam deploy --no-confirm-changeset
```

3. **Verify functionality:**
- Test WebSocket connections
- Test MCP sampling
- Test View Calls screen

---

**Last Updated:** 2025-09-04  
**Status:** Active deployment management required
