#!/usr/bin/env python3
"""
Examine formulas in the database to understand the cluster data better.
"""

import asyncio
import re
import os
from collections import defaultdict, Counter
from typing import Dict, List, Tuple
import mgclient
from dotenv import load_dotenv

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
            self.conn.autocommit = True
            return True
        except Exception as e:
            print(f"Failed to connect to Memgraph: {e}")
            return False
    
    async def execute_query(self, query: str, parameters: Dict[str, any] = None) -> List[Dict[str, any]]:
        """Execute a Cypher query and return results"""
        if not self.conn:
            await self.connect()
        
        cursor = self.conn.cursor()
        cursor.execute(query, parameters or {})
        
        results = []
        for record in cursor.fetchall():
            result = {}
            for i, value in enumerate(record):
                column_name = cursor.description[i].name if cursor.description and len(cursor.description) > i else f"col_{i}"
                if hasattr(value, 'properties'):
                    result[column_name] = {
                        'id': value.id if hasattr(value, 'id') else None,
                        'labels': list(value.labels) if hasattr(value, 'labels') else [],
                        'properties': dict(value.properties) if hasattr(value, 'properties') else {}
                    }
                else:
                    result[column_name] = value
            results.append(result)
        
        return results

async def examine_formulas():
    """Examine the formulas in the database"""
    client = MemgraphClient()
    await client.connect()
    
    # Get all formulas
    formula_query = """
    MATCH (e:Entry)
    WHERE e.formula IS NOT NULL AND e.formula <> ""
    RETURN e.formula as formula, e.entry_id as entry_id, e.entry_name as entry_name
    ORDER BY e.formula
    """
    
    results = await client.execute_query(formula_query)
    print(f"📊 Found {len(results)} entries with formulas")
    
    # Count formulas
    formula_counts = Counter()
    formulas_by_complexity = defaultdict(list)
    
    print("\n🧪 Sample formulas:")
    for i, result in enumerate(results[:30]):  # Show first 30
        formula = result.get('formula', '')
        entry_id = result.get('entry_id', '')
        entry_name = result.get('entry_name', '')
        formula_counts[formula] += 1
        
        # Categorize by complexity (number of characters)
        complexity = len(formula)
        formulas_by_complexity[complexity].append(formula)
        
        print(f"  {formula} (ID: {entry_id[:8]}...)")
    
    print(f"\n📈 Formula complexity distribution:")
    for complexity in sorted(formulas_by_complexity.keys())[:10]:
        sample_formulas = formulas_by_complexity[complexity][:3]
        print(f"  {complexity} chars: {len(formulas_by_complexity[complexity])} formulas (e.g., {sample_formulas})")
    
    print(f"\n🔢 Most common formulas:")
    for formula, count in formula_counts.most_common(20):
        if count > 1:
            print(f"  {formula}: {count} entries")
    
    # Look for potential cluster patterns
    print(f"\n🔍 Looking for potential cluster size patterns...")
    
    # Group formulas by base element patterns
    element_patterns = defaultdict(list)
    
    for formula in formula_counts.keys():
        # Look for patterns like C, C2, C4, C8, etc.
        if re.match(r'^[A-Z][a-z]?\d*$', formula):  # Single element with optional number
            element = re.match(r'^([A-Z][a-z]?)', formula).group(1)
            element_patterns[element].append(formula)
        
        # Look for patterns with simple binary compounds
        binary_match = re.match(r'^([A-Z][a-z]?)(\d*)([A-Z][a-z]?)(\d*)$', formula)
        if binary_match and len(binary_match.groups()) == 4:
            elem1, count1, elem2, count2 = binary_match.groups()
            if elem1 and elem2:  # Valid binary compound
                key = f"{elem1}-{elem2}"
                element_patterns[key].append(formula)
    
    # Show elements with multiple formulas (potential cluster series)
    print(f"\n🧬 Elements with multiple formulas (potential cluster series):")
    for element, formulas in element_patterns.items():
        if len(formulas) > 1:
            sorted_formulas = sorted(formulas)
            print(f"  {element}: {sorted_formulas}")
    
    # Look for systematic size variations
    print(f"\n🔬 Looking for systematic size variations...")
    
    size_variations = defaultdict(list)
    for formula in formula_counts.keys():
        # Extract all elements and their counts
        elements = re.findall(r'([A-Z][a-z]?)(\d*)', formula)
        total_atoms = 0
        for element, count_str in elements:
            count = int(count_str) if count_str else 1
            total_atoms += count
        
        if total_atoms > 1:  # Only clusters with more than 1 atom
            size_variations[total_atoms].append(formula)
    
    print(f"\n📏 Formulas by total atom count:")
    for size in sorted(size_variations.keys())[:15]:  # Show first 15 sizes
        formulas = size_variations[size][:5]  # Show max 5 examples
        print(f"  {size} atoms: {len(size_variations[size])} formulas (e.g., {formulas})")

async def main():
    await examine_formulas()

if __name__ == "__main__":
    asyncio.run(main())