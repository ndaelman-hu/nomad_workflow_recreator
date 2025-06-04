#!/usr/bin/env python3
"""
Create CLUSTER_SIZE_SERIES relationships in Memgraph.

This script identifies entries with different cluster sizes of the same element
and creates relationships connecting smaller to larger clusters.
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
            # Enable autocommit to ensure transactions are committed
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
            # Convert record to dictionary
            result = {}
            for i, value in enumerate(record):
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

class ClusterSizeAnalyzer:
    def __init__(self):
        self.memgraph_client = MemgraphClient()
    
    async def find_cluster_size_relationships(self):
        """Find and create cluster size series relationships"""
        print("🔍 Analyzing cluster size relationships...")
        
        # Connect to Memgraph
        await self.memgraph_client.connect()
        
        # Step 1: Get all formulas from Entry nodes
        formula_query = """
        MATCH (e:Entry)
        WHERE e.formula IS NOT NULL AND e.formula <> ""
        RETURN DISTINCT e.formula as formula, e.entry_id as entry_id
        ORDER BY e.formula
        """
        
        results = await self.memgraph_client.execute_query(formula_query)
        print(f"📊 Found {len(results)} entries with formulas")
        
        # Step 2: Parse formulas to extract elements and cluster sizes
        element_clusters = defaultdict(list)  # element -> [(formula, entry_id, cluster_size)]
        
        for result in results:
            formula = result.get('formula', '')
            entry_id = result.get('entry_id', '')
            
            if formula and entry_id:
                element_info = self._parse_formula_elements(formula)
                for element, count in element_info.items():
                    element_clusters[element].append((formula, entry_id, count))
        
        print(f"🧪 Found clusters for {len(element_clusters)} different elements")
        
        # Step 3: Find elements with multiple cluster sizes
        cluster_series = {}
        for element, clusters in element_clusters.items():
            # Group by cluster size and filter to elements with multiple sizes
            size_groups = defaultdict(list)
            for formula, entry_id, count in clusters:
                size_groups[count].append((formula, entry_id))
            
            # Only create relationships if there are multiple different sizes
            sizes = list(size_groups.keys())
            if len(sizes) > 1:
                sizes.sort()  # Sort by cluster size
                cluster_series[element] = {size: entries for size, entries in size_groups.items()}
                print(f"  {element}: cluster sizes {sizes}")
        
        print(f"🔗 Found {len(cluster_series)} elements with multiple cluster sizes")
        
        # Step 4: Create CLUSTER_SIZE_SERIES relationships
        relationships_created = 0
        for element, size_groups in cluster_series.items():
            sizes = sorted(size_groups.keys())
            
            # Create relationships from smaller to larger clusters
            for i in range(len(sizes) - 1):
                smaller_size = sizes[i]
                larger_size = sizes[i + 1]
                
                smaller_entries = size_groups[smaller_size]
                larger_entries = size_groups[larger_size]
                
                # Create relationships between representative entries
                # (first entry of each size group)
                if smaller_entries and larger_entries:
                    smaller_formula, smaller_entry_id = smaller_entries[0]
                    larger_formula, larger_entry_id = larger_entries[0]
                    
                    # Create the relationship
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
                    
                    reasoning = f"Cluster size series for {element}: {smaller_formula} ({smaller_size} atoms) → {larger_formula} ({larger_size} atoms)"
                    
                    try:
                        await self.memgraph_client.execute_query(relationship_query, {
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
        
        # Step 5: Verify created relationships
        await self._verify_cluster_relationships()
    
    def _parse_formula_elements(self, formula: str) -> Dict[str, int]:
        """Parse chemical formula to extract elements and their counts"""
        elements = {}
        
        # Handle various formula formats
        # Simple pattern for element + number (e.g., C4, N8, S2)
        pattern = r'([A-Z][a-z]?)(\d*)'
        matches = re.findall(pattern, formula)
        
        for element, count_str in matches:
            count = int(count_str) if count_str else 1
            if element in elements:
                elements[element] += count
            else:
                elements[element] = count
        
        return elements
    
    async def _verify_cluster_relationships(self):
        """Verify the created cluster size relationships"""
        print("\n🔍 Verifying cluster size relationships...")
        
        verification_query = """
        MATCH (smaller:Entry)-[r:CLUSTER_SIZE_SERIES]->(larger:Entry)
        RETURN r.element as element, 
               r.smaller_formula as smaller_formula,
               r.larger_formula as larger_formula,
               r.smaller_size as smaller_size,
               r.larger_size as larger_size,
               r.confidence as confidence
        ORDER BY r.element, r.smaller_size
        """
        
        results = await self.memgraph_client.execute_query(verification_query)
        
        print(f"📊 Verification: Found {len(results)} CLUSTER_SIZE_SERIES relationships")
        
        current_element = None
        for result in results:
            element = result.get('element', '')
            smaller_formula = result.get('smaller_formula', '')
            larger_formula = result.get('larger_formula', '')
            smaller_size = result.get('smaller_size', 0)
            larger_size = result.get('larger_size', 0)
            confidence = result.get('confidence', 0.0)
            
            if element != current_element:
                print(f"\n{element} cluster series:")
                current_element = element
            
            print(f"  {smaller_formula} ({smaller_size}) → {larger_formula} ({larger_size}) [confidence: {confidence}]")

async def main():
    """Main function to create cluster size relationships"""
    analyzer = ClusterSizeAnalyzer()
    await analyzer.find_cluster_size_relationships()

if __name__ == "__main__":
    asyncio.run(main())