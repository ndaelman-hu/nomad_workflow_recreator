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