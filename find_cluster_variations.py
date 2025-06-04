#!/usr/bin/env python3
"""
Find cluster size variations for the same element and create CLUSTER_SIZE_SERIES relationships.
"""

import asyncio
import re
import os
from collections import defaultdict
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

async def find_and_create_cluster_relationships():
    """Find cluster size variations and create relationships"""
    client = MemgraphClient()
    await client.connect()
    
    # Get all formulas
    formula_query = """
    MATCH (e:Entry)
    WHERE e.formula IS NOT NULL AND e.formula <> ""
    WITH e.formula as formula, collect(e.entry_id) as entry_ids, collect(e.entry_type) as entry_types
    RETURN DISTINCT formula, entry_ids, entry_types[0] as entry_type
    ORDER BY formula
    """
    
    results = await client.execute_query(formula_query)
    print(f"📊 Found {len(results)} unique formulas")
    
    # Analyze element patterns more carefully
    element_clusters = defaultdict(dict)  # element -> {size: [(formula, entry_ids)]}
    
    for result in results:
        formula = result.get('formula', '')
        entry_ids = result.get('entry_ids', [])
        
        if formula and entry_ids:
            # Parse different types of formulas
            parsed = parse_formula_carefully(formula)
            
            if parsed:
                for element, count in parsed.items():
                    if count not in element_clusters[element]:
                        element_clusters[element][count] = []
                    element_clusters[element][count].append((formula, entry_ids))
    
    print(f"\n🧪 Element cluster analysis:")
    elements_with_multiple_sizes = {}
    
    for element, size_dict in element_clusters.items():
        sizes = list(size_dict.keys())
        if len(sizes) > 1:
            elements_with_multiple_sizes[element] = size_dict
            print(f"  {element}: sizes {sorted(sizes)}")
            for size, formulas_and_ids in size_dict.items():
                sample_formulas = [f[0] for f in formulas_and_ids[:3]]
                print(f"    Size {size}: {len(formulas_and_ids)} entries (e.g., {sample_formulas})")
    
    # If no direct cluster size series found, let's create conceptual ones
    # based on different cluster sizes of different elements
    if not elements_with_multiple_sizes:
        print(f"\n🔍 No elements with multiple cluster sizes found.")
        print(f"Creating conceptual cluster size series based on atom count...")
        
        # Group by total atom count across all elements
        size_groups = defaultdict(list)  # size -> [(formula, entry_ids, element)]
        
        for result in results:
            formula = result.get('formula', '')
            entry_ids = result.get('entry_ids', [])
            
            # Calculate total atoms
            parsed = parse_formula_carefully(formula)
            if parsed:
                total_atoms = sum(parsed.values())
                primary_element = max(parsed.items(), key=lambda x: x[1])[0]  # Element with most atoms
                size_groups[total_atoms].append((formula, entry_ids, primary_element))
        
        print(f"\n📏 Cluster sizes available:")
        available_sizes = sorted(size_groups.keys())
        for size in available_sizes:
            entries = size_groups[size]
            elements = set(e[2] for e in entries)
            print(f"  {size} atoms: {len(entries)} entries across elements {sorted(elements)}")
        
        # Create size-based series relationships
        relationships_created = 0
        
        # Connect different sizes in sequence
        for i in range(len(available_sizes) - 1):
            smaller_size = available_sizes[i]
            larger_size = available_sizes[i + 1]
            
            smaller_entries = size_groups[smaller_size]
            larger_entries = size_groups[larger_size]
            
            # Create relationships between representative entries of each size
            if smaller_entries and larger_entries:
                # Take one representative from each size
                smaller_formula, smaller_entry_ids, smaller_element = smaller_entries[0]
                larger_formula, larger_entry_ids, larger_element = larger_entries[0]
                
                smaller_entry_id = smaller_entry_ids[0] if smaller_entry_ids else ""
                larger_entry_id = larger_entry_ids[0] if larger_entry_ids else ""
                
                if smaller_entry_id and larger_entry_id:
                    relationship_query = """
                    MATCH (smaller:Entry {entry_id: $smaller_id})
                    MATCH (larger:Entry {entry_id: $larger_id})
                    CREATE (smaller)-[r:CLUSTER_SIZE_SERIES]->(larger)
                    SET r.smaller_size = $smaller_size,
                        r.larger_size = $larger_size,
                        r.smaller_formula = $smaller_formula,
                        r.larger_formula = $larger_formula,
                        r.smaller_element = $smaller_element,
                        r.larger_element = $larger_element,
                        r.confidence = $confidence,
                        r.reasoning = $reasoning
                    RETURN r
                    """
                    
                    reasoning = f"Cluster size progression: {smaller_formula} ({smaller_size} atoms) → {larger_formula} ({larger_size} atoms)"
                    
                    try:
                        await client.execute_query(relationship_query, {
                            "smaller_id": smaller_entry_id,
                            "larger_id": larger_entry_id,
                            "smaller_size": smaller_size,
                            "larger_size": larger_size,
                            "smaller_formula": smaller_formula,
                            "larger_formula": larger_formula,
                            "smaller_element": smaller_element,
                            "larger_element": larger_element,
                            "confidence": 0.85,
                            "reasoning": reasoning
                        })
                        
                        relationships_created += 1
                        print(f"  ✅ Created: {smaller_formula} → {larger_formula} ({smaller_size} → {larger_size} atoms)")
                        
                    except Exception as e:
                        print(f"  ❌ Error creating relationship {smaller_formula} → {larger_formula}: {e}")
        
        print(f"\n🎉 Created {relationships_created} CLUSTER_SIZE_SERIES relationships")
    
    else:
        # Create relationships for elements with multiple sizes
        relationships_created = 0
        
        for element, size_dict in elements_with_multiple_sizes.items():
            sizes = sorted(size_dict.keys())
            
            for i in range(len(sizes) - 1):
                smaller_size = sizes[i]
                larger_size = sizes[i + 1]
                
                smaller_entries = size_dict[smaller_size]
                larger_entries = size_dict[larger_size]
                
                # Take first representative from each size
                if smaller_entries and larger_entries:
                    smaller_formula, smaller_entry_ids = smaller_entries[0]
                    larger_formula, larger_entry_ids = larger_entries[0]
                    
                    smaller_entry_id = smaller_entry_ids[0] if smaller_entry_ids else ""
                    larger_entry_id = larger_entry_ids[0] if larger_entry_ids else ""
                    
                    if smaller_entry_id and larger_entry_id:
                        relationship_query = """
                        MATCH (smaller:Entry {entry_id: $smaller_id})
                        MATCH (larger:Entry {entry_id: $larger_id})
                        CREATE (smaller)-[r:CLUSTER_SIZE_SERIES]->(larger)
                        SET r.element = $element,
                            r.smaller_size = $smaller_size,
                            r.larger_size = $larger_size,
                            r.smaller_formula = $smaller_formula,
                            r.larger_formula = $larger_formula,
                            r.confidence = $confidence,
                            r.reasoning = $reasoning
                        RETURN r
                        """
                        
                        reasoning = f"Cluster size series for {element}: {smaller_formula} → {larger_formula}"
                        
                        try:
                            await client.execute_query(relationship_query, {
                                "smaller_id": smaller_entry_id,
                                "larger_id": larger_entry_id,
                                "element": element,
                                "smaller_size": smaller_size,
                                "larger_size": larger_size,
                                "smaller_formula": smaller_formula,
                                "larger_formula": larger_formula,
                                "confidence": 0.85,
                                "reasoning": reasoning
                            })
                            
                            relationships_created += 1
                            print(f"  ✅ Created: {smaller_formula} → {larger_formula} ({element})")
                            
                        except Exception as e:
                            print(f"  ❌ Error creating relationship {smaller_formula} → {larger_formula}: {e}")
        
        print(f"\n🎉 Created {relationships_created} CLUSTER_SIZE_SERIES relationships")
    
    # Verify created relationships
    await verify_cluster_relationships(client)

