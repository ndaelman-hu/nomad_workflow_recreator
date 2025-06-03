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
        ),
        Tool(
            name="memgraph_create_dataset_graph",
            description="Create a complete workflow graph from NOMAD dataset analysis",
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_id": {
                        "type": "string",
                        "description": "Unique identifier for the dataset"
                    },
                    "dataset_name": {
                        "type": "string",
                        "description": "Human-readable dataset name"
                    },
                    "entries": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "entry_id": {"type": "string"},
                                "entry_name": {"type": "string"},
                                "entry_type": {"type": "string"},
                                "formula": {"type": "string"},
                                "upload_name": {"type": "string"},
                                "workflow_metadata": {"type": "object"},
                                "file_structure": {"type": "object"}
                            }
                        },
                        "description": "List of entries with their metadata"
                    }
                },
                "required": ["dataset_id", "entries"]
            }
        ),
        Tool(
            name="memgraph_add_workflow_relationships",
            description="Add semantic relationships between workflow entries based on analysis",
            inputSchema={
                "type": "object",
                "properties": {
                    "relationships": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "from_entry_id": {"type": "string"},
                                "to_entry_id": {"type": "string"},
                                "relationship_type": {"type": "string"},
                                "properties": {"type": "object"}
                            }
                        },
                        "description": "List of relationships to create"
                    }
                },
                "required": ["relationships"]
            }
        ),
        Tool(
            name="memgraph_analyze_workflow_patterns",
            description="Analyze workflow patterns and dependencies in the graph",
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_id": {
                        "type": "string",
                        "description": "Dataset ID to analyze"
                    },
                    "analysis_type": {
                        "type": "string",
                        "enum": ["dependencies", "clusters", "paths", "summary"],
                        "default": "summary",
                        "description": "Type of analysis to perform"
                    }
                },
                "required": ["dataset_id"]
            }
        ),
        Tool(
            name="memgraph_find_workflow_entry_types",
            description="Find all entries of a specific type in workflow graphs",
            inputSchema={
                "type": "object",
                "properties": {
                    "entry_type": {
                        "type": "string",
                        "description": "Type of entry to find (e.g., 'calculation', 'geometry_optimization')"
                    },
                    "dataset_id": {
                        "type": "string",
                        "description": "Optional dataset ID to limit search"
                    }
                }
            }
        ),
        Tool(
            name="memgraph_trace_workflow",
            description="Trace the complete workflow from a starting entry",
            inputSchema={
                "type": "object",
                "properties": {
                    "entry_id": {
                        "type": "string",
                        "description": "Starting entry ID"
                    },
                    "direction": {
                        "type": "string",
                        "enum": ["forward", "backward", "both"],
                        "default": "both",
                        "description": "Direction to trace workflow"
                    },
                    "max_depth": {
                        "type": "number",
                        "default": 5,
                        "description": "Maximum depth to trace"
                    }
                },
                "required": ["entry_id"]
            }
        ),
        Tool(
            name="memgraph_store_file_data",
            description="Store raw file data from NOMAD entry in graph for AI analysis",
            inputSchema={
                "type": "object",
                "properties": {
                    "entry_id": {
                        "type": "string",
                        "description": "NOMAD entry ID"
                    },
                    "file_data": {
                        "type": "object",
                        "description": "Raw file data with metadata, input files, and script files"
                    }
                },
                "required": ["entry_id", "file_data"]
            }
        ),
        Tool(
            name="memgraph_add_file_content_nodes",
            description="Add file content as separate nodes connected to entry",
            inputSchema={
                "type": "object",
                "properties": {
                    "entry_id": {
                        "type": "string",
                        "description": "Parent entry ID"
                    },
                    "files": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "file_path": {"type": "string"},
                                "content": {"type": "string"},
                                "file_type": {"type": "string"},
                                "size": {"type": "number"}
                            }
                        },
                        "description": "List of files to add as nodes"
                    }
                },
                "required": ["entry_id", "files"]
            }
        ),
        Tool(
            name="memgraph_store_parsed_data",
            description="Store AI-parsed data (parameters, commands, etc.) as properties or separate nodes",
            inputSchema={
                "type": "object",
                "properties": {
                    "entry_id": {
                        "type": "string",
                        "description": "Entry ID"
                    },
                    "parsed_data": {
                        "type": "object",
                        "description": "AI-analyzed data to store"
                    },
                    "data_type": {
                        "type": "string",
                        "enum": ["parameters", "commands", "dependencies", "custom"],
                        "description": "Type of parsed data"
                    }
                },
                "required": ["entry_id", "parsed_data", "data_type"]
            }
        ),
        Tool(
            name="memgraph_query_file_patterns",
            description="Query files by patterns for AI analysis (find similar files, extensions, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern_type": {
                        "type": "string",
                        "enum": ["extension", "filename", "content_similarity", "size_range"],
                        "description": "Type of pattern to search for"
                    },
                    "pattern_value": {
                        "type": "string",
                        "description": "Pattern value (e.g., '.inp', 'INCAR', etc.)"
                    },
                    "dataset_id": {
                        "type": "string",
                        "description": "Optional dataset to limit search"
                    }
                },
                "required": ["pattern_type", "pattern_value"]
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
        
        elif name == "memgraph_create_dataset_graph":
            dataset_id = arguments["dataset_id"]
            dataset_name = arguments.get("dataset_name", dataset_id)
            entries = arguments["entries"]
            
            try:
                # Create dataset node
                dataset_query = """
                MERGE (d:Dataset {dataset_id: $dataset_id})
                SET d.name = $dataset_name, d.entry_count = $entry_count
                RETURN d
                """
                await memgraph_client.execute_query(dataset_query, {
                    "dataset_id": dataset_id,
                    "dataset_name": dataset_name,
                    "entry_count": len(entries)
                })
                
                # Create entry nodes
                nodes_created = 0
                for entry in entries:
                    entry_query = """
                    CREATE (e:Entry {
                        entry_id: $entry_id,
                        entry_name: $entry_name,
                        entry_type: $entry_type,
                        formula: $formula,
                        upload_name: $upload_name
                    })
                    WITH e
                    MATCH (d:Dataset {dataset_id: $dataset_id})
                    CREATE (d)-[:CONTAINS]->(e)
                    RETURN e
                    """
                    
                    await memgraph_client.execute_query(entry_query, {
                        "entry_id": entry.get("entry_id"),
                        "entry_name": entry.get("entry_name", ""),
                        "entry_type": entry.get("entry_type", "unknown"),
                        "formula": entry.get("formula", ""),
                        "upload_name": entry.get("upload_name", ""),
                        "dataset_id": dataset_id
                    })
                    nodes_created += 1
                
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=f"Created dataset graph for '{dataset_name}':\n"
                                 f"- 1 Dataset node\n"
                                 f"- {nodes_created} Entry nodes\n"
                                 f"- {nodes_created} CONTAINS relationships"
                        )
                    ]
                )
                
            except Exception as e:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error creating dataset graph: {str(e)}")]
                )
        
        elif name == "memgraph_add_workflow_relationships":
            relationships = arguments["relationships"]
            
            try:
                relationships_created = 0
                for rel in relationships:
                    rel_query = """
                    MATCH (from:Entry {entry_id: $from_id})
                    MATCH (to:Entry {entry_id: $to_id})
                    CREATE (from)-[r:`{rel_type}`]->(to)
                    SET r += $properties
                    RETURN r
                    """.format(rel_type=rel["relationship_type"])
                    
                    await memgraph_client.execute_query(rel_query, {
                        "from_id": rel["from_entry_id"],
                        "to_id": rel["to_entry_id"],
                        "properties": rel.get("properties", {})
                    })
                    relationships_created += 1
                
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=f"Created {relationships_created} workflow relationships"
                        )
                    ]
                )
                
            except Exception as e:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error creating relationships: {str(e)}")]
                )
        
        elif name == "memgraph_analyze_workflow_patterns":
            dataset_id = arguments["dataset_id"]
            analysis_type = arguments.get("analysis_type", "summary")
            
            try:
                if analysis_type == "summary":
                    summary_query = """
                    MATCH (d:Dataset {dataset_id: $dataset_id})-[:CONTAINS]->(e:Entry)
                    WITH d, collect(e.entry_type) as types, count(e) as entry_count
                    MATCH (e1:Entry)-[r]->(e2:Entry)
                    WHERE e1.entry_id STARTS WITH $dataset_id OR e2.entry_id STARTS WITH $dataset_id
                    RETURN d.name as dataset_name, entry_count, 
                           size(apoc.coll.toSet(types)) as unique_types,
                           type(r) as rel_type, count(r) as rel_count
                    """
                    
                elif analysis_type == "dependencies":
                    summary_query = """
                    MATCH (d:Dataset {dataset_id: $dataset_id})-[:CONTAINS]->(e:Entry)
                    MATCH (e)-[r]->(dependent:Entry)
                    RETURN e.entry_id as entry, dependent.entry_id as depends_on, 
                           type(r) as relationship, e.entry_type as entry_type
                    LIMIT 20
                    """
                    
                elif analysis_type == "clusters":
                    summary_query = """
                    MATCH (d:Dataset {dataset_id: $dataset_id})-[:CONTAINS]->(e:Entry)
                    WHERE e.upload_name IS NOT NULL
                    WITH e.upload_name as cluster, collect(e.entry_id) as entries
                    RETURN cluster, size(entries) as cluster_size, entries[0..5] as sample_entries
                    ORDER BY cluster_size DESC
                    """
                    
                results = await memgraph_client.execute_query(summary_query, {"dataset_id": dataset_id})
                
                analysis_text = f"Workflow Analysis ({analysis_type}):\n\n"
                for result in results[:10]:  # Limit results
                    analysis_text += f"{result}\n"
                
                return CallToolResult(
                    content=[
                        TextContent(type="text", text=analysis_text)
                    ]
                )
                
            except Exception as e:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error analyzing workflow patterns: {str(e)}")]
                )
        
        elif name == "memgraph_find_workflow_entry_types":
            entry_type = arguments["entry_type"]
            dataset_id = arguments.get("dataset_id")
            
            try:
                if dataset_id:
                    query = """
                    MATCH (d:Dataset {dataset_id: $dataset_id})-[:CONTAINS]->(e:Entry)
                    WHERE e.entry_type = $entry_type
                    RETURN e.entry_id, e.entry_name, e.formula, e.upload_name
                    LIMIT 20
                    """
                    params = {"entry_type": entry_type, "dataset_id": dataset_id}
                else:
                    query = """
                    MATCH (e:Entry)
                    WHERE e.entry_type = $entry_type
                    RETURN e.entry_id, e.entry_name, e.formula, e.upload_name
                    LIMIT 20
                    """
                    params = {"entry_type": entry_type}
                
                results = await memgraph_client.execute_query(query, params)
                
                result_text = f"Found {len(results)} entries of type '{entry_type}':\n\n"
                for result in results:
                    result_text += f"- {result.get('e.entry_id')}: {result.get('e.entry_name')} ({result.get('e.formula')})\n"
                
                return CallToolResult(
                    content=[
                        TextContent(type="text", text=result_text)
                    ]
                )
                
            except Exception as e:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error finding entry types: {str(e)}")]
                )
        
        elif name == "memgraph_trace_workflow":
            entry_id = arguments["entry_id"]
            direction = arguments.get("direction", "both")
            max_depth = arguments.get("max_depth", 5)
            
            try:
                if direction == "forward":
                    query = f"""
                    MATCH path = (start:Entry {{entry_id: $entry_id}})-[*1..{max_depth}]->(end:Entry)
                    RETURN path
                    LIMIT 10
                    """
                elif direction == "backward":
                    query = f"""
                    MATCH path = (start:Entry)-[*1..{max_depth}]->(end:Entry {{entry_id: $entry_id}})
                    RETURN path
                    LIMIT 10
                    """
                else:  # both
                    query = f"""
                    MATCH path = (start:Entry)-[*1..{max_depth}]-(end:Entry)
                    WHERE start.entry_id = $entry_id OR end.entry_id = $entry_id
                    RETURN path
                    LIMIT 10
                    """
                
                results = await memgraph_client.execute_query(query, {"entry_id": entry_id})
                
                trace_text = f"Workflow trace from entry {entry_id} ({direction}):\n\n"
                trace_text += f"Found {len(results)} workflow paths\n"
                
                # Simplified path display
                for i, result in enumerate(results[:5]):
                    trace_text += f"Path {i+1}: {result}\n"
                
                return CallToolResult(
                    content=[
                        TextContent(type="text", text=trace_text)
                    ]
                )
                
            except Exception as e:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error tracing workflow: {str(e)}")]
                )
        
        elif name == "memgraph_store_file_data":
            entry_id = arguments["entry_id"]
            file_data = arguments["file_data"]
            
            try:
                # Store file metadata as properties on the entry
                file_metadata = file_data.get("file_metadata", {})
                if file_metadata:
                    metadata_query = """
                    MATCH (e:Entry {entry_id: $entry_id})
                    SET e.file_count = $file_count,
                        e.file_extensions = $extensions,
                        e.total_file_size = $total_size
                    RETURN e
                    """
                    
                    extensions = list(set([meta.get("extension", "") for meta in file_metadata.values() if meta.get("extension")]))
                    total_size = sum([meta.get("size", 0) for meta in file_metadata.values()])
                    
                    await memgraph_client.execute_query(metadata_query, {
                        "entry_id": entry_id,
                        "file_count": len(file_metadata),
                        "extensions": extensions,
                        "total_size": total_size
                    })
                
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=f"Stored file metadata for entry {entry_id}: {len(file_metadata)} files, extensions: {extensions}"
                        )
                    ]
                )
                
            except Exception as e:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error storing file data: {str(e)}")]
                )
        
        elif name == "memgraph_add_file_content_nodes":
            entry_id = arguments["entry_id"]
            files = arguments["files"]
            
            try:
                nodes_created = 0
                for file_info in files:
                    file_query = """
                    MATCH (e:Entry {entry_id: $entry_id})
                    CREATE (f:File {
                        file_path: $file_path,
                        content: $content,
                        file_type: $file_type,
                        size: $size,
                        filename: $filename,
                        extension: $extension
                    })
                    CREATE (e)-[:HAS_FILE]->(f)
                    RETURN f
                    """
                    
                    file_path = file_info.get("file_path", "")
                    await memgraph_client.execute_query(file_query, {
                        "entry_id": entry_id,
                        "file_path": file_path,
                        "content": file_info.get("content", ""),
                        "file_type": file_info.get("file_type", "unknown"),
                        "size": file_info.get("size", 0),
                        "filename": file_path.split('/')[-1] if '/' in file_path else file_path,
                        "extension": file_path.split('.')[-1].lower() if '.' in file_path else ""
                    })
                    nodes_created += 1
                
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=f"Created {nodes_created} file nodes for entry {entry_id}"
                        )
                    ]
                )
                
            except Exception as e:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error creating file nodes: {str(e)}")]
                )
        
        elif name == "memgraph_store_parsed_data":
            entry_id = arguments["entry_id"]
            parsed_data = arguments["parsed_data"]
            data_type = arguments["data_type"]
            
            try:
                if data_type == "parameters":
                    # Store as parameter nodes
                    for param_name, param_value in parsed_data.items():
                        param_query = """
                        MATCH (e:Entry {entry_id: $entry_id})
                        CREATE (p:Parameter {
                            name: $param_name,
                            value: $param_value,
                            data_type: 'parameter'
                        })
                        CREATE (e)-[:HAS_PARAMETER]->(p)
                        RETURN p
                        """
                        await memgraph_client.execute_query(param_query, {
                            "entry_id": entry_id,
                            "param_name": str(param_name),
                            "param_value": str(param_value)
                        })
                
                elif data_type == "commands":
                    # Store as command nodes
                    for i, command in enumerate(parsed_data.get("commands", [])):
                        cmd_query = """
                        MATCH (e:Entry {entry_id: $entry_id})
                        CREATE (c:Command {
                            command_text: $command_text,
                            line_number: $line_number,
                            sequence: $sequence
                        })
                        CREATE (e)-[:HAS_COMMAND]->(c)
                        RETURN c
                        """
                        await memgraph_client.execute_query(cmd_query, {
                            "entry_id": entry_id,
                            "command_text": str(command),
                            "line_number": 0,  # AI can provide this
                            "sequence": i
                        })
                
                elif data_type == "dependencies":
                    # Store as dependency relationships
                    for dependency in parsed_data.get("dependencies", []):
                        dep_query = """
                        MATCH (e:Entry {entry_id: $entry_id})
                        CREATE (d:Dependency {
                            dependency_info: $dep_info,
                            dependency_type: $dep_type
                        })
                        CREATE (e)-[:HAS_DEPENDENCY]->(d)
                        RETURN d
                        """
                        await memgraph_client.execute_query(dep_query, {
                            "entry_id": entry_id,
                            "dep_info": str(dependency),
                            "dep_type": "file_dependency"
                        })
                
                else:  # custom
                    # Store as generic data nodes
                    custom_query = """
                    MATCH (e:Entry {entry_id: $entry_id})
                    CREATE (d:Data {
                        data_content: $data_content,
                        data_type: $data_type
                    })
                    CREATE (e)-[:HAS_DATA]->(d)
                    RETURN d
                    """
                    await memgraph_client.execute_query(custom_query, {
                        "entry_id": entry_id,
                        "data_content": str(parsed_data),
                        "data_type": data_type
                    })
                
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=f"Stored {data_type} data for entry {entry_id}"
                        )
                    ]
                )
                
            except Exception as e:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error storing parsed data: {str(e)}")]
                )
        
        elif name == "memgraph_query_file_patterns":
            pattern_type = arguments["pattern_type"]
            pattern_value = arguments["pattern_value"]
            dataset_id = arguments.get("dataset_id")
            
            try:
                if pattern_type == "extension":
                    if dataset_id:
                        query = """
                        MATCH (d:Dataset {dataset_id: $dataset_id})-[:CONTAINS]->(e:Entry)-[:HAS_FILE]->(f:File)
                        WHERE f.extension = $pattern_value
                        RETURN e.entry_id, f.file_path, f.filename, f.size
                        LIMIT 20
                        """
                        params = {"dataset_id": dataset_id, "pattern_value": pattern_value}
                    else:
                        query = """
                        MATCH (e:Entry)-[:HAS_FILE]->(f:File)
                        WHERE f.extension = $pattern_value
                        RETURN e.entry_id, f.file_path, f.filename, f.size
                        LIMIT 20
                        """
                        params = {"pattern_value": pattern_value}
                
                elif pattern_type == "filename":
                    query = """
                    MATCH (e:Entry)-[:HAS_FILE]->(f:File)
                    WHERE f.filename CONTAINS $pattern_value
                    RETURN e.entry_id, f.file_path, f.filename, f.size
                    LIMIT 20
                    """
                    params = {"pattern_value": pattern_value}
                
                elif pattern_type == "size_range":
                    # Assume pattern_value is like "1000-5000" for size range
                    min_size, max_size = map(int, pattern_value.split('-'))
                    query = """
                    MATCH (e:Entry)-[:HAS_FILE]->(f:File)
                    WHERE f.size >= $min_size AND f.size <= $max_size
                    RETURN e.entry_id, f.file_path, f.filename, f.size
                    LIMIT 20
                    """
                    params = {"min_size": min_size, "max_size": max_size}
                
                else:
                    return CallToolResult(
                        content=[TextContent(type="text", text=f"Pattern type '{pattern_type}' not yet implemented")]
                    )
                
                results = await memgraph_client.execute_query(query, params)
                
                result_text = f"Files matching {pattern_type} pattern '{pattern_value}':\n\n"
                for result in results:
                    result_text += f"- {result.get('e.entry_id')}: {result.get('f.file_path')} ({result.get('f.size', 0)} bytes)\n"
                
                if not results:
                    result_text += "No matching files found."
                
                return CallToolResult(
                    content=[TextContent(type="text", text=result_text)]
                )
                
            except Exception as e:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error querying file patterns: {str(e)}")]
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