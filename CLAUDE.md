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
pip install -r requirements.txt
```

### Environment Configuration
Copy `.env.example` to `.env` and configure:
- `NOMAD_TOKEN` - OAuth token from NOMAD-lab.eu
- `MEMGRAPH_HOST/PORT` - Memgraph database connection details

### Running MCP Servers
```bash
# NOMAD MCP server
python src/nomad_server.py

# Memgraph MCP server  
python src/memgraph_server.py
```

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
`src/workflow_orchestrator.py` - Coordinates complete dataset reconstruction:
- Extracts entire datasets from NOMAD
- Analyzes file structures and workflow metadata
- Infers semantic relationships between calculations
- Builds comprehensive workflow graphs in Memgraph

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