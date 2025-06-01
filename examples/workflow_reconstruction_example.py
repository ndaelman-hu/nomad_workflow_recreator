#!/usr/bin/env python3
"""
Example: Workflow Reconstruction from Public Dataset

This example demonstrates how to use the NOMAD Workflow Recreator
to extract and reconstruct computational workflows from public datasets.
"""

import asyncio
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from workflow_orchestrator import WorkflowOrchestrator

async def example_workflow_reconstruction():
    """Example workflow reconstruction process"""
    
    print("🚀 NOMAD Workflow Reconstruction Example")
    print("=" * 50)
    
    # Initialize orchestrator
    orchestrator = WorkflowOrchestrator()
    
    # Example public dataset (replace with actual dataset name)
    dataset_name = "example_computational_study"
    
    print(f"📁 Target Dataset: {dataset_name}")
    print(f"🔍 Starting workflow reconstruction...")
    print()
    
    try:
        # Perform complete workflow reconstruction
        summary = await orchestrator.reconstruct_dataset_workflow(
            dataset_identifier=dataset_name,
            identifier_type="upload_name"
        )
        
        # Display results
        print("\n" + "=" * 50)
        print("📊 RECONSTRUCTION SUMMARY")
        print("=" * 50)
        print(f"Dataset ID: {summary['dataset_id']}")
        print(f"Entries Processed: {summary['entries_processed']}")
        print(f"Relationships Created: {summary['relationships_created']}")
        print(f"Entry Types Found: {', '.join(summary['entry_types'])}")
        print(f"Upload Clusters: {len(summary['upload_clusters'])}")
        
        if summary['upload_clusters']:
            print(f"Cluster Names: {', '.join(summary['upload_clusters'][:3])}{'...' if len(summary['upload_clusters']) > 3 else ''}")
        
        print("\n✅ Workflow reconstruction completed successfully!")
        print("🔗 Graph database now contains the complete workflow structure")
        print("📈 You can now query workflows using Cypher or MCP tools")
        
    except Exception as e:
        print(f"❌ Error during reconstruction: {e}")
        print("💡 Make sure:")
        print("   - NOMAD_TOKEN is configured in .env")
        print("   - Memgraph database is running")
        print("   - Dataset name exists in NOMAD")

async def example_workflow_queries():
    """Example queries after workflow reconstruction"""
    
    print("\n" + "=" * 50)
    print("🔍 EXAMPLE WORKFLOW QUERIES")
    print("=" * 50)
    
    orchestrator = WorkflowOrchestrator()
    
    # Example queries you can run after reconstruction
    example_queries = [
        {
            "description": "Find all geometry optimization entries",
            "cypher": "MATCH (e:Entry) WHERE e.entry_type CONTAINS 'geometry' RETURN e.entry_id, e.formula LIMIT 5"
        },
        {
            "description": "Find workflow dependencies",
            "cypher": "MATCH (e1:Entry)-[r:PROVIDES_STRUCTURE]->(e2:Entry) RETURN e1.entry_id, e2.entry_id, r LIMIT 5"
        },
        {
            "description": "Find entries with same formula",
            "cypher": "MATCH (e1:Entry), (e2:Entry) WHERE e1.formula = e2.formula AND e1 <> e2 RETURN e1.formula, count(*) as entries GROUP BY e1.formula"
        },
        {
            "description": "Trace workflow from specific entry",
            "cypher": "MATCH path = (start:Entry {entry_id: 'YOUR_ENTRY_ID'})-[*1..3]-(connected) RETURN path LIMIT 3"
        }
    ]
    
    print("After reconstruction, you can run these Cypher queries:")
    print()
    
    for i, query in enumerate(example_queries, 1):
        print(f"{i}. {query['description']}:")
        print(f"   {query['cypher']}")
        print()
    
    print("💡 Use memgraph_query MCP tool to execute these queries")
    print("🌐 Or access Memgraph Lab at http://localhost:3000")

if __name__ == "__main__":
    # Run the example
    asyncio.run(example_workflow_reconstruction())
    asyncio.run(example_workflow_queries())