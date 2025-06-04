#!/usr/bin/env python3
"""
Interactive Workflow Analysis Tool

Provides a simple command-line interface to explore and analyze 
the NOMAD workflow graph using the Claude orchestrator tools.
"""

import asyncio
import sys
import json
from src.claude_orchestrator import ClaudeWorkflowOrchestrator

class InteractiveAnalyzer:
    def __init__(self):
        self.orchestrator = ClaudeWorkflowOrchestrator()
    
    async def start(self):
        """Start interactive analysis session"""
        await self.orchestrator.memgraph_client.connect()
        print("🤖 NOMAD Workflow Interactive Analyzer")
        print("=" * 50)
        
        while True:
            print("\nOptions:")
            print("1. Dataset summary")
            print("2. Explore chemical formulas")
            print("3. Compare two entries")
            print("4. Find entries by formula")
            print("5. Create relationship")
            print("6. Custom Cypher query")
            print("7. Exit")
            
            choice = input("\nSelect option (1-7): ").strip()
            
            try:
                if choice == "1":
                    await self.dataset_summary()
                elif choice == "2":
                    await self.explore_formulas()
                elif choice == "3":
                    await self.compare_entries()
                elif choice == "4":
                    await self.find_by_formula()
                elif choice == "5":
                    await self.create_relationship()
                elif choice == "6":
                    await self.custom_query()
                elif choice == "7":
                    print("Goodbye!")
                    break
                else:
                    print("Invalid choice. Please select 1-7.")
            except Exception as e:
                print(f"Error: {e}")
    
    async def dataset_summary(self):
        """Show dataset summary"""
        summary = await self.orchestrator.get_dataset_summary_for_claude("YDXZgPooRb-31Niq48ODPA")
        print(f"\n📊 Dataset Summary:")
        print(f"   Total entries: {summary['total_entries']}")
        print(f"   Entry types: {summary['entry_types']}")
        print(f"   Top formulas: {dict(list(summary['top_formulas'].items())[:10])}")
        print(f"   Upload clusters: {len(summary['upload_clusters'])}")
    
    async def explore_formulas(self):
        """Explore chemical formulas"""
        query = """
        MATCH (e:Entry)
        WHERE e.formula <> ""
        RETURN e.formula as formula, count(e) as count
        ORDER BY count DESC
        LIMIT 15
        """
        results = await self.orchestrator.memgraph_client.execute_query(query)
        print(f"\n🧪 Chemical Formulas:")
        for result in results:
            formula = list(result.values())[0]
            count = list(result.values())[1]
            print(f"   {formula}: {count} calculations")
    
    async def compare_entries(self):
        """Compare two entries"""
        entry1 = input("Enter first entry ID (or partial): ").strip()
        entry2 = input("Enter second entry ID (or partial): ").strip()
        
        # Find full entry IDs if partial given
        if len(entry1) < 20:
            query = f"MATCH (e:Entry) WHERE e.entry_id CONTAINS '{entry1}' RETURN e.entry_id LIMIT 1"
            result = await self.orchestrator.memgraph_client.execute_query(query)
            entry1 = list(result[0].values())[0] if result else entry1
            
        if len(entry2) < 20:
            query = f"MATCH (e:Entry) WHERE e.entry_id CONTAINS '{entry2}' RETURN e.entry_id LIMIT 1"
            result = await self.orchestrator.memgraph_client.execute_query(query)
            entry2 = list(result[0].values())[0] if result else entry2
        
        comparison = await self.orchestrator.compare_entries(entry1, entry2)
        if comparison:
            print(f"\n🔍 Entry Comparison:")
            print(f"   Entry 1: {entry1[:15]}...")
            print(f"   Entry 2: {entry2[:15]}...")
            print(f"   Same formula: {comparison['same_formula']}")
            print(f"   Same type: {comparison['same_type']}")
            print(f"   Same upload: {comparison['same_upload']}")
        else:
            print("Entries not found or error in comparison")
    
    async def find_by_formula(self):
        """Find entries by chemical formula"""
        formula = input("Enter chemical formula (e.g., W2, Li3): ").strip()
        entries = await self.orchestrator.get_entries_by_formula(formula, limit=10)
        
        print(f"\n🔬 Entries for {formula}:")
        for i, entry in enumerate(entries):
            entry_data = list(entry.values())[0]
            if isinstance(entry_data, dict) and 'properties' in entry_data:
                props = entry_data['properties']
                entry_id = props.get('entry_id', 'Unknown')[:15]
                entry_name = props.get('entry_name', 'Unknown')
                print(f"   {i+1}. {entry_id}... - {entry_name}")
    
    async def create_relationship(self):
        """Create a relationship between entries"""
        print("\n🔗 Create Relationship:")
        from_entry = input("From entry ID (or partial): ").strip()
        to_entry = input("To entry ID (or partial): ").strip()
        rel_type = input("Relationship type (e.g., PERIODIC_TREND, CLUSTER_SIZE_SERIES): ").strip()
        confidence = float(input("Confidence (0.0-1.0): ").strip())
        reasoning = input("Reasoning: ").strip()
        
        # Find full entry IDs if partial
        for var_name, entry_id in [("from_entry", from_entry), ("to_entry", to_entry)]:
            if len(entry_id) < 20:
                query = f"MATCH (e:Entry) WHERE e.entry_id CONTAINS '{entry_id}' RETURN e.entry_id LIMIT 1"
                result = await self.orchestrator.memgraph_client.execute_query(query)
                if result:
                    locals()[var_name] = list(result[0].values())[0]
        
        success = await self.orchestrator.create_relationship_from_claude(
            from_entry, to_entry, rel_type, confidence, reasoning
        )
        
        if success:
            print(f"✅ Created relationship: {from_entry[:15]}... --{rel_type}--> {to_entry[:15]}...")
        else:
            print("❌ Failed to create relationship")
    
    async def custom_query(self):
        """Execute custom Cypher query"""
        print("\n💻 Custom Query:")
        print("Examples:")
        print("  MATCH (e:Entry) RETURN count(e)")
        print("  MATCH ()-[r]->() RETURN type(r), count(r)")
        print("  MATCH (e:Entry {formula: 'W2'}) RETURN e LIMIT 5")
        
        query = input("\nEnter Cypher query: ").strip()
        if query:
            results = await self.orchestrator.memgraph_client.execute_query(query)
            print(f"\n📊 Results ({len(results)} rows):")
            for i, result in enumerate(results[:10]):  # Limit display
                print(f"   {i+1}. {result}")
            if len(results) > 10:
                print(f"   ... and {len(results) - 10} more rows")

async def main():
    analyzer = InteractiveAnalyzer()
    await analyzer.start()

if __name__ == "__main__":
    asyncio.run(main())