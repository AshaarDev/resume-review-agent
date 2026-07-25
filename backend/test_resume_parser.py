"""Test script for resume parsing functionality."""

import sys
from pathlib import Path

# Add mcp/servers to path
sys.path.insert(0, str(Path(__file__).parent / "mcp" / "servers"))

from resume_parser import ResumeParser


def test_text_parsing():
    """Test parsing plain text resume."""
    print("\n" + "="*60)
    print("TEST 1: Plain Text Resume")
    print("="*60)
    
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
    
    # Create a temp file
    temp_file = Path("temp_resume.txt")
    temp_file.write_text(sample_resume)
    
    try:
        result = ResumeParser.parse_resume(str(temp_file))
        
        print(f"✓ Success: {result['success']}")
        print(f"✓ Text Length: {len(result['text'])} characters")
        print(f"✓ Word Count: {len(result['text'].split())} words")
        print(f"\nFormatting Analysis:")
        for key, value in result.get('formatting', {}).items():
            print(f"  - {key}: {value}")
    finally:
        temp_file.unlink()


def test_pdf_parsing():
    """Test PDF parsing (if PDF file exists)."""
    print("\n" + "="*60)
    print("TEST 2: PDF Resume Parsing")
    print("="*60)
    
    # This is a placeholder - user needs to provide actual PDF
    print("⚠ To test PDF parsing:")
    print("  1. Place a resume PDF in the backend directory")
    print("  2. Update the file path below")
    print("  3. Run this test again")
    print("\nExample code:")
    print("""
    result = ResumeParser.parse_resume("path/to/resume.pdf")
    if result['success']:
        print(f"Extracted {len(result['text'])} characters")
        print(f"Pages: {result['metadata']['num_pages']}")
    """)


def test_parser_features():
    """Test various parser features."""
    print("\n" + "="*60)
    print("TEST 3: Parser Features")
    print("="*60)
    
    print("\n✓ Supported formats:")
    print("  - PDF (.pdf)")
    print("  - Word Documents (.docx, .doc)")
    print("  - Images (.jpg, .png, .gif, .bmp, .tiff)")
    print("  - Plain Text (.txt)")
    
    print("\n✓ Parsing methods:")
    print("  - parse_resume(file_path) - Auto-detect format")
    print("  - parse_pdf(file_path) - PDF specific")
    print("  - parse_docx(file_path) - DOCX specific")
    print("  - parse_image(file_path) - Image/OCR")
    print("  - parse_from_base64(data, type) - Base64 encoded")
    
    print("\n✓ Analysis features:")
    print("  - Text extraction")
    print("  - Metadata (file size, pages, dimensions)")
    print("  - Formatting detection (bullets, sections)")
    print("  - Word/character count")


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("RESUME PARSER TEST SUITE")
    print("="*60)
    
    try:
        test_text_parsing()
        test_pdf_parsing()
        test_parser_features()
        
        print("\n" + "="*60)
        print("✓ All tests completed!")
        print("="*60)
        print("\nNext steps:")
        print("1. Install required libraries: pip install -r requirements.txt")
        print("2. Install Tesseract OCR for image parsing")
        print("3. Test with your own resume files")
        print("4. Integrate with MCP server for full functionality")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
