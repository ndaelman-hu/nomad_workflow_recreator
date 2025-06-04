#!/bin/bash
"""
NOMAD Workflow Analysis Launcher

One-command setup to launch Claude Code analysis of NOMAD materials data.
"""

set -e  # Exit on any error

echo "🤖 NOMAD Workflow Analysis with Claude Code"
echo "=============================================="

# Check if we're in the right directory
if [ ! -f "setup_claude_analysis.py" ]; then
    echo "❌ Please run from the nomad_workflow_recreator directory"
    exit 1
fi

# Check prerequisites first
echo "🔍 Checking prerequisites..."
python setup_claude_analysis.py --check

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Prerequisites check failed. Please fix the issues above."
    echo ""
    echo "Common fixes:"
    echo "  - Install virtual environment: python -m venv .venv"
    echo "  - Start Memgraph: docker-compose up -d"
    echo "  - Install Claude Code: https://github.com/anthropics/claude-code"
    exit 1
fi

echo ""
echo "🚀 Starting Claude Code analysis..."
echo ""
echo "What will happen:"
echo "  1. ✅ Load NOMAD dataset into Memgraph"
echo "  2. ✅ Start Memgraph MCP server"
echo "  3. 📝 Customize analysis (dataset, focus, instructions)"
echo "  4. ✅ Launch Claude Code with materials science prompt"
echo "  5. 🤖 Claude analyzes dataset and creates workflow relationships"
echo ""

# Check for auto mode
if [ "$1" = "--auto" ]; then
    echo "🤖 Running in automatic mode with defaults..."
    python setup_claude_analysis.py --auto
else
    read -p "Continue with interactive setup? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Cancelled by user"
        exit 1
    fi
    
    # Run the full interactive setup
    python setup_claude_analysis.py
fi

echo ""
echo "🎉 Analysis complete! Check Memgraph for the intelligent workflow relationships."
echo "📊 You can explore results with: python interactive_analysis.py"