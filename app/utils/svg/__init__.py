"""SVG generation and rendering utilities."""

from app.utils.svg.renderer import SVGRenderer
from app.utils.svg.templates import (
    extract_svg_from_text,
    service_status_template,
    failover_process_template,
    capability_degradation_template
)

__all__ = [
    'SVGRenderer',
    'extract_svg_from_text',
    'service_status_template',
    'failover_process_template',
    'capability_degradation_template',
    'process_llm_response'
]


def process_llm_response(llm_response: str) -> dict:
    """Process LLM response to extract and render SVG content.
    
    Args:
        llm_response: Response text from LLM that may contain SVG
        
    Returns:
        Dict with processed text and image data
    """
    svg_content, text_without_svg = extract_svg_from_text(llm_response)

    if svg_content:
        renderer = SVGRenderer()
        _, base64_image = renderer.render_svg(svg_content)
        return {
            "text": text_without_svg,
            "has_image": True,
            "base64_image": base64_image,
            "svg_content": svg_content
        }

    return {
        "text": llm_response,
        "has_image": False
    }
