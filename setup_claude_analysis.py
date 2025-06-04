#!/usr/bin/env python3
"""
Setup Claude Code Analysis Session

Prepares the environment and launches Claude Code with proper MCP configuration
for NOMAD workflow analysis.
"""

import os
import sys
import json
import subprocess
import asyncio
from pathlib import Path

class ClaudeAnalysisSetup:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.venv_path = self.project_root / ".venv"
        self.claude_config = self.project_root / "claude_config.json"
        self.analysis_prompt = self.project_root / "analysis_prompt.md"
    
    def check_prerequisites(self):
        """Check if all prerequisites are met"""
        print("🔍 Checking prerequisites...")
        
        # Check virtual environment
        if not self.venv_path.exists():
            print("❌ Virtual environment not found. Run: python -m venv .venv")
            return False
        
        # Check if Memgraph is running
        try:
            result = subprocess.run(["docker", "ps"], capture_output=True, text=True)
            if "memgraph" not in result.stdout:
                print("❌ Memgraph not running. Run: docker-compose up -d")
                return False
        except FileNotFoundError:
            print("❌ Docker not found. Please install Docker.")
            return False
        
        # Check if Claude Code is available
        try:
            result = subprocess.run(["claude", "--version"], capture_output=True, text=True)
            if result.returncode != 0:
                print("❌ Claude Code not found. Please install Claude Code CLI.")
                return False
        except FileNotFoundError:
            print("❌ Claude Code CLI not found. Please install from: https://github.com/anthropics/claude-code")
            return False
        
        print("✅ All prerequisites met!")
        return True
    
    def prepare_environment(self):
        """Prepare the analysis environment"""
        print("🔧 Preparing analysis environment...")
        
        # Activate virtual environment and install dependencies
        pip_path = self.venv_path / "bin" / "pip"
        subprocess.run([str(pip_path), "install", "-r", "requirements.txt"], check=True)
        
        # Load dataset if not already loaded
        python_path = self.venv_path / "bin" / "python"
        print("📊 Loading dataset into Memgraph...")
        subprocess.run([str(python_path), "src/claude_orchestrator.py"], check=True)
        
        print("✅ Environment prepared!")
    
    def create_claude_session_config(self, user_instructions=None, dataset_id=None, focus_area=None):
        """Create Claude Code session configuration with optional user instructions"""
        print("📝 Creating Claude Code configuration...")
        
        # Read the base analysis prompt
        with open(self.analysis_prompt, 'r') as f:
            base_prompt = f.read()
        
        # Customize prompt based on user input
        prompt_content = base_prompt
        
        if dataset_id and dataset_id != "YDXZgPooRb-31Niq48ODPA":
            prompt_content = prompt_content.replace(
                'dataset "YDXZgPooRb-31Niq48ODPA"',
                f'dataset "{dataset_id}"'
            )
        
        if focus_area:
            focus_instructions = f"""
## USER FOCUS AREA: {focus_area}

Pay special attention to: {focus_area}
Prioritize analysis and relationships related to this area.
"""
            prompt_content = focus_instructions + prompt_content
        
        if user_instructions:
            custom_instructions = f"""
## USER INSTRUCTIONS

{user_instructions}

Follow these specific instructions while conducting the materials science analysis.

---

"""
            prompt_content = custom_instructions + prompt_content
        
        # Add attribution notice
        attribution_notice = """
## ATTRIBUTION AND CITATIONS

This analysis uses:
- NOMAD Materials Science Database (nomad-lab.eu) - Cite: Draxl & Scheffler, J. Phys. Mater. 2, 036001 (2019)
- Claude Code AI Assistant (anthropic.com) - AI-driven workflow analysis
- Memgraph Graph Database (memgraph.com) - Graph storage and querying

Please include appropriate citations when publishing results from this analysis.
See CITATIONS.md for detailed citation information.

---

"""
        prompt_content = attribution_notice + prompt_content
        
        # Create session configuration
        session_config = {
            "mcp_servers": {
                "memgraph": {
                    "command": str(self.venv_path / "bin" / "python"),
                    "args": ["src/memgraph_server.py"],
                    "cwd": str(self.project_root),
                    "env": {
                        "MEMGRAPH_HOST": "localhost",
                        "MEMGRAPH_PORT": "7687",
                        "MEMGRAPH_USERNAME": "",
                        "MEMGRAPH_PASSWORD": ""
                    }
                }
            },
            "initial_prompt": prompt_content
        }
        
        # Write configuration
        config_file = self.project_root / "claude_session.json"
        with open(config_file, 'w') as f:
            json.dump(session_config, f, indent=2)
        
        print("✅ Claude Code configuration created!")
        return config_file
    
    def launch_claude_analysis(self, user_instructions=None, dataset_id=None, focus_area=None):
        """Launch Claude Code with the analysis configuration"""
        print("🚀 Launching Claude Code analysis session...")
        
        config_file = self.create_claude_session_config(user_instructions, dataset_id, focus_area)
        
        # Launch Claude Code with the configuration
        cmd = [
            "claude",
            "--config", str(config_file),
            "--prompt-file", str(self.analysis_prompt)
        ]
        
        print(f"💬 Starting Claude Code with command:")
        print(f"   {' '.join(cmd)}")
        print(f"\n🎯 Claude will now analyze the NOMAD dataset using materials science knowledge!")
        
        dataset_display = dataset_id or "YDXZgPooRb-31Niq48ODPA"
        print(f"📊 Dataset: {dataset_display}")
        
        if focus_area:
            print(f"🎯 Focus Area: {focus_area}")
        if user_instructions:
            print(f"📝 Custom Instructions: {user_instructions[:100]}{'...' if len(user_instructions) > 100 else ''}")
        
        print(f"🔬 Base Focus: Create intelligent workflow relationships based on periodic trends and cluster science")
        
        # Execute Claude Code
        subprocess.run(cmd)
    
    def get_user_input(self):
        """Get user instructions interactively"""
        print("\n📝 CUSTOMIZATION OPTIONS")
        print("=" * 40)
        
        # Dataset selection
        print("Dataset options:")
        print("  1. YDXZgPooRb-31Niq48ODPA (default - Numerical Errors FHI-aims)")
        print("  2. Custom dataset ID")
        
        dataset_choice = input("Select dataset (1-2, or Enter for default): ").strip()
        dataset_id = None
        if dataset_choice == "2":
            dataset_id = input("Enter dataset ID: ").strip()
        
        # Focus area
        print("\nAnalysis focus options:")
        print("  1. Periodic trends (default)")
        print("  2. Cluster size scaling")
        print("  3. Electronic structure")
        print("  4. Parameter studies")
        print("  5. Custom focus")
        
        focus_choice = input("Select focus (1-5, or Enter for default): ").strip()
        focus_area = None
        focus_map = {
            "2": "cluster size scaling and size-dependent properties",
            "3": "electronic structure relationships and DFT method validation",
            "4": "parameter studies and computational convergence",
            "5": None  # Custom
        }
        
        if focus_choice in focus_map:
            focus_area = focus_map[focus_choice]
            if focus_choice == "5":
                focus_area = input("Enter custom focus area: ").strip()
        
        # Custom instructions
        print("\nCustom instructions (optional):")
        print("Examples:")
        print("  - Focus only on transition metals")
        print("  - Create relationships with confidence > 0.8")
        print("  - Analyze only the first 100 entries")
        print("  - Compare with experimental data patterns")
        
        user_instructions = input("Enter custom instructions (or Enter to skip): ").strip()
        if not user_instructions:
            user_instructions = None
        
        return user_instructions, dataset_id, focus_area
    
    def run_full_setup(self, interactive=True):
        """Run the complete setup and analysis"""
        print("🤖 NOMAD Workflow Analysis with Claude Code")
        print("=" * 60)
        
        if not self.check_prerequisites():
            print("\n❌ Prerequisites not met. Please fix the issues above.")
            return False
        
        # Get user customizations
        user_instructions = None
        dataset_id = None
        focus_area = None
        
        if interactive:
            user_instructions, dataset_id, focus_area = self.get_user_input()
        
        try:
            self.prepare_environment()
            self.launch_claude_analysis(user_instructions, dataset_id, focus_area)
            return True
        except Exception as e:
            print(f"\n❌ Error during setup: {e}")
            return False

def main():
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        # Just check prerequisites
        setup = ClaudeAnalysisSetup()
        setup.check_prerequisites()
        return
    
    # Check for non-interactive mode
    non_interactive = len(sys.argv) > 1 and sys.argv[1] == "--auto"
    
    # Run setup
    setup = ClaudeAnalysisSetup()
    success = setup.run_full_setup(interactive=not non_interactive)
    
    if success:
        print("\n✅ Claude Code analysis session started!")
        print("🎯 Claude will now create intelligent workflow relationships!")
    else:
        print("\n❌ Setup failed. Check the errors above.")

if __name__ == "__main__":
    main()