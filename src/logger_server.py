#!/usr/bin/env python3
"""
Logger MCP Server

Tracks tool usage, suggestions, and when Claude attempts to use non-existent tools.
Provides a dedicated logging infrastructure separate from the data servers.
"""

import asyncio
import os
import json
from typing import Any, Dict, List, Optional
from datetime import datetime
from pathlib import Path
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool, 
    TextContent, 
    CallToolRequest, 
    CallToolResult
)

class LoggerService:
    def __init__(self):
        self.log_dir = Path(os.getenv("LOG_DIR", "./claude_logs"))
        self.log_dir.mkdir(exist_ok=True)
        
        # Different log files for different purposes
        self.tool_usage_log = self.log_dir / "tool_usage.jsonl"
        self.suggestions_log = self.log_dir / "suggestions.jsonl"
        self.missing_tools_log = self.log_dir / "missing_tools.jsonl"
        self.session_log = self.log_dir / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
    
    async def log_tool_usage(self, tool_name: str, arguments: Dict[str, Any], 
                            success: bool, duration_ms: Optional[float] = None,
                            error: Optional[str] = None) -> Dict[str, Any]:
        """Log successful or failed tool usage"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "tool_name": tool_name,
            "arguments": arguments,
            "success": success,
            "duration_ms": duration_ms,
            "error": error
        }
        
        # Write to tool usage log
        with open(self.tool_usage_log, 'a') as f:
            f.write(json.dumps(entry) + '\n')
        
        # Also write to session log
        with open(self.session_log, 'a') as f:
            f.write(json.dumps(entry) + '\n')
        
        return entry
    
    async def log_suggestion(self, suggestion_type: str, title: str, 
                           description: str, code: Optional[str] = None,
                           context: Optional[Dict[str, Any]] = None) -> str:
        """Log a suggestion for new tools or improvements"""
        suggestion_id = f"sug_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(title) % 1000}"
        
        entry = {
            "suggestion_id": suggestion_id,
            "timestamp": datetime.now().isoformat(),
            "type": suggestion_type,
            "title": title,
            "description": description,
            "code": code,
            "context": context,
            "status": "pending"
        }
        
        with open(self.suggestions_log, 'a') as f:
            f.write(json.dumps(entry) + '\n')
        
        return suggestion_id
    
    async def log_missing_tool(self, attempted_tool: str, similar_tools: List[str],
                              context: Optional[str] = None) -> None:
        """Log when Claude tries to use a tool that doesn't exist"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "attempted_tool": attempted_tool,
            "similar_existing_tools": similar_tools,
            "context": context
        }
        
        with open(self.missing_tools_log, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    
    async def get_tool_usage_stats(self, tool_name: Optional[str] = None,
                                 last_n_hours: Optional[int] = None) -> Dict[str, Any]:
        """Get statistics about tool usage"""
        stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "tools_used": {},
            "errors": []
        }
        
        if not self.tool_usage_log.exists():
            return stats
        
        cutoff_time = None
        if last_n_hours:
            cutoff_time = datetime.now().timestamp() - (last_n_hours * 3600)
        
        with open(self.tool_usage_log, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    
                    # Check time filter
                    if cutoff_time:
                        entry_time = datetime.fromisoformat(entry['timestamp']).timestamp()
                        if entry_time < cutoff_time:
                            continue
                    
                    # Check tool filter
                    if tool_name and entry['tool_name'] != tool_name:
                        continue
                    
                    stats['total_calls'] += 1
                    
                    if entry['success']:
                        stats['successful_calls'] += 1
                    else:
                        stats['failed_calls'] += 1
                        if entry.get('error'):
                            stats['errors'].append({
                                "tool": entry['tool_name'],
                                "error": entry['error'],
                                "timestamp": entry['timestamp']
                            })
                    
                    tool = entry['tool_name']
                    if tool not in stats['tools_used']:
                        stats['tools_used'][tool] = {
                            "calls": 0,
                            "successes": 0,
                            "failures": 0,
                            "avg_duration_ms": 0
                        }
                    
                    stats['tools_used'][tool]['calls'] += 1
                    if entry['success']:
                        stats['tools_used'][tool]['successes'] += 1
                    else:
                        stats['tools_used'][tool]['failures'] += 1
                    
                    if entry.get('duration_ms'):
                        current_avg = stats['tools_used'][tool]['avg_duration_ms']
                        count = stats['tools_used'][tool]['calls']
                        new_avg = (current_avg * (count - 1) + entry['duration_ms']) / count
                        stats['tools_used'][tool]['avg_duration_ms'] = new_avg
                
                except json.JSONDecodeError:
                    continue
        
        return stats
    
    async def get_suggestions(self, suggestion_type: Optional[str] = None,
                            status: str = "pending") -> List[Dict[str, Any]]:
        """Get logged suggestions"""
        suggestions = []
        
        if not self.suggestions_log.exists():
            return suggestions
        
        with open(self.suggestions_log, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    
                    if suggestion_type and entry['type'] != suggestion_type:
                        continue
                    
                    if status and entry.get('status', 'pending') != status:
                        continue
                    
                    suggestions.append(entry)
                
                except json.JSONDecodeError:
                    continue
        
        return suggestions
    
    async def get_missing_tools_report(self) -> Dict[str, Any]:
        """Get report on tools Claude tried to use that don't exist"""
        report = {
            "total_attempts": 0,
            "unique_tools": set(),
            "frequency": {},
            "recent_attempts": []
        }
        
        if not self.missing_tools_log.exists():
            return {
                "total_attempts": 0,
                "unique_tools": [],
                "frequency": {},
                "recent_attempts": []
            }
        
        with open(self.missing_tools_log, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    report['total_attempts'] += 1
                    report['unique_tools'].add(entry['attempted_tool'])
                    
                    tool = entry['attempted_tool']
                    report['frequency'][tool] = report['frequency'].get(tool, 0) + 1
                    
                    report['recent_attempts'].append(entry)
                
                except json.JSONDecodeError:
                    continue
        
        # Convert set to list and limit recent attempts
        report['unique_tools'] = list(report['unique_tools'])
        report['recent_attempts'] = report['recent_attempts'][-10:]  # Last 10
        
        return report

# Create logger service
logger_service = LoggerService()

# Create MCP server
server = Server("logger-mcp-server")

@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available logging tools"""
    return [
        Tool(
            name="log_tool_usage",
            description="Log tool usage (success or failure) - should be called by other MCP servers",
            inputSchema={
                "type": "object",
                "properties": {
                    "tool_name": {
                        "type": "string",
                        "description": "Name of the tool that was called"
                    },
                    "arguments": {
                        "type": "object",
                        "description": "Arguments passed to the tool"
                    },
                    "success": {
                        "type": "boolean",
                        "description": "Whether the tool call succeeded"
                    },
                    "duration_ms": {
                        "type": "number",
                        "description": "Duration of the tool call in milliseconds"
                    },
                    "error": {
                        "type": "string",
                        "description": "Error message if the tool failed"
                    }
                },
                "required": ["tool_name", "arguments", "success"]
            }
        ),
        Tool(
            name="log_suggestion",
            description="Log a suggestion for a new tool, script, or improvement",
            inputSchema={
                "type": "object",
                "properties": {
                    "suggestion_type": {
                        "type": "string",
                        "enum": ["new_tool", "script", "improvement", "bug_fix", "feature"],
                        "description": "Type of suggestion"
                    },
                    "title": {
                        "type": "string",
                        "description": "Short title for the suggestion"
                    },
                    "description": {
                        "type": "string",
                        "description": "Detailed description"
                    },
                    "code": {
                        "type": "string",
                        "description": "Optional code snippet"
                    },
                    "context": {
                        "type": "object",
                        "description": "Additional context"
                    }
                },
                "required": ["suggestion_type", "title", "description"]
            }
        ),
        Tool(
            name="log_missing_tool",
            description="Log when attempting to use a tool that doesn't exist",
            inputSchema={
                "type": "object",
                "properties": {
                    "attempted_tool": {
                        "type": "string",
                        "description": "Name of the tool that was attempted"
                    },
                    "similar_tools": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of similar existing tools"
                    },
                    "context": {
                        "type": "string",
                        "description": "Context about what was being attempted"
                    }
                },
                "required": ["attempted_tool", "similar_tools"]
            }
        ),
        Tool(
            name="get_tool_usage_stats",
            description="Get statistics about tool usage",
            inputSchema={
                "type": "object",
                "properties": {
                    "tool_name": {
                        "type": "string",
                        "description": "Filter by specific tool name"
                    },
                    "last_n_hours": {
                        "type": "number",
                        "description": "Limit to last N hours"
                    }
                }
            }
        ),
        Tool(
            name="get_suggestions",
            description="Retrieve logged suggestions",
            inputSchema={
                "type": "object",
                "properties": {
                    "suggestion_type": {
                        "type": "string",
                        "description": "Filter by suggestion type"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["pending", "reviewed", "implemented", "rejected"],
                        "default": "pending"
                    }
                }
            }
        ),
        Tool(
            name="get_missing_tools_report",
            description="Get report on tools Claude tried to use that don't exist",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
    """Handle tool calls"""
    
    try:
        if name == "log_tool_usage":
            entry = await logger_service.log_tool_usage(
                tool_name=arguments["tool_name"],
                arguments=arguments["arguments"],
                success=arguments["success"],
                duration_ms=arguments.get("duration_ms"),
                error=arguments.get("error")
            )
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"Tool usage logged: {arguments['tool_name']} - {'Success' if arguments['success'] else 'Failed'}"
                )]
            )
        
        elif name == "log_suggestion":
            suggestion_id = await logger_service.log_suggestion(
                suggestion_type=arguments["suggestion_type"],
                title=arguments["title"],
                description=arguments["description"],
                code=arguments.get("code"),
                context=arguments.get("context")
            )
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"Suggestion logged with ID: {suggestion_id}\n"
                         f"Type: {arguments['suggestion_type']}\n"
                         f"Title: {arguments['title']}"
                )]
            )
        
        elif name == "log_missing_tool":
            await logger_service.log_missing_tool(
                attempted_tool=arguments["attempted_tool"],
                similar_tools=arguments["similar_tools"],
                context=arguments.get("context")
            )
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"Missing tool logged: {arguments['attempted_tool']}\n"
                         f"Similar tools: {', '.join(arguments['similar_tools'])}"
                )]
            )
        
        elif name == "get_tool_usage_stats":
            stats = await logger_service.get_tool_usage_stats(
                tool_name=arguments.get("tool_name"),
                last_n_hours=arguments.get("last_n_hours")
            )
            
            stats_text = "Tool Usage Statistics:\n\n"
            stats_text += f"Total calls: {stats['total_calls']}\n"
            stats_text += f"Successful: {stats['successful_calls']}\n"
            stats_text += f"Failed: {stats['failed_calls']}\n\n"
            
            if stats['tools_used']:
                stats_text += "By Tool:\n"
                for tool, data in sorted(stats['tools_used'].items(), 
                                       key=lambda x: x[1]['calls'], reverse=True):
                    stats_text += f"\n{tool}:\n"
                    stats_text += f"  Calls: {data['calls']}\n"
                    stats_text += f"  Success rate: {data['successes']/data['calls']*100:.1f}%\n"
                    if data['avg_duration_ms'] > 0:
                        stats_text += f"  Avg duration: {data['avg_duration_ms']:.1f}ms\n"
            
            if stats['errors']:
                stats_text += f"\nRecent errors: {len(stats['errors'])}"
            
            return CallToolResult(
                content=[TextContent(type="text", text=stats_text)]
            )
        
        elif name == "get_suggestions":
            suggestions = await logger_service.get_suggestions(
                suggestion_type=arguments.get("suggestion_type"),
                status=arguments.get("status", "pending")
            )
            
            suggestions_text = f"Suggestions ({arguments.get('status', 'pending')}):\n\n"
            
            if not suggestions:
                suggestions_text += "No suggestions found."
            else:
                for i, sug in enumerate(suggestions[:20], 1):  # Limit to 20
                    suggestions_text += f"{i}. [{sug['type']}] {sug['title']}\n"
                    suggestions_text += f"   ID: {sug['suggestion_id']}\n"
                    suggestions_text += f"   Time: {sug['timestamp']}\n"
                    suggestions_text += f"   Description: {sug['description'][:100]}...\n"
                    if sug.get('code'):
                        suggestions_text += f"   Has code: Yes\n"
                    suggestions_text += "\n"
            
            suggestions_text += f"\nTotal: {len(suggestions)} suggestions"
            
            return CallToolResult(
                content=[TextContent(type="text", text=suggestions_text)]
            )
        
        elif name == "get_missing_tools_report":
            report = await logger_service.get_missing_tools_report()
            
            report_text = "Missing Tools Report:\n\n"
            report_text += f"Total attempts: {report['total_attempts']}\n"
            report_text += f"Unique tools: {len(report['unique_tools'])}\n\n"
            
            if report['frequency']:
                report_text += "Most frequently attempted:\n"
                sorted_tools = sorted(report['frequency'].items(), 
                                    key=lambda x: x[1], reverse=True)
                for tool, count in sorted_tools[:10]:
                    report_text += f"  {tool}: {count} times\n"
            
            if report['recent_attempts']:
                report_text += "\nRecent attempts:\n"
                for attempt in report['recent_attempts'][-5:]:
                    report_text += f"  - {attempt['attempted_tool']} at {attempt['timestamp']}\n"
                    if attempt.get('context'):
                        report_text += f"    Context: {attempt['context'][:50]}...\n"
            
            return CallToolResult(
                content=[TextContent(type="text", text=report_text)]
            )
        
        else:
            # Log this as a missing tool!
            await logger_service.log_missing_tool(
                attempted_tool=name,
                similar_tools=[],
                context=f"Called with arguments: {arguments}"
            )
            
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unknown tool: {name}")]
            )
    
    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error executing {name}: {str(e)}")]
        )

async def main():
    """Main entry point for the logger MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())