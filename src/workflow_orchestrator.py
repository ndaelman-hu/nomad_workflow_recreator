#!/usr/bin/env python3
"""
Workflow Orchestrator

Coordinates NOMAD data extraction and Memgraph graph construction
for complete workflow recreation from public datasets.
"""

import asyncio
import json
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from nomad_server_improved import NomadClient
from memgraph_server import MemgraphClient

@dataclass
class WorkflowEntry:
    """Represents a workflow entry with all necessary metadata"""
    entry_id: str
    entry_name: str
    entry_type: str
    formula: str
    upload_name: str
    workflow_metadata: Dict[str, Any]
    file_structure: Dict[str, Any]
    
class WorkflowOrchestrator:
    """Orchestrates the complete workflow reconstruction process"""
    
    def __init__(self):
        self.nomad_client = NomadClient()
        self.memgraph_client = MemgraphClient()
    
    async def reconstruct_dataset_workflow(self, dataset_identifier: str, identifier_type: str = "upload_id") -> Dict[str, Any]:
        """
        Complete workflow reconstruction from NOMAD dataset to Memgraph
        
        Args:
            dataset_identifier: Dataset ID or upload name
            identifier_type: 'dataset_id' or 'upload_name'
            
        Returns:
            Summary of reconstruction process
        """
        
        # Step 1: Preview dataset first to understand scope
        print(f"🔍 Previewing NOMAD dataset: {dataset_identifier}")
        if identifier_type == "dataset_id":
            preview_data = await self.nomad_client.get_dataset_entries(dataset_id=dataset_identifier, max_entries=50)
        elif identifier_type == "upload_id":
            preview_data = await self.nomad_client.get_upload_entries(upload_id=dataset_identifier, max_entries=50)
        else:
            # For upload_name, we'll need to search for it
            search_query = {"query": {"upload_name": dataset_identifier}, "pagination": {"page_size": 50}}
            preview_data = await self.nomad_client.search_entries(search_query)
        
        preview_entries = preview_data.get("data", [])
        total_estimated = preview_data.get("pagination", {}).get("total", len(preview_entries))
        
        print(f"📊 Dataset preview: ~{total_estimated} total entries, analyzing first {len(preview_entries)}")
        
        # Decide on full extraction strategy based on size
        if total_estimated > 1000:
            print(f"⚠️  Large dataset detected ({total_estimated} entries). Using sampling strategy...")
            max_entries = 500  # Limit for very large datasets
        else:
            max_entries = None  # Extract all entries
        
        # Step 2: Extract full dataset with pagination
        print(f"🔍 Extracting entries from NOMAD dataset: {dataset_identifier}")
        if identifier_type == "dataset_id":
            dataset_data = await self.nomad_client.get_dataset_entries(dataset_id=dataset_identifier, max_entries=max_entries)
        elif identifier_type == "upload_id":
            dataset_data = await self.nomad_client.get_upload_entries(upload_id=dataset_identifier, max_entries=max_entries)
        else:
            # For upload_name, use search
            search_query = {"query": {"upload_name": dataset_identifier}}
            if max_entries:
                search_query["pagination"] = {"page_size": min(max_entries, 100)}
            dataset_data = await self.nomad_client.search_entries(search_query)
        
        entries = dataset_data.get("data", [])
        pagination_info = dataset_data.get("pagination", {})
        print(f"📊 Retrieved {len(entries)} entries ({pagination_info.get('pages_fetched', 1)} pages)")
        
        # Step 3: Convert entries to workflow entries using data already available
        print("🔬 Converting entries to workflow format (using existing data only)...")
        workflow_entries = []
        
        for i, entry in enumerate(entries):
            try:
                if not isinstance(entry, dict):
                    print(f"  ⚠️  Skipping non-dict entry {i}: {type(entry)}")
                    continue
                    
                entry_id = entry.get("entry_id")
                if not entry_id:
                    print(f"  ⚠️  Skipping entry {i} without entry_id")
                    continue
                
                # Extract workflow data from the correct NOMAD entry structure with safety checks
                results = entry.get("results", {})
                if not isinstance(results, dict):
                    results = {}
                    
                material = results.get("material", {})
                if not isinstance(material, dict):
                    material = {}
                    
                method = results.get("method", {})
                if not isinstance(method, dict):
                    method = {}
                
                workflow_data = {
                    "workflow_name": method.get("workflow_name", "") if isinstance(method, dict) else "",
                    "programs": [entry.get("parser_name", "").replace("parsers/", "")] if entry.get("parser_name") else [],
                    "methods": [method.get("method_name", "")] if isinstance(method, dict) and method.get("method_name") else [],
                    "system_info": {
                        "formula": material.get("chemical_formula_reduced", "") if isinstance(material, dict) else "",
                        "elements": material.get("elements", []) if isinstance(material, dict) else []
                    }
                }
                
                # Use minimal file structure from available entry data
                files = entry.get("files", [])
                file_structure = {
                    "total_files": len(files),
                    "input_files": [],
                    "output_files": [],
                    "script_files": [],
                    "data_files": [],
                    "config_files": []
                }
                
                # Basic file categorization from files list if available
                if files:
                    file_structure = self._analyze_file_structure(files)
                
                # Determine entry type from mainfile and method
                mainfile = entry.get("mainfile", "")
                entry_type = "calculation"
                if mainfile:
                    if "aims.out" in mainfile:
                        entry_type = "fhi-aims_calculation"
                    elif ".inp" in mainfile or ".in" in mainfile:
                        entry_type = "input_file"
                    elif "control" in mainfile.lower():
                        entry_type = "control_file"
                
                workflow_entry = WorkflowEntry(
                    entry_id=entry_id,
                    entry_name=mainfile.split('/')[-1] if mainfile else f"entry_{entry_id[:8]}",
                    entry_type=entry_type,
                    formula=material.get("chemical_formula_reduced", ""),
                    upload_name=entry.get("upload_id", ""),
                    workflow_metadata=workflow_data,
                    file_structure=file_structure
                )
                workflow_entries.append(workflow_entry)
            
            except Exception as e:
                print(f"  ⚠️  Error processing entry {i}: {e}")
                continue
        
        print(f"  ✅ Converted {len(workflow_entries)} entries to workflow format")
        
        # Step 3: Create graph structure in Memgraph
        print("🔗 Creating graph structure in Memgraph...")
        await self._create_dataset_graph(dataset_identifier, workflow_entries)
        
        # Step 4: Analyze and create workflow relationships
        print("🕸️  Analyzing workflow relationships...")
        relationships = await self._infer_workflow_relationships(workflow_entries)
        print(f"🔗 Creating {len(relationships)} workflow relationships in Memgraph...")
        await self._create_workflow_relationships(relationships)
        
        # Step 5: Generate summary
        print("📋 Generating summary...")
        try:
            entry_types = list(set(e.entry_type for e in workflow_entries))
            upload_clusters = list(set(e.upload_name for e in workflow_entries if e.upload_name))
            
            summary = {
                "dataset_id": dataset_identifier,
                "entries_processed": len(workflow_entries),
                "relationships_created": len(relationships),
                "entry_types": entry_types,
                "upload_clusters": upload_clusters
            }
        except Exception as e:
            print(f"  ⚠️  Error generating summary: {e}")
            summary = {
                "dataset_id": dataset_identifier,
                "entries_processed": len(workflow_entries),
                "relationships_created": len(relationships),
                "entry_types": ["unknown"],
                "upload_clusters": ["unknown"]
            }
        
        print("✅ Workflow reconstruction complete!")
        return summary
    
    def _analyze_file_structure(self, files: List[Any]) -> Dict[str, Any]:
        """Analyze file structure to identify workflow components"""
        structure = {
            "total_files": len(files),
            "input_files": [],
            "output_files": [],
            "script_files": [],
            "data_files": [],
            "config_files": []
        }
        
        for file_info in files:
            # Handle both string paths and dict file info
            if isinstance(file_info, str):
                path = file_info.lower()
                original_path = file_info
            elif isinstance(file_info, dict):
                path = file_info.get("path", "").lower()
                original_path = file_info.get("path", "")
            else:
                continue
            
            # Categorize files
            if any(ext in path for ext in ['.in', '.inp', '.input']):
                structure["input_files"].append(original_path)
            elif any(ext in path for ext in ['.out', '.output', '.log']):
                structure["output_files"].append(original_path)
            elif any(ext in path for ext in ['.py', '.sh', '.slurm', '.pbs', '.job']):
                structure["script_files"].append(original_path)
            elif any(ext in path for ext in ['.json', '.yaml', '.yml', '.xml', '.cfg', '.conf']):
                structure["config_files"].append(original_path)
            elif any(ext in path for ext in ['.csv', '.dat', '.txt', '.hdf5', '.h5']):
                structure["data_files"].append(original_path)
        
        return structure
    
    async def _create_dataset_graph(self, dataset_id: str, entries: List[WorkflowEntry]):
        """Create the basic dataset graph structure"""
        await self.memgraph_client.connect()
        
        # Create dataset node
        print(f"  Creating dataset node for {dataset_id}")
        dataset_query = """
        MERGE (d:Dataset {dataset_id: $dataset_id})
        SET d.entry_count = $entry_count
        RETURN d
        """
        try:
            await self.memgraph_client.execute_query(dataset_query, {
                "dataset_id": dataset_id,
                "entry_count": len(entries)
            })
            print(f"  ✅ Dataset node created")
        except Exception as e:
            print(f"  ❌ Error creating dataset node: {e}")
            raise
        
        # Create entry nodes with rich metadata
        print(f"  Creating {len(entries)} entry nodes...")
        for i, entry in enumerate(entries):
            try:
                entry_query = """
                CREATE (e:Entry {
                    entry_id: $entry_id,
                    entry_name: $entry_name,
                    entry_type: $entry_type,
                    formula: $formula,
                    upload_name: $upload_name,
                    total_files: $total_files,
                    has_input_files: $has_input_files,
                    has_output_files: $has_output_files,
                    has_scripts: $has_scripts
                })
                WITH e
                MATCH (d:Dataset {dataset_id: $dataset_id})
                CREATE (d)-[:CONTAINS]->(e)
                RETURN e
                """
                
                await self.memgraph_client.execute_query(entry_query, {
                    "entry_id": entry.entry_id,
                    "entry_name": entry.entry_name,
                    "entry_type": entry.entry_type,
                    "formula": entry.formula,
                    "upload_name": entry.upload_name,
                    "dataset_id": dataset_id,
                    "total_files": entry.file_structure.get("total_files", 0),
                    "has_input_files": len(entry.file_structure.get("input_files", [])) > 0,
                    "has_output_files": len(entry.file_structure.get("output_files", [])) > 0,
                    "has_scripts": len(entry.file_structure.get("script_files", [])) > 0
                })
                
                if (i + 1) % 50 == 0:
                    print(f"    Created {i + 1}/{len(entries)} entries")
                    
            except Exception as e:
                print(f"  ❌ Error creating entry {i} ({entry.entry_id}): {e}")
                print(f"     Entry data: {entry}")
                raise
    
    async def _infer_workflow_relationships(self, entries: List[WorkflowEntry]) -> List[Dict[str, Any]]:
        """Infer relationships between workflow entries based on metadata and file analysis"""
        relationships = []
        
        print(f"  Analyzing relationships for {len(entries)} entries")
        
        # Group entries by upload_name (likely workflow clusters)
        upload_groups = {}
        for entry in entries:
            try:
                if entry.upload_name:
                    if entry.upload_name not in upload_groups:
                        upload_groups[entry.upload_name] = []
                    upload_groups[entry.upload_name].append(entry)
            except Exception as e:
                print(f"  ⚠️  Error grouping entry: {e}")
                continue
        
        print(f"  Found {len(upload_groups)} upload groups")
        
        # Analyze relationships within each upload group
        for upload_name, group_entries in upload_groups.items():
            try:
                if len(group_entries) <= 1:
                    continue
                    
                print(f"    Processing upload group {upload_name} with {len(group_entries)} entries")
                
                # Sort entries by likely execution order (heuristics)
                print(f"      Sorting {len(group_entries)} entries by execution order")
                sorted_entries = self._sort_entries_by_execution_order(group_entries)
                print(f"      ✅ Sorted entries")
                
                # Create sequential relationships for likely workflow steps
                print(f"      Creating {len(sorted_entries) - 1} sequential relationships")
                for i in range(len(sorted_entries) - 1):
                    current_entry = sorted_entries[i]
                    next_entry = sorted_entries[i + 1]
                    
                    
                    # Check if entries are valid
                    if not hasattr(current_entry, 'entry_id') or not hasattr(next_entry, 'entry_id'):
                        print(f"        ⚠️  Invalid entry objects: {current_entry}, {next_entry}")
                        continue
                    
                    # Determine relationship type based on entry types and file analysis
                    rel_type = self._determine_relationship_type(current_entry, next_entry)
                    
                    relationships.append({
                        "from_entry_id": current_entry.entry_id,
                        "to_entry_id": next_entry.entry_id,
                        "relationship_type": rel_type,
                        "properties": {
                            "upload_cluster": upload_name,
                            "confidence": self._calculate_relationship_confidence(current_entry, next_entry)
                        }
                    })
            except Exception as e:
                print(f"  ⚠️  Error processing upload group {upload_name}: {e}")
                continue
        
        # Look for cross-upload relationships (shared formulas, similar structures) 
        try:
            cross_relationships = self._find_cross_upload_relationships(entries)
            relationships.extend(cross_relationships)
            print(f"  Added {len(cross_relationships)} cross-upload relationships")
        except Exception as e:
            print(f"  ⚠️  Error finding cross-upload relationships: {e}")
        
        return relationships
    
    def _sort_entries_by_execution_order(self, entries: List[WorkflowEntry]) -> List[WorkflowEntry]:
        """Sort entries by likely execution order using heuristics"""
        def execution_priority(entry: WorkflowEntry) -> int:
            # Lower number = earlier in workflow
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
            
            # Adjust based on file structure
            if entry.file_structure.get("has_input_files") and not entry.file_structure.get("has_output_files"):
                priority -= 5  # Likely early step
            elif entry.file_structure.get("has_output_files") and not entry.file_structure.get("has_input_files"):
                priority += 5  # Likely final step
            
            return priority
        
        return sorted(entries, key=execution_priority)
    
    def _determine_relationship_type(self, from_entry: WorkflowEntry, to_entry: WorkflowEntry) -> str:
        """Determine the semantic relationship type between two entries"""
        
        # Structural relationships
        if "geometry" in from_entry.entry_type.lower() and "scf" in to_entry.entry_type.lower():
            return "PROVIDES_STRUCTURE"
        elif "scf" in from_entry.entry_type.lower() and ("dos" in to_entry.entry_type.lower() or "band" in to_entry.entry_type.lower()):
            return "PROVIDES_ELECTRONIC_STRUCTURE"
        elif from_entry.entry_type == to_entry.entry_type:
            return "SIMILAR_CALCULATION"
        
        # File-based relationships
        elif from_entry.file_structure.get("has_output_files") and to_entry.file_structure.get("has_input_files"):
            return "PROVIDES_INPUT_DATA"
        
        # Default sequential relationship
        else:
            return "WORKFLOW_STEP"
    
    def _calculate_relationship_confidence(self, from_entry: WorkflowEntry, to_entry: WorkflowEntry) -> float:
        """Calculate confidence score for inferred relationship"""
        confidence = 0.5  # Base confidence
        
        # Same formula increases confidence
        if from_entry.formula == to_entry.formula and from_entry.formula:
            confidence += 0.3
        
        # Compatible file structure increases confidence
        if from_entry.file_structure.get("has_output_files") and to_entry.file_structure.get("has_input_files"):
            confidence += 0.2
        
        # Compatible entry types increase confidence
        if self._are_compatible_entry_types(from_entry.entry_type, to_entry.entry_type):
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def _are_compatible_entry_types(self, type1: str, type2: str) -> bool:
        """Check if two entry types are compatible in a workflow"""
        compatible_sequences = [
            ["geometry_optimization", "single_point", "dos"],
            ["structure", "scf", "band_structure"],
            ["optimization", "frequency", "thermodynamics"]
        ]
        
        for sequence in compatible_sequences:
            if type1.lower() in sequence and type2.lower() in sequence:
                return True
        
        return False
    
    def _find_cross_upload_relationships(self, entries: List[WorkflowEntry]) -> List[Dict[str, Any]]:
        """Find relationships between entries in different uploads"""
        relationships = []
        
        # Find entries with same formula but different uploads
        formula_groups = {}
        for entry in entries:
            if entry.formula and entry.upload_name:
                if entry.formula not in formula_groups:
                    formula_groups[entry.formula] = {}
                if entry.upload_name not in formula_groups[entry.formula]:
                    formula_groups[entry.formula][entry.upload_name] = []
                formula_groups[entry.formula][entry.upload_name].append(entry)
        
        # Create cross-upload relationships for same formulas
        for formula, upload_groups in formula_groups.items():
            uploads = list(upload_groups.keys())
            for i in range(len(uploads)):
                for j in range(i + 1, len(uploads)):
                    upload1_entries = upload_groups[uploads[i]]
                    upload2_entries = upload_groups[uploads[j]]
                    
                    # Link representative entries from each upload
                    if upload1_entries and upload2_entries:
                        relationships.append({
                            "from_entry_id": upload1_entries[0].entry_id,
                            "to_entry_id": upload2_entries[0].entry_id,
                            "relationship_type": "SAME_MATERIAL",
                            "properties": {
                                "formula": formula,
                                "confidence": 0.8
                            }
                        })
        
        return relationships
    
    async def _create_workflow_relationships(self, relationships: List[Dict[str, Any]]):
        """Create relationships in Memgraph"""
        print(f"  Creating {len(relationships)} relationships...")
        for i, rel in enumerate(relationships):
            # Format query outside try block
            rel_type = rel["relationship_type"]
            rel_query = """
            MATCH (from:Entry {{entry_id: $from_id}})
            MATCH (to:Entry {{entry_id: $to_id}})
            CREATE (from)-[r:{rel_type}]->(to)
            SET r += $properties
            RETURN r
            """.format(rel_type=rel_type)
            
            try:
                await self.memgraph_client.execute_query(rel_query, {
                    "from_id": rel["from_entry_id"],
                    "to_id": rel["to_entry_id"],
                    "properties": rel.get("properties", {})
                })
                
                if (i + 1) % 50 == 0:
                    print(f"    Created {i + 1}/{len(relationships)} relationships")
                    
            except Exception as e:
                print(f"    ⚠️  Error creating relationship {i}: {e}")
                # Continue with other relationships

async def main():
    """Example usage of the workflow orchestrator"""
    import sys
    
    orchestrator = WorkflowOrchestrator()
    
    # Get dataset name from command line or use default
    dataset_name = sys.argv[1] if len(sys.argv) > 1 else "example_dataset"
    
    try:
        summary = await orchestrator.reconstruct_dataset_workflow(dataset_name, "upload_id")
        print(f"\n📋 Workflow Reconstruction Summary:")
        print(f"   Dataset: {summary['dataset_id']}")
        print(f"   Entries processed: {summary['entries_processed']}")
        print(f"   Relationships created: {summary['relationships_created']}")
        print(f"   Entry types: {summary['entry_types']}")
        print(f"   Upload clusters: {len(summary['upload_clusters'])}")
    except Exception as e:
        print(f"❌ Error during workflow reconstruction: {e}")

if __name__ == "__main__":
    asyncio.run(main())