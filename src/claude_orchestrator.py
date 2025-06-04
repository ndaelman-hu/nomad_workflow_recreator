#!/usr/bin/env python3
"""
Claude-Driven Workflow Orchestrator

Delegates all intelligent analysis to Claude while providing data access tools.
The orchestrator simply provides data and executes Claude's decisions.
"""

import asyncio
import json
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
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

class ClaudeWorkflowOrchestrator:
    """
    Data-only orchestrator that provides Claude with tools to analyze workflows.
    All intelligence and reasoning is delegated to Claude via MCP interactions.
    """
    
    def __init__(self):
        self.nomad_client = NomadClient()
        self.memgraph_client = MemgraphClient()
    
    async def extract_dataset_for_claude(self, dataset_identifier: str, identifier_type: str = "upload_id") -> Dict[str, Any]:
        """
        Extract raw dataset for Claude to analyze.
        No intelligence - just data extraction and basic storage.
        """
        
        print(f"🔍 Extracting NOMAD dataset for Claude analysis: {dataset_identifier}")
        
        # Extract entries using existing logic (no intelligence here)
        if identifier_type == "dataset_id":
            dataset_data = await self.nomad_client.get_dataset_entries(dataset_id=dataset_identifier)
        elif identifier_type == "upload_id":
            dataset_data = await self.nomad_client.get_upload_entries(upload_id=dataset_identifier)
        else:
            search_query = {"query": {"upload_name": dataset_identifier}}
            dataset_data = await self.nomad_client.search_entries(search_query)
        
        entries = dataset_data.get("data", [])
        print(f"📊 Extracted {len(entries)} entries")
        
        # Convert to WorkflowEntry objects (minimal processing)
        workflow_entries = []
        for entry in entries:
            if not isinstance(entry, dict) or not entry.get("entry_id"):
                continue
                
            # Basic data extraction - no intelligence
            results = entry.get("results", {})
            material = results.get("material", {}) if isinstance(results, dict) else {}
            method = results.get("method", {}) if isinstance(results, dict) else {}
            
            workflow_data = {
                "workflow_name": method.get("workflow_name", "") if isinstance(method, dict) else "",
                "programs": [entry.get("parser_name", "").replace("parsers/", "")] if entry.get("parser_name") else [],
                "methods": [method.get("method_name", "")] if isinstance(method, dict) and method.get("method_name") else [],
                "system_info": {
                    "formula": material.get("chemical_formula_reduced", "") if isinstance(material, dict) else "",
                    "elements": material.get("elements", []) if isinstance(material, dict) else []
                }
            }
            
            files = entry.get("files", [])
            file_structure = self._basic_file_analysis(files)
            
            # Basic entry type from mainfile
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
                entry_id=entry.get("entry_id"),
                entry_name=mainfile.split('/')[-1] if mainfile else f"entry_{entry.get('entry_id', '')[:8]}",
                entry_type=entry_type,
                formula=material.get("chemical_formula_reduced", "") if isinstance(material, dict) else "",
                upload_name=entry.get("upload_id", ""),
                workflow_metadata=workflow_data,
                file_structure=file_structure
            )
            workflow_entries.append(workflow_entry)
        
        # Store basic dataset structure in Memgraph (no relationships yet)
        await self._store_basic_dataset(dataset_identifier, workflow_entries)
        
        return {
            "dataset_id": dataset_identifier,
            "entries_extracted": len(workflow_entries),
            "entries": [asdict(entry) for entry in workflow_entries],
            "ready_for_claude_analysis": True
        }
    
    def _basic_file_analysis(self, files: List[Any]) -> Dict[str, Any]:
        """Basic file categorization - no intelligence"""
        structure = {
            "total_files": len(files),
            "input_files": [],
            "output_files": [],
            "script_files": [],
            "data_files": [],
            "config_files": []
        }
        
        for file_info in files:
            if isinstance(file_info, str):
                path = file_info.lower()
                original_path = file_info
            elif isinstance(file_info, dict):
                path = file_info.get("path", "").lower()
                original_path = file_info.get("path", "")
            else:
                continue
            
            # Simple categorization
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
    
    async def _store_basic_dataset(self, dataset_id: str, entries: List[WorkflowEntry]):
        """Store dataset and entries - no relationships"""
        await self.memgraph_client.connect()
        
        # Create dataset node
        dataset_query = """
        MERGE (d:Dataset {dataset_id: $dataset_id})
        SET d.entry_count = $entry_count
        RETURN d
        """
        await self.memgraph_client.execute_query(dataset_query, {
            "dataset_id": dataset_id,
            "entry_count": len(entries)
        })
        
        # Create entry nodes with CONTAINS relationships
        for entry in entries:
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
    
    # Claude Analysis Tools
    
    async def get_entry_details(self, entry_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific entry for Claude"""
        query = """
        MATCH (e:Entry {entry_id: $entry_id})
        RETURN e
        """
        results = await self.memgraph_client.execute_query(query, {"entry_id": entry_id})
        return results[0] if results else None
    
    async def get_entries_by_formula(self, formula: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get entries with specific chemical formula for Claude analysis"""
        query = """
        MATCH (e:Entry {formula: $formula})
        RETURN e
        LIMIT $limit
        """
        return await self.memgraph_client.execute_query(query, {"formula": formula, "limit": limit})
    
    async def get_entries_by_type(self, entry_type: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get entries of specific type for Claude analysis"""
        query = """
        MATCH (e:Entry {entry_type: $entry_type})
        RETURN e
        LIMIT $limit
        """
        return await self.memgraph_client.execute_query(query, {"entry_type": entry_type, "limit": limit})
    
    async def get_upload_clusters(self, dataset_id: str) -> Dict[str, List[str]]:
        """Get entries grouped by upload_name for Claude to analyze workflow clusters"""
        query = """
        MATCH (d:Dataset {dataset_id: $dataset_id})-[:CONTAINS]->(e:Entry)
        WHERE e.upload_name IS NOT NULL
        RETURN e.upload_name as upload, collect(e.entry_id) as entry_ids
        """
        results = await self.memgraph_client.execute_query(query, {"dataset_id": dataset_id})
        return {list(r.values())[0]: list(r.values())[1] for r in results}
    
    async def compare_entries(self, entry_id1: str, entry_id2: str) -> Dict[str, Any]:
        """Compare two entries for Claude to analyze relationships"""
        query = """
        MATCH (e1:Entry {entry_id: $id1}), (e2:Entry {entry_id: $id2})
        RETURN e1, e2
        """
        results = await self.memgraph_client.execute_query(query, {"id1": entry_id1, "id2": entry_id2})
        if not results:
            return {}
        
        e1, e2 = list(results[0].values())
        return {
            "entry1": e1,
            "entry2": e2,
            "same_formula": e1.get("properties", {}).get("formula") == e2.get("properties", {}).get("formula"),
            "same_type": e1.get("properties", {}).get("entry_type") == e2.get("properties", {}).get("entry_type"),
            "same_upload": e1.get("properties", {}).get("upload_name") == e2.get("properties", {}).get("upload_name")
        }
    
    async def create_relationship_from_claude(self, from_entry_id: str, to_entry_id: str, 
                                            relationship_type: str, confidence: float, 
                                            reasoning: str = "") -> bool:
        """Create a relationship based on Claude's analysis"""
        query = """
        MATCH (from:Entry {entry_id: $from_id})
        MATCH (to:Entry {entry_id: $to_id})
        CREATE (from)-[r:`{rel_type}`]->(to)
        SET r.confidence = $confidence, r.reasoning = $reasoning, r.created_by = 'claude'
        RETURN r
        """.format(rel_type=relationship_type)
        
        try:
            await self.memgraph_client.execute_query(query, {
                "from_id": from_entry_id,
                "to_id": to_entry_id,
                "confidence": confidence,
                "reasoning": reasoning
            })
            return True
        except Exception as e:
            print(f"Error creating relationship: {e}")
            return False
    
    async def get_dataset_summary_for_claude(self, dataset_id: str) -> Dict[str, Any]:
        """Get comprehensive dataset summary for Claude to understand scope"""
        summary = {}
        
        # Basic counts
        count_query = """
        MATCH (d:Dataset {dataset_id: $dataset_id})-[:CONTAINS]->(e:Entry)
        RETURN count(e) as total_entries
        """
        count_result = await self.memgraph_client.execute_query(count_query, {"dataset_id": dataset_id})
        summary["total_entries"] = list(count_result[0].values())[0] if count_result else 0
        
        # Entry types distribution
        types_query = """
        MATCH (d:Dataset {dataset_id: $dataset_id})-[:CONTAINS]->(e:Entry)
        RETURN e.entry_type as type, count(e) as count
        """
        types_result = await self.memgraph_client.execute_query(types_query, {"dataset_id": dataset_id})
        summary["entry_types"] = {list(r.values())[0]: list(r.values())[1] for r in types_result}
        
        # Formula distribution
        formulas_query = """
        MATCH (d:Dataset {dataset_id: $dataset_id})-[:CONTAINS]->(e:Entry)
        WHERE e.formula <> ""
        RETURN e.formula as formula, count(e) as count
        ORDER BY count DESC
        LIMIT 10
        """
        formulas_result = await self.memgraph_client.execute_query(formulas_query, {"dataset_id": dataset_id})
        summary["top_formulas"] = {list(r.values())[0]: list(r.values())[1] for r in formulas_result}
        
        # Upload clusters
        summary["upload_clusters"] = await self.get_upload_clusters(dataset_id)
        
        return summary

async def main():
    """Main entry point for Claude-driven workflow orchestration"""
    import sys
    
    orchestrator = ClaudeWorkflowOrchestrator()
    
    # Get dataset name from command line or use default
    dataset_name = sys.argv[1] if len(sys.argv) > 1 else "YDXZgPooRb-31Niq48ODPA"
    
    try:
        # Extract dataset for Claude
        print("🤖 Extracting dataset for Claude analysis...")
        result = await orchestrator.extract_dataset_for_claude(dataset_name, "upload_id")
        
        print(f"\n📋 Dataset Ready for Claude:")
        print(f"   Dataset: {result['dataset_id']}")
        print(f"   Entries extracted: {result['entries_extracted']}")
        print(f"   Status: {result['ready_for_claude_analysis']}")
        
        # Get summary for Claude
        summary = await orchestrator.get_dataset_summary_for_claude(dataset_name)
        print(f"\n📊 Dataset Summary for Claude:")
        print(f"   Total entries: {summary['total_entries']}")
        print(f"   Entry types: {summary['entry_types']}")
        print(f"   Top formulas: {list(summary['top_formulas'].keys())[:5]}")
        print(f"   Upload clusters: {len(summary['upload_clusters'])}")
        
        print(f"\n🎯 Next Steps:")
        print(f"   1. Claude should analyze the dataset using MCP tools")
        print(f"   2. Claude will identify workflow relationships using domain knowledge")
        print(f"   3. Claude will create relationships via create_relationship_from_claude()")
        print(f"   4. No hardcoded rules - pure AI reasoning!")
        
    except Exception as e:
        print(f"❌ Error during extraction: {e}")

if __name__ == "__main__":
    asyncio.run(main())