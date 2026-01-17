#!/bin/bash
# Handler Cleanup Script
# Removes unused Lambda handlers before Strands refactoring

set -e  # Exit on error

echo "🧹 CalledIt Handler Cleanup"
echo "============================"
echo ""

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  WARNING: Virtual environment is not activated!"
    echo ""
    echo "Please activate the virtual environment first:"
    echo "  source /home/wsluser/projects/calledit/venv/bin/activate"
    echo ""
    echo "Then run this script again."
    exit 1
fi

echo "✅ Virtual environment active: $VIRTUAL_ENV"
echo ""

# Confirm with user
echo "This script will delete the following unused handlers:"
echo "  - handlers/hello_world/"
echo "  - handlers/make_call/"
echo "  - handlers/prompt_bedrock/"
echo "  - handlers/prompt_agent/"
echo "  - handlers/shared/"
echo "  - tests/hello_world/"
echo "  - tests/make_call/"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Cleanup cancelled"
    exit 1
fi

# Navigate to backend directory
cd /home/wsluser/projects/calledit/backend/calledit-backend

echo ""
echo "📁 Deleting unused handler directories..."

# Delete handler directories
rm -rf handlers/hello_world/
echo "  ✅ Deleted handlers/hello_world/"

rm -rf handlers/make_call/
echo "  ✅ Deleted handlers/make_call/"

rm -rf handlers/prompt_bedrock/
echo "  ✅ Deleted handlers/prompt_bedrock/"

rm -rf handlers/prompt_agent/
echo "  ✅ Deleted handlers/prompt_agent/"

rm -rf handlers/shared/
echo "  ✅ Deleted handlers/shared/"

echo ""
echo "🧪 Deleting unused test directories..."

# Delete test directories
rm -rf tests/hello_world/
echo "  ✅ Deleted tests/hello_world/"

rm -rf tests/make_call/
echo "  ✅ Deleted tests/make_call/"

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "📋 Next steps:"
echo "  1. Review template.yaml and remove unused function definitions"
echo "  2. Run: sam validate"
echo "  3. Run: sam build"
echo "  4. Test deployment"
echo ""
echo "💡 Tip: Commit these changes before proceeding with Strands refactoring"
