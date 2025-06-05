#!/usr/bin/env python3
"""
Fix workflow relationships based on better understanding of the data
"""

import asyncio
import sys
sys.path.append('src')
from memgraph_server import MemgraphClient
from collections import defaultdict

class RelationshipFixer:
    def __init__(self):
        self.client = MemgraphClient()
        self.upload_id = "YDXZgPooRb-31Niq48ODPA"
        
    async def connect(self):
        await self.client.connect()
    
    async def analyze_and_fix(self):
        """Analyze the true structure and create proper relationships"""
        print("🔧 FIXING WORKFLOW RELATIONSHIPS")
        print("=" * 60)
        
        # First, let's understand why there are duplicates
        duplicate_query = """
        MATCH (e:Entry {upload_name: $upload_id})
        WITH e.entry_id as id, count(e) as duplicates
        WHERE duplicates > 1
        RETURN id, duplicates
        ORDER BY duplicates DESC
        LIMIT 10
        """
        duplicates = await self.client.execute_query(duplicate_query, {"upload_id": self.upload_id})
        
        if duplicates:
            print(f"\n⚠️  Found duplicate entries:")
            for dup in duplicates[:5]:
                print(f"   Entry {dup['id'][:12]}... appears {dup['duplicates']} times")
        
        # Get unique entries per formula
        unique_formula_query = """
        MATCH (e:Entry {upload_name: $upload_id, formula: 'W2'})
        RETURN DISTINCT e.entry_id as id, e.entry_name as name
        ORDER BY e.entry_id
        """
        w2_entries = await self.client.execute_query(unique_formula_query, {"upload_id": self.upload_id})
        
        print(f"\n📊 W2 has {len(w2_entries)} unique calculations")
        
        # Create sequential workflow relationships for W2
        print("\n🔗 Creating workflow relationships for W2:")
        for i in range(len(w2_entries) - 1):
            from_entry = w2_entries[i]
            to_entry = w2_entries[i + 1]
            
            rel_query = """
            MATCH (e1:Entry {entry_id: $from_id})
            MATCH (e2:Entry {entry_id: $to_id})
            WHERE e1.upload_name = $upload_id AND e2.upload_name = $upload_id
            MERGE (e1)-[r:COMPUTATIONAL_SEQUENCE {
                step: $step,
                formula: 'W2',
                confidence: 0.9,
                reasoning: $reasoning
            }]->(e2)
            RETURN r
            """
            
            reasoning = f"Sequential calculation step {i+1} to {i+2} for W2 dimer"
            
            try:
                result = await self.client.execute_query(rel_query, {
                    'from_id': from_entry['id'],
                    'to_id': to_entry['id'],
                    'upload_id': self.upload_id,
                    'step': i + 1,
                    'reasoning': reasoning
                })
                print(f"   ✓ Step {i+1}: {from_entry['id'][:8]}... → {to_entry['id'][:8]}...")
            except Exception as e:
                print(f"   ✗ Failed to create relationship: {e}")
        
        # Now let's understand CLUSTER_SIZE_SERIES better
        print("\n\n📊 CLUSTER_SIZE_SERIES Analysis:")
        
        # Get the actual logic behind these relationships
        cluster_examples = await self.client.execute_query("""
        MATCH (e1:Entry)-[r:CLUSTER_SIZE_SERIES]->(e2:Entry)
        RETURN DISTINCT e1.formula as from_formula, e2.formula as to_formula, 
               r.reasoning as reasoning
        LIMIT 20
        """)
        
        print("\nCluster size progression patterns:")
        size_progressions = defaultdict(set)
        
        for ex in cluster_examples:
            from_f = ex['from_formula']
            to_f = ex['to_formula']
            reasoning = ex.get('reasoning', '')
            
            # Extract cluster sizes
            import re
            from_nums = re.findall(r'\d+', from_f)
            to_nums = re.findall(r'\d+', to_f)
            
            if from_nums and to_nums:
                from_size = int(from_nums[0])
                to_size = int(to_nums[0])
                
                if from_size < to_size:
                    size_progressions[from_size].add(to_size)
                    print(f"   {from_f} (n={from_size}) → {to_f} (n={to_size})")
                    if reasoning:
                        print(f"     Reasoning: {reasoning}")
        
        print(f"\n📈 Size progression summary:")
        for from_size in sorted(size_progressions.keys()):
            to_sizes = sorted(size_progressions[from_size])
            print(f"   Clusters of size {from_size} connect to sizes: {to_sizes}")
        
        # Create proper relationships for all formulas
        print("\n\n🔧 Creating COMPUTATIONAL_SEQUENCE for all formulas with multiple entries:")
        
        formulas_query = """
        MATCH (e:Entry {upload_name: $upload_id})
        WHERE e.formula IS NOT NULL AND e.formula <> ''
        WITH e.formula as formula, count(DISTINCT e.entry_id) as unique_count
        WHERE unique_count > 1
        RETURN formula, unique_count
        ORDER BY unique_count DESC
        LIMIT 10
        """
        formulas = await self.client.execute_query(formulas_query, {"upload_id": self.upload_id})
        
        relationships_created = 0
        for formula_data in formulas[:5]:  # Process top 5 formulas
            formula = formula_data['formula']
            count = formula_data['unique_count']
            
            print(f"\n   Processing {formula} ({count} unique calculations)")
            
            # Get unique entries for this formula
            entries_query = """
            MATCH (e:Entry {upload_name: $upload_id, formula: $formula})
            RETURN DISTINCT e.entry_id as id
            ORDER BY e.entry_id
            """
            entries = await self.client.execute_query(entries_query, {"upload_id": self.upload_id, "formula": formula})
            
            # Create sequential relationships
            for i in range(len(entries) - 1):
                from_id = entries[i]['id']
                to_id = entries[i + 1]['id']
                
                seq_query = """
                MATCH (e1:Entry {entry_id: $from_id})
                MATCH (e2:Entry {entry_id: $to_id})
                WHERE e1.upload_name = $upload_id AND e2.upload_name = $upload_id
                MERGE (e1)-[r:COMPUTATIONAL_SEQUENCE {
                    step: $step,
                    formula: $formula,
                    confidence: 0.85,
                    reasoning: $reasoning
                }]->(e2)
                RETURN r
                """
                
                reasoning = f"Computational sequence for {formula}, step {i+1} to {i+2}"
                
                try:
                    await self.client.execute_query(seq_query, {
                        'from_id': from_id,
                        'to_id': to_id,
                        'upload_id': self.upload_id,
                        'step': i + 1,
                        'formula': formula,
                        'reasoning': reasoning
                    })
                    relationships_created += 1
                except:
                    pass
        
        print(f"\n\n✅ Created {relationships_created} new COMPUTATIONAL_SEQUENCE relationships")
        
        # Final summary
        final_stats = await self.client.execute_query("""
        MATCH ()-[r]->()
        WHERE type(r) IN ['COMPUTATIONAL_SEQUENCE', 'CLUSTER_SIZE_SERIES', 'PERIODIC_TREND', 'SAME_MATERIAL', 'SIMILAR_CALCULATION']
        RETURN type(r) as rel_type, count(r) as count
        ORDER BY count DESC
        """)
        
        print(f"\n📊 Final Relationship Summary:")
        for stat in final_stats:
            print(f"   {stat['rel_type']}: {stat['count']}")

async def main():
    fixer = RelationshipFixer()
    await fixer.connect()
    await fixer.analyze_and_fix()

if __name__ == "__main__":
    asyncio.run(main())