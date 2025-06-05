#!/usr/bin/env python3
"""
Enhanced NOMAD MCP Server

Provides tools for accessing NOMAD materials science database via MCP,
including dataset initialization and workflow analysis capabilities.
"""

import asyncio
import os
import sys
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

# Add parent directory to path to import workflow orchestrator
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests"""
        headers = {"Content-Type": "application/json"}
        if self.token and self.token.strip():
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    async def get_uploads(self, is_published: bool = True, page_size: int = 100, max_entries: int = None) -> Dict[str, Any]:
        """Get list of uploads with pagination"""
        all_uploads = []
        page_after_value = None
        total_uploads = 0
        pages_fetched = 0
        
        while True:
            url = f"{self.base_url}/uploads?page_size={page_size}&owner=public"
            if is_published:
                url += "&is_published=true"
            if page_after_value:
                url += f"&page_after_value={page_after_value}"
            
            try:
                response = await self.client.get(url, headers=self._get_headers())
                response.raise_for_status()
                result = response.json()
                
                # Get uploads from this page
                page_uploads = result.get("data", [])
                all_uploads.extend(page_uploads)
                pages_fetched += 1
                
                # Update total count from first response
                if total_uploads == 0:
                    total_uploads = result.get("pagination", {}).get("total", len(page_uploads))
                
                # Check if we have all uploads or hit max limit
                if len(page_uploads) < page_size or (max_entries and len(all_uploads) >= max_entries):
                    break
                
                # Get next page token
                page_after_value = result.get("pagination", {}).get("next_page_after_value")
                if not page_after_value:
                    break
                    
            except Exception as e:
                print(f"Error fetching uploads: {e}")
                break
        
        # Trim to max_entries if specified
        if max_entries:
            all_uploads = all_uploads[:max_entries]
        
        return {
            "data": all_uploads,
            "pagination": {
                "total": total_uploads,
                "pages_fetched": pages_fetched
            }
        }
    
    async def get_upload_details(self, upload_id: str) -> Dict[str, Any]:
        """Get details for a specific upload"""
        try:
            response = await self.client.get(
                f"{self.base_url}/uploads/{upload_id}",
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Error fetching upload details: {e}")
    
    async def get_upload_entries(self, upload_id: str, page_size: int = 100, max_entries: int = None) -> Dict[str, Any]:
        """Get all entries from a specific upload using entries/query with upload_id filter"""
        all_entries = []
        page_after_value = None
        total_entries = 0
        pages_fetched = 0
        
        while True:
            query = {
                "pagination": {"page_size": page_size},
                "owner": "public",
                "query": {"upload_id": upload_id}
            }
            if page_after_value:
                query["pagination"]["page_after_value"] = page_after_value
            
            try:
                response = await self.client.post(
                    f"{self.base_url}/entries/query",
                    json=query,
                    headers={"Content-Type": "application/json"}  # No auth for public entries
                )
                response.raise_for_status()
                result = response.json()
                
                # Get entries from this page
                page_entries = result.get("data", [])
                all_entries.extend(page_entries)
                pages_fetched += 1
                
                # Update total count from first response
                if total_entries == 0:
                    total_entries = result.get("pagination", {}).get("total", len(page_entries))
                
                # Check if we have all entries or hit max limit
                if len(page_entries) < page_size or (max_entries and len(all_entries) >= max_entries):
                    break
                
                # Get next page token
                page_after_value = result.get("pagination", {}).get("next_page_after_value")
                if not page_after_value:
                    break
                    
            except Exception as e:
                print(f"Error fetching upload entries: {e}")
                break
        
        # Trim to max_entries if specified
        if max_entries:
            all_entries = all_entries[:max_entries]
        
        return {
            "data": all_entries,
            "pagination": {
                "total": total_entries,
                "pages_fetched": pages_fetched
            }
        }
    
    async def get_dataset_entries(self, dataset_id: str, page_size: int = 100, max_entries: int = None) -> Dict[str, Any]:
        """Get all entries from a specific dataset"""
        all_entries = []
        page_after_value = None
        total_entries = 0
        pages_fetched = 0
        
        while True:
            url = f"{self.base_url}/entries?dataset_id={dataset_id}&page_size={page_size}&owner=public"
            if page_after_value:
                url += f"&page_after_value={page_after_value}"
            
            try:
                response = await self.client.get(url, headers=self._get_headers())
                response.raise_for_status()
                result = response.json()
                
                # Get entries from this page
                page_entries = result.get("data", [])
                all_entries.extend(page_entries)
                pages_fetched += 1
                
                # Update total count from first response
                if total_entries == 0:
                    total_entries = result.get("pagination", {}).get("total", len(page_entries))
                
                # Check if we have all entries or hit max limit
                if len(page_entries) < page_size or (max_entries and len(all_entries) >= max_entries):
                    break
                
                # Get next page token
                page_after_value = result.get("pagination", {}).get("next_page_after_value")
                if not page_after_value:
                    break
                    
            except Exception as e:
                print(f"Error fetching dataset entries: {e}")
                break
        
        # Trim to max_entries if specified
        if max_entries:
            all_entries = all_entries[:max_entries]
        
        return {
            "data": all_entries,
            "pagination": {
                "total": total_entries,
                "pages_fetched": pages_fetched
            }
        }
    
    async def get_entry_archive(self, entry_id: str, upload_id: str = None, required: List[str] = None) -> Dict[str, Any]:
        """Get full archive data for a specific entry"""
        headers = self._get_headers()
        
        if upload_id:
            # Use upload-specific archive endpoint
            url = f"{self.base_url}/uploads/{upload_id}/archive/{entry_id}"
            try:
                response = await self.client.get(url, headers=headers)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                print(f"Error fetching archive from upload: {e}")
        
        # Fallback to general archive endpoint
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
    
    async def get_upload_raw_files(self, upload_id: str, path: str = "") -> Dict[str, Any]:
        """Get raw file metadata for an upload"""
        try:
            url = f"{self.base_url}/uploads/{upload_id}/rawdir"
            if path:
                url += f"/{path}"
            
            response = await self.client.get(url, headers=self._get_headers())
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Error fetching raw files: {e}")
    
    async def search_entries(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Search for entries using complex queries"""
        headers = self._get_headers()
        
        # Ensure public access and proper pagination
        if "owner" not in query:
            query["owner"] = "public"
        
        response = await self.client.post(
            f"{self.base_url}/entries/query",
            json=query,
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    
    async def get_entry_workflow_summary(self, entry_id: str) -> Dict[str, Any]:
        """Get lightweight workflow summary for an entry"""
        headers = {"Content-Type": "application/json"}
        
        # Use entries endpoint to get basic workflow info
        try:
            response = await self.client.get(
                f"{self.base_url}/entries/{entry_id}?include=results.method,workflow,run.program",
                headers=headers
            )
            response.raise_for_status()
            data = response.json()
            
            # Extract workflow summary from entry data
            results = data.get("data", {}).get("results", {})
            workflow = data.get("data", {}).get("workflow", {})
            run = data.get("data", {}).get("run", {})
            
            return {
                "workflow_name": workflow.get("type", ""),
                "programs": [run.get("program", {}).get("name", "")] if run.get("program") else [],
                "methods": [results.get("method", {}).get("method_name", "")] if results.get("method") else [],
                "system_info": {
                    "formula": results.get("material", {}).get("chemical_formula_reduced", ""),
                    "elements": results.get("material", {}).get("elements", [])
                }
            }
        except Exception as e:
            print(f"Error getting workflow summary for {entry_id}: {e}")
            return {}
    
    async def get_entry_files_info(self, entry_id: str) -> Dict[str, Any]:
        """Get file structure information for an entry"""
        headers = {"Content-Type": "application/json"}
        
        # Use entries endpoint to get file information
        try:
            response = await self.client.get(
                f"{self.base_url}/entries/{entry_id}?include=files",
                headers=headers
            )
            response.raise_for_status()
            data = response.json()
            
            # Extract file information
            files = data.get("data", {}).get("files", [])
            
            return {
                "data": {
                    "archive": {
                        "data": {
                            "files": files
                        }
                    }
                }
            }
        except Exception as e:
            print(f"Error getting files info for {entry_id}: {e}")
            return {"data": {"archive": {"data": {"files": []}}}}
    
    async def list_datasets(self, max_datasets: int = 20) -> Dict[str, Any]:
        """List available NOMAD datasets"""
        try:
            response = await self.client.get(
                f"{self.base_url}/datasets?page_size={max_datasets}&owner=public",
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Error listing datasets: {e}")

# Create MCP server
app = Server("nomad-server-enhanced")

# Global client instance
nomad_client = NomadClient()

@app.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available NOMAD tools"""
    return [
        # Original tools
        Tool(
            name="get_upload_entries",
            description="Get all entries from a specific NOMAD upload",
            inputSchema={
                "type": "object",
                "properties": {
                    "upload_id": {
                        "type": "string",
                        "description": "The NOMAD upload ID"
                    },
                    "max_entries": {
                        "type": "integer",
                        "description": "Maximum number of entries to retrieve (optional)",
                        "minimum": 1
                    }
                },
                "required": ["upload_id"]
            }
        ),
        Tool(
            name="get_dataset_entries",
            description="Get all entries from a specific NOMAD dataset",
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_id": {
                        "type": "string",
                        "description": "The NOMAD dataset ID"
                    },
                    "max_entries": {
                        "type": "integer",
                        "description": "Maximum number of entries to retrieve (optional)",
                        "minimum": 1
                    }
                },
                "required": ["dataset_id"]
            }
        ),
        Tool(
            name="get_upload_details",
            description="Get metadata and details for a specific upload",
            inputSchema={
                "type": "object",
                "properties": {
                    "upload_id": {
                        "type": "string",
                        "description": "The NOMAD upload ID"
                    }
                },
                "required": ["upload_id"]
            }
        ),
        Tool(
            name="get_entry_archive",
            description="Get full archive data for a specific entry",
            inputSchema={
                "type": "object",
                "properties": {
                    "entry_id": {
                        "type": "string",
                        "description": "The NOMAD entry ID"
                    },
                    "upload_id": {
                        "type": "string",
                        "description": "The upload ID (optional, for faster access)"
                    }
                },
                "required": ["entry_id"]
            }
        ),
        Tool(
            name="search_entries",
            description="Search NOMAD entries with custom filters",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "object",
                        "description": "Query parameters for search"
                    },
                    "max_entries": {
                        "type": "integer",
                        "description": "Maximum number of entries to retrieve",
                        "minimum": 1,
                        "maximum": 1000
                    }
                },
                "required": ["query"]
            }
        ),
        
        # New dataset tools
        Tool(
            name="list_datasets",
            description="List available NOMAD datasets",
            inputSchema={
                "type": "object",
                "properties": {
                    "max_datasets": {
                        "type": "integer",
                        "description": "Maximum number of datasets to list",
                        "default": 20,
                        "minimum": 1,
                        "maximum": 100
                    }
                }
            }
        ),
        Tool(
            name="initialize_dataset_workflow",
            description="Initialize a complete workflow analysis for a NOMAD dataset",
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_id": {
                        "type": "string",
                        "description": "The NOMAD dataset ID to analyze"
                    },
                    "dataset_name": {
                        "type": "string",
                        "description": "Human-readable name for the dataset"
                    },
                    "max_entries": {
                        "type": "integer",
                        "description": "Maximum entries to analyze",
                        "minimum": 1
                    },
                    "include_file_content": {
                        "type": "boolean",
                        "default": False,
                        "description": "Whether to include raw file content"
                    }
                },
                "required": ["dataset_id"]
            }
        ),
        Tool(
            name="analyze_dataset_formulas",
            description="Analyze chemical formulas in a dataset for patterns",
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_id": {
                        "type": "string",
                        "description": "The NOMAD dataset ID"
                    },
                    "group_by": {
                        "type": "string",
                        "enum": ["element", "size", "composition"],
                        "default": "element",
                        "description": "How to group the analysis"
                    }
                }
            }
        ),
        Tool(
            name="get_dataset_workflow_patterns",
            description="Extract workflow patterns from dataset entries",
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_id": {
                        "type": "string",
                        "description": "The NOMAD dataset ID"
                    },
                    "pattern_type": {
                        "type": "string",
                        "enum": ["file_patterns", "method_patterns", "parameter_studies"],
                        "default": "file_patterns",
                        "description": "Type of patterns to extract"
                    }
                }
            }
        ),
        Tool(
            name="get_entry_with_files",
            description="Get entry data including raw file contents",
            inputSchema={
                "type": "object",
                "properties": {
                    "entry_id": {
                        "type": "string",
                        "description": "The NOMAD entry ID"
                    },
                    "file_patterns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "File patterns to include (e.g., ['*.inp', '*.sh'])"
                    }
                }
            }
        )
    ]

@app.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
    """Handle tool calls"""
    try:
        # Original tools
        if name == "get_upload_entries":
            upload_id = arguments["upload_id"]
            max_entries = arguments.get("max_entries")
            result = await nomad_client.get_upload_entries(upload_id, max_entries=max_entries)
            return CallToolResult(content=[TextContent(type="text", text=str(result))])
        
        elif name == "get_dataset_entries":
            dataset_id = arguments["dataset_id"]
            max_entries = arguments.get("max_entries")
            result = await nomad_client.get_dataset_entries(dataset_id, max_entries=max_entries)
            return CallToolResult(content=[TextContent(type="text", text=str(result))])
        
        elif name == "get_upload_details":
            upload_id = arguments["upload_id"]
            result = await nomad_client.get_upload_details(upload_id)
            return CallToolResult(content=[TextContent(type="text", text=str(result))])
        
        elif name == "get_entry_archive":
            entry_id = arguments["entry_id"]
            upload_id = arguments.get("upload_id")
            result = await nomad_client.get_entry_archive(entry_id, upload_id)
            return CallToolResult(content=[TextContent(type="text", text=str(result))])
        
        elif name == "search_entries":
            query = arguments["query"]
            max_entries = arguments.get("max_entries", 100)
            
            # Add pagination limit
            if "pagination" not in query:
                query["pagination"] = {}
            query["pagination"]["page_size"] = min(max_entries, 100)
            
            result = await nomad_client.search_entries(query)
            return CallToolResult(content=[TextContent(type="text", text=str(result))])
        
        # New dataset tools
        elif name == "list_datasets":
            max_datasets = arguments.get("max_datasets", 20)
            result = await nomad_client.list_datasets(max_datasets)
            
            datasets = result.get("data", [])
            dataset_text = f"Found {len(datasets)} datasets:\n\n"
            for ds in datasets:
                dataset_text += f"- {ds.get('name', 'Unnamed')} ({ds.get('dataset_id')})\n"
                dataset_text += f"  Entries: {ds.get('n_entries', 0)}\n"
                if ds.get('description'):
                    dataset_text += f"  Description: {ds['description'][:100]}...\n"
                dataset_text += "\n"
            
            return CallToolResult(content=[TextContent(type="text", text=dataset_text)])
        
        elif name == "initialize_dataset_workflow":
            dataset_id = arguments["dataset_id"]
            dataset_name = arguments.get("dataset_name", dataset_id)
            max_entries = arguments.get("max_entries", 100)
            include_files = arguments.get("include_file_content", False)
            
            # Get dataset entries
            entries_result = await nomad_client.get_dataset_entries(dataset_id, max_entries=max_entries)
            entries = entries_result.get("data", [])
            
            # Process entries for workflow initialization
            processed_entries = []
            for entry in entries:
                entry_data = {
                    "entry_id": entry.get("entry_id"),
                    "entry_name": entry.get("mainfile", ""),
                    "entry_type": entry.get("entry_type", "unknown"),
                    "formula": entry.get("results", {}).get("material", {}).get("chemical_formula_reduced", ""),
                    "upload_name": entry.get("upload_name", ""),
                    "workflow_metadata": {
                        "upload_id": entry.get("upload_id"),
                        "process_status": entry.get("process_status"),
                        "entry_create_time": entry.get("entry_create_time")
                    }
                }
                
                # Get file structure if requested
                if include_files:
                    files_info = await nomad_client.get_entry_files_info(entry["entry_id"])
                    entry_data["file_structure"] = files_info.get("data", {}).get("archive", {}).get("data", {}).get("files", [])
                
                processed_entries.append(entry_data)
            
            result_text = f"Dataset Initialization Complete:\n"
            result_text += f"Dataset: {dataset_name} ({dataset_id})\n"
            result_text += f"Entries processed: {len(processed_entries)}\n"
            result_text += f"Total entries in dataset: {entries_result.get('pagination', {}).get('total', len(entries))}\n\n"
            result_text += "Ready for workflow analysis. Use Memgraph tools to create the graph."
            
            # Return both summary and data
            return CallToolResult(content=[
                TextContent(type="text", text=result_text),
                TextContent(type="text", text=f"ENTRY_DATA: {processed_entries}")
            ])
        
        elif name == "analyze_dataset_formulas":
            dataset_id = arguments["dataset_id"]
            group_by = arguments.get("group_by", "element")
            
            # Get dataset entries
            entries_result = await nomad_client.get_dataset_entries(dataset_id, max_entries=500)
            entries = entries_result.get("data", [])
            
            # Extract formulas
            formula_analysis = {}
            for entry in entries:
                formula = entry.get("results", {}).get("material", {}).get("chemical_formula_reduced", "")
                if not formula:
                    continue
                
                if group_by == "element":
                    # Extract elements from formula
                    import re
                    elements = re.findall(r'([A-Z][a-z]?)', formula)
                    for elem in elements:
                        if elem not in formula_analysis:
                            formula_analysis[elem] = []
                        formula_analysis[elem].append(formula)
                
                elif group_by == "size":
                    # Extract total atom count
                    import re
                    numbers = re.findall(r'(\d+)', formula)
                    size = sum(int(n) for n in numbers) if numbers else 1
                    size_key = f"size_{size}"
                    if size_key not in formula_analysis:
                        formula_analysis[size_key] = []
                    formula_analysis[size_key].append(formula)
                
                else:  # composition
                    if formula not in formula_analysis:
                        formula_analysis[formula] = 0
                    formula_analysis[formula] += 1
            
            # Format results
            analysis_text = f"Formula Analysis for Dataset {dataset_id}:\n"
            analysis_text += f"Grouped by: {group_by}\n\n"
            
            for key, value in sorted(formula_analysis.items()):
                if isinstance(value, list):
                    unique_formulas = list(set(value))
                    analysis_text += f"{key}: {len(value)} occurrences, {len(unique_formulas)} unique\n"
                    analysis_text += f"  Examples: {', '.join(unique_formulas[:5])}\n"
                else:
                    analysis_text += f"{key}: {value} entries\n"
            
            return CallToolResult(content=[TextContent(type="text", text=analysis_text)])
        
        elif name == "get_dataset_workflow_patterns":
            dataset_id = arguments["dataset_id"]
            pattern_type = arguments.get("pattern_type", "file_patterns")
            
            # Get sample entries to analyze patterns
            entries_result = await nomad_client.get_dataset_entries(dataset_id, max_entries=50)
            entries = entries_result.get("data", [])
            
            patterns = {}
            
            if pattern_type == "file_patterns":
                # Analyze file patterns across entries
                for entry in entries[:20]:  # Sample first 20
                    files_info = await nomad_client.get_entry_files_info(entry["entry_id"])
                    files = files_info.get("data", {}).get("archive", {}).get("data", {}).get("files", [])
                    
                    for file_path in files:
                        ext = file_path.split('.')[-1] if '.' in file_path else 'no_ext'
                        if ext not in patterns:
                            patterns[ext] = 0
                        patterns[ext] += 1
                
                pattern_text = "File Pattern Analysis:\n\n"
                for ext, count in sorted(patterns.items(), key=lambda x: x[1], reverse=True):
                    pattern_text += f".{ext}: {count} files\n"
            
            elif pattern_type == "method_patterns":
                # Analyze computational methods
                for entry in entries:
                    method = entry.get("results", {}).get("method", {}).get("method_name", "")
                    if method:
                        if method not in patterns:
                            patterns[method] = 0
                        patterns[method] += 1
                
                pattern_text = "Method Pattern Analysis:\n\n"
                for method, count in sorted(patterns.items(), key=lambda x: x[1], reverse=True):
                    pattern_text += f"{method}: {count} entries\n"
            
            else:  # parameter_studies
                # Group by formula to find parameter studies
                formula_groups = {}
                for entry in entries:
                    formula = entry.get("results", {}).get("material", {}).get("chemical_formula_reduced", "")
                    if formula:
                        if formula not in formula_groups:
                            formula_groups[formula] = []
                        formula_groups[formula].append(entry["entry_id"])
                
                pattern_text = "Parameter Study Patterns:\n\n"
                for formula, entry_ids in sorted(formula_groups.items(), key=lambda x: len(x[1]), reverse=True):
                    if len(entry_ids) > 1:
                        pattern_text += f"{formula}: {len(entry_ids)} calculations\n"
            
            return CallToolResult(content=[TextContent(type="text", text=pattern_text)])
        
        elif name == "get_entry_with_files":
            entry_id = arguments["entry_id"]
            file_patterns = arguments.get("file_patterns", [])
            
            # Get entry archive
            archive = await nomad_client.get_entry_archive(entry_id)
            
            # Get file list
            files_info = await nomad_client.get_entry_files_info(entry_id)
            files = files_info.get("data", {}).get("archive", {}).get("data", {}).get("files", [])
            
            # Filter files by patterns if specified
            if file_patterns:
                import fnmatch
                filtered_files = []
                for file_path in files:
                    for pattern in file_patterns:
                        if fnmatch.fnmatch(file_path, pattern):
                            filtered_files.append(file_path)
                            break
                files = filtered_files
            
            result_text = f"Entry {entry_id}:\n"
            result_text += f"Archive data available\n"
            result_text += f"Files ({len(files)}):\n"
            for f in files[:10]:  # Show first 10
                result_text += f"  - {f}\n"
            if len(files) > 10:
                result_text += f"  ... and {len(files) - 10} more files\n"
            
            # Note: Actual file content would need additional API calls
            result_text += "\nNote: Use NOMAD web interface or API to download actual file contents"
            
            return CallToolResult(content=[TextContent(type="text", text=result_text)])
        
        else:
            raise ValueError(f"Unknown tool: {name}")
    
    except Exception as e:
        return CallToolResult(content=[TextContent(type="text", text=f"Error: {str(e)}")], isError=True)

async def main():
    """Run the enhanced NOMAD MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())