"""MCP Server for resume review and creation tools."""

import asyncio
import json
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from resume_parser import ResumeParser


app = Server("resume-server")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available resume tools."""
    return [
        Tool(
            name="review_resume",
            description="Review a resume and provide feedback on content, formatting, and improvements. Supports PDF, DOCX, images, and text.",
            inputSchema={
                "type": "object",
                "properties": {
                    "resume_text": {
                        "type": "string",
                        "description": "The resume content as plain text (optional if file_path or file_base64 provided)"
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Path to resume file (PDF, DOCX, image, or text)"
                    },
                    "file_base64": {
                        "type": "string",
                        "description": "Base64 encoded resume file data"
                    },
                    "file_type": {
                        "type": "string",
                        "description": "File type when using file_base64 (pdf, docx, jpg, png, etc.)"
                    },
                    "job_description": {
                        "type": "string",
                        "description": "Optional job description to tailor feedback"
                    }
                },
                "required": []
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
    file_path = arguments.get("file_path", "")
    file_base64 = arguments.get("file_base64", "")
    file_type = arguments.get("file_type", "")
    job_description = arguments.get("job_description", "")
    
    parsed_data = None
    
    # Parse from file path
    if file_path:
        parsed_data = ResumeParser.parse_resume(file_path)
        if not parsed_data["success"]:
            return [
                TextContent(
                    type="text",
                    text=f"Error parsing resume file: {parsed_data.get('error', 'Unknown error')}"
                )
            ]
        resume_text = parsed_data["text"]
    
    # Parse from base64
    elif file_base64 and file_type:
        parsed_data = ResumeParser.parse_from_base64(file_base64, file_type)
        if not parsed_data["success"]:
            return [
                TextContent(
                    type="text",
                    text=f"Error parsing base64 resume: {parsed_data.get('error', 'Unknown error')}"
                )
            ]
        resume_text = parsed_data["text"]
    
    # Build response with parsing results
    response_parts = []
    
    if parsed_data:
        response_parts.append("## Parsed Resume Data")
        response_parts.append(f"**Text Length:** {len(resume_text)} characters")
        response_parts.append(f"**Word Count:** {len(resume_text.split())} words")
        
        if "metadata" in parsed_data:
            response_parts.append("\n### File Metadata")
            for key, value in parsed_data["metadata"].items():
                response_parts.append(f"- **{key}:** {value}")
        
        if "formatting" in parsed_data:
            response_parts.append("\n### Formatting Analysis")
            for key, value in parsed_data["formatting"].items():
                response_parts.append(f"- **{key}:** {value}")
        
        response_parts.append("\n### Extracted Text Preview")
        preview = resume_text[:500] + "..." if len(resume_text) > 500 else resume_text
        response_parts.append(f"```\n{preview}\n```")
    else:
        response_parts.append(f"Resume text provided directly: {len(resume_text)} characters")
    
    if job_description:
        response_parts.append(f"\n**Job Description:** {job_description[:200]}...")
    
    response_parts.append("\n---\n*Note: This is the parsing output. Connect to LLM for detailed review feedback.*")
    
    return [
        TextContent(
            type="text",
            text="\n".join(response_parts)
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
