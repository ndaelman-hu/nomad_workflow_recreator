# AI-Driven Workflow Analysis

## Philosophy: MCP Provides Tools, AI Makes Decisions

The MCP servers are designed as **pure data extraction and storage tools**, not interpretation engines. All software-specific pattern recognition, relationship inference, and workflow understanding is left to the AI assistant.

## 🔧 MCP Server Responsibilities (What MCP Does)

### Data Extraction Tools:
- `nomad_extract_file_data` - Extract raw file contents + metadata
- `nomad_read_input_files` - Read input file text (no parsing)
- `nomad_read_script_files` - Read script file text (no parsing)
- `nomad_get_entry_workflow_summary` - Basic metadata only

### Data Storage Tools:
- `memgraph_store_file_data` - Store raw file data in graph
- `memgraph_add_file_content_nodes` - Create file nodes with content
- `memgraph_store_parsed_data` - Store AI-analyzed results
- `memgraph_query_file_patterns` - Query by basic patterns

### Query Tools:
- `memgraph_query` - Execute custom Cypher queries
- `memgraph_find_nodes` - Basic node finding
- `memgraph_trace_workflow` - Graph traversal

## 🧠 AI Assistant Responsibilities (What AI Does)

### File Content Analysis:
```python
# AI decides what's important in input files
raw_data = nomad_extract_file_data(entry_id)
input_files = raw_data["input_files"]

# AI parses based on context and software knowledge
for file_path, content in input_files.items():
    if "INCAR" in file_path:
        # AI knows this is VASP and parses accordingly
        params = parse_vasp_incar(content)
    elif file_path.endswith(".inp"):
        # AI detects CP2K/Gaussian context and parses
        params = parse_quantum_input(content, software=detect_software(content))
    
    # Store AI's interpretation
    memgraph_store_parsed_data(entry_id, params, "parameters")
```

### Relationship Inference:
```python
# AI analyzes multiple entries to infer relationships
entry1_data = nomad_extract_file_data(entry1_id)
entry2_data = nomad_extract_file_data(entry2_id)

# AI decides if entries are related based on:
# - File content similarities  
# - Parameter matches
# - Script dependencies
# - Output → Input file patterns

if ai_detects_dependency(entry1_data, entry2_data):
    relationship_type = ai_classify_relationship(entry1_data, entry2_data)
    memgraph_add_workflow_relationships([{
        "from_entry_id": entry1_id,
        "to_entry_id": entry2_id, 
        "relationship_type": relationship_type,
        "properties": {"confidence": ai_confidence_score}
    }])
```

### Software Detection:
```python
# AI identifies computational software from context
script_content = raw_data["script_files"]["run.sh"]

software_detected = []
if "mpirun vasp_std" in script_content:
    software_detected.append("VASP")
if "cp2k.psmp" in script_content:
    software_detected.append("CP2K")

# Store AI's analysis
memgraph_store_parsed_data(entry_id, {
    "detected_software": software_detected,
    "execution_commands": extract_commands(script_content)
}, "commands")
```

### Pattern Recognition:
```python
# AI finds patterns across datasets
all_entries = memgraph_query("MATCH (e:Entry) RETURN e")

# AI groups by computational parameters
parameter_groups = ai_cluster_by_parameters(all_entries)

# AI identifies workflow templates
workflow_patterns = ai_detect_workflow_patterns(all_entries)

# Store insights
for pattern in workflow_patterns:
    memgraph_store_parsed_data("dataset_" + dataset_id, pattern, "custom")
```

## 📊 Example AI-Driven Workflow

### Step 1: Raw Data Extraction
```python
# MCP extracts raw data
file_data = nomad_extract_file_data("entry_123")
# Returns: {"input_files": {"INCAR": "ENCUT = 400\nISMEAR = 0"}, ...}
```

### Step 2: AI Analysis
```python
# AI interprets the raw data
def analyze_vasp_calculation(file_data):
    incar_content = file_data["input_files"]["INCAR"]
    
    # AI parses parameters
    params = {}
    for line in incar_content.split('\n'):
        if '=' in line:
            key, value = line.split('=', 1)
            params[key.strip()] = value.strip()
    
    # AI classifies calculation type
    calc_type = "geometry_optimization" if "IBRION" in params else "static"
    
    return {
        "parameters": params,
        "calculation_type": calc_type,
        "software": "VASP",
        "quality": assess_parameter_quality(params)
    }
```

### Step 3: Store AI Insights
```python
# Store AI's interpretation in graph
insights = analyze_vasp_calculation(file_data)
memgraph_store_parsed_data("entry_123", insights["parameters"], "parameters")
memgraph_store_parsed_data("entry_123", {"type": insights["calculation_type"]}, "custom")
```

### Step 4: AI-Driven Relationship Building
```python
# AI finds related calculations
similar_entries = memgraph_query("""
    MATCH (e1:Entry)-[:HAS_PARAMETER]->(p1:Parameter {name: 'ENCUT'})
    MATCH (e2:Entry)-[:HAS_PARAMETER]->(p2:Parameter {name: 'ENCUT'})
    WHERE e1 <> e2 AND p1.value = p2.value
    RETURN e1.entry_id, e2.entry_id
""")

# AI decides relationship semantics
for e1, e2 in similar_entries:
    memgraph_add_workflow_relationships([{
        "from_entry_id": e1,
        "to_entry_id": e2,
        "relationship_type": "SAME_CUTOFF_ENERGY",
        "properties": {"parameter": "ENCUT", "ai_inferred": True}
    }])
```

## 🎯 Benefits of This Approach

### ✅ **Flexibility**: 
- AI can adapt to new software packages
- No hardcoded assumptions in MCP server
- Easy to extend to new analysis methods

### ✅ **Context Awareness**:
- AI understands research context
- Can handle edge cases and variations
- Learns from patterns across datasets

### ✅ **Maintainability**:
- MCP server remains simple and stable
- All interpretation logic in AI layer
- Clear separation of concerns

### ✅ **Customization**:
- Different AIs can analyze same data differently
- Research-specific analysis approaches
- Domain expert knowledge integration

## 🔄 Workflow Summary

1. **MCP**: Extract raw file data from NOMAD
2. **AI**: Analyze content, detect patterns, infer relationships  
3. **MCP**: Store AI insights in graph database
4. **AI**: Query graph for complex workflow analysis
5. **AI**: Generate insights and recreate workflows

The MCP servers provide the **tools**, the AI provides the **intelligence**.