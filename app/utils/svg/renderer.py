"""SVG rendering utilities."""

import base64
import logging
from io import BytesIO
from typing import Tuple, Optional

import cairosvg
from PIL import Image

logger = logging.getLogger(__name__)


class SVGRenderer:
    """Renders SVG content to various formats with caching."""

    def __init__(self, dpi: int = 300, scale: float = 1.0):
        self.dpi = dpi
        self.scale = scale
        self.logger = logging.getLogger(__name__)

    def render_svg(self, svg_content: str, format: str = 'PNG') -> Tuple[Optional[str], Optional[str]]:
        """Render SVG content to specified format and return base64 image.
        
        Args:
            svg_content: The SVG XML content
            format: Output format (PNG, JPEG, etc.)
            
        Returns:
            Tuple of (file_path, base64_image)
        """
        try:
            # Convert SVG to PNG using cairo
            png_data = cairosvg.svg2png(
                bytestring=svg_content.encode(),
                dpi=self.dpi,
                scale=self.scale
            )

            # If requested format isn't PNG, convert using PIL
            if format.upper() != 'PNG':
                img = Image.open(BytesIO(png_data))
                output = BytesIO()
                img.save(output, format=format)
                img_data = output.getvalue()
            else:
                img_data = png_data

            # Convert to base64
            base64_image = base64.b64encode(img_data).decode()

            self.logger.debug(f"Successfully rendered SVG to {format}")
            return None, base64_image

        except Exception as e:
            self.logger.error(f"Error rendering SVG: {str(e)}")
            return None, None

    def render_svg_to_file(self, svg_content: str, output_path: str, format: str = 'PNG') -> bool:
        """Render SVG content to a file.
        
        Args:
            svg_content: The SVG XML content
            output_path: Path to save the rendered image
            format: Output format (PNG, JPEG, etc.)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert SVG to PNG using cairo
            png_data = cairosvg.svg2png(
                bytestring=svg_content.encode(),
                dpi=self.dpi,
                scale=self.scale
            )

            # If requested format isn't PNG, convert using PIL
            if format.upper() != 'PNG':
                img = Image.open(BytesIO(png_data))
                img.save(output_path, format=format)
            else:
                with open(output_path, 'wb') as f:
                    f.write(png_data)

            self.logger.debug(f"Successfully rendered SVG to file: {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"Error rendering SVG to file: {str(e)}")
            return False


def process_llm_response(llm_response):
    """Process LLM response to extract and render SVG content.
    
    Args:
        llm_response: Response from LLM
        
    Returns:
        Dict with processed text and image data if SVG is found
    """
    renderer = SVGRenderer()
    svg_content, text_without_svg = renderer.extract_svg_from_text(llm_response)

    if svg_content:
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
