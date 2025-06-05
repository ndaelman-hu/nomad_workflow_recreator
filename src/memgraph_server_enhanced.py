#!/usr/bin/env python3
"""
Enhanced Memgraph MCP Server

Provides tools for interacting with Memgraph graph database via MCP,
including advanced analysis tools and dataset initialization.
"""

import asyncio
import os
import sys
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

# Add parent directory to path to import analysis tools
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
            # Enable autocommit to ensure transactions are committed
            self.conn.autocommit = True
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
                # Fix: Access column name via .name attribute instead of subscription
                column_name = cursor.description[i].name if cursor.description and len(cursor.description) > i else f"col_{i}"
                if hasattr(value, 'properties'):
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
server = Server("memgraph-mcp-server-enhanced")

@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available Memgraph tools"""
    return [
        # Original database tools
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
        
        # Analysis tools
        Tool(
            name="memgraph_analyze_periodic_trends",
            description="Analyze and create PERIODIC_TREND relationships based on periodic table groups",
            inputSchema={
                "type": "object",
                "properties": {
                    "create_relationships": {
                        "type": "boolean",
                        "default": False,
                        "description": "Whether to create the relationships or just analyze"
                    },
                    "group_filter": {
                        "type": "string",
                        "description": "Filter to specific group (e.g., 'alkali_metals', 'halogens')"
                    }
                }
            }
        ),
        Tool(
            name="memgraph_analyze_cluster_patterns",
            description="Find and analyze cluster size variations and create CLUSTER_SIZE_SERIES relationships",
            inputSchema={
                "type": "object",
                "properties": {
                    "element": {
                        "type": "string",
                        "description": "Specific element to analyze (e.g., 'C', 'Si')"
                    },
                    "create_relationships": {
                        "type": "boolean",
                        "default": False,
                        "description": "Whether to create the relationships"
                    },
                    "min_confidence": {
                        "type": "number",
                        "default": 0.8,
                        "description": "Minimum confidence score for relationships"
                    }
                }
            }
        ),
        Tool(
            name="memgraph_quick_analysis",
            description="Run predefined analysis queries for common patterns",
            inputSchema={
                "type": "object",
                "properties": {
                    "analysis_type": {
                        "type": "string",
                        "enum": ["formulas", "relationships", "periodic_trends", "clusters", "summary"],
                        "description": "Type of quick analysis to run"
                    },
                    "limit": {
                        "type": "number",
                        "default": 20,
                        "description": "Maximum results to return"
                    }
                }
            }
        ),
        Tool(
            name="memgraph_interactive_explore",
            description="Interactive exploration of the dataset with various options",
            inputSchema={
                "type": "object",
                "properties": {
                    "explore_type": {
                        "type": "string",
                        "enum": ["dataset_summary", "formula_details", "entry_comparison", "relationship_explorer"],
                        "description": "Type of exploration"
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Additional parameters for the exploration"
                    }
                }
            }
        ),
        Tool(
            name="memgraph_query_graph_export",
            description="Export graph data in various formats for analysis",
            inputSchema={
                "type": "object",
                "properties": {
                    "export_format": {
                        "type": "string",
                        "enum": ["cypher", "json", "summary"],
                        "default": "summary",
                        "description": "Format for export"
                    },
                    "include_relationships": {
                        "type": "boolean",
                        "default": True,
                        "description": "Include relationships in export"
                    }
                }
            }
        ),
        
        # Dataset initialization tools
        Tool(
            name="memgraph_clear_dataset",
            description="Clear existing dataset from the database",
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_id": {
                        "type": "string",
                        "description": "Dataset ID to clear (or 'all' for everything)"
                    },
                    "confirm": {
                        "type": "boolean",
                        "description": "Confirm the deletion"
                    }
                },
                "required": ["dataset_id", "confirm"]
            }
        ),
        Tool(
            name="memgraph_initialize_indexes",
            description="Create database indexes for optimal performance",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="memgraph_get_dataset_stats",
            description="Get detailed statistics about datasets in the database",
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_id": {
                        "type": "string",
                        "description": "Specific dataset ID or 'all'"
                    }
                }
            }
        ),
        Tool(
            name="memgraph_get_reasoning_patterns",
            description="Get existing reasoning patterns from relationships to maintain consistency",
            inputSchema={
                "type": "object",
                "properties": {
                    "relationship_type": {
                        "type": "string",
                        "description": "Filter by specific relationship type (optional)"
                    },
                    "include_examples": {
                        "type": "boolean",
                        "default": True,
                        "description": "Include example relationships with each reasoning pattern"
                    },
                    "min_confidence": {
                        "type": "number",
                        "default": 0.0,
                        "description": "Minimum confidence threshold"
                    }
                }
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
    """Handle tool calls"""
    
    try:
        # Original database tools (keep existing implementations)
        if name in ["memgraph_query", "memgraph_create_node", "memgraph_create_relationship", 
                    "memgraph_find_nodes", "memgraph_get_schema", "memgraph_shortest_path"]:
            # Use existing implementations from original file
            # (Copy the implementations from the original memgraph_server.py)
            pass
        
        # Analysis tools
        elif name == "memgraph_analyze_periodic_trends":
            create_rels = arguments.get("create_relationships", False)
            group_filter = arguments.get("group_filter")
            
            # Define periodic groups
            periodic_groups = {
                "alkali_metals": ["Li", "Na", "K", "Rb", "Cs"],
                "alkaline_earth": ["Be", "Mg", "Ca", "Sr", "Ba"],
                "transition_metals": ["Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn"],
                "halogens": ["F", "Cl", "Br", "I"],
                "noble_gases": ["He", "Ne", "Ar", "Kr", "Xe", "Rn"],
                "pnictogens": ["N", "P", "As", "Sb", "Bi"],
                "chalcogens": ["O", "S", "Se", "Te", "Po"]
            }
            
            results_text = "Periodic Trend Analysis:\n\n"
            relationships_created = 0
            
            for group_name, elements in periodic_groups.items():
                if group_filter and group_name != group_filter:
                    continue
                
                # Find entries for this group
                group_query = """
                MATCH (e:Entry)
                WHERE any(elem IN $elements WHERE e.formula CONTAINS elem)
                RETURN e.entry_id, e.formula
                ORDER BY e.formula
                """
                
                entries = await memgraph_client.execute_query(group_query, {"elements": elements})
                
                if entries:
                    results_text += f"{group_name.replace('_', ' ').title()}:\n"
                    for entry in entries[:5]:  # Limit display
                        results_text += f"  - {entry['e.formula']} ({entry['e.entry_id']})\n"
                    
                    if create_rels:
                        # Create relationships within group
                        for i in range(len(entries) - 1):
                            rel_query = """
                            MATCH (e1:Entry {entry_id: $id1})
                            MATCH (e2:Entry {entry_id: $id2})
                            MERGE (e1)-[r:PERIODIC_TREND {
                                group: $group, 
                                confidence: 0.9,
                                reasoning: $reasoning
                            }]->(e2)
                            RETURN r
                            """
                            reasoning = f"Both {entries[i]['e.formula']} and {entries[i+1]['e.formula']} are {group_name.replace('_', ' ')} showing similar chemical properties and periodic trends"
                            await memgraph_client.execute_query(rel_query, {
                                "id1": entries[i]['e.entry_id'],
                                "id2": entries[i+1]['e.entry_id'],
                                "group": group_name,
                                "reasoning": reasoning
                            })
                            relationships_created += 1
                    
                    results_text += "\n"
            
            if create_rels:
                results_text += f"\nCreated {relationships_created} PERIODIC_TREND relationships"
            
            return CallToolResult(
                content=[TextContent(type="text", text=results_text)]
            )
        
        elif name == "memgraph_analyze_cluster_patterns":
            element = arguments.get("element")
            create_rels = arguments.get("create_relationships", False)
            min_confidence = arguments.get("min_confidence", 0.8)
            
            # Find cluster variations
            if element:
                cluster_query = """
                MATCH (e:Entry)
                WHERE e.formula =~ $pattern
                RETURN e.entry_id, e.formula
                ORDER BY e.formula
                """
                pattern = f"^{element}[0-9]+$"
            else:
                cluster_query = """
                MATCH (e:Entry)
                WHERE e.formula =~ '^[A-Z][a-z]?[0-9]+$'
                RETURN e.entry_id, e.formula
                ORDER BY e.formula
                LIMIT 100
                """
                pattern = None
            
            entries = await memgraph_client.execute_query(
                cluster_query, 
                {"pattern": pattern} if pattern else {}
            )
            
            # Group by element
            element_clusters = {}
            for entry in entries:
                formula = entry['e.formula']
                # Extract element and size
                import re
                match = re.match(r'^([A-Z][a-z]?)([0-9]+)$', formula)
                if match:
                    elem, size = match.groups()
                    if elem not in element_clusters:
                        element_clusters[elem] = []
                    element_clusters[elem].append({
                        'entry_id': entry['e.entry_id'],
                        'formula': formula,
                        'size': int(size)
                    })
            
            results_text = "Cluster Pattern Analysis:\n\n"
            relationships_created = 0
            
            for elem, clusters in element_clusters.items():
                if len(clusters) > 1:
                    results_text += f"{elem} clusters:\n"
                    # Sort by size
                    clusters.sort(key=lambda x: x['size'])
                    
                    for cluster in clusters[:10]:  # Limit display
                        results_text += f"  - {cluster['formula']} (size: {cluster['size']})\n"
                    
                    if create_rels:
                        # Create size series relationships
                        for i in range(len(clusters) - 1):
                            if clusters[i+1]['size'] > clusters[i]['size']:
                                confidence = min(1.0, 0.7 + 0.3 * (1.0 / (clusters[i+1]['size'] - clusters[i]['size'])))
                                if confidence >= min_confidence:
                                    rel_query = """
                                    MATCH (e1:Entry {entry_id: $id1})
                                    MATCH (e2:Entry {entry_id: $id2})
                                    MERGE (e1)-[r:CLUSTER_SIZE_SERIES {
                                        size_from: $size1, 
                                        size_to: $size2,
                                        confidence: $conf,
                                        reasoning: $reasoning
                                    }]->(e2)
                                    RETURN r
                                    """
                                    reasoning = f"Cluster size progression from {clusters[i]['formula']} ({clusters[i]['size']} atoms) to {clusters[i+1]['formula']} ({clusters[i+1]['size']} atoms) represents systematic size scaling for {elem} clusters"
                                    await memgraph_client.execute_query(rel_query, {
                                        "id1": clusters[i]['entry_id'],
                                        "id2": clusters[i+1]['entry_id'],
                                        "size1": clusters[i]['size'],
                                        "size2": clusters[i+1]['size'],
                                        "conf": confidence,
                                        "reasoning": reasoning
                                    })
                                    relationships_created += 1
                    
                    results_text += "\n"
            
            if create_rels:
                results_text += f"\nCreated {relationships_created} CLUSTER_SIZE_SERIES relationships"
            
            return CallToolResult(
                content=[TextContent(type="text", text=results_text)]
            )
        
        elif name == "memgraph_quick_analysis":
            analysis_type = arguments.get("analysis_type", "summary")
            limit = arguments.get("limit", 20)
            
            queries = {
                "formulas": """
                    MATCH (e:Entry)
                    WITH e.formula as formula, COUNT(e) as count
                    RETURN formula, count
                    ORDER BY count DESC, formula
                    LIMIT $limit
                """,
                "relationships": """
                    MATCH ()-[r]->()
                    WITH type(r) as rel_type, COUNT(r) as count
                    RETURN rel_type, count
                    ORDER BY count DESC
                    LIMIT $limit
                """,
                "periodic_trends": """
                    MATCH (e1:Entry)-[r:PERIODIC_TREND]->(e2:Entry)
                    RETURN e1.formula, e2.formula, r.group, r.confidence
                    ORDER BY r.group, e1.formula
                    LIMIT $limit
                """,
                "clusters": """
                    MATCH (e1:Entry)-[r:CLUSTER_SIZE_SERIES]->(e2:Entry)
                    RETURN e1.formula, e2.formula, r.size_from, r.size_to, r.confidence
                    ORDER BY e1.formula
                    LIMIT $limit
                """,
                "summary": """
                    MATCH (n)
                    WITH labels(n) as node_labels, COUNT(n) as count
                    RETURN node_labels, count
                    ORDER BY count DESC
                """
            }
            
            query = queries.get(analysis_type, queries["summary"])
            results = await memgraph_client.execute_query(query, {"limit": limit})
            
            results_text = f"Quick Analysis - {analysis_type}:\n\n"
            for result in results:
                results_text += f"{result}\n"
            
            return CallToolResult(
                content=[TextContent(type="text", text=results_text)]
            )
        
        elif name == "memgraph_interactive_explore":
            explore_type = arguments["explore_type"]
            params = arguments.get("parameters", {})
            
            if explore_type == "dataset_summary":
                summary_query = """
                MATCH (d:Dataset)
                OPTIONAL MATCH (d)-[:CONTAINS]->(e:Entry)
                WITH d, COUNT(e) as entry_count, COLLECT(DISTINCT e.entry_type) as types
                RETURN d.dataset_id, d.name, entry_count, types
                """
                results = await memgraph_client.execute_query(summary_query)
                
                summary_text = "Dataset Summary:\n\n"
                for dataset in results:
                    summary_text += f"Dataset: {dataset['d.name']} ({dataset['d.dataset_id']})\n"
                    summary_text += f"  Entries: {dataset['entry_count']}\n"
                    summary_text += f"  Types: {', '.join(dataset['types']) if dataset['types'] else 'None'}\n\n"
                
                return CallToolResult(
                    content=[TextContent(type="text", text=summary_text)]
                )
            
            elif explore_type == "formula_details":
                formula = params.get("formula", "C2")
                detail_query = """
                MATCH (e:Entry {formula: $formula})
                OPTIONAL MATCH (e)-[r]-()
                WITH e, type(r) as rel_type, COUNT(r) as rel_count
                RETURN e.entry_id, e.entry_name, e.entry_type, rel_type, rel_count
                """
                results = await memgraph_client.execute_query(detail_query, {"formula": formula})
                
                detail_text = f"Formula Details for {formula}:\n\n"
                for result in results:
                    detail_text += f"Entry: {result['e.entry_id']}\n"
                    detail_text += f"  Name: {result['e.entry_name']}\n"
                    detail_text += f"  Type: {result['e.entry_type']}\n"
                    if result['rel_type']:
                        detail_text += f"  {result['rel_type']}: {result['rel_count']} connections\n"
                    detail_text += "\n"
                
                return CallToolResult(
                    content=[TextContent(type="text", text=detail_text)]
                )
            
            else:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Explore type '{explore_type}' not implemented")]
                )
        
        elif name == "memgraph_query_graph_export":
            export_format = arguments.get("export_format", "summary")
            include_rels = arguments.get("include_relationships", True)
            
            if export_format == "summary":
                # Get graph statistics
                stats_query = """
                MATCH (n)
                WITH labels(n) as labels, COUNT(n) as node_count
                RETURN 'Nodes' as type, labels, node_count
                UNION ALL
                MATCH ()-[r]->()
                WITH type(r) as rel_type, COUNT(r) as rel_count
                RETURN 'Relationships' as type, [rel_type] as labels, rel_count
                """
                results = await memgraph_client.execute_query(stats_query)
                
                export_text = "Graph Export Summary:\n\n"
                nodes_section = "Nodes:\n"
                rels_section = "\nRelationships:\n"
                
                for result in results:
                    if result['type'] == 'Nodes':
                        nodes_section += f"  {result['labels']}: {result['node_count']}\n"
                    else:
                        rels_section += f"  {result['labels'][0]}: {result['rel_count']}\n"
                
                export_text += nodes_section + rels_section
                
                return CallToolResult(
                    content=[TextContent(type="text", text=export_text)]
                )
            
            else:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Export format '{export_format}' not implemented")]
                )
        
        # Dataset initialization tools
        elif name == "memgraph_clear_dataset":
            dataset_id = arguments["dataset_id"]
            confirm = arguments["confirm"]
            
            if not confirm:
                return CallToolResult(
                    content=[TextContent(type="text", text="Deletion cancelled - confirmation required")]
                )
            
            if dataset_id == "all":
                # Clear everything
                clear_query = "MATCH (n) DETACH DELETE n"
                await memgraph_client.execute_query(clear_query)
                result_text = "Cleared entire database"
            else:
                # Clear specific dataset
                clear_query = """
                MATCH (d:Dataset {dataset_id: $dataset_id})
                OPTIONAL MATCH (d)-[:CONTAINS]->(e:Entry)
                OPTIONAL MATCH (e)-[r]-()
                DETACH DELETE d, e
                """
                await memgraph_client.execute_query(clear_query, {"dataset_id": dataset_id})
                result_text = f"Cleared dataset: {dataset_id}"
            
            return CallToolResult(
                content=[TextContent(type="text", text=result_text)]
            )
        
        elif name == "memgraph_initialize_indexes":
            # Create indexes for better performance
            indexes = [
                "CREATE INDEX ON :Entry(entry_id)",
                "CREATE INDEX ON :Entry(formula)",
                "CREATE INDEX ON :Entry(entry_type)",
                "CREATE INDEX ON :Dataset(dataset_id)",
                "CREATE INDEX ON :File(file_path)",
                "CREATE INDEX ON :Parameter(name)"
            ]
            
            created = 0
            for index_query in indexes:
                try:
                    await memgraph_client.execute_query(index_query)
                    created += 1
                except Exception as e:
                    # Index might already exist
                    pass
            
            return CallToolResult(
                content=[TextContent(type="text", text=f"Created {created} indexes")]
            )
        
        elif name == "memgraph_get_dataset_stats":
            dataset_id = arguments.get("dataset_id", "all")
            
            if dataset_id == "all":
                stats_query = """
                MATCH (d:Dataset)
                OPTIONAL MATCH (d)-[:CONTAINS]->(e:Entry)
                WITH d, COUNT(DISTINCT e) as entries, 
                     COUNT(DISTINCT e.formula) as unique_formulas,
                     COLLECT(DISTINCT e.entry_type) as entry_types
                RETURN d.dataset_id as id, d.name as name, entries, 
                       unique_formulas, entry_types
                """
                params = {}
            else:
                stats_query = """
                MATCH (d:Dataset {dataset_id: $dataset_id})
                OPTIONAL MATCH (d)-[:CONTAINS]->(e:Entry)
                OPTIONAL MATCH (e)-[r]-()
                WITH d, COUNT(DISTINCT e) as entries, 
                     COUNT(DISTINCT e.formula) as unique_formulas,
                     COUNT(r) as relationships,
                     COLLECT(DISTINCT e.entry_type) as entry_types,
                     COLLECT(DISTINCT type(r)) as rel_types
                RETURN d.dataset_id as id, d.name as name, entries, 
                       unique_formulas, relationships, entry_types, rel_types
                """
                params = {"dataset_id": dataset_id}
            
            results = await memgraph_client.execute_query(stats_query, params)
            
            stats_text = "Dataset Statistics:\n\n"
            for stat in results:
                stats_text += f"Dataset: {stat['name']} ({stat['id']})\n"
                stats_text += f"  Total entries: {stat['entries']}\n"
                stats_text += f"  Unique formulas: {stat['unique_formulas']}\n"
                if 'relationships' in stat:
                    stats_text += f"  Relationships: {stat['relationships']}\n"
                stats_text += f"  Entry types: {', '.join(stat['entry_types']) if stat['entry_types'] else 'None'}\n"
                if 'rel_types' in stat and stat['rel_types']:
                    stats_text += f"  Relationship types: {', '.join([r for r in stat['rel_types'] if r])}\n"
                stats_text += "\n"
            
            return CallToolResult(
                content=[TextContent(type="text", text=stats_text)]
            )
        
        elif name == "memgraph_get_reasoning_patterns":
            relationship_type = arguments.get("relationship_type")
            include_examples = arguments.get("include_examples", True)
            min_confidence = arguments.get("min_confidence", 0.0)
            
            try:
                # Query to get reasoning patterns
                if relationship_type:
                    reasoning_query = """
                    MATCH (e1:Entry)-[r:`{rel_type}`]->(e2:Entry)
                    WHERE r.reasoning IS NOT NULL AND r.reasoning <> '' 
                    AND (r.confidence IS NULL OR r.confidence >= $min_conf)
                    WITH r.reasoning as reasoning, type(r) as rel_type, 
                         COUNT(r) as usage_count, AVG(r.confidence) as avg_confidence,
                         COLLECT({from: e1.formula, to: e2.formula, confidence: r.confidence})[0..3] as examples
                    RETURN reasoning, rel_type, usage_count, avg_confidence, examples
                    ORDER BY usage_count DESC
                    """.format(rel_type=relationship_type)
                else:
                    reasoning_query = """
                    MATCH (e1:Entry)-[r]->(e2:Entry)
                    WHERE r.reasoning IS NOT NULL AND r.reasoning <> ''
                    AND (r.confidence IS NULL OR r.confidence >= $min_conf)
                    WITH r.reasoning as reasoning, type(r) as rel_type, 
                         COUNT(r) as usage_count, AVG(r.confidence) as avg_confidence,
                         COLLECT({from: e1.formula, to: e2.formula, confidence: r.confidence})[0..3] as examples
                    RETURN reasoning, rel_type, usage_count, avg_confidence, examples
                    ORDER BY usage_count DESC
                    """
                
                results = await memgraph_client.execute_query(
                    reasoning_query, 
                    {"min_conf": min_confidence}
                )
                
                # Group by relationship type
                patterns_by_type = {}
                for result in results:
                    rel_type = result['rel_type']
                    if rel_type not in patterns_by_type:
                        patterns_by_type[rel_type] = []
                    patterns_by_type[rel_type].append({
                        'reasoning': result['reasoning'],
                        'usage_count': result['usage_count'],
                        'avg_confidence': result['avg_confidence'],
                        'examples': result['examples'] if include_examples else []
                    })
                
                # Also get common reasoning keywords/phrases
                keyword_query = """
                MATCH ()-[r]->()
                WHERE r.reasoning IS NOT NULL AND r.reasoning <> ''
                WITH r.reasoning as reasoning
                RETURN reasoning
                LIMIT 100
                """
                keyword_results = await memgraph_client.execute_query(keyword_query, {})
                
                # Extract common patterns
                common_phrases = {}
                for result in keyword_results:
                    reasoning = result['reasoning'].lower()
                    # Look for common patterns
                    patterns = [
                        "same group", "periodic trend", "cluster size", "isoelectronic",
                        "parameter study", "similar structure", "workflow step", 
                        "provides input", "optimization", "calculation"
                    ]
                    for pattern in patterns:
                        if pattern in reasoning:
                            common_phrases[pattern] = common_phrases.get(pattern, 0) + 1
                
                # Format results
                reasoning_text = "Reasoning Patterns Analysis:\n\n"
                
                if patterns_by_type:
                    reasoning_text += "## Reasoning by Relationship Type:\n\n"
                    for rel_type, patterns in patterns_by_type.items():
                        reasoning_text += f"### {rel_type}:\n"
                        for i, pattern in enumerate(patterns[:5], 1):  # Top 5 per type
                            reasoning_text += f"{i}. \"{pattern['reasoning']}\"\n"
                            reasoning_text += f"   Used: {pattern['usage_count']} times"
                            if pattern['avg_confidence']:
                                reasoning_text += f", Avg confidence: {pattern['avg_confidence']:.2f}"
                            reasoning_text += "\n"
                            
                            if include_examples and pattern['examples']:
                                reasoning_text += "   Examples:\n"
                                for ex in pattern['examples']:
                                    reasoning_text += f"     - {ex['from']} → {ex['to']}"
                                    if ex.get('confidence'):
                                        reasoning_text += f" (conf: {ex['confidence']:.2f})"
                                    reasoning_text += "\n"
                            reasoning_text += "\n"
                
                if common_phrases:
                    reasoning_text += "\n## Common Reasoning Phrases:\n"
                    sorted_phrases = sorted(common_phrases.items(), key=lambda x: x[1], reverse=True)
                    for phrase, count in sorted_phrases[:10]:
                        reasoning_text += f"- \"{phrase}\": {count} occurrences\n"
                
                # Add guidelines for consistent reasoning
                reasoning_text += "\n## Reasoning Guidelines:\n"
                reasoning_text += "- Use scientific terminology consistently\n"
                reasoning_text += "- Reference specific properties (e.g., 'same periodic group', 'increasing cluster size')\n"
                reasoning_text += "- Include confidence rationale when relevant\n"
                reasoning_text += "- Be specific about the relationship direction and purpose\n"
                
                return CallToolResult(
                    content=[TextContent(type="text", text=reasoning_text)]
                )
                
            except Exception as e:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error getting reasoning patterns: {str(e)}")]
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
    """Main entry point for the enhanced Memgraph MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())