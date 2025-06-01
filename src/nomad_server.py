#!/usr/bin/env python3
"""
NOMAD MCP Server

Provides tools for accessing NOMAD materials science database via MCP.
"""

import asyncio
import os
from typing import Any, Dict, List, Optional
import httpx
from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool, 
    TextContent, 
    ImageContent, 
    CallToolRequest, 
    CallToolResult
)
from pydantic import AnyUrl

load_dotenv()

class NomadClient:
    def __init__(self):
        self.base_url = os.getenv("NOMAD_BASE_URL", "https://nomad-lab.eu/prod/v1/api/v1")
        self.token = os.getenv("NOMAD_TOKEN")
        self.client = httpx.AsyncClient()
    
    async def authenticate(self) -> bool:
        """Check if authentication token is valid"""
        if not self.token:
            return False
        
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            response = await self.client.get(f"{self.base_url}/auth/me", headers=headers)
            return response.status_code == 200
        except:
            return False
    
    async def search_entries(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Search for entries in NOMAD database"""
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        
        response = await self.client.post(
            f"{self.base_url}/entries/query",
            json=query,
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    
    async def get_entry_archive(self, entry_id: str, required: List[str] = None) -> Dict[str, Any]:
        """Get archive data for a specific entry"""
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        
        query = {"entry_id": entry_id}
        if required:
            query["required"] = required
        
        response = await self.client.post(
            f"{self.base_url}/entries/archive/query",
            json=query,
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    
    async def download_raw_files(self, entry_ids: List[str]) -> bytes:
        """Download raw files for entries as zip"""
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        
        response = await self.client.post(
            f"{self.base_url}/entries/raw/query",
            json={"entry_id": entry_ids},
            headers=headers
        )
        response.raise_for_status()
        return response.content
    
    async def get_dataset_entries(self, dataset_id: str = None, upload_name: str = None) -> Dict[str, Any]:
        """Get all entries from a specific dataset/upload"""
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        
        query = {"pagination": {"page_size": 1000}}
        
        if dataset_id:
            query["dataset_id"] = dataset_id
        if upload_name:
            query["upload_name"] = upload_name
        
        response = await self.client.post(
            f"{self.base_url}/entries/query",
            json=query,
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    
    async def get_entry_files_info(self, entry_id: str) -> Dict[str, Any]:
        """Get file structure information for an entry without downloading content"""
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        
        query = {
            "entry_id": entry_id,
            "required": ["files"]
        }
        
        response = await self.client.post(
            f"{self.base_url}/entries/archive/query",
            json=query,
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    
    async def get_workflow_metadata(self, entry_id: str) -> Dict[str, Any]:
        """Extract workflow-relevant metadata from entry"""
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        
        query = {
            "entry_id": entry_id,
            "required": [
                "workflow2",
                "run",
                "results",
                "metadata"
            ]
        }
        
        response = await self.client.post(
            f"{self.base_url}/entries/archive/query",
            json=query,
            headers=headers
        )
        response.raise_for_status()
        return response.json()

# Initialize NOMAD client
nomad_client = NomadClient()

# Create MCP server
server = Server("nomad-mcp-server")

@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available NOMAD tools"""
    return [
        Tool(
            name="nomad_search_entries",
            description="Search for materials science entries in NOMAD database",
            inputSchema={
                "type": "object",
                "properties": {
                    "elements": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Chemical elements to search for"
                    },
                    "formula": {
                        "type": "string", 
                        "description": "Chemical formula to search for"
                    },
                    "n_atoms": {
                        "type": "object",
                        "properties": {
                            "gte": {"type": "number"},
                            "lte": {"type": "number"}
                        },
                        "description": "Number of atoms range filter"
                    },
                    "owner": {
                        "type": "string",
                        "enum": ["public", "user", "shared"],
                        "description": "Entry ownership filter"
                    },
                    "max_results": {
                        "type": "number",
                        "default": 10,
                        "description": "Maximum number of results to return"
                    }
                }
            }
        ),
        Tool(
            name="nomad_get_entry_details",
            description="Get detailed archive data for a specific NOMAD entry",
            inputSchema={
                "type": "object",
                "properties": {
                    "entry_id": {
                        "type": "string",
                        "description": "NOMAD entry ID"
                    },
                    "sections": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific archive sections to retrieve"
                    }
                },
                "required": ["entry_id"]
            }
        ),
        Tool(
            name="nomad_check_auth",
            description="Check if NOMAD authentication is configured and valid",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="nomad_get_dataset_entries",
            description="Get all entries from a specific dataset or upload for workflow reconstruction",
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_id": {
                        "type": "string",
                        "description": "NOMAD dataset ID"
                    },
                    "upload_name": {
                        "type": "string",
                        "description": "Upload/dataset name to search for"
                    }
                }
            }
        ),
        Tool(
            name="nomad_get_entry_files",
            description="Get file structure information for an entry (no raw content)",
            inputSchema={
                "type": "object",
                "properties": {
                    "entry_id": {
                        "type": "string",
                        "description": "NOMAD entry ID"
                    }
                },
                "required": ["entry_id"]
            }
        ),
        Tool(
            name="nomad_get_workflow_metadata",
            description="Extract workflow and calculation metadata from an entry",
            inputSchema={
                "type": "object",
                "properties": {
                    "entry_id": {
                        "type": "string",
                        "description": "NOMAD entry ID"
                    }
                },
                "required": ["entry_id"]
            }
        ),
        Tool(
            name="nomad_analyze_dataset_structure",
            description="Analyze the overall structure and relationships in a dataset",
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_id": {
                        "type": "string",
                        "description": "NOMAD dataset ID"
                    },
                    "upload_name": {
                        "type": "string",
                        "description": "Upload/dataset name"
                    }
                }
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
    """Handle tool calls"""
    
    if name == "nomad_search_entries":
        # Build search query
        query = {
            "pagination": {
                "page_size": arguments.get("max_results", 10)
            }
        }
        
        # Add filters
        if "elements" in arguments:
            query["elements"] = arguments["elements"]
        if "formula" in arguments:
            query["formula"] = arguments["formula"]
        if "n_atoms" in arguments:
            query["n_atoms"] = arguments["n_atoms"]
        if "owner" in arguments:
            query["owner"] = arguments["owner"]
        
        try:
            results = await nomad_client.search_entries(query)
            
            # Format results for display
            entries = results.get("data", [])
            formatted_results = []
            
            for entry in entries:
                formatted_results.append({
                    "entry_id": entry.get("entry_id"),
                    "formula": entry.get("formula"),
                    "elements": entry.get("elements"),
                    "n_atoms": entry.get("n_atoms"),
                    "upload_name": entry.get("upload_name"),
                    "authors": entry.get("authors", [])
                })
            
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Found {len(formatted_results)} entries:\n\n" + 
                             "\n".join([
                                 f"- {r['entry_id']}: {r['formula']} ({r['n_atoms']} atoms)"
                                 for r in formatted_results
                             ])
                    )
                ]
            )
            
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error searching NOMAD: {str(e)}")]
            )
    
    elif name == "nomad_get_entry_details":
        entry_id = arguments["entry_id"]
        sections = arguments.get("sections")
        
        try:
            archive_data = await nomad_client.get_entry_archive(entry_id, sections)
            
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Archive data for entry {entry_id}:\n\n{archive_data}"
                    )
                ]
            )
            
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error retrieving entry details: {str(e)}")]
            )
    
    elif name == "nomad_check_auth":
        try:
            is_authenticated = await nomad_client.authenticate()
            token_status = "configured and valid" if is_authenticated else "not configured or invalid"
            
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"NOMAD authentication: {token_status}\n"
                             f"Base URL: {nomad_client.base_url}"
                    )
                ]
            )
            
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error checking authentication: {str(e)}")]
            )
    
    elif name == "nomad_get_dataset_entries":
        dataset_id = arguments.get("dataset_id")
        upload_name = arguments.get("upload_name")
        
        try:
            dataset_data = await nomad_client.get_dataset_entries(dataset_id, upload_name)
            entries = dataset_data.get("data", [])
            
            # Format entries for workflow analysis
            formatted_entries = []
            for entry in entries:
                formatted_entries.append({
                    "entry_id": entry.get("entry_id"),
                    "upload_name": entry.get("upload_name"),
                    "entry_name": entry.get("entry_name"),
                    "formula": entry.get("formula"),
                    "entry_type": entry.get("entry_type"),
                    "authors": entry.get("authors", []),
                    "processing_errors": entry.get("processing_errors", [])
                })
            
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Dataset contains {len(formatted_entries)} entries:\n\n" +
                             "\n".join([
                                 f"- {e['entry_id']}: {e['entry_name']} ({e['entry_type']})"
                                 for e in formatted_entries[:20]  # Limit display
                             ]) + (f"\n... and {len(formatted_entries) - 20} more" if len(formatted_entries) > 20 else "")
                    )
                ]
            )
            
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error retrieving dataset entries: {str(e)}")]
            )
    
    elif name == "nomad_get_entry_files":
        entry_id = arguments["entry_id"]
        
        try:
            files_data = await nomad_client.get_entry_files_info(entry_id)
            files = files_data.get("data", {}).get("archive", {}).get("data", {}).get("files", [])
            
            # Analyze file structure
            file_tree = {}
            for file_info in files:
                path = file_info.get("path", "")
                size = file_info.get("size", 0)
                file_tree[path] = {"size": size}
            
            # Identify important file types
            input_files = [f for f in file_tree.keys() if any(ext in f.lower() for ext in ['.in', '.inp', '.input'])]
            output_files = [f for f in file_tree.keys() if any(ext in f.lower() for ext in ['.out', '.output', '.log'])]
            script_files = [f for f in file_tree.keys() if any(ext in f.lower() for ext in ['.py', '.sh', '.slurm', '.pbs'])]
            
            structure_summary = {
                "total_files": len(file_tree),
                "input_files": input_files,
                "output_files": output_files,
                "script_files": script_files,
                "file_tree": file_tree
            }
            
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"File structure for entry {entry_id}:\n\n"
                             f"Total files: {structure_summary['total_files']}\n"
                             f"Input files: {len(input_files)}\n"
                             f"Output files: {len(output_files)}\n"
                             f"Script files: {len(script_files)}\n\n"
                             f"Key files:\n" +
                             "\n".join([f"  INPUT: {f}" for f in input_files[:5]]) + "\n" +
                             "\n".join([f"  OUTPUT: {f}" for f in output_files[:5]]) + "\n" +
                             "\n".join([f"  SCRIPT: {f}" for f in script_files[:5]])
                    )
                ]
            )
            
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error retrieving file structure: {str(e)}")]
            )
    
    elif name == "nomad_get_workflow_metadata":
        entry_id = arguments["entry_id"]
        
        try:
            workflow_data = await nomad_client.get_workflow_metadata(entry_id)
            archive = workflow_data.get("data", {}).get("archive", {}).get("data", {})
            
            # Extract workflow information
            workflow_info = {
                "entry_id": entry_id,
                "workflow": archive.get("workflow2", {}),
                "run": archive.get("run", []),
                "results": archive.get("results", {}),
                "metadata": archive.get("metadata", {})
            }
            
            # Summarize workflow steps
            workflow_summary = "Workflow metadata:\n\n"
            
            if workflow_info["workflow"]:
                workflow_summary += f"Workflow type: {workflow_info['workflow'].get('name', 'Unknown')}\n"
            
            if workflow_info["run"]:
                workflow_summary += f"Calculation runs: {len(workflow_info['run'])}\n"
                for i, run in enumerate(workflow_info['run'][:3]):  # Show first 3 runs
                    program = run.get("program", {})
                    workflow_summary += f"  Run {i+1}: {program.get('name', 'Unknown')} v{program.get('version', 'Unknown')}\n"
            
            if workflow_info["results"]:
                results = workflow_info["results"]
                if "properties" in results:
                    workflow_summary += f"Computed properties: {list(results['properties'].keys())}\n"
            
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=workflow_summary
                    )
                ]
            )
            
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error retrieving workflow metadata: {str(e)}")]
            )
    
    elif name == "nomad_analyze_dataset_structure":
        dataset_id = arguments.get("dataset_id")
        upload_name = arguments.get("upload_name")
        
        try:
            # Get all entries in dataset
            dataset_data = await nomad_client.get_dataset_entries(dataset_id, upload_name)
            entries = dataset_data.get("data", [])
            
            # Analyze structure
            entry_types = {}
            upload_names = set()
            entry_relationships = []
            
            for entry in entries:
                entry_type = entry.get("entry_type", "unknown")
                entry_types[entry_type] = entry_types.get(entry_type, 0) + 1
                upload_names.add(entry.get("upload_name", ""))
            
            analysis = {
                "total_entries": len(entries),
                "entry_types": entry_types,
                "uploads": list(upload_names),
                "potential_workflows": []
            }
            
            # Look for workflow patterns
            for upload in upload_names:
                upload_entries = [e for e in entries if e.get("upload_name") == upload]
                if len(upload_entries) > 1:
                    analysis["potential_workflows"].append({
                        "upload": upload,
                        "entry_count": len(upload_entries),
                        "types": list(set(e.get("entry_type", "") for e in upload_entries))
                    })
            
            analysis_text = f"Dataset Analysis:\n\n"
            analysis_text += f"Total entries: {analysis['total_entries']}\n"
            analysis_text += f"Entry types: {analysis['entry_types']}\n"
            analysis_text += f"Number of uploads: {len(analysis['uploads'])}\n\n"
            analysis_text += f"Potential workflows detected: {len(analysis['potential_workflows'])}\n"
            
            for wf in analysis["potential_workflows"][:5]:  # Show first 5
                analysis_text += f"  - {wf['upload']}: {wf['entry_count']} entries, types: {wf['types']}\n"
            
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=analysis_text
                    )
                ]
            )
            
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error analyzing dataset structure: {str(e)}")]
            )
    
    else:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Unknown tool: {name}")]
        )

async def main():
    """Main entry point for the NOMAD MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())