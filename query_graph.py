#!/usr/bin/env python3
"""
Complete Graph Query Tool
Provides various ways to query and analyze the entire NOMAD workflow graph
"""

import asyncio
import sys
sys.path.append('src')
from memgraph_server import MemgraphClient

class GraphExplorer:
    def __init__(self):
        self.client = MemgraphClient()
    
    async def connect(self):
        await self.client.connect()
    
    async def full_graph_export(self):
        """Export the entire graph structure"""
        print("🌐 Full Graph Export:")
        print("=" * 50)
        
        # All nodes
        nodes = await self.client.execute_query("MATCH (n) RETURN n")
        print(f"📊 Total Nodes: {len(nodes)}")
        
        # All relationships
        rels = await self.client.execute_query("MATCH ()-[r]->() RETURN r")
        print(f"🔗 Total Relationships: {len(rels)}")
        
        # Node types
        node_types = await self.client.execute_query("""
            MATCH (n) 
            RETURN labels(n)[0] as label, count(n) as count
        """)
        print("\n📋 Node Types:")
        for result in node_types:
            label = list(result.values())[0]
            count = list(result.values())[1]
            print(f"   {label}: {count}")
        
        # Relationship types
        rel_types = await self.client.execute_query("""
            MATCH ()-[r]->() 
            RETURN type(r) as rel_type, count(r) as count
        """)
        print("\n🔗 Relationship Types:")
        for result in rel_types:
            rel_type = list(result.values())[0]
            count = list(result.values())[1]
            print(f"   {rel_type}: {count}")
    
    async def workflow_analysis(self):
        """Analyze workflow patterns across the entire graph"""
        print("\n🔬 Workflow Analysis:")
        print("=" * 50)
        
        # Find workflow entry points (no incoming relationships)
        entry_points = await self.client.execute_query("""
            MATCH (e:Entry)
            OPTIONAL MATCH (other)-[:SIMILAR_CALCULATION]->(e)
            WHERE other IS NULL
            RETURN e.entry_id, e.formula, e.entry_type
            LIMIT 10
        """)
        print(f"\n🚀 Workflow Entry Points: {len(entry_points)}")
        for result in entry_points:
            entry_id = list(result.values())[0][:12] + "..."
            formula = list(result.values())[1]
            entry_type = list(result.values())[2]
            print(f"   {entry_id} ({formula}) - {entry_type}")
        
        # Find workflow endpoints (no outgoing relationships)
        endpoints = await self.client.execute_query("""
            MATCH (e:Entry)
            OPTIONAL MATCH (e)-[:SIMILAR_CALCULATION]->(other)
            WHERE other IS NULL
            RETURN e.entry_id, e.formula, e.entry_type
            LIMIT 10
        """)
        print(f"\n🏁 Workflow Endpoints: {len(endpoints)}")
        for result in endpoints:
            entry_id = list(result.values())[0][:12] + "..."
            formula = list(result.values())[1]
            entry_type = list(result.values())[2]
            print(f"   {entry_id} ({formula}) - {entry_type}")
    
    async def chemical_analysis(self):
        """Analyze chemical composition across the graph"""
        print("\n⚗️  Chemical Analysis:")
        print("=" * 50)
        
        # All unique formulas
        formulas = await self.client.execute_query("""
            MATCH (e:Entry)
            WHERE e.formula <> ""
            RETURN DISTINCT e.formula
            ORDER BY e.formula
        """)
        print(f"\n🧪 Unique Chemical Formulas: {len(formulas)}")
        formula_list = [list(result.values())[0] for result in formulas]
        print(f"   {', '.join(formula_list[:20])}")
        if len(formulas) > 20:
            print(f"   ... and {len(formulas) - 20} more")
        
        # Element distribution
        elements = {}
        for result in formulas:
            formula = list(result.values())[0]
            # Simple element extraction (you could make this more sophisticated)
            for element in ['H', 'He', 'Li', 'Be', 'B', 'C', 'N', 'O', 'F', 'Ne',
                           'Na', 'Mg', 'Al', 'Si', 'P', 'S', 'Cl', 'Ar', 'K', 'Ca',
                           'Sc', 'Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn',
                           'Ga', 'Ge', 'As', 'Se', 'Br', 'Kr', 'Rb', 'Sr', 'Y', 'Zr',
                           'Nb', 'Mo', 'Tc', 'Ru', 'Rh', 'Pd', 'Ag', 'Cd', 'In', 'Sn',
                           'Sb', 'Te', 'I', 'Xe', 'Cs', 'Ba', 'La', 'Ce', 'Pr', 'Nd',
                           'Pm', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb',
                           'Lu', 'Hf', 'Ta', 'W', 'Re', 'Os', 'Ir', 'Pt', 'Au', 'Hg',
                           'Tl', 'Pb', 'Bi', 'Po', 'At', 'Rn']:
                if element in formula:
                    elements[element] = elements.get(element, 0) + 1
        
        print(f"\n🔬 Element Distribution (Top 10):")
        sorted_elements = sorted(elements.items(), key=lambda x: x[1], reverse=True)
        for element, count in sorted_elements[:10]:
            print(f"   {element}: {count} compounds")
    
    async def custom_query(self, query):
        """Execute a custom Cypher query"""
        print(f"\n🔍 Custom Query: {query}")
        print("=" * 50)
        results = await self.client.execute_query(query)
        for i, result in enumerate(results[:20]):  # Limit to first 20 results
            print(f"   {i+1}. {result}")
        if len(results) > 20:
            print(f"   ... and {len(results) - 20} more results")

async def main():
    explorer = GraphExplorer()
    await explorer.connect()
    
    if len(sys.argv) > 1:
        # Custom query mode
        custom_query = " ".join(sys.argv[1:])
        await explorer.custom_query(custom_query)
    else:
        # Full analysis mode
        await explorer.full_graph_export()
        await explorer.workflow_analysis()
        await explorer.chemical_analysis()
        
        print(f"\n💡 Usage Examples:")
        print(f"   python query_graph.py 'MATCH (n) RETURN count(n)'")
        print(f"   python query_graph.py 'MATCH (e:Entry) WHERE e.formula CONTAINS \"Au\" RETURN e'")

if __name__ == "__main__":
    asyncio.run(main())