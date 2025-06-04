# Calculation Similarity Algorithm

## Overview
The workflow orchestrator determines relationships between calculations using a multi-step algorithm that combines domain knowledge from computational chemistry with file structure analysis.

## Current Relationship Types

### 1. **CONTAINS** (284 relationships)
- **Direction:** Dataset → Entry  
- **Purpose:** Organizational - links datasets to their constituent calculations
- **Algorithm:** Direct mapping from NOMAD dataset structure
- **Properties:** None

### 2. **SIMILAR_CALCULATION** (283 relationships)
- **Direction:** Entry → Entry
- **Purpose:** Sequential workflow steps between similar calculations
- **Algorithm:** Complex heuristic-based analysis (detailed below)
- **Properties:** 
  - `confidence` (0.0-1.0): How certain we are about the relationship
  - `upload_cluster`: Which dataset/workflow the relationship belongs to

## Similarity Determination Algorithm

### Step 1: Grouping by Upload
```python
# Group entries by upload_name (workflow clusters)
upload_groups = {}
for entry in entries:
    if entry.upload_name:
        upload_groups[entry.upload_name].append(entry)
```

### Step 2: Execution Order Sorting
Each entry gets a priority score based on computational chemistry conventions:

```python
def execution_priority(entry):
    priority = 100  # Default
    
    # Structure optimization typically comes first
    if "geometry" in entry.entry_type.lower() or "optimization" in entry.entry_type.lower():
        priority = 10
    # Then electronic structure calculations  
    elif "scf" in entry.entry_type.lower() or "dft" in entry.entry_type.lower():
        priority = 20
    # Then property calculations
    elif "dos" in entry.entry_type.lower() or "band" in entry.entry_type.lower():
        priority = 30
    # Post-processing and analysis last
    elif "analysis" in entry.entry_type.lower() or "post" in entry.entry_type.lower():
        priority = 40
    
    # File structure adjustments
    if entry.has_input_files and not entry.has_output_files:
        priority -= 5  # Likely early step
    elif entry.has_output_files and not entry.has_input_files:
        priority += 5  # Likely final step
        
    return priority
```

### Step 3: Relationship Type Determination
For each sequential pair of sorted entries:

```python
def determine_relationship_type(from_entry, to_entry):
    # Structural relationships
    if "geometry" in from_entry.entry_type.lower() and "scf" in to_entry.entry_type.lower():
        return "PROVIDES_STRUCTURE"
    elif "scf" in from_entry.entry_type.lower() and ("dos" in to_entry.entry_type.lower() or "band" in to_entry.entry_type.lower()):
        return "PROVIDES_ELECTRONIC_STRUCTURE"
    elif from_entry.entry_type == to_entry.entry_type:
        return "SIMILAR_CALCULATION"  # ← Currently all relationships are this type
    
    # File-based relationships
    elif from_entry.has_output_files and to_entry.has_input_files:
        return "PROVIDES_INPUT_DATA"
    
    # Default sequential relationship
    else:
        return "WORKFLOW_STEP"
```

### Step 4: Confidence Calculation
```python
def calculate_confidence(from_entry, to_entry):
    confidence = 0.5  # Base confidence
    
    # Same chemical formula increases confidence
    if from_entry.formula == to_entry.formula and from_entry.formula:
        confidence += 0.3
    
    # Compatible file structure increases confidence
    if from_entry.has_output_files and to_entry.has_input_files:
        confidence += 0.2
    
    # Compatible entry types increase confidence
    if are_compatible_entry_types(from_entry.entry_type, to_entry.entry_type):
        confidence += 0.2
    
    return min(confidence, 1.0)
```

## Why All Current Relationships Are "SIMILAR_CALCULATION"

In the current dataset, all entries have `entry_type = "fhi-aims_calculation"`, so the algorithm always hits this condition:

```python
elif from_entry.entry_type == to_entry.entry_type:
    return "SIMILAR_CALCULATION"
```

## Confidence Score Distribution

Let me check the actual confidence scores in the database: