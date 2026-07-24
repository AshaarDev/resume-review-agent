"""MCP Server for resume review and creation tools."""

import asyncio
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent


app = Server("resume-server")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available resume tools."""
    return [
        Tool(
            name="review_resume",
            description="Review a resume and provide feedback on content, formatting, and improvements",
            inputSchema={
                "type": "object",
                "properties": {
                    "resume_text": {
                        "type": "string",
                        "description": "The resume content to review"
                    },
                    "job_description": {
                        "type": "string",
                        "description": "Optional job description to tailor feedback"
                    }
                },
                "required": ["resume_text"]
            }
        ),
        Tool(
            name="create_resume",
            description="Create a resume based on user information and preferences",
            inputSchema={
                "type": "object",
                "properties": {
                    "personal_info": {
                        "type": "object",
                        "description": "Personal information (name, email, phone, etc.)"
                    },
                    "work_experience": {
                        "type": "array",
                        "description": "List of work experiences"
                    },
                    "education": {
                        "type": "array",
                        "description": "List of education entries"
                    },
                    "skills": {
                        "type": "array",
                        "description": "List of skills"
                    },
                    "template": {
                        "type": "string",
                        "description": "Resume template style (modern, classic, minimal)"
                    }
                },
                "required": ["personal_info"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""
    if name == "review_resume":
        return await review_resume(arguments)
    elif name == "create_resume":
        return await create_resume(arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")


async def review_resume(arguments: dict) -> list[TextContent]:
    """Review a resume and provide feedback."""
    resume_text = arguments.get("resume_text", "")
    job_description = arguments.get("job_description", "")
    
    return [
        TextContent(
            type="text",
            text=f"Resume review tool called with resume length: {len(resume_text)} characters"
        )
    ]


async def create_resume(arguments: dict) -> list[TextContent]:
    """Create a resume based on provided information."""
    personal_info = arguments.get("personal_info", {})
    
    return [
        TextContent(
            type="text",
            text=f"Resume creation tool called for: {personal_info.get('name', 'Unknown')}"
        )
    ]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
