#!/usr/bin/env python3
"""
Review and export Claude's suggestions from the logger
"""

import json
import argparse
from pathlib import Path
from datetime import datetime

def load_suggestions(log_file: Path) -> list:
    """Load suggestions from the log file"""
    suggestions = []
    if log_file.exists():
        with open(log_file, 'r') as f:
            for line in f:
                try:
                    suggestions.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return suggestions

def export_suggestions(suggestions: list, output_format: str, output_file: Path):
    """Export suggestions in the requested format"""
    
    if output_format == "markdown":
        with open(output_file, 'w') as f:
            f.write("# Claude Suggestions\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Group by type
            by_type = {}
            for sug in suggestions:
                sug_type = sug.get('type', 'unknown')
                if sug_type not in by_type:
                    by_type[sug_type] = []
                by_type[sug_type].append(sug)
            
            for sug_type, items in by_type.items():
                f.write(f"## {sug_type.replace('_', ' ').title()}\n\n")
                
                for i, sug in enumerate(items, 1):
                    f.write(f"### {i}. {sug['title']}\n")
                    f.write(f"**ID:** {sug['suggestion_id']}\n")
                    f.write(f"**Time:** {sug['timestamp']}\n")
                    f.write(f"**Status:** {sug.get('status', 'pending')}\n\n")
                    f.write(f"**Description:**\n{sug['description']}\n\n")
                    
                    if sug.get('code'):
                        f.write("**Code:**\n```python\n")
                        f.write(sug['code'])
                        f.write("\n```\n\n")
                    
                    if sug.get('context'):
                        f.write(f"**Context:** {json.dumps(sug['context'], indent=2)}\n\n")
                    
                    f.write("---\n\n")
    
    elif output_format == "json":
        with open(output_file, 'w') as f:
            json.dump(suggestions, f, indent=2)
    
    elif output_format == "python":
        # Export as executable Python scripts
        scripts_dir = output_file.parent / "suggested_scripts"
        scripts_dir.mkdir(exist_ok=True)
        
        script_count = 0
        for sug in suggestions:
            if sug.get('code') and sug['type'] in ['script', 'new_tool']:
                script_count += 1
                filename = f"{sug['suggestion_id']}_{sug['title'].replace(' ', '_')}.py"
                script_file = scripts_dir / filename
                
                with open(script_file, 'w') as f:
                    f.write("#!/usr/bin/env python3\n")
                    f.write(f'"""\n{sug["title"]}\n\n{sug["description"]}\n\n')
                    f.write(f'Suggested: {sug["timestamp"]}\nID: {sug["suggestion_id"]}\n"""\n\n')
                    f.write(sug['code'])
        
        with open(output_file, 'w') as f:
            f.write(f"Exported {script_count} scripts to {scripts_dir}\n")

def main():
    parser = argparse.ArgumentParser(description="Review Claude's suggestions")
    parser.add_argument("--log-dir", default="./claude_logs", help="Log directory")
    parser.add_argument("--format", choices=["markdown", "json", "python"], 
                       default="markdown", help="Output format")
    parser.add_argument("--output", help="Output file (default: suggestions.<format>)")
    parser.add_argument("--type", help="Filter by suggestion type")
    parser.add_argument("--status", default="pending", help="Filter by status")
    
    args = parser.parse_args()
    
    log_dir = Path(args.log_dir)
    suggestions_log = log_dir / "suggestions.jsonl"
    
    if not suggestions_log.exists():
        print(f"No suggestions log found at {suggestions_log}")
        return
    
    # Load suggestions
    all_suggestions = load_suggestions(suggestions_log)
    
    # Filter if requested
    filtered = []
    for sug in all_suggestions:
        if args.type and sug.get('type') != args.type:
            continue
        if args.status and sug.get('status', 'pending') != args.status:
            continue
        filtered.append(sug)
    
    print(f"Found {len(filtered)} suggestions (from {len(all_suggestions)} total)")
    
    # Determine output file
    if args.output:
        output_file = Path(args.output)
    else:
        ext = "md" if args.format == "markdown" else args.format
        output_file = Path(f"suggestions.{ext}")
    
    # Export
    export_suggestions(filtered, args.format, output_file)
    print(f"Exported to {output_file}")

if __name__ == "__main__":
    main()