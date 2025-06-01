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

### Integration Pattern
The servers work together to:
1. Query NOMAD for materials data
2. Store relationships and workflows in Memgraph
3. Enable graph-based workflow recreation and analysis