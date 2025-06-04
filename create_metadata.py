#!/usr/bin/env python3
"""
Metadata and Attribution Generator

Creates proper metadata files with attribution information
for materials science workflow analysis results.
"""

import json
import datetime
from pathlib import Path
import asyncio
from src.claude_orchestrator import ClaudeWorkflowOrchestrator

class MetadataGenerator:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.orchestrator = ClaudeWorkflowOrchestrator()
    
    async def generate_analysis_metadata(self, dataset_id="YDXZgPooRb-31Niq48ODPA", 
                                       user_name="", institution="", 
                                       purpose="", funding=""):
        """Generate comprehensive metadata for the analysis"""
        
        # Get dataset statistics
        await self.orchestrator.memgraph_client.connect()
        summary = await self.orchestrator.get_dataset_summary_for_claude(dataset_id)
        
        # Count relationships created
        rel_query = "MATCH ()-[r]->() RETURN type(r) as rel_type, count(r) as count"
        relationships = await self.orchestrator.memgraph_client.execute_query(rel_query)
        
        metadata = {
            "analysis_info": {
                "dataset_id": dataset_id,
                "analysis_date": datetime.datetime.now().isoformat(),
                "system_version": "1.0.0",
                "analyst": {
                    "name": user_name or "Anonymous",
                    "institution": institution or "Not specified",
                    "purpose": purpose or "Materials science workflow analysis"
                }
            },
            
            "dataset_statistics": {
                "total_entries": summary.get("total_entries", 0),
                "unique_formulas": len(summary.get("top_formulas", {})),
                "entry_types": summary.get("entry_types", {}),
                "upload_clusters": len(summary.get("upload_clusters", {}))
            },
            
            "relationships_created": {
                rel["rel_type"]: rel["count"] for rel in relationships
            },
            
            "technology_stack": {
                "data_source": "NOMAD Materials Science Database",
                "ai_system": "Claude Code (Anthropic)",
                "graph_database": "Memgraph",
                "analysis_framework": "NOMAD Workflow Recreator"
            },
            
            "citations": {
                "nomad_database": {
                    "title": "The NOMAD laboratory: from data sharing to artificial intelligence",
                    "authors": ["Claudia Draxl", "Matthias Scheffler"],
                    "journal": "Journal of Physics: Materials",
                    "volume": "2",
                    "number": "3",
                    "pages": "036001",
                    "year": "2019",
                    "doi": "10.1088/2515-7639/ab13bb"
                },
                "claude_code": {
                    "title": "Claude Code: AI-Powered Development Environment",
                    "author": "Anthropic",
                    "year": "2024",
                    "url": "https://claude.ai/code"
                },
                "this_system": {
                    "title": "NOMAD Workflow Recreator: AI-Driven Materials Science Workflow Analysis",
                    "author": user_name or "[User]",
                    "institution": institution,
                    "year": "2025",
                    "funding": funding
                }
            },
            
            "acknowledgments": {
                "data_provider": "NOMAD Materials Science Database and Laboratory",
                "ai_system": "Claude Code AI Assistant for intelligent analysis",
                "infrastructure": "Memgraph graph database for workflow relationships",
                "funding": funding or "Not specified"
            }
        }
        
        return metadata
    
    def create_attribution_file(self, metadata, output_file="analysis_attribution.json"):
        """Create a detailed attribution file"""
        output_path = self.project_root / output_file
        
        with open(output_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"✅ Attribution metadata saved to: {output_path}")
        return output_path
    
    def create_bibtex_file(self, metadata, output_file="citations.bib"):
        """Create a BibTeX file with all necessary citations"""
        output_path = self.project_root / output_file
        
        bibtex_content = f"""% Citations for NOMAD Workflow Analysis
% Generated on {metadata['analysis_info']['analysis_date']}

% Main data source
@article{{nomad_database,
  title={{{metadata['citations']['nomad_database']['title']}}},
  author={{{' and '.join(metadata['citations']['nomad_database']['authors'])}}},
  journal={{{metadata['citations']['nomad_database']['journal']}}},
  volume={{{metadata['citations']['nomad_database']['volume']}}},
  number={{{metadata['citations']['nomad_database']['number']}}},
  pages={{{metadata['citations']['nomad_database']['pages']}}},
  year={{{metadata['citations']['nomad_database']['year']}}},
  publisher={{IOP Publishing}},
  doi={{{metadata['citations']['nomad_database']['doi']}}}
}}

% AI analysis system
@software{{claude_code,
  title={{{metadata['citations']['claude_code']['title']}}},
  author={{{metadata['citations']['claude_code']['author']}}},
  year={{{metadata['citations']['claude_code']['year']}}},
  url={{{metadata['citations']['claude_code']['url']}}},
  note={{Used for intelligent materials science workflow analysis}}
}}

% This analysis system
@software{{nomad_workflow_recreator,
  title={{{metadata['citations']['this_system']['title']}}},
  author={{{metadata['citations']['this_system']['author']}}},
  institution={{{metadata['citations']['this_system']['institution']}}},
  year={{{metadata['citations']['this_system']['year']}}},
  note={{Dataset: {metadata['analysis_info']['dataset_id']}, Entries: {metadata['dataset_statistics']['total_entries']}}},
  funding={{{metadata['citations']['this_system']['funding']}}}
}}

% Dataset-specific citation
@dataset{{nomad_dataset_{metadata['analysis_info']['dataset_id']},
  title={{NOMAD Dataset {metadata['analysis_info']['dataset_id']}}},
  publisher={{NOMAD Laboratory}},
  year={{{metadata['analysis_info']['analysis_date'][:4]}}},
  url={{https://nomad-lab.eu/prod/v1/staging/gui/search/entries}},
  note={{Analyzed on {metadata['analysis_info']['analysis_date'][:10]}}}
}}
"""
        
        with open(output_path, 'w') as f:
            f.write(bibtex_content)
        
        print(f"✅ BibTeX citations saved to: {output_path}")
        return output_path
    
    def create_readme_attribution(self, metadata, output_file="ANALYSIS_README.md"):
        """Create a README with attribution information"""
        output_path = self.project_root / output_file
        
        readme_content = f"""# Materials Science Workflow Analysis Results

## Analysis Summary

- **Dataset**: {metadata['analysis_info']['dataset_id']}
- **Analysis Date**: {metadata['analysis_info']['analysis_date'][:10]}
- **Analyst**: {metadata['analysis_info']['analyst']['name']}
- **Institution**: {metadata['analysis_info']['analyst']['institution']}
- **Purpose**: {metadata['analysis_info']['analyst']['purpose']}

## Dataset Statistics

- **Total Entries**: {metadata['dataset_statistics']['total_entries']:,}
- **Unique Chemical Formulas**: {metadata['dataset_statistics']['unique_formulas']}
- **Entry Types**: {', '.join(metadata['dataset_statistics']['entry_types'].keys())}

## Relationships Created

{chr(10).join([f"- **{rel_type}**: {count:,} relationships" for rel_type, count in metadata['relationships_created'].items()])}

## Technology Stack

- **Data Source**: {metadata['technology_stack']['data_source']}
- **AI Analysis**: {metadata['technology_stack']['ai_system']}
- **Graph Database**: {metadata['technology_stack']['graph_database']}
- **Framework**: {metadata['technology_stack']['analysis_framework']}

## Citations

### Primary Data Source
{metadata['citations']['nomad_database']['authors'][0]} et al., "{metadata['citations']['nomad_database']['title']}", *{metadata['citations']['nomad_database']['journal']}* **{metadata['citations']['nomad_database']['volume']}**, {metadata['citations']['nomad_database']['pages']} ({metadata['citations']['nomad_database']['year']}). DOI: {metadata['citations']['nomad_database']['doi']}

### AI Analysis System
{metadata['citations']['claude_code']['author']}, "{metadata['citations']['claude_code']['title']}" ({metadata['citations']['claude_code']['year']}). URL: {metadata['citations']['claude_code']['url']}

## Acknowledgments

- **Data Provider**: {metadata['acknowledgments']['data_provider']}
- **AI System**: {metadata['acknowledgments']['ai_system']}
- **Infrastructure**: {metadata['acknowledgments']['infrastructure']}
- **Funding**: {metadata['acknowledgments']['funding']}

## How to Cite This Analysis

```bibtex
@software{{nomad_workflow_analysis,
  title={{Materials Science Workflow Analysis of {metadata['analysis_info']['dataset_id']}}},
  author={{{metadata['analysis_info']['analyst']['name']}}},
  institution={{{metadata['analysis_info']['analyst']['institution']}}},
  year={{{metadata['analysis_info']['analysis_date'][:4]}}},
  note={{Powered by Claude Code and NOMAD Database}}
}}
```

## Files Included

- `analysis_attribution.json` - Complete metadata
- `citations.bib` - BibTeX citations
- `ANALYSIS_README.md` - This summary file

---

*Generated by NOMAD Workflow Recreator v{metadata['analysis_info']['system_version']}*
"""
        
        with open(output_path, 'w') as f:
            f.write(readme_content)
        
        print(f"✅ Analysis README saved to: {output_path}")
        return output_path

