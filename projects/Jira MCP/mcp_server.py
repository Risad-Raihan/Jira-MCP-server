#!/usr/bin/env python3
"""
JIRA MCP Server - Comprehensive JIRA integration for Claude and other AI assistants
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Sequence
from urllib.parse import urljoin
import aiohttp
import base64
from dataclasses import dataclass

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class JIRAConfig:
    """JIRA configuration"""
    base_url: str
    username: str
    api_token: str
    default_project_key: str = ""

class JIRAMCPServer:
    """JIRA MCP Server implementation"""
    
    def __init__(self):
        self.config: Optional[JIRAConfig] = None
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def initialize(self, config: JIRAConfig):
        """Initialize the JIRA client"""
        self.config = config
        
        # Create authentication header
        auth_string = f"{config.username}:{config.api_token}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        # Create aiohttp session with authentication
        headers = {
            'Authorization': f'Basic {auth_b64}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        self.session = aiohttp.ClientSession(
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=30)
        )
        
        logger.info(f"Initialized JIRA client for {config.base_url}")
    
    async def close(self):
        """Close the HTTP session"""
        if self.session:
            await self.session.close()
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make authenticated request to JIRA API"""
        if not self.session or not self.config:
            raise ValueError("JIRA client not initialized")
            
        url = urljoin(self.config.base_url, f"/rest/api/3/{endpoint}")
        
        try:
            async with self.session.request(method, url, **kwargs) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"JIRA API request failed: {e}")
            raise
    
    async def get_projects(self) -> List[Dict[str, Any]]:
        """Get all accessible projects"""
        return await self._make_request("GET", "project")
    
    async def get_project_details(self, project_key: str) -> Dict[str, Any]:
        """Get detailed information about a specific project"""
        return await self._make_request("GET", f"project/{project_key}")
    
    async def search_issues(self, jql: str, fields: Optional[List[str]] = None, max_results: int = 50) -> Dict[str, Any]:
        """Search for issues using JQL"""
        params = {
            'jql': jql,
            'maxResults': max_results,
            'fields': ','.join(fields) if fields else '*all'
        }
        return await self._make_request("GET", "search", params=params)
    
    async def get_issue(self, issue_key: str) -> Dict[str, Any]:
        """Get detailed information about a specific issue"""
        return await self._make_request("GET", f"issue/{issue_key}")
    
    async def create_issue(self, issue_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new issue"""
        return await self._make_request("POST", "issue", json=issue_data)
    
    async def update_issue(self, issue_key: str, update_data: Dict[str, Any]) -> None:
        """Update an existing issue"""
        await self._make_request("PUT", f"issue/{issue_key}", json=update_data)
    
    async def transition_issue(self, issue_key: str, transition_id: str) -> None:
        """Transition an issue to a new status"""
        transition_data = {
            "transition": {"id": transition_id}
        }
        await self._make_request("POST", f"issue/{issue_key}/transitions", json=transition_data)
    
    async def get_issue_transitions(self, issue_key: str) -> List[Dict[str, Any]]:
        """Get available transitions for an issue"""
        result = await self._make_request("GET", f"issue/{issue_key}/transitions")
        return result.get('transitions', [])
    
    async def add_comment(self, issue_key: str, comment: str) -> Dict[str, Any]:
        """Add a comment to an issue"""
        comment_data = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "text": comment,
                                "type": "text"
                            }
                        ]
                    }
                ]
            }
        }
        return await self._make_request("POST", f"issue/{issue_key}/comment", json=comment_data)
    
    async def get_issue_types(self, project_key: str) -> List[Dict[str, Any]]:
        """Get available issue types for a project"""
        project = await self.get_project_details(project_key)
        return project.get('issueTypes', [])
    
    async def get_epics(self, project_key: str) -> List[Dict[str, Any]]:
        """Get all epics in a project"""
        jql = f'project = "{project_key}" AND issuetype = Epic ORDER BY created DESC'
        result = await self.search_issues(jql)
        return result.get('issues', [])
    
    async def link_issue_to_epic(self, issue_key: str, epic_key: str) -> None:
        """Link an issue to an epic"""
        update_data = {
            "fields": {
                "parent": {"key": epic_key}
            }
        }
        await self.update_issue(issue_key, update_data)

# Initialize the MCP server
server = Server("jira-mcp")
jira_client = JIRAMCPServer()

@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available JIRA tools"""
    return [
        Tool(
            name="jira_get_projects",
            description="Get all accessible JIRA projects",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="jira_get_project_details",
            description="Get detailed information about a specific JIRA project",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_key": {
                        "type": "string",
                        "description": "The project key (e.g., 'PROJ')"
                    }
                },
                "required": ["project_key"]
            }
        ),
        Tool(
            name="jira_search_issues",
            description="Search for issues using JQL (JIRA Query Language)",
            inputSchema={
                "type": "object",
                "properties": {
                    "jql": {
                        "type": "string",
                        "description": "JQL query string (e.g., 'project = PROJ AND status = \"In Progress\"')"
                    },
                    "fields": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of fields to return (optional)"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 50)",
                        "default": 50
                    }
                },
                "required": ["jql"]
            }
        ),
        Tool(
            name="jira_get_issue",
            description="Get detailed information about a specific issue",
            inputSchema={
                "type": "object",
                "properties": {
                    "issue_key": {
                        "type": "string",
                        "description": "The issue key (e.g., 'PROJ-123')"
                    }
                },
                "required": ["issue_key"]
            }
        ),
        Tool(
            name="jira_create_issue",
            description="Create a new JIRA issue (story, task, bug, epic, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_key": {
                        "type": "string",
                        "description": "The project key where to create the issue"
                    },
                    "issue_type": {
                        "type": "string",
                        "description": "Issue type (Story, Task, Bug, Epic, Sub-task, etc.)"
                    },
                    "summary": {
                        "type": "string",
                        "description": "Issue title/summary"
                    },
                    "description": {
                        "type": "string",
                        "description": "Detailed description of the issue (optional)"
                    },
                    "assignee": {
                        "type": "string",
                        "description": "Assignee username (optional)"
                    },
                    "priority": {
                        "type": "string",
                        "description": "Priority (Highest, High, Medium, Low, Lowest) - optional"
                    },
                    "labels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of labels (optional)"
                    },
                    "parent_key": {
                        "type": "string",
                        "description": "Parent issue key (for sub-tasks or linking to epics)"
                    }
                },
                "required": ["project_key", "issue_type", "summary"]
            }
        ),
        Tool(
            name="jira_update_issue",
            description="Update an existing JIRA issue",
            inputSchema={
                "type": "object",
                "properties": {
                    "issue_key": {
                        "type": "string",
                        "description": "The issue key to update"
                    },
                    "summary": {
                        "type": "string",
                        "description": "New summary/title (optional)"
                    },
                    "description": {
                        "type": "string",
                        "description": "New description (optional)"
                    },
                    "assignee": {
                        "type": "string",
                        "description": "New assignee username (optional)"
                    },
                    "priority": {
                        "type": "string",
                        "description": "New priority (optional)"
                    },
                    "labels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "New labels list (optional)"
                    }
                },
                "required": ["issue_key"]
            }
        ),
        Tool(
            name="jira_transition_issue",
            description="Change the status of an issue (e.g., move from To Do to In Progress)",
            inputSchema={
                "type": "object",
                "properties": {
                    "issue_key": {
                        "type": "string",
                        "description": "The issue key to transition"
                    },
                    "transition_name": {
                        "type": "string",
                        "description": "Name of the transition (e.g., 'Start Progress', 'Done', 'Close Issue')"
                    }
                },
                "required": ["issue_key", "transition_name"]
            }
        ),
        Tool(
            name="jira_get_available_transitions",
            description="Get all available status transitions for an issue",
            inputSchema={
                "type": "object",
                "properties": {
                    "issue_key": {
                        "type": "string",
                        "description": "The issue key"
                    }
                },
                "required": ["issue_key"]
            }
        ),
        Tool(
            name="jira_add_comment",
            description="Add a comment to a JIRA issue",
            inputSchema={
                "type": "object",
                "properties": {
                    "issue_key": {
                        "type": "string",
                        "description": "The issue key"
                    },
                    "comment": {
                        "type": "string",
                        "description": "The comment text"
                    }
                },
                "required": ["issue_key", "comment"]
            }
        ),
        Tool(
            name="jira_get_epics",
            description="Get all epics in a project",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_key": {
                        "type": "string",
                        "description": "The project key"
                    }
                },
                "required": ["project_key"]
            }
        ),
        Tool(
            name="jira_get_issue_types",
            description="Get available issue types for a project",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_key": {
                        "type": "string",
                        "description": "The project key"
                    }
                },
                "required": ["project_key"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> List[TextContent]:
    """Handle tool calls"""
    try:
        if name == "jira_get_projects":
            projects = await jira_client.get_projects()
            return [TextContent(type="text", text=json.dumps(projects, indent=2))]
        
        elif name == "jira_get_project_details":
            project = await jira_client.get_project_details(arguments["project_key"])
            return [TextContent(type="text", text=json.dumps(project, indent=2))]
        
        elif name == "jira_search_issues":
            result = await jira_client.search_issues(
                arguments["jql"],
                arguments.get("fields"),
                arguments.get("max_results", 50)
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "jira_get_issue":
            issue = await jira_client.get_issue(arguments["issue_key"])
            return [TextContent(type="text", text=json.dumps(issue, indent=2))]
        
        elif name == "jira_create_issue":
            # Build issue data
            issue_data = {
                "fields": {
                    "project": {"key": arguments["project_key"]},
                    "issuetype": {"name": arguments["issue_type"]},
                    "summary": arguments["summary"]
                }
            }
            
            # Add optional fields
            if "description" in arguments:
                issue_data["fields"]["description"] = {
                    "type": "doc",
                    "version": 1,
                    "content": [{
                        "type": "paragraph",
                        "content": [{
                            "text": arguments["description"],
                            "type": "text"
                        }]
                    }]
                }
            
            if "assignee" in arguments:
                issue_data["fields"]["assignee"] = {"name": arguments["assignee"]}
            
            if "priority" in arguments:
                issue_data["fields"]["priority"] = {"name": arguments["priority"]}
            
            if "labels" in arguments:
                issue_data["fields"]["labels"] = arguments["labels"]
            
            if "parent_key" in arguments:
                issue_data["fields"]["parent"] = {"key": arguments["parent_key"]}
            
            result = await jira_client.create_issue(issue_data)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "jira_update_issue":
            # Build update data
            update_data = {"fields": {}}
            
            if "summary" in arguments:
                update_data["fields"]["summary"] = arguments["summary"]
            
            if "description" in arguments:
                update_data["fields"]["description"] = {
                    "type": "doc",
                    "version": 1,
                    "content": [{
                        "type": "paragraph",
                        "content": [{
                            "text": arguments["description"],
                            "type": "text"
                        }]
                    }]
                }
            
            if "assignee" in arguments:
                update_data["fields"]["assignee"] = {"name": arguments["assignee"]}
            
            if "priority" in arguments:
                update_data["fields"]["priority"] = {"name": arguments["priority"]}
            
            if "labels" in arguments:
                update_data["fields"]["labels"] = arguments["labels"]
            
            await jira_client.update_issue(arguments["issue_key"], update_data)
            return [TextContent(type="text", text=f"Issue {arguments['issue_key']} updated successfully")]
        
        elif name == "jira_transition_issue":
            # First, get available transitions
            transitions = await jira_client.get_issue_transitions(arguments["issue_key"])
            
            # Find the transition by name
            transition_id = None
            for transition in transitions:
                if transition["name"].lower() == arguments["transition_name"].lower():
                    transition_id = transition["id"]
                    break
            
            if not transition_id:
                available = [t["name"] for t in transitions]
                return [TextContent(
                    type="text", 
                    text=f"Transition '{arguments['transition_name']}' not found. Available transitions: {available}"
                )]
            
            await jira_client.transition_issue(arguments["issue_key"], transition_id)
            return [TextContent(type="text", text=f"Issue {arguments['issue_key']} transitioned to {arguments['transition_name']}")]
        
        elif name == "jira_get_available_transitions":
            transitions = await jira_client.get_issue_transitions(arguments["issue_key"])
            return [TextContent(type="text", text=json.dumps(transitions, indent=2))]
        
        elif name == "jira_add_comment":
            result = await jira_client.add_comment(arguments["issue_key"], arguments["comment"])
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "jira_get_epics":
            epics = await jira_client.get_epics(arguments["project_key"])
            return [TextContent(type="text", text=json.dumps(epics, indent=2))]
        
        elif name == "jira_get_issue_types":
            issue_types = await jira_client.get_issue_types(arguments["project_key"])
            return [TextContent(type="text", text=json.dumps(issue_types, indent=2))]
        
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    
    except Exception as e:
        logger.error(f"Error handling tool call {name}: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]

async def main():
    """Main entry point"""
    # Load configuration from environment variables or config file
    import os
    
    # Load configuration with your JIRA details
    config = JIRAConfig(
        base_url=os.getenv("JIRA_BASE_URL", "https://risadsbrain.atlassian.net"),
        username=os.getenv("JIRA_USERNAME", "rrmalik66@gmail.com"),
        api_token=os.getenv("JIRA_API_TOKEN", "REDACTED"),
        default_project_key=os.getenv("JIRA_DEFAULT_PROJECT", "DAV1")
    )
    
    # Initialize the JIRA client
    await jira_client.initialize(config)
    
    try:
        # Run the MCP server
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream, 
                write_stream, 
                InitializationOptions(
                    server_name="jira-mcp",
                    server_version="1.0.0",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={}
                    )
                )
            )
    finally:
        await jira_client.close()

if __name__ == "__main__":
    asyncio.run(main())