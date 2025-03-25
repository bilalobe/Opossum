"""Image processing resolvers with enhanced functionality."""
import base64
import json
import logging

from app.api.directives import apply_cost, rate_limit
from app.api.types import Error
from app.utils.processing.image_processor import ImageProcessor

logger = logging.getLogger(__name__)


@apply_cost(value=5)
async def resolve_image_info(root, info, image_data):
    """Extract metadata from an image."""
    try:
        # Decode base64 image data
        if not image_data or "base64," not in image_data:
            return Error.create(
                message="Invalid image data format",
                code="INVALID_IMAGE_DATA"
            )

        # Extract the actual base64 content after the comma
        _, b64data = image_data.split("base64,", 1)
        image_bytes = base64.b64decode(b64data)

        # Create processor and analyze image
        processor = ImageProcessor()
        image_info = processor.get_image_info(image_bytes)

        if not image_info:
            return Error.create(
                message="Failed to process image",
                code="IMAGE_PROCESSING_ERROR"
            )

        # Return standardized format
        return {
            "width": image_info.get("width", 0),
            "height": image_info.get("height", 0),
            "format": image_info.get("format", "UNKNOWN"),
            "size": image_info.get("size", 0),
            "metadata": json.dumps(image_info.get("metadata", {}))
        }
    except Exception as e:
        logger.error(f"Error getting image info: {e}", exc_info=True)
        return Error.create(
            message=f"Error processing image: {str(e)}",
            code="IMAGE_PROCESSING_ERROR"
        )


@apply_cost(value=15, multipliers="effects")
@rate_limit(limit=20, duration=60)  # 20 requests per minute
async def resolve_process_image(root, info, image_data, effects=None):
    """Process an image with various effects."""
    try:
        # Decode base64 image data
        if not image_data or "base64," not in image_data:
            return Error.create(
                message="Invalid image data format",
                code="INVALID_IMAGE_DATA"
            )

        # Extract the actual base64 content after the comma
        _, b64data = image_data.split("base64,", 1)
        image_bytes = base64.b64decode(b64data)

        # Default empty effects if none provided
        if effects is None:
            effects = {}

        # Create processor and process image
        processor = ImageProcessor()
        result = processor.process_image(
            image_bytes,
            brightness=effects.get("brightness", 0),
            contrast=effects.get("contrast", 0),
            saturation=effects.get("saturation", 0),
            blur=effects.get("blur", 0),
            sharpen=effects.get("sharpen", 0)
        )

        if not result:
            return Error.create(
                message="Failed to process image",
                code="IMAGE_PROCESSING_ERROR"
            )

        # Get image info for the processed result
        processed_info = processor.get_image_info(result["processed_image"])

        # Return processed result with thumbnail
        return {
            "processed_image": f"data:image/{result['format'].lower()};base64,{base64.b64encode(result['processed_image']).decode('utf-8')}",
            "thumbnail": f"data:image/{result['format'].lower()};base64,{base64.b64encode(result['thumbnail']).decode('utf-8')}",
            "info": {
                "width": processed_info.get("width", 0),
                "height": processed_info.get("height", 0),
                "format": processed_info.get("format", "UNKNOWN"),
                "size": processed_info.get("size", 0),
                "metadata": json.dumps(processed_info.get("metadata", {}))
            }
        }
    except Exception as e:
        logger.error(f"Error processing image: {e}", exc_info=True)
        return Error.create(
            message=f"Error processing image: {str(e)}",
            code="IMAGE_PROCESSING_ERROR"
        )


@apply_cost(value=10)
@rate_limit(limit=30, duration=60)  # 30 requests per minute
async def resolve_upload_image(root, info, file_data, content_type):
    """Upload and process a new image."""
    try:
        # Handle file upload data
        if not file_data or not content_type:
            return Error.create(
                message="Missing file data or content type",
                code="INVALID_UPLOAD"
            )

        # Decode base64 file data
        file_bytes = base64.b64decode(file_data)

        # Create processor and handle the uploaded image
        processor = ImageProcessor()

        # Basic validation of image type
        if not content_type.startswith("image/"):
            return Error.create(
                message="Invalid file type. Only images are supported.",
                code="INVALID_FILE_TYPE"
            )

        # Process uploaded image (with default effects)
        result = processor.process_image(file_bytes)

        if not result:
            return Error.create(
                message="Failed to process uploaded image",
                code="IMAGE_PROCESSING_ERROR"
            )

        # Get image info for the processed result
        processed_info = processor.get_image_info(result["processed_image"])

        # Return processed result with thumbnail
        return {
            "processed_image": f"data:image/{result['format'].lower()};base64,{base64.b64encode(result['processed_image']).decode('utf-8')}",
            "thumbnail": f"data:image/{result['format'].lower()};base64,{base64.b64encode(result['thumbnail']).decode('utf-8')}",
            "info": {
                "width": processed_info.get("width", 0),
                "height": processed_info.get("height", 0),
                "format": processed_info.get("format", "UNKNOWN"),
                "size": processed_info.get("size", 0),
                "metadata": json.dumps(processed_info.get("metadata", {}))
            }
        }
    except Exception as e:
        logger.error(f"Error uploading image: {e}", exc_info=True)
        return Error.create(
            message=f"Error uploading image: {str(e)}",
            code="IMAGE_UPLOAD_ERROR"
        )
