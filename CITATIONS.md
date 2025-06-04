# Citations and Attributions

## How to Cite This Work

### For the NOMAD Workflow Recreator System
```bibtex
@software{nomad_workflow_recreator,
  title={NOMAD Workflow Recreator: AI-Driven Materials Science Workflow Analysis},
  author={[Your Name/Organization]},
  year={2025},
  url={https://github.com/[your-repo]/nomad_workflow_recreator},
  note={Powered by Claude Code and NOMAD Materials Science Database}
}
```

### For Claude Code Integration
```bibtex
@software{claude_code,
  title={Claude Code: AI-Powered Development Environment},
  author={Anthropic},
  year={2024},
  url={https://claude.ai/code},
  note={Used for intelligent materials science workflow analysis}
}
```

## Data Sources to Cite

### NOMAD Materials Science Database
```bibtex
@article{nomad_database,
  title={The NOMAD laboratory: from data sharing to artificial intelligence},
  author={Draxl, Claudia and Scheffler, Matthias},
  journal={Journal of Physics: Materials},
  volume={2},
  number={3},
  pages={036001},
  year={2019},
  publisher={IOP Publishing},
  doi={10.1088/2515-7639/ab13bb}
}
```

### Specific Dataset Citation
For dataset "YDXZgPooRb-31Niq48ODPA":
```bibtex
@dataset{nomad_numerical_errors,
  title={Numerical Errors FHI-aims Dataset},
  author={[Dataset Authors from NOMAD]},
  year={[Dataset Year]},
  publisher={NOMAD Laboratory},
  url={https://nomad-lab.eu/prod/v1/staging/gui/search/entries},
  note={Dataset ID: YDXZgPooRb-31Niq48ODPA}
}
```

## Technology Stack to Acknowledge

### Core Technologies
- **NOMAD API**: Materials science data source
- **Memgraph**: Graph database for workflow relationships  
- **Claude Code**: AI analysis and relationship inference
- **MCP (Model Context Protocol)**: AI-tool integration framework
- **FHI-aims**: Computational chemistry software (for dataset calculations)

### Python Libraries
- **pymgclient**: Memgraph Python client
- **httpx**: HTTP client for NOMAD API
- **pydantic**: Data validation and modeling

## Attribution in Publications

### Minimal Attribution
"Workflow analysis performed using the NOMAD Workflow Recreator system powered by Claude Code (Anthropic) and NOMAD Materials Science Database."

### Full Attribution
"Materials science workflow relationships were analyzed using a custom AI-driven system integrating the NOMAD Materials Science Database [1], Claude Code AI assistant [2], and Memgraph graph database. The system applies computational chemistry domain knowledge to infer semantic relationships between DFT calculations, creating scientifically meaningful workflow graphs for materials discovery."

## Acknowledgments Template

### For Research Papers
"We acknowledge the use of the NOMAD Materials Science Database and Laboratory for providing open access to computational materials data. Workflow analysis was enhanced using Claude Code AI integration. Graph database operations were performed using Memgraph."

### For Software/Code
```python
"""
NOMAD Workflow Recreator
Powered by:
- NOMAD Materials Science Database (nomad-lab.eu)
- Claude Code AI Assistant (anthropic.com)
- Memgraph Graph Database (memgraph.com)

Please cite appropriately when using this system.
"""
```

## Dataset-Specific Citations

When analyzing specific datasets, users should:
1. **Identify dataset authors** from NOMAD metadata
2. **Include dataset DOI** if available
3. **Cite original publications** that created the data
4. **Acknowledge computational resources** used for original calculations

## Compliance Notes

- **NOMAD Data**: Subject to Creative Commons licenses (check individual datasets)
- **Claude Code**: Commercial AI service with usage terms
- **This System**: [Specify your license - MIT, Apache 2.0, etc.]
- **Academic Use**: Generally permitted with proper attribution
- **Commercial Use**: Check individual component licenses

## How to Add Your Attribution

Users should modify the citation template above to include:
- **Your name/institution**
- **Publication details** if applicable  
- **Funding acknowledgments**
- **Specific use case description**