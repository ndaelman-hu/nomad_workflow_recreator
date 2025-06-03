#!/usr/bin/env python3
"""
Improved NOMAD MCP Server

Provides tools for accessing NOMAD materials science database via MCP
using proper API endpoints based on official documentation.
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

# Create MCP server
app = Server("nomad-server")

# Global client instance
nomad_client = NomadClient()

@app.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available NOMAD tools"""
    return [
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
        )
    ]

@app.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
    """Handle tool calls"""
    try:
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
        
        else:
            raise ValueError(f"Unknown tool: {name}")
    
    except Exception as e:
        return CallToolResult(content=[TextContent(type="text", text=f"Error: {str(e)}")], isError=True)

async def main():
    """Run the NOMAD MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())