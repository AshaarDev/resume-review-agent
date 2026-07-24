"""MCP Client to connect to resume server and use tools."""

import asyncio
from typing import Any, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPClient:
    """Client for interacting with MCP resume server."""
    
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.available_tools: list[Any] = []
    
    async def connect(self):
        """Connect to the MCP resume server."""
        server_params = StdioServerParameters(
            command="python",
            args=["mcp/servers/resume_server.py"],
        )
        
        stdio_transport = await stdio_client(server_params)
        self.stdio, self.write = stdio_transport
        
        self.session = ClientSession(self.stdio, self.write)
        await self.session.initialize()
        
        response = await self.session.list_tools()
        self.available_tools = response.tools
        
        print(f"Connected to MCP server. Available tools: {[tool.name for tool in self.available_tools]}")
    
    async def call_tool(self, tool_name: str, arguments: dict) -> Any:
        """Call a tool on the MCP server."""
        if not self.session:
            raise RuntimeError("Not connected to MCP server. Call connect() first.")
        
        result = await self.session.call_tool(tool_name, arguments)
        return result
    
    async def review_resume(self, resume_text: str, job_description: str = "") -> Any:
        """Review a resume using the MCP server."""
        return await self.call_tool(
            "review_resume",
            {
                "resume_text": resume_text,
                "job_description": job_description
            }
        )
    
    async def create_resume(
        self,
        personal_info: dict,
        work_experience: list = None,
        education: list = None,
        skills: list = None,
        template: str = "modern"
    ) -> Any:
        """Create a resume using the MCP server."""
        arguments = {
            "personal_info": personal_info,
            "work_experience": work_experience or [],
            "education": education or [],
            "skills": skills or [],
            "template": template
        }
        return await self.call_tool("create_resume", arguments)
    
    async def close(self):
        """Close the connection to the MCP server."""
        if self.session:
            await self.session.__aexit__(None, None, None)


async def test_mcp_client():
    """Test the MCP client."""
    client = MCPClient()
    
    try:
        await client.connect()
        
        print("\n--- Testing review_resume tool ---")
        result = await client.review_resume(
            resume_text="John Doe\nSoftware Engineer\n...",
            job_description="Looking for a Python developer"
        )
        print(f"Result: {result}")
        
        print("\n--- Testing create_resume tool ---")
        result = await client.create_resume(
            personal_info={"name": "Jane Smith", "email": "jane@example.com"},
            skills=["Python", "FastAPI", "React"]
        )
        print(f"Result: {result}")
        
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_mcp_client())
