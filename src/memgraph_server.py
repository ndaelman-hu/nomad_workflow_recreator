#!/usr/bin/env python3
"""
Memgraph MCP Server

Provides tools for interacting with Memgraph graph database via MCP.
"""

import asyncio
import os
from typing import Any, Dict, List, Optional
import mgclient
from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool, 
    TextContent, 
    CallToolRequest, 
    CallToolResult
)

load_dotenv()

class MemgraphClient:
    def __init__(self):
        self.host = os.getenv("MEMGRAPH_HOST", "localhost")
        self.port = int(os.getenv("MEMGRAPH_PORT", "7687"))
        self.username = os.getenv("MEMGRAPH_USERNAME", "")
        self.password = os.getenv("MEMGRAPH_PASSWORD", "")
        self.conn = None
    
    async def connect(self):
        """Establish connection to Memgraph"""
        try:
            self.conn = mgclient.connect(
                host=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                lazy=False
            )
            return True
        except Exception as e:
            print(f"Failed to connect to Memgraph: {e}")
            return False
    
    async def execute_query(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Execute a Cypher query and return results"""
        if not self.conn:
            await self.connect()
        
        cursor = self.conn.cursor()
        cursor.execute(query, parameters or {})
        
        results = []
        for record in cursor.fetchall():
            # Convert record to dictionary
            result = {}
            for i, value in enumerate(record):
                column_name = cursor.description[i][0] if cursor.description else f"col_{i}"
                if hasattr(value, '_properties'):
                    # Node or relationship
                    result[column_name] = {
                        'id': value.id if hasattr(value, 'id') else None,
                        'labels': list(value.labels) if hasattr(value, 'labels') else [],
                        'properties': dict(value.properties) if hasattr(value, 'properties') else {}
                    }
                else:
                    result[column_name] = value
            results.append(result)
        
        return results
    
    async def get_schema(self) -> Dict[str, Any]:
        """Get database schema information"""
        queries = {
            "node_labels": "CALL db.labels()",
            "relationship_types": "CALL db.relationshipTypes()",
            "property_keys": "CALL db.propertyKeys()"
        }
        
        schema = {}
        for key, query in queries.items():
            try:
                results = await self.execute_query(query)
                schema[key] = [list(record.values())[0] for record in results]
            except:
                schema[key] = []
        
        return schema
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

# Initialize Memgraph client
memgraph_client = MemgraphClient()

# Create MCP server
server = Server("memgraph-mcp-server")

@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available Memgraph tools"""
    return [
        Tool(
            name="memgraph_query",
            description="Execute a Cypher query on Memgraph database",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Cypher query to execute"
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Query parameters as key-value pairs"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="memgraph_create_node",
            description="Create a new node in the graph",
            inputSchema={
                "type": "object",
                "properties": {
                    "labels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Node labels"
                    },
                    "properties": {
                        "type": "object",
                        "description": "Node properties as key-value pairs"
                    }
                },
                "required": ["labels"]
            }
        ),
        Tool(
            name="memgraph_create_relationship",
            description="Create a relationship between two nodes",
            inputSchema={
                "type": "object",
                "properties": {
                    "from_node": {
                        "type": "object",
                        "properties": {
                            "labels": {"type": "array", "items": {"type": "string"}},
                            "properties": {"type": "object"}
                        },
                        "description": "Source node identifier"
                    },
                    "to_node": {
                        "type": "object",
                        "properties": {
                            "labels": {"type": "array", "items": {"type": "string"}},
                            "properties": {"type": "object"}
                        },
                        "description": "Target node identifier"
                    },
                    "relationship_type": {
                        "type": "string",
                        "description": "Type of relationship"
                    },
                    "properties": {
                        "type": "object",
                        "description": "Relationship properties"
                    }
                },
                "required": ["from_node", "to_node", "relationship_type"]
            }
        ),
        Tool(
            name="memgraph_find_nodes",
            description="Find nodes matching specified criteria",
            inputSchema={
                "type": "object",
                "properties": {
                    "labels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Node labels to match"
                    },
                    "properties": {
                        "type": "object",
                        "description": "Properties to match"
                    },
                    "limit": {
                        "type": "number",
                        "default": 10,
                        "description": "Maximum number of results"
                    }
                }
            }
        ),
        Tool(
            name="memgraph_get_schema",
            description="Get database schema information (labels, relationship types, properties)",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="memgraph_shortest_path",
            description="Find shortest path between two nodes",
            inputSchema={
                "type": "object",
                "properties": {
                    "from_node": {
                        "type": "object",
                        "properties": {
                            "labels": {"type": "array", "items": {"type": "string"}},
                            "properties": {"type": "object"}
                        },
                        "description": "Source node identifier"
                    },
                    "to_node": {
                        "type": "object",
                        "properties": {
                            "labels": {"type": "array", "items": {"type": "string"}},
                            "properties": {"type": "object"}
                        },
                        "description": "Target node identifier"
                    },
                    "max_depth": {
                        "type": "number",
                        "default": 10,
                        "description": "Maximum path depth"
                    }
                },
                "required": ["from_node", "to_node"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
    """Handle tool calls"""
    
    try:
        if name == "memgraph_query":
            query = arguments["query"]
            parameters = arguments.get("parameters", {})
            
            results = await memgraph_client.execute_query(query, parameters)
            
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Query executed successfully. Found {len(results)} results:\n\n" +
                             "\n".join([str(result) for result in results[:10]])  # Limit display
                    )
                ]
            )
        
        elif name == "memgraph_create_node":
            labels = arguments["labels"]
            properties = arguments.get("properties", {})
            
            # Build CREATE query
            labels_str = ":".join(labels)
            props_str = ", ".join([f"{k}: ${k}" for k in properties.keys()]) if properties else ""
            
            if props_str:
                query = f"CREATE (n:{labels_str} {{{props_str}}}) RETURN n"
            else:
                query = f"CREATE (n:{labels_str}) RETURN n"
            
            results = await memgraph_client.execute_query(query, properties)
            
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Node created successfully: {results[0] if results else 'No result returned'}"
                    )
                ]
            )
        
        elif name == "memgraph_create_relationship":
            from_node = arguments["from_node"]
            to_node = arguments["to_node"]
            rel_type = arguments["relationship_type"]
            rel_props = arguments.get("properties", {})
            
            # Build MATCH and CREATE query
            from_labels = ":".join(from_node.get("labels", []))
            to_labels = ":".join(to_node.get("labels", []))
            
            from_props = from_node.get("properties", {})
            to_props = to_node.get("properties", {})
            
            # Build WHERE conditions
            from_where = " AND ".join([f"from.{k} = ${f'from_{k}'}" for k in from_props.keys()])
            to_where = " AND ".join([f"to.{k} = ${f'to_{k}'}" for k in to_props.keys()])
            
            query = f"""
            MATCH (from:{from_labels}), (to:{to_labels})
            WHERE {from_where} AND {to_where}
            CREATE (from)-[r:{rel_type}]->(to)
            RETURN r
            """
            
            # Combine parameters
            params = {}
            for k, v in from_props.items():
                params[f"from_{k}"] = v
            for k, v in to_props.items():
                params[f"to_{k}"] = v
            params.update(rel_props)
            
            results = await memgraph_client.execute_query(query, params)
            
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Relationship created successfully: {results[0] if results else 'No result returned'}"
                    )
                ]
            )
        
        elif name == "memgraph_find_nodes":
            labels = arguments.get("labels", [])
            properties = arguments.get("properties", {})
            limit = arguments.get("limit", 10)
            
            # Build MATCH query
            labels_str = ":".join(labels) if labels else ""
            where_conditions = []
            
            if properties:
                where_conditions = [f"n.{k} = ${k}" for k in properties.keys()]
            
            where_clause = f"WHERE {' AND '.join(where_conditions)}" if where_conditions else ""
            
            query = f"MATCH (n{':' + labels_str if labels_str else ''}) {where_clause} RETURN n LIMIT {limit}"
            
            results = await memgraph_client.execute_query(query, properties)
            
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Found {len(results)} nodes:\n\n" +
                             "\n".join([str(result) for result in results])
                    )
                ]
            )
        
        elif name == "memgraph_get_schema":
            schema = await memgraph_client.get_schema()
            
            schema_text = "Database Schema:\n\n"
            schema_text += f"Node Labels: {', '.join(schema.get('node_labels', []))}\n"
            schema_text += f"Relationship Types: {', '.join(schema.get('relationship_types', []))}\n"
            schema_text += f"Property Keys: {', '.join(schema.get('property_keys', []))}"
            
            return CallToolResult(
                content=[
                    TextContent(type="text", text=schema_text)
                ]
            )
        
        elif name == "memgraph_shortest_path":
            from_node = arguments["from_node"]
            to_node = arguments["to_node"]
            max_depth = arguments.get("max_depth", 10)
            
            # Build shortest path query
            from_labels = ":".join(from_node.get("labels", []))
            to_labels = ":".join(to_node.get("labels", []))
            
            from_props = from_node.get("properties", {})
            to_props = to_node.get("properties", {})
            
            from_where = " AND ".join([f"from.{k} = ${f'from_{k}'}" for k in from_props.keys()])
            to_where = " AND ".join([f"to.{k} = ${f'to_{k}'}" for k in to_props.keys()])
            
            query = f"""
            MATCH (from:{from_labels}), (to:{to_labels})
            WHERE {from_where} AND {to_where}
            MATCH path = shortestPath((from)-[*..{max_depth}]-(to))
            RETURN path
            """
            
            params = {}
            for k, v in from_props.items():
                params[f"from_{k}"] = v
            for k, v in to_props.items():
                params[f"to_{k}"] = v
            
            results = await memgraph_client.execute_query(query, params)
            
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Shortest path found: {results[0] if results else 'No path found'}"
                    )
                ]
            )
        
        else:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unknown tool: {name}")]
            )
    
    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error executing {name}: {str(e)}")]
        )

async def main():
    """Main entry point for the Memgraph MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())