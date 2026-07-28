"""FastMCP server for resume review and analysis tools."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    # Fallback for different mcp package structure
    from mcp import FastMCP

from services.resume_parser import ResumeParser
from services.openai_service import run_chat
from services.document_processor import (
    DocumentProcessingError,
    decode_resume_file,
    normalize_file_type,
)
from services.review_pipeline import (
    analyze_layout_bytes,
    analyze_layout_file,
    analyze_resume_bytes,
    analyze_resume_file,
    analyze_visual_bytes,
    analyze_visual_file,
    load_resume_file,
)
from services.resume_policy import serialize_resume_quality_policy
from workflows.resume_workflow import (
    run_resume_review_workflow as execute_resume_review_workflow,
)

# Initialize FastMCP server
mcp = FastMCP("resume-review-server")


@mcp.resource("resume-policy://current")
def get_resume_review_policy() -> str:
    """Return the versioned policy applied by review and future creator agents."""

    return serialize_resume_quality_policy()


@mcp.tool()
def parse_resume(file_path: str) -> dict:
    """
    Parse a resume file and extract text content.
    
    Args:
        file_path: Path to the resume file (PDF, DOCX, image, or text)
    
    Returns:
        Dictionary containing extracted text, metadata, and success status
    """
    try:
        load_resume_file(file_path)
        return ResumeParser.parse_resume(file_path)
    except DocumentProcessingError as exc:
        return _processing_error(exc)


@mcp.tool()
def parse_resume_base64(file_base64: str, file_type: str) -> dict:
    """
    Parse a resume from base64 encoded data.
    
    Args:
        file_base64: Base64 encoded resume file data
        file_type: File extension (pdf, docx, jpg, png, etc.)
    
    Returns:
        Dictionary containing extracted text, metadata, and success status
    """
    result = ResumeParser.parse_from_base64(file_base64, file_type)
    return result


@mcp.tool()
def review_resume(resume_text: str, job_description: str = "") -> str:
    """
    Review a resume and provide detailed feedback.
    
    Args:
        resume_text: The resume content as plain text
        job_description: Optional job description to tailor feedback
    
    Returns:
        AI-generated review and feedback
    """
    prompt = f"Please review this resume and provide detailed feedback:\n\n{resume_text}"
    
    if job_description:
        prompt += f"\n\nJob Description:\n{job_description}\n\nPlease tailor your feedback to this job description."
    
    response = run_chat(prompt)
    return response


@mcp.tool()
def analyze_resume_from_file(file_path: str, job_description: str = "") -> str:
    """
    Parse and analyze a resume file in one step.
    
    Args:
        file_path: Path to the resume file
        job_description: Optional job description to tailor feedback
    
    Returns:
        AI-generated review and feedback
    """
    try:
        load_resume_file(file_path)
    except DocumentProcessingError as exc:
        return f"Error: {exc.code} - {str(exc)}"
    parsed_data = ResumeParser.parse_resume(file_path)
    
    if not parsed_data["success"]:
        return f"Error parsing resume: {parsed_data.get('error', 'Unknown error')}"
    
    # Review the parsed text
    resume_text = parsed_data["text"]
    return review_resume(resume_text, job_description)


def _processing_error(exc: DocumentProcessingError) -> dict:
    """Convert invalid MCP inputs into a stable structured tool result."""

    return {
        "status": "unavailable",
        "error_code": exc.code,
        "error_message": str(exc),
    }


@mcp.tool()
def analyze_resume_layout(file_path: str) -> dict:
    """Measure page dimensions, density, and font sizes without an AI call.

    Args:
        file_path: Local path to a PDF, DOCX, JPG, JPEG, or PNG resume.

    Returns:
        Deterministic layout metrics or an explicit unavailable result.
    """

    try:
        return analyze_layout_file(file_path).model_dump(mode="json")
    except DocumentProcessingError as exc:
        return _processing_error(exc)


@mcp.tool()
def analyze_resume_layout_base64(file_base64: str, file_type: str) -> dict:
    """Measure resume layout when the MCP client cannot share a local path.

    Args:
        file_base64: Base64-encoded resume bytes.
        file_type: PDF, DOCX, JPG, JPEG, or PNG extension.

    Returns:
        Deterministic layout metrics or an explicit unavailable result.
    """

    try:
        normalized_type = normalize_file_type(file_type)
        file_bytes = decode_resume_file(file_base64)
        return analyze_layout_bytes(file_bytes, normalized_type).model_dump(
            mode="json"
        )
    except DocumentProcessingError as exc:
        return _processing_error(exc)


@mcp.tool()
def review_resume_visual(file_path: str) -> dict:
    """Run Gemini Flash visual review with deterministic layout context.

    Args:
        file_path: Local path to a PDF, DOCX, JPG, JPEG, or PNG resume.

    Returns:
        Validated visual score, strengths, coded issues, or unavailable status.
    """

    try:
        return analyze_visual_file(file_path).model_dump(mode="json")
    except DocumentProcessingError as exc:
        return _processing_error(exc)


@mcp.tool()
def review_resume_visual_base64(file_base64: str, file_type: str) -> dict:
    """Run Gemini visual review for a base64-encoded resume.

    Args:
        file_base64: Base64-encoded resume bytes.
        file_type: PDF, DOCX, JPG, JPEG, or PNG extension.

    Returns:
        Validated visual score, strengths, coded issues, or unavailable status.
    """

    try:
        normalized_type = normalize_file_type(file_type)
        file_bytes = decode_resume_file(file_base64)
        return analyze_visual_bytes(file_bytes, normalized_type).model_dump(
            mode="json"
        )
    except DocumentProcessingError as exc:
        return _processing_error(exc)


@mcp.tool()
def review_resume_unified(
    file_path: str, job_description: str = ""
) -> dict:
    """Run GPT content, Gemini visual, and deterministic layout reviews.

    Args:
        file_path: Local path to a PDF, DOCX, JPG, JPEG, or PNG resume.
        job_description: Optional role description for tailored content review.

    Returns:
        Unified partial-result-safe review response.
    """

    try:
        return analyze_resume_file(
            file_path, job_description
        ).model_dump(mode="json")
    except DocumentProcessingError as exc:
        return _processing_error(exc)


@mcp.tool()
def review_resume_unified_base64(
    file_base64: str,
    file_type: str,
    job_description: str = "",
) -> dict:
    """Run the unified review for a base64-encoded resume.

    Args:
        file_base64: Base64-encoded resume bytes.
        file_type: PDF, DOCX, JPG, JPEG, or PNG extension.
        job_description: Optional role description for tailored content review.

    Returns:
        Unified partial-result-safe review response.
    """

    try:
        normalized_type = normalize_file_type(file_type)
        file_bytes = decode_resume_file(file_base64)
        return analyze_resume_bytes(
            file_bytes, normalized_type, job_description
        ).model_dump(mode="json")
    except DocumentProcessingError as exc:
        return _processing_error(exc)


@mcp.tool()
def run_resume_review_workflow(
    file_path: str,
    job_description: str = "",
    user_instructions: str = "",
) -> dict:
    """Run the complete LangGraph resume review workflow from a local file.
    
    This tool uses the LangGraph orchestrator with Resume Review Agent,
    GPT-5.6 Luna synthesis, and deterministic fallback.
    
    Args:
        file_path: Local path to a PDF, DOCX, JPG, JPEG, or PNG resume
        job_description: Optional job description for tailored review
        user_instructions: Optional user-specific instructions
        
    Returns:
        Complete workflow response with synthesis and structured findings
    """
    try:
        file_bytes, file_type = load_resume_file(file_path)
        return execute_resume_review_workflow(
            file_bytes=file_bytes,
            file_type=file_type,
            job_description=job_description,
            user_instructions=user_instructions,
        ).model_dump(mode="json")
    except DocumentProcessingError as exc:
        return _processing_error(exc)


@mcp.tool()
def run_resume_review_workflow_base64(
    file_base64: str,
    file_type: str,
    job_description: str = "",
    user_instructions: str = "",
) -> dict:
    """Run the complete LangGraph resume review workflow from base64 input.
    
    This tool uses the LangGraph orchestrator with Resume Review Agent,
    GPT-5.6 Luna synthesis, and deterministic fallback.
    
    Args:
        file_base64: Base64-encoded resume bytes
        file_type: PDF, DOCX, JPG, JPEG, or PNG extension
        job_description: Optional job description for tailored review
        user_instructions: Optional user-specific instructions
        
    Returns:
        Complete workflow response with synthesis and structured findings
    """
    try:
        normalized_type = normalize_file_type(file_type)
        file_bytes = decode_resume_file(file_base64)
        return execute_resume_review_workflow(
            file_bytes=file_bytes,
            file_type=normalized_type,
            job_description=job_description,
            user_instructions=user_instructions,
        ).model_dump(mode="json")
    except DocumentProcessingError as exc:
        return _processing_error(exc)


@mcp.tool()
def get_resume_statistics(resume_text: str) -> dict:
    """
    Get basic statistics about a resume.
    
    Args:
        resume_text: The resume content as plain text
    
    Returns:
        Dictionary with word count, character count, and other stats
    """
    words = resume_text.split()
    lines = resume_text.split('\n')
    
    return {
        "character_count": len(resume_text),
        "word_count": len(words),
        "line_count": len(lines),
        "has_bullet_points": any(char in resume_text for char in ['•', '●', '○', '-']),
        "estimated_pages": len(words) // 250 + 1,  # Rough estimate: 250 words per page
    }


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
