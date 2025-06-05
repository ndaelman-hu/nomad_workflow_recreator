# Enhanced MCP Tools Documentation

This document details the enhanced MCP tools available in the NOMAD Workflow Recreator system.

## Overview

The enhanced MCP servers consolidate functionality from 11+ standalone Python scripts into a clean, unified interface accessible through Claude Code or other MCP-compatible AI assistants.

## NOMAD Server Tools (`nomad_server_enhanced.py`)

### Dataset Management

#### `list_datasets`
Lists available NOMAD datasets with metadata.
- **Parameters**: 
  - `max_datasets` (int, optional): Maximum number to list (default: 20)
- **Returns**: Dataset names, IDs, entry counts, and descriptions

#### `initialize_dataset_workflow`
Initializes a complete workflow analysis for a NOMAD dataset.
- **Parameters**:
  - `dataset_id` (str): The NOMAD dataset ID
  - `dataset_name` (str, optional): Human-readable name
  - `max_entries` (int, optional): Maximum entries to analyze
  - `include_file_content` (bool, optional): Include raw file content
- **Returns**: Processed entries ready for graph creation

### Formula Analysis

#### `analyze_dataset_formulas`
Analyzes chemical formulas in a dataset for patterns.
- **Parameters**:
  - `dataset_id` (str): The NOMAD dataset ID
  - `group_by` (str): "element", "size", or "composition"
- **Returns**: Grouped analysis of formulas

#### `get_dataset_workflow_patterns`
Extracts workflow patterns from dataset entries.
- **Parameters**:
  - `dataset_id` (str): The NOMAD dataset ID
  - `pattern_type` (str): "file_patterns", "method_patterns", or "parameter_studies"
- **Returns**: Pattern analysis results

## Memgraph Server Tools (`memgraph_server_enhanced.py`)

### Analysis Tools

#### `memgraph_analyze_periodic_trends`
Analyzes and creates PERIODIC_TREND relationships based on periodic table groups.
- **Parameters**:
  - `create_relationships` (bool): Whether to create relationships
  - `group_filter` (str, optional): Filter to specific group
- **Groups**: alkali_metals, alkaline_earth, transition_metals, halogens, noble_gases, pnictogens, chalcogens

#### `memgraph_analyze_cluster_patterns`
Finds and analyzes cluster size variations.
- **Parameters**:
  - `element` (str, optional): Specific element to analyze
  - `create_relationships` (bool): Whether to create relationships
  - `min_confidence` (float): Minimum confidence score (default: 0.8)
- **Creates**: CLUSTER_SIZE_SERIES relationships

#### `memgraph_quick_analysis`
Runs predefined analysis queries.
- **Parameters**:
  - `analysis_type` (str): Type of analysis
  - `limit` (int): Maximum results
- **Types**:
  - `formulas`: Formula occurrence counts
  - `relationships`: Relationship type counts
  - `periodic_trends`: PERIODIC_TREND relationships
  - `clusters`: CLUSTER_SIZE_SERIES relationships
  - `summary`: Node type summary

#### `memgraph_interactive_explore`
Interactive exploration of the dataset.
- **Parameters**:
  - `explore_type` (str): Type of exploration
  - `parameters` (dict): Additional parameters
- **Types**:
  - `dataset_summary`: Overview of all datasets
  - `formula_details`: Details for specific formula
  - `entry_comparison`: Compare entries
  - `relationship_explorer`: Explore relationships

### Dataset Management

#### `memgraph_clear_dataset`
Clears existing dataset from the database.
- **Parameters**:
  - `dataset_id` (str): Dataset ID or "all"
  - `confirm` (bool): Confirmation required
- **Warning**: This permanently deletes data

#### `memgraph_initialize_indexes`
Creates database indexes for optimal performance.
- **Creates indexes on**: Entry(entry_id), Entry(formula), Entry(entry_type), Dataset(dataset_id), File(file_path), Parameter(name)

#### `memgraph_get_dataset_stats`
Gets detailed statistics about datasets.
- **Parameters**:
  - `dataset_id` (str): Specific dataset or "all"
- **Returns**: Entry counts, unique formulas, relationship counts

## Usage Examples

### Example 1: Initialize and Analyze New Dataset
```
1. Use list_datasets to find available datasets
2. Use initialize_dataset_workflow to set up the dataset
3. Use memgraph_create_dataset_graph to build the graph
4. Use analyze_periodic_trends to create relationships
5. Use quick_analysis to verify results
```

### Example 2: Explore Existing Data
```
1. Use memgraph_get_dataset_stats to understand what's loaded
2. Use interactive_explore with dataset_summary
3. Use quick_analysis with "formulas" to see chemical diversity
4. Use analyze_cluster_patterns for specific elements
```

### Example 3: Clean and Restart
```
1. Use memgraph_clear_dataset to remove old data
2. Use initialize_indexes to optimize performance
3. Start fresh with new dataset initialization
```

## Migration from Standalone Scripts

| Old Script | New MCP Tool |
|------------|--------------|
| query_graph.py | memgraph_query_graph_export |
| quick_queries.py | memgraph_quick_analysis |
| interactive_analysis.py | memgraph_interactive_explore |
| cluster_size_relationships.py | memgraph_analyze_cluster_patterns |
| periodic_trends_summary.py | memgraph_analyze_periodic_trends |
| analyze_and_populate.py | Combination of tools |

## Best Practices

1. **Start with Dataset Stats**: Always check what's in the database first
2. **Use Indexes**: Run initialize_indexes for better performance
3. **Batch Operations**: Create relationships in batches for efficiency
4. **Verify Results**: Use quick_analysis to verify relationship creation
5. **Clean Up**: Use clear_dataset when switching between analyses