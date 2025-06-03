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
        headers = {"Content-Type": "application/json"}
        if self.token and self.token.strip():
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
        headers = {"Content-Type": "application/json"}
        if self.token and self.token.strip():
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
        headers = {"Content-Type": "application/json"}
        if self.token and self.token.strip():
            headers["Authorization"] = f"Bearer {self.token}"
        
        response = await self.client.post(
            f"{self.base_url}/entries/raw/query",
            json={"entry_id": entry_ids},
            headers=headers
        )
        response.raise_for_status()
        return response.content
    
    async def get_dataset_entries(self, dataset_id: str = None, upload_name: str = None, upload_id: str = None, max_entries: int = None) -> Dict[str, Any]:
        """Get all entries from a specific dataset/upload with pagination handling"""
        headers = {"Content-Type": "application/json"}
        if self.token and self.token.strip():
            headers["Authorization"] = f"Bearer {self.token}"
        
        all_entries = []
        page_size = 100  # Smaller page size for reliability
        total_entries = 0
        
        if upload_id:
            # Use uploads endpoint - this returns upload info, not entries directly
            try:
                response = await self.client.get(f"{self.base_url}/uploads/{upload_id}")
                response.raise_for_status()
                result = response.json()
                
                # The uploads endpoint returns upload metadata, not entries
                # We need to use the entries count and then query entries separately
                upload_data = result.get("data", {})
                total_entries = upload_data.get("entries", 0)
                
                # Now query entries using the entries/query endpoint with upload_id filter
                page = 0
                while True:
                    query = {
                        "pagination": {
                            "page_size": page_size,
                            "page": page
                        },
                        "query": {"upload_id": upload_id}
                    }
                    
                    try:
                        entries_response = await self.client.post(
                            f"{self.base_url}/entries/query",
                            json=query,
                            headers={"Content-Type": "application/json"}
                        )
                        entries_response.raise_for_status()
                        entries_result = entries_response.json()
                        
                        # Get entries from this page
                        page_entries = entries_result.get("data", [])
                        all_entries.extend(page_entries)
                        
                        # Check if we have all entries or hit max limit
                        if len(page_entries) < page_size or (max_entries and len(all_entries) >= max_entries):
                            break
                        
                        page += 1
                        
                        # Safety limit to prevent infinite loops
                        if page > 1000:  # Max 100k entries
                            break
                            
                    except Exception as e:
                        print(f"Error fetching entries page {page}: {e}")
                        break
                        
            except Exception as e:
                print(f"Error fetching upload info: {e}")
                return {"data": [], "pagination": {"total": 0, "pages_fetched": 0}}
        else:
            # Use entries query endpoint for other identifiers
            page = 0
            
            while True:
                query = {
                    "pagination": {
                        "page_size": page_size,
                        "page": page
                    }
                }
                
                if dataset_id:
                    query["query"] = {"dataset_id": dataset_id}
                elif upload_name:
                    query["query"] = {"upload_name": upload_name}
                
                try:
                    response = await self.client.post(
                        f"{self.base_url}/entries/query",
                        json=query,
                        headers=headers
                    )
                    response.raise_for_status()
                    result = response.json()
                    
                    # Get entries from this page
                    page_entries = result.get("data", [])
                    all_entries.extend(page_entries)
                    
                    # Update total count from first response
                    if page == 0:
                        total_entries = result.get("pagination", {}).get("total", len(page_entries))
                    
                    # Check if we have all entries or hit max limit
                    if len(page_entries) < page_size or (max_entries and len(all_entries) >= max_entries):
                        break
                    
                    page += 1
                    
                    # Safety limit to prevent infinite loops
                    if page > 1000:  # Max 100k entries
                        break
                        
                except Exception as e:
                    print(f"Error fetching page {page}: {e}")
                    break
        
        # Trim to max_entries if specified
        if max_entries:
            all_entries = all_entries[:max_entries]
        
        return {
            "data": all_entries,
            "pagination": {
                "total": total_entries,
                "retrieved": len(all_entries),
                "pages_fetched": page + 1
            }
        }
    
    async def get_dataset_entries_lightweight(self, dataset_id: str = None, upload_name: str = None, upload_id: str = None, max_entries: int = 50) -> Dict[str, Any]:
        """Lightweight preview of dataset entries focusing on workflow essentials"""
        headers = {"Content-Type": "application/json"}
        if self.token and self.token.strip():
            headers["Authorization"] = f"Bearer {self.token}"
        
        if upload_id:
            # Use uploads endpoint for upload_id - no auth for public uploads
            response = await self.client.get(
                f"{self.base_url}/uploads/{upload_id}"
            )
        else:
            # Use entries query endpoint for other identifiers
            query = {
                "pagination": {"page_size": min(max_entries, 100)},
                "required": {
                    "include": [
                        "entry_id",
                        "entry_name", 
                        "entry_type",
                        "formula",
                        "upload_name",
                        "processing_errors"
                    ]
                }
            }
            
            if dataset_id:
                query["query"] = {"dataset_id": dataset_id}
            elif upload_name:
                query["query"] = {"upload_name": upload_name}
            
            response = await self.client.post(
                f"{self.base_url}/entries/query",
                json=query,
                headers=headers
            )
        
        response.raise_for_status()
        return response.json()
    
    async def get_entry_workflow_summary(self, entry_id: str) -> Dict[str, Any]:
        """Get lightweight workflow summary focusing on method and system info"""
        headers = {"Content-Type": "application/json"}
        if self.token and self.token.strip():
            headers["Authorization"] = f"Bearer {self.token}"
        
        # Request only workflow-relevant sections
        query = {
            "entry_id": entry_id,
            "required": [
                "run.program",
                "run.method", 
                "run.system",
                "workflow2.name",
                "metadata.entry_type",
                "results.material.formula_hill"
            ]
        }
        
        response = await self.client.post(
            f"{self.base_url}/entries/archive/query",
            json=query,
            headers=headers
        )
        response.raise_for_status()
        
        result = response.json()
        archive = result.get("data", {}).get("archive", {}).get("data", {})
        
        # Extract and summarize key workflow information
        summary = {
            "entry_id": entry_id,
            "workflow_name": None,
            "programs": [],
            "methods": [],
            "system_info": {},
            "formula": None
        }
        
        # Extract workflow name
        if "workflow2" in archive:
            summary["workflow_name"] = archive["workflow2"].get("name")
        
        # Extract run information
        if "run" in archive:
            runs = archive["run"] if isinstance(archive["run"], list) else [archive["run"]]
            for run in runs:
                if "program" in run:
                    prog = run["program"]
                    summary["programs"].append({
                        "name": prog.get("name"),
                        "version": prog.get("version")
                    })
                
                if "method" in run:
                    methods = run["method"] if isinstance(run["method"], list) else [run["method"]]
                    for method in methods:
                        summary["methods"].append({
                            "type": method.get("type"),
                            "basis_set": method.get("basis_set", {}).get("type"),
                            "electronic": method.get("electronic", {}).get("method")
                        })
                
                if "system" in run:
                    systems = run["system"] if isinstance(run["system"], list) else [run["system"]]
                    for system in systems:
                        summary["system_info"] = {
                            "n_atoms": len(system.get("atoms", {}).get("labels", [])) if "atoms" in system else None,
                            "chemical_formula": system.get("chemical_formula"),
                            "crystal_system": system.get("symmetry", {}).get("crystal_system")
                        }
                        break  # Just take first system
        
        # Extract formula from results
        if "results" in archive and "material" in archive["results"]:
            summary["formula"] = archive["results"]["material"].get("formula_hill")
        
        return summary
    
    async def get_file_content(self, entry_id: str, file_path: str) -> str:
        """Get the content of a specific file from an entry"""
        headers = {"Content-Type": "application/json"}
        if self.token and self.token.strip():
            headers["Authorization"] = f"Bearer {self.token}"
        
        # Use the files API endpoint to get file content
        response = await self.client.get(
            f"{self.base_url}/entries/{entry_id}/raw/{file_path}",
            headers=headers
        )
        response.raise_for_status()
        
        # Return as text (assumes most input/script files are text-based)
        try:
            return response.text
        except Exception:
            # If not text, return indication of binary content
            return f"[Binary file: {len(response.content)} bytes]"
    
    async def get_input_files_content(self, entry_id: str, max_files: int = 5) -> Dict[str, str]:
        """Get content of input files from an entry"""
        # First get file structure to identify input files
        files_data = await self.get_entry_files_info(entry_id)
        files = files_data.get("data", {}).get("archive", {}).get("data", {}).get("files", [])
        
        # Identify input files
        input_files = []
        for file_info in files:
            path = file_info.get("path", "").lower()
            if any(ext in path for ext in ['.in', '.inp', '.input']) or any(name in path for name in ['poscar', 'kpoints', 'potcar', 'incar']):
                input_files.append(file_info.get("path"))
        
        # Limit number of files to read
        input_files = input_files[:max_files]
        
        # Read content of each input file
        file_contents = {}
        for file_path in input_files:
            try:
                content = await self.get_file_content(entry_id, file_path)
                file_contents[file_path] = content
            except Exception as e:
                file_contents[file_path] = f"[Error reading file: {e}]"
        
        return file_contents
    
    async def get_script_files_content(self, entry_id: str, max_files: int = 3) -> Dict[str, str]:
        """Get content of script files from an entry"""
        # First get file structure to identify script files
        files_data = await self.get_entry_files_info(entry_id)
        files = files_data.get("data", {}).get("archive", {}).get("data", {}).get("files", [])
        
        # Identify script files
        script_files = []
        for file_info in files:
            path = file_info.get("path", "").lower()
            if any(ext in path for ext in ['.py', '.sh', '.slurm', '.pbs', '.job', '.batch']):
                script_files.append(file_info.get("path"))
        
        # Limit number of files to read
        script_files = script_files[:max_files]
        
        # Read content of each script file
        file_contents = {}
        for file_path in script_files:
            try:
                content = await self.get_file_content(entry_id, file_path)
                file_contents[file_path] = content
            except Exception as e:
                file_contents[file_path] = f"[Error reading file: {e}]"
        
        return file_contents
    
    async def extract_file_data_for_analysis(self, entry_id: str) -> Dict[str, Any]:
        """Extract raw file data without interpretation - let AI analyze patterns"""
        data = {
            "entry_id": entry_id,
            "input_files": {},
            "script_files": {},
            "file_metadata": {}
        }
        
        try:
            # Get file structure first
            files_info = await self.get_entry_files_info(entry_id)
            files = files_info.get("data", {}).get("archive", {}).get("data", {}).get("files", [])
            
            # Store file metadata
            for file_info in files:
                path = file_info.get("path", "")
                data["file_metadata"][path] = {
                    "size": file_info.get("size", 0),
                    "path": path,
                    "extension": path.split('.')[-1].lower() if '.' in path else "",
                    "filename": path.split('/')[-1],
                    "directory": '/'.join(path.split('/')[:-1]) if '/' in path else ""
                }
            
            # Get input file contents (raw, no parsing)
            input_contents = await self.get_input_files_content(entry_id, max_files=5)
            data["input_files"] = input_contents
            
            # Get script file contents (raw, no parsing)  
            script_contents = await self.get_script_files_content(entry_id, max_files=3)
            data["script_files"] = script_contents
            
        except Exception as e:
            data["error"] = str(e)
        
        return data
    
    async def get_entry_files_info(self, entry_id: str) -> Dict[str, Any]:
        """Get file structure information for an entry without downloading content"""
        headers = {"Content-Type": "application/json"}
        if self.token and self.token.strip():
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
        headers = {"Content-Type": "application/json"}
        if self.token and self.token.strip():
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
        ),
        Tool(
            name="nomad_preview_dataset",
            description="Lightweight preview of dataset entries focusing on workflow essentials",
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
                    },
                    "max_entries": {
                        "type": "number",
                        "default": 20,
                        "description": "Maximum number of entries to preview"
                    }
                }
            }
        ),
        Tool(
            name="nomad_get_entry_workflow_summary",
            description="Get lightweight workflow summary focusing on method, program, and system info",
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
            name="nomad_get_dataset_entries_paginated", 
            description="Get dataset entries with full pagination support and optional limits",
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
                    },
                    "max_entries": {
                        "type": "number",
                        "description": "Maximum number of entries to retrieve (for large datasets)"
                    }
                }
            }
        ),
        Tool(
            name="nomad_read_input_files",
            description="Read content of input files from a NOMAD entry for workflow analysis",
            inputSchema={
                "type": "object",
                "properties": {
                    "entry_id": {
                        "type": "string",
                        "description": "NOMAD entry ID"
                    },
                    "max_files": {
                        "type": "number",
                        "default": 5,
                        "description": "Maximum number of input files to read"
                    }
                },
                "required": ["entry_id"]
            }
        ),
        Tool(
            name="nomad_read_script_files",
            description="Read content of script files from a NOMAD entry to understand execution workflow",
            inputSchema={
                "type": "object",
                "properties": {
                    "entry_id": {
                        "type": "string",
                        "description": "NOMAD entry ID"
                    },
                    "max_files": {
                        "type": "number",
                        "default": 3,
                        "description": "Maximum number of script files to read"
                    }
                },
                "required": ["entry_id"]
            }
        ),
        Tool(
            name="nomad_read_specific_file",
            description="Read content of a specific file from a NOMAD entry",
            inputSchema={
                "type": "object",
                "properties": {
                    "entry_id": {
                        "type": "string",
                        "description": "NOMAD entry ID"
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Path to the specific file within the entry"
                    }
                },
                "required": ["entry_id", "file_path"]
            }
        ),
        Tool(
            name="nomad_extract_file_data",
            description="Extract raw file data (content + metadata) for AI analysis - no interpretation by MCP",
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
    
    elif name == "nomad_preview_dataset":
        dataset_id = arguments.get("dataset_id")
        upload_name = arguments.get("upload_name")
        max_entries = arguments.get("max_entries", 20)
        
        try:
            preview_data = await nomad_client.get_dataset_entries_lightweight(dataset_id, upload_name, max_entries)
            entries = preview_data.get("data", [])
            
            # Create lightweight summary
            preview_text = f"Dataset Preview ({len(entries)} entries shown):\n\n"
            
            # Group by entry type and formula for overview
            type_counts = {}
            formula_counts = {}
            upload_counts = {}
            
            for entry in entries:
                entry_type = entry.get("entry_type", "unknown")
                formula = entry.get("formula", "unknown")
                upload = entry.get("upload_name", "unknown")
                
                type_counts[entry_type] = type_counts.get(entry_type, 0) + 1
                formula_counts[formula] = formula_counts.get(formula, 0) + 1
                upload_counts[upload] = upload_counts.get(upload, 0) + 1
            
            preview_text += f"Entry Types: {dict(list(type_counts.items())[:5])}\n"
            preview_text += f"Top Formulas: {dict(list(formula_counts.items())[:5])}\n"
            preview_text += f"Upload Groups: {len(upload_counts)} groups\n\n"
            
            preview_text += "Sample Entries:\n"
            for entry in entries[:10]:
                preview_text += f"- {entry.get('entry_id')}: {entry.get('formula')} ({entry.get('entry_type')})\n"
            
            if len(entries) > 10:
                preview_text += f"... and {len(entries) - 10} more entries"
            
            return CallToolResult(
                content=[
                    TextContent(type="text", text=preview_text)
                ]
            )
            
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error previewing dataset: {str(e)}")]
            )
    
    elif name == "nomad_get_entry_workflow_summary":
        entry_id = arguments["entry_id"]
        
        try:
            summary = await nomad_client.get_entry_workflow_summary(entry_id)
            
            summary_text = f"Workflow Summary for {entry_id}:\n\n"
            
            if summary["workflow_name"]:
                summary_text += f"Workflow: {summary['workflow_name']}\n"
            
            if summary["formula"]:
                summary_text += f"Formula: {summary['formula']}\n"
            
            if summary["programs"]:
                programs_str = ", ".join([f"{p['name']} v{p['version']}" for p in summary["programs"]])
                summary_text += f"Programs: {programs_str}\n"
            
            if summary["methods"]:
                for i, method in enumerate(summary["methods"]):
                    summary_text += f"Method {i+1}: {method.get('type', 'Unknown')}\n"
                    if method.get("electronic"):
                        summary_text += f"  Electronic: {method['electronic']}\n"
                    if method.get("basis_set"):
                        summary_text += f"  Basis Set: {method['basis_set']}\n"
            
            if summary["system_info"]:
                sys_info = summary["system_info"]
                summary_text += f"System: "
                if sys_info.get("n_atoms"):
                    summary_text += f"{sys_info['n_atoms']} atoms, "
                if sys_info.get("chemical_formula"):
                    summary_text += f"{sys_info['chemical_formula']}, "
                if sys_info.get("crystal_system"):
                    summary_text += f"{sys_info['crystal_system']} crystal"
                summary_text += "\n"
            
            return CallToolResult(
                content=[
                    TextContent(type="text", text=summary_text)
                ]
            )
            
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error getting workflow summary: {str(e)}")]
            )
    
    elif name == "nomad_get_dataset_entries_paginated":
        dataset_id = arguments.get("dataset_id")
        upload_name = arguments.get("upload_name")
        max_entries = arguments.get("max_entries")
        
        try:
            dataset_data = await nomad_client.get_dataset_entries(dataset_id, upload_name, max_entries)
            entries = dataset_data.get("data", [])
            pagination = dataset_data.get("pagination", {})
            
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
            
            result_text = f"Paginated Dataset Entries:\n\n"
            result_text += f"Retrieved: {pagination.get('retrieved', len(entries))} / {pagination.get('total', 'unknown')} total entries\n"
            result_text += f"Pages fetched: {pagination.get('pages_fetched', 1)}\n\n"
            
            # Show sample entries
            for entry in formatted_entries[:15]:
                result_text += f"- {entry['entry_id']}: {entry['entry_name']} ({entry['entry_type']})\n"
            
            if len(formatted_entries) > 15:
                result_text += f"... and {len(formatted_entries) - 15} more entries\n"
            
            return CallToolResult(
                content=[
                    TextContent(type="text", text=result_text)
                ]
            )
            
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error retrieving paginated entries: {str(e)}")]
            )
    
    elif name == "nomad_read_input_files":
        entry_id = arguments["entry_id"]
        max_files = arguments.get("max_files", 5)
        
        try:
            file_contents = await nomad_client.get_input_files_content(entry_id, max_files)
            
            if not file_contents:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"No input files found for entry {entry_id}")]
                )
            
            result_text = f"Input Files for {entry_id}:\n\n"
            
            for file_path, content in file_contents.items():
                result_text += f"=== {file_path} ===\n"
                if content.startswith("[Error") or content.startswith("[Binary"):
                    result_text += f"{content}\n\n"
                else:
                    # Truncate very long files
                    if len(content) > 2000:
                        result_text += f"{content[:2000]}...\n[Truncated: {len(content)} total characters]\n\n"
                    else:
                        result_text += f"{content}\n\n"
            
            return CallToolResult(
                content=[TextContent(type="text", text=result_text)]
            )
            
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error reading input files: {str(e)}")]
            )
    
    elif name == "nomad_read_script_files":
        entry_id = arguments["entry_id"]
        max_files = arguments.get("max_files", 3)
        
        try:
            file_contents = await nomad_client.get_script_files_content(entry_id, max_files)
            
            if not file_contents:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"No script files found for entry {entry_id}")]
                )
            
            result_text = f"Script Files for {entry_id}:\n\n"
            
            for file_path, content in file_contents.items():
                result_text += f"=== {file_path} ===\n"
                if content.startswith("[Error") or content.startswith("[Binary"):
                    result_text += f"{content}\n\n"
                else:
                    # Truncate very long files
                    if len(content) > 1500:
                        result_text += f"{content[:1500]}...\n[Truncated: {len(content)} total characters]\n\n"
                    else:
                        result_text += f"{content}\n\n"
            
            return CallToolResult(
                content=[TextContent(type="text", text=result_text)]
            )
            
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error reading script files: {str(e)}")]
            )
    
    elif name == "nomad_read_specific_file":
        entry_id = arguments["entry_id"]
        file_path = arguments["file_path"]
        
        try:
            content = await nomad_client.get_file_content(entry_id, file_path)
            
            result_text = f"Content of {file_path} from entry {entry_id}:\n\n"
            
            if content.startswith("[Error") or content.startswith("[Binary"):
                result_text += content
            else:
                # Truncate very long files
                if len(content) > 3000:
                    result_text += f"{content[:3000]}...\n[Truncated: {len(content)} total characters]"
                else:
                    result_text += content
            
            return CallToolResult(
                content=[TextContent(type="text", text=result_text)]
            )
            
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error reading file {file_path}: {str(e)}")]
            )
    
    elif name == "nomad_analyze_workflow_dependencies":
        entry_id = arguments["entry_id"]
        
        try:
            analysis = await nomad_client.analyze_workflow_dependencies(entry_id)
            
            result_text = f"Workflow Dependencies Analysis for {entry_id}:\n\n"
            
            if "error" in analysis:
                result_text += f"Error: {analysis['error']}\n"
            else:
                # Input parameters
                if analysis["input_parameters"]:
                    result_text += "📋 INPUT PARAMETERS:\n"
                    for file_path, params in analysis["input_parameters"].items():
                        result_text += f"  {file_path}:\n"
                        for key, value in list(params.items())[:10]:  # Limit to 10 params per file
                            result_text += f"    {key}: {value}\n"
                        if len(params) > 10:
                            result_text += f"    ... and {len(params) - 10} more parameters\n"
                        result_text += "\n"
                
                # Software commands
                if analysis["software_commands"]:
                    result_text += "💻 SOFTWARE COMMANDS:\n"
                    for cmd in analysis["software_commands"][:10]:  # Limit to 10 commands
                        result_text += f"  Line {cmd['line']}: {cmd['command']} (software: {cmd['software']})\n"
                    if len(analysis["software_commands"]) > 10:
                        result_text += f"  ... and {len(analysis['software_commands']) - 10} more commands\n"
                    result_text += "\n"
                
                # File dependencies
                if analysis["dependencies"]:
                    result_text += "📁 FILE DEPENDENCIES:\n"
                    for dep in analysis["dependencies"][:10]:
                        result_text += f"  Line {dep['line']}: {dep['operation']} ({dep['type']})\n"
                    if len(analysis["dependencies"]) > 10:
                        result_text += f"  ... and {len(analysis['dependencies']) - 10} more dependencies\n"
                    result_text += "\n"
                
                # Workflow steps
                if analysis["workflow_steps"]:
                    result_text += "🔄 WORKFLOW STEPS:\n"
                    for step in analysis["workflow_steps"][:10]:
                        result_text += f"  Line {step['line']}: {step['step']} ({step['type']})\n"
                    if len(analysis["workflow_steps"]) > 10:
                        result_text += f"  ... and {len(analysis['workflow_steps']) - 10} more steps\n"
                    result_text += "\n"
                
                if not any([analysis["input_parameters"], analysis["software_commands"], 
                           analysis["dependencies"], analysis["workflow_steps"]]):
                    result_text += "No workflow dependencies detected from available files.\n"
            
            return CallToolResult(
                content=[TextContent(type="text", text=result_text)]
            )
            
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error extracting file data: {str(e)}")]
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