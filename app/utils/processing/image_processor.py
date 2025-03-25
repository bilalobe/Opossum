import base64
import logging
from io import BytesIO
from time import time
from typing import Tuple, Optional, Dict, Any, Callable

from wand.image import Image

from app.utils.infrastructure.cache import get_from_cache, add_to_cache
from app.utils.infrastructure.cache_config import IMAGE_MAX_DIMENSION

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Image processing utility with caching and performance monitoring."""

    def __init__(self) -> None:
        self.__supported_effects: Dict[str, Callable] = {
            'resize': self.__resize,
            'rotate': self.__rotate,
            'blur': self.__blur,
            'sharpen': self.__sharpen
        }
        self.__logger = logger
        self.__max_dimension = IMAGE_MAX_DIMENSION

    def process_image(self, base64_image: str, effects: Optional[Dict[str, Dict[str, Any]]] = None) -> str:
        """Process an image with the specified effects with performance monitoring."""
        if effects is None:
            effects = {}

        cache_key = self.__generate_cache_key(base64_image, effects)
        cached = get_from_cache(cache_key, cache_type='image')
        if cached:
            return cached

        start_time = time()
        try:
            image_data = base64.b64decode(base64_image.split(',')[1])

            with Image(blob=image_data) as img:
                if img.width > self.__max_dimension or img.height > self.__max_dimension:
                    self.__logger.warning(f"Large image detected: {img.width}x{img.height}")
                    scale = min(self.__max_dimension / img.width, self.__max_dimension / img.height)
                    img.resize(int(img.width * scale), int(img.height * scale))

                for effect, params in effects.items():
                    if effect in self.__supported_effects:
                        effect_start = time()
                        self.__supported_effects[effect](img, params)
                        self.__logger.debug(f"Effect {effect} took {time() - effect_start:.3f}s")

                buffer = BytesIO()
                img.save(buffer)
                result = f"data:image/{img.format.lower()};base64,{base64.b64encode(buffer.getvalue()).decode()}"
                add_to_cache(cache_key, result, cache_type='image')
                self.__logger.info(f"Total processing time: {time() - start_time:.3f}s")
                return result

        except Exception as e:
            self.__logger.error(f"Image processing error: {str(e)}")
            raise

    def process_svg(self, svg_content: str, target_format: str = 'PNG') -> str:
        """Special handling for SVG files with format conversion."""
        try:
            with Image(blob=svg_content.encode(), format='SVG') as img:
                img.resolution = (300, 300)
                img.format = target_format
                buffer = BytesIO()
                img.save(buffer)
                return f"data:image/{target_format.lower()};base64,{base64.b64encode(buffer.getvalue()).decode()}"
        except Exception as e:
            self.__logger.error(f"SVG processing error: {str(e)}")
            raise

    def get_image_info(self, base64_image: str) -> Dict[str, Any]:
        """Get information about the image."""
        image_data = base64.b64decode(base64_image.split(',')[1])

        with Image(blob=image_data) as img:
            return {
                'format': img.format,
                'width': img.width,
                'height': img.height,
                'colorspace': str(img.colorspace),
                'size': len(image_data)
            }

    @staticmethod
    def create_thumbnail(image_data: str, size: Tuple[int, int] = (200, 200)) -> str:
        """Create a thumbnail of the processed image."""
        if ',' in image_data:
            image_data = image_data.split(',')[1]

        image_bytes = base64.b64decode(image_data)

        with Image(blob=image_bytes) as img:
            img.resize(*size)
            buffer = BytesIO()
            img.save(buffer)
            return base64.b64encode(buffer.getvalue()).decode()

    def __generate_cache_key(self, image_data: str, effects: Dict) -> str:
        """Generate a unique key for caching."""
        import hashlib
        effects_str = str(sorted(effects.items()))
        return hashlib.md5((image_data + effects_str).encode()).hexdigest()

    def __resize(self, img: Image, params: Dict[str, int]) -> None:
        """Resize the image."""
        width = params.get('width')
        height = params.get('height')
        if width and height:
            img.resize(width, height)

    def __rotate(self, img: Image, params: Dict[str, float]) -> None:
        """Rotate the image."""
        degrees = params.get('degrees', 0)
        img.rotate(degrees)

    def __blur(self, img: Image, params: Dict[str, float]) -> None:
        """Apply Gaussian blur to the image."""
        sigma = params.get('sigma', 3)
        img.gaussian_blur(sigma=sigma)

    def __sharpen(self, img: Image, params: Dict[str, float]) -> None:
        """Sharpen the image."""
        radius = params.get('radius', 2)
        sigma = params.get('sigma', 1)
        img.sharpen(radius=radius, sigma=sigma)
