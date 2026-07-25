"""Test script for the FastMCP resume server."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_server_import():
    """Test that the server can be imported."""
    print("Testing MCP server import...")
    try:
        from mcp_server.resume_server import mcp
        print(f"✓ Server imported successfully: {mcp.name}")
        
        # List available tools
        print("\nAvailable tools:")
        for tool_name in dir(mcp):
            if not tool_name.startswith('_'):
                print(f"  - {tool_name}")
        
        return True
    except Exception as e:
        print(f"✗ Error importing server: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_resume_statistics():
    """Test the resume statistics tool."""
    print("\n" + "="*60)
    print("Testing get_resume_statistics tool")
    print("="*60)
    
    try:
        from mcp_server.resume_server import get_resume_statistics
        
        sample_resume = """
        John Doe
        Software Engineer
        john.doe@email.com | (555) 123-4567
        
        EXPERIENCE
        • Senior Developer at Tech Corp (2020-Present)
        • Built scalable web applications
        • Led team of 5 developers
        
        EDUCATION
        • BS Computer Science, University XYZ (2018)
        
        SKILLS
        Python, JavaScript, React, FastAPI
        """
        
        stats = get_resume_statistics(sample_resume)
        
        print("✓ Statistics generated:")
        for key, value in stats.items():
            print(f"  - {key}: {value}")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("FASTMCP RESUME SERVER TEST SUITE")
    print("="*60)
    
    tests = [
        test_server_import,
        test_resume_statistics,
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n" + "="*60)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("="*60)
    
    if all(results):
        print("\n✓ All tests passed!")
        print("\nTo run the MCP server:")
        print("  python mcp/resume_server.py")
    else:
        print("\n✗ Some tests failed")


if __name__ == "__main__":
    main()
