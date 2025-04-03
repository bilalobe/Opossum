"""Helper functions for Chat2SVG pipeline."""
import asyncio
import base64
import logging
import os
import re
import tempfile
from typing import Optional

try:
    import cairosvg
except ImportError:
    cairosvg = None
    logging.warning("cairosvg not installed, SVG to PNG conversion will fail")

logger = logging.getLogger(__name__)


def sanitize_filename(text: str) -> str:
    """Create a safe filename from text."""
    text = re.sub(r'[<>:"/\\|?*]', '', text)
    text = re.sub(r'[\s\-,]+', '_', text)
    return text[:50].strip('. ')


async def to_thread(func, *args, **kwargs):
    """Run synchronous function in thread pool."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: func(*args, **kwargs))


def encode_svg_to_png_base64(svg_content: str) -> str:
    """Convert SVG to PNG and encode as base64."""
    if cairosvg is None:
        logger.error("cairosvg is not installed, cannot encode SVG to PNG.")
        return ""
    try:
        if not svg_content:
            logger.warning("Attempted to encode empty SVG content.")
            return ""
            
        # Add explicit width/height if missing
        if 'width=' not in svg_content or 'height=' not in svg_content:
            logger.debug("SVG lacks width/height, adding defaults.")
            svg_content = re.sub(r'(<svg[^>]*)', r'\1 width="512px" height="512px"', 
                               svg_content, count=1)

        png_data = cairosvg.svg2png(
            bytestring=svg_content.encode('utf-8'),
            output_width=512,
            output_height=512
        )
        return base64.b64encode(png_data).decode('utf-8')
    except Exception as e:
        logger.error(f"Error converting SVG to PNG: {e}")
        return ""


async def read_file_async(filepath: str) -> Optional[str]:
    """Read file content asynchronously."""
    try:
        with open(filepath, "r", encoding='utf-8') as f:
            content = await to_thread(f.read)
        return content
    except FileNotFoundError:
        logger.error(f"File not found: {filepath}")
        return None
    except Exception as e:
        logger.error(f"Error reading file {filepath}: {e}")
        return None


def create_temp_dir(prefix: str) -> str:
    """Create a temporary directory with proper error handling."""
    try:
        return tempfile.mkdtemp(prefix=prefix)
    except Exception as e:
        logger.error(f"Failed to create temp directory: {e}")
        raise