async def main():
    """Interactive metadata generation"""
    print("📝 NOMAD Workflow Analysis Attribution Generator")
    print("=" * 55)
    
    # Get user information
    user_name = input("Your name: ").strip()
    institution = input("Institution/Organization: ").strip()
    purpose = input("Analysis purpose: ").strip()
    funding = input("Funding source (optional): ").strip()
    dataset_id = input("Dataset ID (or Enter for default): ").strip() or "YDXZgPooRb-31Niq48ODPA"
    
    generator = MetadataGenerator()
    
    print(f"\n🔍 Generating metadata for dataset {dataset_id}...")
    metadata = await generator.generate_analysis_metadata(
        dataset_id=dataset_id,
        user_name=user_name,
        institution=institution,
        purpose=purpose,
        funding=funding
    )
    
    print(f"\n📁 Creating attribution files...")
    generator.create_attribution_file(metadata)
    generator.create_bibtex_file(metadata)
    generator.create_readme_attribution(metadata)
    
    print(f"\n✅ Attribution files created successfully!")
    print(f"📊 Analysis statistics:")
    print(f"   - Entries analyzed: {metadata['dataset_statistics']['total_entries']:,}")
    print(f"   - Relationships created: {sum(metadata['relationships_created'].values()):,}")
    print(f"   - Chemical formulas: {metadata['dataset_statistics']['unique_formulas']}")

if __name__ == "__main__":
    asyncio.run(main())