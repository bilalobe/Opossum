"""Image processing and analysis resolvers."""
import logging
from app.utils.processing.image_processor import ImageProcessor

logger = logging.getLogger(__name__)

def resolve_process_image(root, info, image_data, effects=None):
    """Process and transform images with optional effects."""
    try:
        image_processor = ImageProcessor()
        processed_image = image_processor.process_image(
            image_data,
            effects=effects or {}
        )
        image_info = image_processor.get_image_info(image_data)
        thumbnail = image_processor.create_thumbnail(processed_image)
        
        return {
            "processed_image": processed_image,
            "thumbnail": thumbnail,
            "info": image_info
        }
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        raise

def resolve_image_info(root, info, image_data):
    """Get metadata and information about an image."""
    try:
        image_processor = ImageProcessor()
        image_info = image_processor.get_image_info(image_data)
        return image_info
    except Exception as e:
        logger.error(f"Error getting image info: {e}")
        raise

def resolve_upload_image(root, info, file_data, content_type):
    """Handle image upload and initial processing."""
    try:
        base64_image = f"data:{content_type};base64,{file_data}"
        image_processor = ImageProcessor()
        info = image_processor.get_image_info(base64_image)
        
        return {
            "processed_image": base64_image,
            "info": info
        }
    except Exception as e:
        logger.error(f"Error uploading image: {e}")
        raise