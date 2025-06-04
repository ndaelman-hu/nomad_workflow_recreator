#!/usr/bin/env python3
"""
Quick Query Examples

Common queries for exploring the NOMAD workflow graph.
Run with: python quick_queries.py [query_name]
"""

import asyncio
import sys
from src.claude_orchestrator import ClaudeWorkflowOrchestrator

QUERIES = {
    "summary": """
    // Dataset overview
    MATCH (d:Dataset)-[:CONTAINS]->(e:Entry)
    RETURN d.dataset_id as dataset, count(e) as entries
    """,
    
    "formulas": """
    // Chemical formula distribution
    MATCH (e:Entry)
    WHERE e.formula <> ""
    RETURN e.formula as formula, count(e) as count
    ORDER BY count DESC
    LIMIT 20
    """,
    
    "relationships": """
    // All relationship types and counts
    MATCH ()-[r]->()
    RETURN type(r) as relationship_type, count(r) as count
    ORDER BY count DESC
    """,
    
    "periodic_trends": """
    // Find periodic trend relationships
    MATCH (from)-[r:PERIODIC_TREND]->(to)
    RETURN from.formula as from_formula, to.formula as to_formula, 
           r.confidence as confidence, r.reasoning as reasoning
    LIMIT 10
    """,
    
    "cluster_sizes": """
    // Find cluster size relationships
    MATCH (from)-[r:CLUSTER_SIZE_SERIES]->(to)
    RETURN from.formula as smaller_cluster, to.formula as larger_cluster,
           r.confidence as confidence
    LIMIT 10
    """,
    
    "same_element": """
    // Find entries with same element but different sizes
    MATCH (e1:Entry), (e2:Entry)
    WHERE e1.formula CONTAINS 'W' AND e2.formula CONTAINS 'W'
    AND e1.formula <> e2.formula
    RETURN DISTINCT e1.formula, e2.formula
    """,
    
    "w2_entries": """
    // All W2 (tungsten dimer) entries
    MATCH (e:Entry {formula: 'W2'})
    RETURN e.entry_id, e.entry_name, e.has_input_files, e.has_output_files
    """,
    
    "isolated_entries": """
    // Entries with no workflow relationships
    MATCH (e:Entry)
    WHERE NOT (e)-[:PERIODIC_TREND|CLUSTER_SIZE_SERIES|PARAMETER_STUDY]-()
    RETURN e.formula, count(e) as isolated_count
    ORDER BY isolated_count DESC
    LIMIT 10
    """
}

async def run_query(query_name: str):
    """Run a predefined query"""
    if query_name not in QUERIES:
        print(f"❌ Unknown query: {query_name}")
        print(f"Available queries: {', '.join(QUERIES.keys())}")
        return
    
    orchestrator = ClaudeWorkflowOrchestrator()
    await orchestrator.memgraph_client.connect()
    
    print(f"🔍 Running query: {query_name}")
    print("=" * 50)
    
    query = QUERIES[query_name]
    results = await orchestrator.memgraph_client.execute_query(query)
    
    print(f"📊 Results ({len(results)} rows):")
    for i, result in enumerate(results):
        print(f"   {i+1}. {result}")
    
    if not results:
        print("   No results found.")

def main():
    if len(sys.argv) < 2:
        print("🤖 NOMAD Workflow Quick Queries")
        print("=" * 40)
        print("Usage: python quick_queries.py [query_name]")
        print("\nAvailable queries:")
        for name, query in QUERIES.items():
            # Extract comment from query
            comment = query.strip().split('\n')[1].replace('//', '').strip()
            print(f"   {name:15} - {comment}")
        print(f"\nExample: python quick_queries.py formulas")
        return
    
    query_name = sys.argv[1]
    asyncio.run(run_query(query_name))

if __name__ == "__main__":
    main()