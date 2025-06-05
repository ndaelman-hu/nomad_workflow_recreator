#!/usr/bin/env python3
"""
Investigate the 8-calculation pattern and CLUSTER_SIZE_SERIES semantics
"""

import asyncio
import sys
sys.path.append('src')
from memgraph_server import MemgraphClient
from collections import defaultdict

class RelationshipInvestigator:
    def __init__(self):
        self.client = MemgraphClient()
        self.upload_id = "YDXZgPooRb-31Niq48ODPA"
        
    async def connect(self):
        await self.client.connect()
    
    async def investigate_8_calculation_pattern(self):
        """Deep dive into formulas with 8 calculations"""
        print("🔍 INVESTIGATING 8-CALCULATION PATTERN")
        print("=" * 60)
        
        # Get a sample formula with 8 calculations
        sample_query = """
        MATCH (e:Entry {upload_name: $upload_id})
        WHERE e.formula IS NOT NULL AND e.formula <> ''
        WITH e.formula as formula, count(e) as count
        WHERE count = 8
        RETURN formula
        LIMIT 5
        """
        sample_formulas = await self.client.execute_query(sample_query, {"upload_id": self.upload_id})
        
        for formula_result in sample_formulas:
            formula = formula_result['formula']
            print(f"\n📊 Analyzing formula: {formula}")
            
            # Get all 8 entries for this formula
            entries_query = """
            MATCH (e:Entry {upload_name: $upload_id, formula: $formula})
            RETURN e.entry_id as id, e.entry_name as name, e.entry_type as type,
                   e.has_input_files as has_inputs, e.has_output_files as has_outputs,
                   e.total_files as total_files
            ORDER BY e.entry_id
            """
            entries = await self.client.execute_query(entries_query, {"formula": formula})
            
            print(f"   Found {len(entries)} calculations:")
            for i, entry in enumerate(entries):
                print(f"   {i+1}. ID: {entry['id'][:12]}... Name: {entry['name']}")
            
            # Check existing relationships between these entries
            rel_query = """
            MATCH (e1:Entry {upload_name: $upload_id, formula: $formula})-[r]->(e2:Entry {formula: $formula})
            RETURN e1.entry_id as from_id, type(r) as rel_type, e2.entry_id as to_id,
                   r.confidence as confidence, r.reasoning as reasoning
            LIMIT 20
            """
            relationships = await self.client.execute_query(rel_query, {"formula": formula})
            
            if relationships:
                print(f"\n   Existing relationships within {formula}:")
                for rel in relationships[:5]:
                    print(f"     {rel['from_id'][:8]}... --[{rel['rel_type']}]--> {rel['to_id'][:8]}...")
                    if rel.get('reasoning'):
                        print(f"       Reasoning: {rel['reasoning']}")
            
            # Look for patterns in entry names or IDs
            print(f"\n   Entry ID pattern analysis:")
            id_prefixes = defaultdict(list)
            for entry in entries:
                # Group by first few characters of ID
                prefix = entry['id'][:4]
                id_prefixes[prefix].append(entry['id'])
            
            for prefix, ids in id_prefixes.items():
                if len(ids) > 1:
                    print(f"     Prefix '{prefix}': {len(ids)} entries")
    
    async def investigate_cluster_size_series(self):
        """Understand CLUSTER_SIZE_SERIES relationships"""
        print("\n\n🔬 INVESTIGATING CLUSTER_SIZE_SERIES RELATIONSHIPS")
        print("=" * 60)
        
        # Get examples of CLUSTER_SIZE_SERIES relationships
        cluster_query = """
        MATCH (e1:Entry)-[r:CLUSTER_SIZE_SERIES]->(e2:Entry)
        RETURN e1.formula as from_formula, e2.formula as to_formula,
               e1.entry_id as from_id, e2.entry_id as to_id,
               r.confidence as confidence, r.reasoning as reasoning
        LIMIT 20
        """
        cluster_rels = await self.client.execute_query(cluster_query)
        
        print(f"\n📊 CLUSTER_SIZE_SERIES Examples:")
        formula_patterns = defaultdict(list)
        
        for rel in cluster_rels:
            from_formula = rel['from_formula']
            to_formula = rel['to_formula']
            formula_patterns[from_formula].append(to_formula)
            
            print(f"\n   {from_formula} --> {to_formula}")
            print(f"   From ID: {rel['from_id'][:12]}...")
            print(f"   To ID: {rel['to_id'][:12]}...")
            if rel.get('reasoning'):
                print(f"   Reasoning: {rel['reasoning']}")
            if rel.get('confidence'):
                print(f"   Confidence: {rel['confidence']}")
        
        # Analyze the pattern
        print(f"\n📈 Pattern Analysis:")
        for from_formula, to_formulas in formula_patterns.items():
            print(f"   {from_formula} connects to: {', '.join(set(to_formulas))}")
        
        # Get statistics about cluster size series
        stats_query = """
        MATCH (e1:Entry)-[r:CLUSTER_SIZE_SERIES]->(e2:Entry)
        WITH e1.formula as from_formula, e2.formula as to_formula, count(r) as count
        RETURN from_formula, to_formula, count
        ORDER BY count DESC
        LIMIT 10
        """
        stats = await self.client.execute_query(stats_query)
        
        print(f"\n📊 Most Common CLUSTER_SIZE_SERIES Patterns:")
        for stat in stats:
            print(f"   {stat['from_formula']} --> {stat['to_formula']}: {stat['count']} relationships")
        
        # Check if it's about cluster size progression
        print(f"\n🔍 Checking for size progression patterns...")
        size_patterns = []
        for rel in cluster_rels[:10]:
            from_f = rel['from_formula']
            to_f = rel['to_formula']
            
            # Extract numbers from formulas
            import re
            from_nums = re.findall(r'\d+', from_f)
            to_nums = re.findall(r'\d+', to_f)
            
            if from_nums and to_nums:
                from_size = int(from_nums[0])
                to_size = int(to_nums[0])
                size_patterns.append((from_f, to_f, from_size, to_size))
                
        if size_patterns:
            print("\n   Size progression examples:")
            for from_f, to_f, from_size, to_size in size_patterns[:5]:
                print(f"     {from_f} (size {from_size}) --> {to_f} (size {to_size})")

async def main():
    investigator = RelationshipInvestigator()
    await investigator.connect()
    
    # Investigate both aspects
    await investigator.investigate_8_calculation_pattern()
    await investigator.investigate_cluster_size_series()

if __name__ == "__main__":
    asyncio.run(main())