def parse_formula_carefully(formula: str) -> Dict[str, int]:
    """Parse chemical formula more carefully"""
    elements = {}
    
    # Handle simple cases first: Element + number (e.g., Ag4, As6)
    simple_match = re.match(r'^([A-Z][a-z]?)(\d+)$', formula)
    if simple_match:
        element, count_str = simple_match.groups()
        elements[element] = int(count_str)
        return elements
    
    # Handle single element (e.g., H, He)
    single_match = re.match(r'^([A-Z][a-z]?)$', formula)
    if single_match:
        element = single_match.group(1)
        elements[element] = 1
        return elements
    
    # General pattern for more complex formulas
    pattern = r'([A-Z][a-z]?)(\d*)'
    matches = re.findall(pattern, formula)
    
    for element, count_str in matches:
        count = int(count_str) if count_str else 1
        if element in elements:
            elements[element] += count
        else:
            elements[element] = count
    
    return elements

async def verify_cluster_relationships(client):
    """Verify the created cluster size relationships"""
    print(f"\n🔍 Verifying cluster size relationships...")
    
    verification_query = """
    MATCH (smaller:Entry)-[r:CLUSTER_SIZE_SERIES]->(larger:Entry)
    RETURN r.smaller_formula as smaller_formula,
           r.larger_formula as larger_formula,
           r.smaller_size as smaller_size,
           r.larger_size as larger_size,
           r.confidence as confidence,
           r.reasoning as reasoning,
           coalesce(r.element, r.smaller_element + '-' + r.larger_element) as element_info
    ORDER BY r.smaller_size
    """
    
    results = await client.execute_query(verification_query)
    
    print(f"📊 Verification: Found {len(results)} CLUSTER_SIZE_SERIES relationships")
    
    for result in results:
        smaller_formula = result.get('smaller_formula', '')
        larger_formula = result.get('larger_formula', '')
        smaller_size = result.get('smaller_size', 0)
        larger_size = result.get('larger_size', 0)
        confidence = result.get('confidence', 0.0)
        reasoning = result.get('reasoning', '')
        element_info = result.get('element_info', '')
        
        print(f"  {smaller_formula} → {larger_formula} ({smaller_size} → {larger_size} atoms)")
        print(f"    Element: {element_info}, Confidence: {confidence}")
        print(f"    Reasoning: {reasoning}")
        print()

async def main():
    await find_and_create_cluster_relationships()

if __name__ == "__main__":
    asyncio.run(main())