"""Image processing schema types and operations."""
import graphene

from app.api.resolvers.images import resolve_process_image, resolve_image_info, resolve_upload_image


class ImageInfo(graphene.ObjectType):
    """Metadata and information about an image."""
    width = graphene.Int(description="Width of the image in pixels")
    height = graphene.Int(description="Height of the image in pixels")
    format = graphene.String(description="Image format (e.g., 'JPEG', 'PNG')")
    size = graphene.Int(description="File size in bytes")
    metadata = graphene.JSONString(description="Additional image metadata in JSON format")


class ProcessedImage(graphene.ObjectType):
    """Result of image processing operations."""
    processed_image = graphene.String(description="Base64-encoded processed image data")
    thumbnail = graphene.String(description="Base64-encoded thumbnail of the processed image")
    info = graphene.Field(ImageInfo, description="Metadata about the processed image")


class ImageEffects(graphene.InputObjectType):
    """Parameters for image processing effects."""
    brightness = graphene.Float(description="Brightness adjustment (-1.0 to 1.0)")
    contrast = graphene.Float(description="Contrast adjustment (-1.0 to 1.0)")
    saturation = graphene.Float(description="Saturation adjustment (-1.0 to 1.0)")
    blur = graphene.Float(description="Gaussian blur radius (0.0+)")
    sharpen = graphene.Float(description="Sharpening intensity (0.0 to 1.0)")


# Image-related Query fields
images_query_fields = {
    'image_info': graphene.Field(
        ImageInfo,
        image_data=graphene.String(required=True),
        description="Get metadata about an image",
        resolver=resolve_image_info
    )
}

# Image-related Mutation fields
images_mutation_fields = {
    'process_image': graphene.Field(
        ProcessedImage,
        image_data=graphene.String(required=True),
        effects=ImageEffects(),
        description="Process an image with optional effects",
        resolver=resolve_process_image
    ),

    'upload_image': graphene.Field(
        ProcessedImage,
        file_data=graphene.String(required=True),
        content_type=graphene.String(required=True),
        description="Upload and process a new image",
        resolver=resolve_upload_image
    )
}
