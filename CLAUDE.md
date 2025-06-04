# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

The nomad_workflow_recreator provides MCP (Model Context Protocol) servers for accessing NOMAD materials science database and Memgraph graph database. This enables AI assistants to query materials data and manage workflow relationships through graph operations.

## Repository Structure

- `src/nomad_server.py` - MCP server for NOMAD API integration
- `src/memgraph_server.py` - MCP server for Memgraph database operations
- `requirements.txt` - Python dependencies
- `pyproject.toml` - Project configuration
- `.env.example` - Environment variables template

## Development Setup

### Installation
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Environment Configuration
Copy `.env.example` to `.env` and configure:
- `NOMAD_TOKEN` - OAuth token from NOMAD-lab.eu
- `MEMGRAPH_HOST/PORT` - Memgraph database connection details

### Running MCP Servers
```bash
# Activate virtual environment first
source .venv/bin/activate

# NOMAD MCP server
python src/nomad_server.py

# Memgraph MCP server  
python src/memgraph_server.py

# Claude-driven workflow orchestrator
python src/claude_orchestrator.py
```

## Usage

### Automated Claude Code Analysis (Recommended)

#### Interactive Mode (Customizable)
```bash
# Interactive setup with customization options
./run_analysis.sh
```

#### Automatic Mode (Default Settings)
```bash
# Non-interactive mode with defaults
./run_analysis.sh --auto
```

This will:
1. Check prerequisites (Docker, Claude Code CLI, virtual env)
2. Load NOMAD dataset into Memgraph  
3. **Get user instructions** (interactive mode only):
   - Dataset selection (default or custom)
   - Analysis focus (periodic trends, clusters, electronic structure, etc.)
   - Custom instructions (specific requirements)
4. Start MCP servers
5. Launch Claude Code with customized materials science analysis prompt
6. Claude automatically creates intelligent workflow relationships

#### User Instructions Examples
- `"Focus only on transition metals and create PERIODIC_TREND relationships"`
- `"Analyze cluster size scaling for carbon, silicon, and nitrogen compounds"`
- `"Create relationships with confidence > 0.85 only"`
- `"Compare computational parameters across the 8 calculations per formula"`
- `"Focus on electronic structure relationships for d-block elements"`

### Manual Analysis Options

#### Quick Queries
```bash
source .venv/bin/activate
python quick_queries.py formulas
python quick_queries.py relationships
python quick_queries.py periodic_trends
```

#### Interactive Analysis
```bash
source .venv/bin/activate
python interactive_analysis.py
```

#### Direct MCP Usage
Use Claude Code manually with the Memgraph MCP tools:
- `memgraph_query` - Execute custom Cypher queries
- `memgraph_find_nodes` - Find specific entries
- `memgraph_create_relationship` - Create workflow relationships

## Prerequisites for Automated Analysis

- **Docker**: For Memgraph database
- **Claude Code CLI**: From https://github.com/anthropics/claude-code
- **Python 3.8+**: With virtual environment support

## Attribution and Citations

### After Analysis
```bash
# Generate proper attribution files
python create_metadata.py
```
This creates:
- `analysis_attribution.json` - Complete metadata
- `citations.bib` - BibTeX citations  
- `ANALYSIS_README.md` - Summary with citations

### Required Citations
When publishing results, cite:
1. **NOMAD Database**: Draxl & Scheffler, J. Phys. Mater. 2, 036001 (2019)
2. **Claude Code**: Anthropic AI system for analysis
3. **Your analysis**: Custom citation with your details

See `CITATIONS.md` for complete citation information.

## Architecture

### NOMAD Server
Provides tools for:
- Searching materials science entries by formula, elements, properties
- Retrieving detailed archive data for specific entries
- Authentication management with NOMAD API

### Memgraph Server
Provides tools for:
- Executing Cypher queries
- Creating nodes and relationships
- Finding shortest paths between entities
- Schema introspection

### Workflow Orchestrator
`src/workflow_orchestrator.py` - Original orchestrator with hardcoded relationship rules
`src/claude_orchestrator.py` - **Claude-driven orchestrator** that delegates intelligence to AI:
- Extracts datasets from NOMAD with minimal processing
- Provides MCP tools for Claude to explore and analyze data
- Claude applies materials science knowledge to create relationships
- No hardcoded rules - pure AI reasoning for workflow reconstruction

### Integration Pattern
The system reconstructs workflows through:
1. **Dataset Analysis**: Extract all entries from NOMAD public datasets
2. **Metadata Extraction**: Get workflow metadata and file structures (no raw content)
3. **Relationship Inference**: Analyze entry types, file patterns, and formulas to infer workflow dependencies
4. **Graph Construction**: Build semantic graph with entries as nodes and workflow relationships as edges
5. **Workflow Recreation**: Trace complete computational workflows through graph traversal

### Key Workflow Relationship Types
- `PROVIDES_STRUCTURE`: Geometry optimization → Electronic structure calculation
- `PROVIDES_ELECTRONIC_STRUCTURE`: SCF → DOS/Band structure calculations  
- `PROVIDES_INPUT_DATA`: Output files → Input for next calculation
- `WORKFLOW_STEP`: Sequential steps in same workflow
- `SAME_MATERIAL`: Same formula across different workflows