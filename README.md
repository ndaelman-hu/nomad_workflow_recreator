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

### Dataset Workflow Reconstruction

The system can automatically reconstruct complete computational workflows from NOMAD public datasets:

```python
from src.workflow_orchestrator import WorkflowOrchestrator

orchestrator = WorkflowOrchestrator()
summary = await orchestrator.reconstruct_dataset_workflow("dataset_name", "upload_name")
```

### MCP Server Tools

#### NOMAD Operations
- `nomad_search_entries` - Search materials by formula, elements, properties
- `nomad_get_dataset_entries` - Extract all entries from a dataset
- `nomad_get_entry_files` - Analyze file structures (no raw content)
- `nomad_get_workflow_metadata` - Extract workflow and calculation metadata
- `nomad_analyze_dataset_structure` - Overview of dataset composition

#### Graph Operations  
- `memgraph_create_dataset_graph` - Build complete workflow graph from dataset
- `memgraph_add_workflow_relationships` - Add semantic relationships
- `memgraph_analyze_workflow_patterns` - Analyze workflow dependencies
- `memgraph_trace_workflow` - Trace complete workflows from any entry
- `memgraph_find_workflow_entry_types` - Find specific calculation types

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