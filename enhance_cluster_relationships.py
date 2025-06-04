#!/usr/bin/env python3
"""
Enhance cluster size relationships by creating more comprehensive series
and cleaning up duplicates.
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

async def enhance_cluster_relationships():
    """Create enhanced cluster size relationships"""
    client = MemgraphClient()
    await client.connect()
    
    # First, clean up any existing CLUSTER_SIZE_SERIES relationships
    print("🧹 Cleaning up existing CLUSTER_SIZE_SERIES relationships...")
    cleanup_query = """
    MATCH ()-[r:CLUSTER_SIZE_SERIES]->()
    DELETE r
    """
    await client.execute_query(cleanup_query)
    
    # Get all formulas and organize by element families
    formula_query = """
    MATCH (e:Entry)
    WHERE e.formula IS NOT NULL AND e.formula <> ""
    RETURN e.formula as formula, e.entry_id as entry_id, e.entry_name as entry_name
    ORDER BY e.formula
    """
    
    results = await client.execute_query(formula_query)
    print(f"📊 Found {len(results)} entries with formulas")
    
    # Organize by element families and cluster sizes
    element_families = {
        "noble_gases": ["He", "Ne", "Ar", "Kr", "Xe", "Rn"],
        "alkali_metals": ["Li", "Na", "K", "Rb", "Cs"],
        "alkaline_earth": ["Be", "Mg", "Ca", "Sr", "Ba"],
        "transition_metals": ["Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn", 
                             "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd",
                             "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg"],
        "halogens": ["F", "Cl", "Br", "I"],
        "metalloids": ["B", "Si", "Ge", "As", "Sb", "Te", "Po"],
        "p_block": ["C", "N", "O", "P", "S"],
        "post_transition": ["Al", "Ga", "In", "Tl", "Sn", "Pb", "Bi"]
    }
    
    # Parse all entries and organize by element and size
    entries_by_element_size = defaultdict(lambda: defaultdict(list))  # element -> size -> [(formula, entry_id)]
    entries_by_family_size = defaultdict(lambda: defaultdict(list))   # family -> size -> [(formula, entry_id, element)]
    size_representatives = defaultdict(list)  # size -> [(formula, entry_id, element)]
    
    for result in results:
        formula = result.get('formula', '')
        entry_id = result.get('entry_id', '')
        entry_name = result.get('entry_name', '')
        
        if formula and entry_id:
            parsed = parse_formula_carefully(formula)
            if parsed:
                total_atoms = sum(parsed.values())
                primary_element = max(parsed.items(), key=lambda x: x[1])[0]
                
                # Organize by individual element
                entries_by_element_size[primary_element][total_atoms].append((formula, entry_id))
                
                # Organize by element family
                for family, elements in element_families.items():
                    if primary_element in elements:
                        entries_by_family_size[family][total_atoms].append((formula, entry_id, primary_element))
                        break
                
                # Global size representatives
                size_representatives[total_atoms].append((formula, entry_id, primary_element))
    
    relationships_created = 0
    
    # 1. Create same-element cluster size series (if any exist)
    print("\n🧪 Creating same-element cluster size series...")
    for element, size_dict in entries_by_element_size.items():
        sizes = sorted(size_dict.keys())
        if len(sizes) > 1:
            print(f"  {element}: sizes {sizes}")
            relationships_created += await create_element_series(client, element, size_dict, sizes)
    
    # 2. Create family-based cluster size series
    print("\n🧬 Creating element family cluster size series...")
    for family, size_dict in entries_by_family_size.items():
        sizes = sorted(size_dict.keys())
        if len(sizes) > 1:
            print(f"  {family}: sizes {sizes}")
            relationships_created += await create_family_series(client, family, size_dict, sizes)
    
    # 3. Create global cluster size progression
    print("\n🌐 Creating global cluster size progression...")
    sizes = sorted(size_representatives.keys())
    if len(sizes) > 1:
        print(f"  Global sizes: {sizes}")
        relationships_created += await create_global_series(client, size_representatives, sizes)
    
    print(f"\n🎉 Total CLUSTER_SIZE_SERIES relationships created: {relationships_created}")
    
    # Verify final relationships
    await verify_all_relationships(client)

async def create_element_series(client, element, size_dict, sizes):
    """Create cluster size series for the same element"""
    relationships = 0
    for i in range(len(sizes) - 1):
        smaller_size = sizes[i]
        larger_size = sizes[i + 1]
        
        smaller_entries = size_dict[smaller_size]
        larger_entries = size_dict[larger_size]
        
        if smaller_entries and larger_entries:
            smaller_formula, smaller_id = smaller_entries[0]
            larger_formula, larger_id = larger_entries[0]
            
            relationship_query = """
            MATCH (smaller:Entry {entry_id: $smaller_id})
            MATCH (larger:Entry {entry_id: $larger_id})
            CREATE (smaller)-[r:CLUSTER_SIZE_SERIES]->(larger)
            SET r.series_type = 'same_element',
                r.element = $element,
                r.smaller_size = $smaller_size,
                r.larger_size = $larger_size,
                r.smaller_formula = $smaller_formula,
                r.larger_formula = $larger_formula,
                r.confidence = 0.95,
                r.reasoning = $reasoning
            RETURN r
            """
            
            reasoning = f"Same element cluster series: {element} from {smaller_size} to {larger_size} atoms"
            
            try:
                await client.execute_query(relationship_query, {
                    "smaller_id": smaller_id,
                    "larger_id": larger_id,
                    "element": element,
                    "smaller_size": smaller_size,
                    "larger_size": larger_size,
                    "smaller_formula": smaller_formula,
                    "larger_formula": larger_formula,
                    "reasoning": reasoning
                })
                relationships += 1
                print(f"    ✅ {smaller_formula} → {larger_formula}")
            except Exception as e:
                print(f"    ❌ Error: {e}")
    
    return relationships

async def create_family_series(client, family, size_dict, sizes):
    """Create cluster size series within element families"""
    relationships = 0
    for i in range(len(sizes) - 1):
        smaller_size = sizes[i]
        larger_size = sizes[i + 1]
        
        smaller_entries = size_dict[smaller_size]
        larger_entries = size_dict[larger_size]
        
        if smaller_entries and larger_entries:
            smaller_formula, smaller_id, smaller_element = smaller_entries[0]
            larger_formula, larger_id, larger_element = larger_entries[0]
            
            relationship_query = """
            MATCH (smaller:Entry {entry_id: $smaller_id})
            MATCH (larger:Entry {entry_id: $larger_id})
            CREATE (smaller)-[r:CLUSTER_SIZE_SERIES]->(larger)
            SET r.series_type = 'element_family',
                r.element_family = $family,
                r.smaller_element = $smaller_element,
                r.larger_element = $larger_element,
                r.smaller_size = $smaller_size,
                r.larger_size = $larger_size,
                r.smaller_formula = $smaller_formula,
                r.larger_formula = $larger_formula,
                r.confidence = 0.85,
                r.reasoning = $reasoning
            RETURN r
            """
            
            reasoning = f"{family} family cluster series: {smaller_element}{smaller_size} → {larger_element}{larger_size}"
            
            try:
                await client.execute_query(relationship_query, {
                    "smaller_id": smaller_id,
                    "larger_id": larger_id,
                    "family": family,
                    "smaller_element": smaller_element,
                    "larger_element": larger_element,
                    "smaller_size": smaller_size,
                    "larger_size": larger_size,
                    "smaller_formula": smaller_formula,
                    "larger_formula": larger_formula,
                    "reasoning": reasoning
                })
                relationships += 1
                print(f"    ✅ {smaller_formula} → {larger_formula} ({smaller_element} → {larger_element})")
            except Exception as e:
                print(f"    ❌ Error: {e}")
    
    return relationships

async def create_global_series(client, size_representatives, sizes):
    """Create global cluster size progression across all elements"""
    relationships = 0
    for i in range(len(sizes) - 1):
        smaller_size = sizes[i]
        larger_size = sizes[i + 1]
        
        smaller_entries = size_representatives[smaller_size]
        larger_entries = size_representatives[larger_size]
        
        if smaller_entries and larger_entries:
            # Pick representative entries (prefer common elements)
            smaller_formula, smaller_id, smaller_element = smaller_entries[0]
            larger_formula, larger_id, larger_element = larger_entries[0]
            
            relationship_query = """
            MATCH (smaller:Entry {entry_id: $smaller_id})
            MATCH (larger:Entry {entry_id: $larger_id})
            CREATE (smaller)-[r:CLUSTER_SIZE_SERIES]->(larger)
            SET r.series_type = 'global_size',
                r.smaller_element = $smaller_element,
                r.larger_element = $larger_element,
                r.smaller_size = $smaller_size,
                r.larger_size = $larger_size,
                r.smaller_formula = $smaller_formula,
                r.larger_formula = $larger_formula,
                r.confidence = 0.75,
                r.reasoning = $reasoning
            RETURN r
            """
            
            reasoning = f"Global cluster size progression: {smaller_size} → {larger_size} atoms ({smaller_formula} → {larger_formula})"
            
            try:
                await client.execute_query(relationship_query, {
                    "smaller_id": smaller_id,
                    "larger_id": larger_id,
                    "smaller_element": smaller_element,
                    "larger_element": larger_element,
                    "smaller_size": smaller_size,
                    "larger_size": larger_size,
                    "smaller_formula": smaller_formula,
                    "larger_formula": larger_formula,
                    "reasoning": reasoning
                })
                relationships += 1
                print(f"    ✅ {smaller_formula} → {larger_formula} ({smaller_size} → {larger_size} atoms)")
            except Exception as e:
                print(f"    ❌ Error: {e}")
    
    return relationships

def parse_formula_carefully(formula: str) -> Dict[str, int]:
    """Parse chemical formula carefully"""
    elements = {}
    
    # Handle simple cases first: Element + number (e.g., Ag4, As6)
    simple_match = re.match(r'^([A-Z][a-z]?)(\d+)$', formula)
    if simple_match:
        element, count_str = simple_match.groups()
        elements[element] = int(count_str)
        return elements
    
    # Handle single element (e.g., H, He, Po)
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

async def verify_all_relationships(client):
    """Verify all cluster size relationships"""
    print(f"\n🔍 Verifying all cluster size relationships...")
    
    verification_query = """
    MATCH (smaller:Entry)-[r:CLUSTER_SIZE_SERIES]->(larger:Entry)
    RETURN r.series_type as series_type,
           r.smaller_formula as smaller_formula,
           r.larger_formula as larger_formula,
           r.smaller_size as smaller_size,
           r.larger_size as larger_size,
           r.confidence as confidence,
           coalesce(r.element, r.element_family, r.smaller_element + '-' + r.larger_element) as context
    ORDER BY r.series_type, r.smaller_size
    """
    
    results = await client.execute_query(verification_query)
    
    print(f"📊 Final verification: Found {len(results)} CLUSTER_SIZE_SERIES relationships")
    
    by_type = defaultdict(list)
    for result in results:
        series_type = result.get('series_type', 'unknown')
        by_type[series_type].append(result)
    
    for series_type, relationships in by_type.items():
        print(f"\n{series_type.replace('_', ' ').title()} ({len(relationships)} relationships):")
        for rel in relationships[:5]:  # Show first 5 of each type
            smaller_formula = rel.get('smaller_formula', '')
            larger_formula = rel.get('larger_formula', '')
            smaller_size = rel.get('smaller_size', 0)
            larger_size = rel.get('larger_size', 0)
            confidence = rel.get('confidence', 0.0)
            context = rel.get('context', '')
            
            print(f"  {smaller_formula} → {larger_formula} ({smaller_size}→{larger_size} atoms) [{context}] (conf: {confidence})")

async def main():
    await enhance_cluster_relationships()

if __name__ == "__main__":
    asyncio.run(main())