# Deprecated Orchestrator Files

This directory contains deprecated orchestrator implementations that have been superseded by newer approaches.

## Deprecated Files

### workflow_orchestrator.py
- **Status**: DEPRECATED
- **Reason**: Uses hardcoded relationship rules for workflow reconstruction
- **Replacement**: Claude-driven analysis via `run_analysis.sh` and MCP tools
- **Description**: Original orchestrator with predefined rules for creating relationships between NOMAD entries

### claude_orchestrator.py  
- **Status**: DEPRECATED
- **Reason**: Direct orchestration approach replaced by MCP-based architecture
- **Replacement**: Use `run_analysis.sh` with MCP servers for Claude-driven analysis
- **Description**: Early attempt at Claude-driven orchestration, now replaced by MCP server pattern

## Migration Guide

Instead of using these deprecated orchestrators, use the modern MCP-based approach:

1. **Automated Analysis** (Recommended):
   ```bash
   ./run_analysis.sh
   ```

2. **Manual MCP Usage**:
   - Start MCP servers: `nomad_server.py` and `memgraph_server.py`
   - Use Claude Code with MCP tools for intelligent workflow reconstruction

## Why Deprecated?

The old orchestrators had limitations:
- **workflow_orchestrator.py**: Hardcoded rules couldn't adapt to new patterns
- **claude_orchestrator.py**: Direct API calls limited flexibility

The new MCP architecture provides:
- Better separation of concerns
- More flexible Claude integration
- Dynamic, AI-driven relationship discovery
- No hardcoded assumptions about workflows

## Archive Notice

These files are kept for reference only. Do not use them for new development.