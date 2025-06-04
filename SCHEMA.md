# Memgraph Schema for NOMAD Workflow Recreation

## Overview
The schema represents materials science computational workflows from NOMAD as a graph database, capturing both the individual calculations and their relationships.

## Node Types

### 1. Dataset Nodes
**Label:** `Dataset`
**Purpose:** Represents a collection of related entries from NOMAD (e.g., a research dataset)

**Properties:**
- `dataset_id` (string): Unique identifier, typically the NOMAD upload_id
- `entry_count` (integer): Number of entries contained in this dataset

**Example:**
```cypher
(:Dataset {
  dataset_id: "YDXZgPooRb-31Niq48ODPA",
  entry_count: 284
})
```

### 2. Entry Nodes  
**Label:** `Entry`
**Purpose:** Represents individual computational chemistry calculations from NOMAD

**Properties:**
- `entry_id` (string): Unique NOMAD entry identifier
- `entry_name` (string): Human-readable name, usually the main output filename
- `entry_type` (string): Type of calculation (e.g., "fhi-aims_calculation")
- `formula` (string): Chemical formula of the material (e.g., "F8", "Au4")
- `upload_name` (string): Source dataset/upload identifier
- `total_files` (integer): Number of files associated with this calculation
- `has_input_files` (boolean): Whether the calculation has input files
- `has_output_files` (boolean): Whether the calculation has output files  
- `has_scripts` (boolean): Whether the calculation has script files

**Example:**
```cypher
(:Entry {
  entry_id: "-HX-_yjOTLprRuLn2yAHJWGwJKqG",
  entry_name: "aims.out",
  entry_type: "fhi-aims_calculation",
  formula: "F8",
  upload_name: "YDXZgPooRb-31Niq48ODPA",
  total_files: 3,
  has_input_files: true,
  has_output_files: true,
  has_scripts: false
})
```

## Relationship Types

### 1. CONTAINS
**Direction:** Dataset → Entry
**Purpose:** Organizational relationship linking datasets to their constituent entries

**Properties:** None

**Example:**
```cypher
(:Dataset)-[:CONTAINS]->(:Entry)
```

### 2. SIMILAR_CALCULATION
**Direction:** Entry → Entry  
**Purpose:** Represents workflow relationships between computational steps

**Properties:**
- `confidence` (float): Confidence score for the inferred relationship (0.0-1.0)
- `upload_cluster` (string): Identifier for the workflow cluster/dataset

**Relationship Types (planned/extensible):**
- `SIMILAR_CALCULATION`: Sequential calculations in workflow
- `PROVIDES_STRUCTURE`: Geometry optimization → Electronic structure calculation
- `PROVIDES_ELECTRONIC_STRUCTURE`: SCF → DOS/Band structure calculations
- `PROVIDES_INPUT_DATA`: Output files → Input for next calculation
- `WORKFLOW_STEP`: Sequential steps in same workflow
- `SAME_MATERIAL`: Same formula across different workflows

**Example:**
```cypher
(:Entry)-[:SIMILAR_CALCULATION {
  confidence: 0.5,
  upload_cluster: "YDXZgPooRb-31Niq48ODPA"
}]->(:Entry)
```

## Schema Design Principles

### 1. Materials Science Focus
- **Chemical formulas** as primary identifiers for grouping related calculations
- **File structure analysis** to infer calculation types and workflow steps
- **Workflow relationships** based on computational chemistry conventions

### 2. Extensibility
- Schema can accommodate additional relationship types as workflow patterns are identified
- Node properties can be extended with additional NOMAD metadata
- Supports multiple datasets and cross-dataset relationships

### 3. Query Patterns
The schema is optimized for common materials science queries:

```cypher
-- Find all calculations for a specific material
MATCH (e:Entry) WHERE e.formula = "Au4" RETURN e;

-- Trace workflow from a starting calculation
MATCH path = (start:Entry)-[:SIMILAR_CALCULATION*]->(end:Entry)
WHERE start.entry_id = "some-id"
RETURN path;

-- Find all datasets and their sizes
MATCH (d:Dataset) RETURN d.dataset_id, d.entry_count;

-- Group calculations by element type
MATCH (e:Entry) 
WHERE e.formula CONTAINS "Fe"
RETURN count(e) as iron_calculations;
```

## Current Implementation Status

### ✅ Implemented
- Dataset and Entry nodes with core properties
- CONTAINS relationships for dataset organization
- SIMILAR_CALCULATION relationships for basic workflow sequencing
- File structure analysis and metadata extraction

### 🔄 In Development
- Additional relationship types for specific workflow patterns
- Cross-dataset material relationships
- Enhanced chemical formula parsing and element extraction

### 📋 Planned Extensions
- Integration with raw file content for deeper analysis
- Support for computational parameters and results
- Temporal relationships based on calculation timestamps
- Integration with additional NOMAD metadata fields

## Data Sources

All data is extracted from the **NOMAD Materials Science Database** via their REST API:
- Entry metadata from `/entries/query` endpoint
- File structure information from entry data
- Chemical formulas and calculation types from NOMAD's processed results
- Workflow relationships inferred from file patterns and metadata analysis