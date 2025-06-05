# NOMAD Workflow Recreator

Enhanced MCP (Model Context Protocol) servers for integrating NOMAD materials science database with Memgraph graph database, enabling AI-assisted workflow recreation and advanced materials analysis.

## Features

### Enhanced MCP Servers
- **NOMAD MCP Server**: Dataset discovery, initialization, formula analysis, workflow patterns
- **Memgraph MCP Server**: Graph operations, periodic trend analysis, cluster patterns, interactive exploration
- **Logger MCP Server**: Tool usage tracking, suggestion logging, missing tool detection

### Analysis Capabilities
- Extract and analyze entries from NOMAD datasets
- Build semantic workflow graphs automatically
- Identify periodic trends and cluster size relationships
- Perform interactive dataset exploration
- Export graph data in multiple formats

## Quick Start

### Automated Analysis (Recommended)
```bash
# Interactive mode with customization
./run_analysis.sh

# Automatic mode with defaults
./run_analysis.sh --auto
```

### Manual Setup

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

4. **Run enhanced MCP servers**:
   ```bash
   # Terminal 1 - NOMAD server
   python src/nomad_server_enhanced.py
   
   # Terminal 2 - Memgraph server
   python src/memgraph_server_enhanced.py
   
   # Terminal 3 - Logger server (optional but recommended)
   python src/logger_server.py
   ```

5. **Launch Claude Code**:
   ```bash
   claude --config claude_config.json
   ```

## Enhanced MCP Tools

### NOMAD Server Tools
- **Dataset Management**
  - `list_datasets` - List available NOMAD datasets
  - `initialize_dataset_workflow` - Initialize complete workflow analysis
  - `get_dataset_entries` - Extract all entries from a dataset
  - `analyze_dataset_formulas` - Analyze chemical formula patterns
  - `get_dataset_workflow_patterns` - Extract workflow patterns

- **Entry Operations**
  - `get_entry_archive` - Get full archive data for an entry
  - `get_entry_with_files` - Get entry data including file contents
  - `search_entries` - Search with custom filters

### Memgraph Server Tools
- **Analysis Tools**
  - `memgraph_analyze_periodic_trends` - Analyze and create periodic relationships
  - `memgraph_analyze_cluster_patterns` - Find cluster size variations
  - `memgraph_quick_analysis` - Run predefined queries (formulas, relationships, trends)
  - `memgraph_interactive_explore` - Interactive dataset exploration
  - `memgraph_query_graph_export` - Export graph data

- **Dataset Operations**
  - `memgraph_clear_dataset` - Clear existing datasets
  - `memgraph_initialize_indexes` - Create performance indexes
  - `memgraph_get_dataset_stats` - Get detailed statistics

- **Graph Operations**
  - `memgraph_query` - Execute Cypher queries
  - `memgraph_create_node` - Create nodes
  - `memgraph_create_relationship` - Create relationships
  - `memgraph_find_nodes` - Find nodes by criteria
  - `memgraph_shortest_path` - Find paths between nodes

## Usage Examples

### Initialize New Dataset
```
Claude: Please list available NOMAD datasets and initialize the one about carbon clusters.
```

### Analyze Periodic Trends
```
Claude: Analyze periodic trends in the dataset and create PERIODIC_TREND relationships for alkali metals.
```

### Quick Analysis
```
Claude: Run a quick analysis to show all formulas and their occurrence counts.
```

### Interactive Exploration
```
Claude: Show me a dataset summary and then explore the details of C60 entries.
```

## Architecture

```
┌─────────────────┐    ┌─────────────────┐
│   NOMAD API     │    │   Memgraph DB   │
│ (Materials Data)│    │ (Workflows)     │
└─────────────────┘    └─────────────────┘
         │                       │
         │                       │
    ┌─────────────────────────────────────┐
    │      Enhanced MCP Servers           │
    │  ┌─────────────────┐ ┌─────────────┐│
    │  │  NOMAD Server   │ │Memgraph     ││
    │  │  + Dataset Init │ │+ Analysis   ││
    │  │  + Formulas     │ │+ Trends     ││
    │  │  + Patterns     │ │+ Export     ││
    │  └─────────────────┘ └─────────────┘│
    └─────────────────────────────────────┘
                     │
                     │
            ┌─────────────────┐
            │  Claude Code    │
            │ (AI Assistant)  │
            └─────────────────┘
```

## Key Improvements

1. **Unified Interface**: All analysis tools now accessible through MCP
2. **Dynamic Dataset Support**: Initialize and analyze any NOMAD dataset
3. **Advanced Analysis**: Periodic trends, cluster patterns, interactive exploration
4. **Better Performance**: Database indexes and optimized queries
5. **Cleaner Architecture**: Consolidated 11+ scripts into 2 enhanced MCP servers

## Development

See [CLAUDE.md](CLAUDE.md) for detailed development guidance and tool documentation.