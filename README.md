# NOMAD Workflow Recreator

MCP (Model Context Protocol) servers for integrating NOMAD materials science database with Memgraph graph database, enabling AI-assisted workflow recreation and analysis.

## Features

- **NOMAD MCP Server**: Query materials science data from NOMAD-lab.eu
- **Memgraph MCP Server**: Manage workflow relationships using graph database
- **Workflow Recreation**: Analyze and recreate computational workflows through graph traversal

## Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Start Memgraph database**:
   ```bash
   docker-compose up -d
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your NOMAD token and database settings
   ```

4. **Run MCP servers**:
   ```bash
   # Terminal 1 - NOMAD server
   python src/nomad_server.py
   
   # Terminal 2 - Memgraph server
   python src/memgraph_server.py
   ```

## Usage

The MCP servers expose tools for:

### NOMAD Operations
- Search materials by formula, elements, or properties
- Retrieve detailed entry archives
- Download raw computational files

### Graph Operations
- Execute Cypher queries
- Create material and workflow nodes
- Establish relationships between calculations
- Find shortest paths in workflow graphs

## Architecture

```
┌─────────────────┐    ┌─────────────────┐
│   NOMAD API     │    │   Memgraph DB   │
│ (Materials Data)│    │ (Workflows)     │
└─────────────────┘    └─────────────────┘
         │                       │
         │                       │
    ┌─────────────────────────────────────┐
    │         MCP Servers                 │
    │  ┌─────────────┐ ┌─────────────┐   │
    │  │NOMAD Server │ │Graph Server │   │
    │  └─────────────┘ └─────────────┘   │
    └─────────────────────────────────────┘
                     │
                     │
            ┌─────────────────┐
            │   AI Assistant  │
            │ (Claude, etc.)  │
            └─────────────────┘
```

## Development

See [CLAUDE.md](CLAUDE.md) for detailed development guidance.