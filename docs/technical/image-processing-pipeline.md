# Technical Documentation: Image Processing Pipeline

## 1. Overview

The Image Processing Pipeline in Opossum Search handles multimodal queries containing images, preparing them for analysis by various AI backends. This pipeline ensures optimal image formatting for different models, performs necessary transformations, and extracts relevant metadata to enhance multimodal understanding.

## 2. Processing Stages

### 2.1 Initial Processing

```python
async def process_incoming_image(self, image_data, image_type=None):
    """Process incoming image data for multimodal analysis"""
    # Detect format if not provided
    if not image_type:
        image_type = self._detect_image_format(image_data)
    
    # Validate image for security
    if not self._validate_image(image_data, image_type):
        raise InvalidImageError("Invalid or corrupted image data")
    
    # Extract basic metadata
    metadata = await self._extract_metadata(image_data)
    
    # Create processing context
    context = {
        "original_size": metadata.get("size", 0),
        "dimensions": metadata.get("dimensions", (0, 0)),
        "format": image_type,
        "content_type": f"image/{image_type}",
        "requires_resize": any(dim > Config.MAX_IMAGE_DIMENSION for dim in metadata.get("dimensions", (0, 0)))
    }
    
    return {
        "image_data": image_data,
        "metadata": metadata,
        "context": context
    }
```

#### Format Detection

```python
def _detect_image_format(self, image_data):
    """Detect image format from binary data"""
    # Check magic bytes for common formats
    if image_data.startswith(b'\xFF\xD8\xFF'):
        return "jpeg"
    elif image_data.startswith(b'\x89PNG\r\n\x1a\n'):
        return "png"
    elif image_data.startswith(b'GIF87a') or image_data.startswith(b'GIF89a'):
        return "gif"
    elif image_data.startswith(b'RIFF') and image_data[8:12] == b'WEBP':
        return "webp"
    
    # Use ImageMagick for more complex detection
    with wand.image.Image(blob=image_data) as img:
        return img.format.lower()
```

#### Metadata Extraction

```python
async def _extract_metadata(self, image_data):
    """Extract metadata from image"""
    metadata = {}
    
    with wand.image.Image(blob=image_data) as img:
        # Basic properties
        metadata["dimensions"] = (img.width, img.height)
        metadata["format"] = img.format.lower()
        metadata["size"] = len(image_data)
        metadata["colorspace"] = str(img.colorspace)
        metadata["depth"] = img.depth
        
        # Extract EXIF if available
        if hasattr(img, 'metadata'):
            exif = {}
            for k, v in img.metadata.items():
                if k.startswith('exif:'):
                    exif_key = k.split(':', 1)[1]
                    exif[exif_key] = v
            
            if exif:
                metadata["exif"] = exif
    
    return metadata
```

### 2.2 Transformation Pipeline

```python
async def transform_for_model(self, image_data, target_model, context=None):
    """Transform image for specific model requirements"""
    context = context or {}
    transformations = []
    
    # Determine required transformations based on model
    if target_model == "gemini-thinking":
        transformations = [
            self._resize_image(max_dimension=1024),
            self._convert_format(target_format="jpeg", quality=90)
        ]
    elif target_model == "llava":
        transformations = [
            self._resize_image(max_dimension=512),
            self._convert_format(target_format="jpeg", quality=80)
        ]
    else:
        # Default transformations
        transformations = [
            self._resize_image(max_dimension=768),
            self._convert_format(target_format="jpeg", quality=85)
        ]
    
    # Apply transformations in sequence
    processed_image = image_data
    for transform_fn in transformations:
        processed_image = await transform_fn(processed_image)
    
    # Update context with transformed image details
    with wand.image.Image(blob=processed_image) as img:
        context["transformed_size"] = len(processed_image)
        context["transformed_dimensions"] = (img.width, img.height)
    
    return processed_image, context
```

#### Resize Function

```python
def _resize_image(self, max_dimension=768):
    """Create a resize transformation function"""
    async def resize_transform(image_data):
        with wand.image.Image(blob=image_data) as img:
            # Check if resize needed
            if img.width <= max_dimension and img.height <= max_dimension:
                return image_data
            
            # Calculate new dimensions maintaining aspect ratio
            ratio = min(max_dimension / img.width, max_dimension / img.height)
            new_width = int(img.width * ratio)
            new_height = int(img.height * ratio)
            
            # Perform resize
            img.resize(new_width, new_height)
            
            # Return resized image
            return img.make_blob()
            
    return resize_transform
```

#### Format Conversion

```python
def _convert_format(self, target_format="jpeg", quality=85):
    """Create a format conversion transformation function"""
    async def format_transform(image_data):
        with wand.image.Image(blob=image_data) as img:
            # Set format and quality
            img.format = target_format
            if hasattr(img, 'compression_quality'):
                img.compression_quality = quality
            
            # Handle transparency for JPEG conversion
            if target_format.lower() == 'jpeg' and img.alpha_channel:
                # Add white background for transparent images
                with wand.image.Image(
                    width=img.width,
                    height=img.height,
                    background=wand.color.Color('white')
                ) as bg:
                    bg.composite(img, 0, 0)
                    return bg.make_blob(format=target_format)
            
            # Standard conversion
            return img.make_blob(format=target_format)
            
    return format_transform
```

### 2.3 Parallel Processing

For efficiency, the system processes multiple transformations in parallel:

```python
async def parallel_image_processing(self, image_data):
    """Process image with parallel transformations"""
    # Define processing tasks
    tasks = [
        self._resize_image(max_dimension=512)(image_data),  # Standard size
        self._extract_metadata(image_data),              # Metadata extraction
        self._generate_thumbnail(image_data)             # Thumbnail generation
    ]
    
    # Run processing tasks in parallel
    resized, metadata, thumbnail = await asyncio.gather(*tasks)
    
    # Combine results
    return {
        "image": resized,
        "metadata": metadata,
        "thumbnail": thumbnail
    }
```

## 3. Multimodal Routing

### 3.1 Model Capability Assessment

The system routes images to appropriate models based on their capabilities:

```python
async def select_model_for_image(self, image_context, query_text=None):
    """Select appropriate model for image processing"""
    # Check for image-specific features
    has_text = image_context.get("has_text", False)
    is_chart = image_context.get("is_chart", False)
    needs_detail = image_context.get("high_detail", False)
    
    # Score each available model
    scores = {}
    
    if self.is_available("gemini-thinking"):
        scores["gemini-thinking"] = 10  # Base score
        if needs_detail:
            scores["gemini-thinking"] += 5  # Good with details
    
    if self.is_available("llava"):
        scores["llava"] = 8  # Base score
        if has_text:
            scores["llava"] += 3  # Good with text in images
    
    # Get highest scoring model
    if not scores:
        return Config.DEFAULT_MODEL  # No multimodal models available
    
    return max(scores.items(), key=lambda x: x[1])[0]
```

### 3.2 Image Analysis Pre-processing

Before sending to model, images may undergo analysis to guide model selection:

```python
async def analyze_image_content(self, image_data):
    """Analyze image to determine key characteristics"""
    analysis = {
        "has_text": False,
        "is_chart": False,
        "is_photo": False,
        "high_detail": False
    }
    
    # Use MiniLM for quick embedding-based classification
    if self.minilm_embedder:
        # Extract image features
        features = await self._extract_image_features(image_data)
        
        # Compare with feature vectors for different image types
        text_score = cosine_similarity(features, self.text_image_embedding)
        chart_score = cosine_similarity(features, self.chart_image_embedding)
        photo_score = cosine_similarity(features, self.photo_image_embedding)
        
        # Set flags based on similarity scores
        if text_score > 0.65:
            analysis["has_text"] = True
        if chart_score > 0.7:
            analysis["is_chart"] = True
        if photo_score > 0.75:
            analysis["is_photo"] = True
    
    # Check for high detail based on entropy
    analysis["high_detail"] = await self._check_image_detail(image_data)
    
    return analysis
```

## 4. Image-to-Base64 Conversion

For API transmission, images are encoded to base64:

```python
def encode_image_for_api(self, image_data, prefix=True):
    """Encode image data as base64 for API transmission"""
    # Get image format if available
    image_format = "jpeg"  # Default
    try:
        with wand.image.Image(blob=image_data) as img:
            image_format = img.format.lower()
    except Exception:
        pass
    
    # Base64 encode
    b64_data = base64.b64encode(image_data).decode('utf-8')
    
    # Add data URI prefix if requested
    if prefix:
        return f"data:image/{image_format};base64,{b64_data}"
    
    return b64_data
```

## 5. Security Considerations

### 5.1 Image Validation

```python
def _validate_image(self, image_data, image_type=None):
    """Validate image for security and integrity"""
    # Size validation
    if len(image_data) > Config.MAX_IMAGE_SIZE:
        logger.warning(f"Image exceeds maximum size: {len(image_data)} bytes")
        return False
    
    # Format validation
    allowed_formats = ['jpeg', 'jpg', 'png', 'gif', 'webp']
    if image_type and image_type.lower() not in allowed_formats:
        logger.warning(f"Image format not allowed: {image_type}")
        return False
    
    # Integrity check - attempt to open and process
    try:
        with wand.image.Image(blob=image_data) as img:
            # Check for potential dangerous sizes
            if img.width > 10000 or img.height > 10000:
                logger.warning(f"Suspicious image dimensions: {img.width}x{img.height}")
                return False
            
            # Additional validation can be performed here
            
            # Image passed all checks
            return True
    except Exception as e:
        logger.warning(f"Image validation failed: {e}")
        return False
```

### 5.2 Malware Scanning

For production environments, the system can integrate with ClamAV:

```python
async def scan_image_for_malware(self, image_data):
    """Scan image for malware (requires ClamAV)"""
    # Skip if scanning disabled
    if not Config.ENABLE_MALWARE_SCAN:
        return True
    
    # Connect to ClamAV daemon
    try:
        clamd = clamd.ClamdNetworkSocket(
            host=Config.CLAMAV_HOST,
            port=Config.CLAMAV_PORT
        )
        
        # Scan the image data
        scan_result = clamd.instream(io.BytesIO(image_data))
        
        # Check result
        status = scan_result['stream'][0]
        if status == 'OK':
            return True
        else:
            logger.warning(f"Malware scan detected: {status}")
            return False
    except Exception as e:
        logger.error(f"Malware scan error: {e}")
        # Fail open or closed based on config
        return not Config.FAIL_CLOSED_ON_SCAN_ERROR
```

## 6. Performance Optimization

### 6.1 Image Processing Caching

```python
async def get_processed_image(self, image_hash, target_model):
    """Get processed image from cache or process it"""
    cache_key = f"image:processed:{image_hash}:{target_model}"
    
    # Check cache
    cached = await self.redis.get(cache_key)
    if cached:
        return pickle.loads(cached)
    
    # Process image if not cached
    original = await self.get_original_image(image_hash)
    if not original:
        return None
    
    # Process for target model
    processed, context = await self.transform_for_model(original, target_model)
    
    # Cache processed version
    await self.redis.setex(
        cache_key,
        Config.IMAGE_CACHE_TTL,
        pickle.dumps((processed, context))
    )
    
    return processed, context
```

### 6.2 Image Compression Strategies

```python
async def optimize_for_bandwidth(self, image_data, context):
    """Optimize image based on network conditions"""
    # Get network context
    bandwidth = context.get("bandwidth", "high")
    
    if bandwidth == "low":
        # Aggressive optimization for low bandwidth
        return await self._apply_transformations(image_data, [
            self._resize_image(max_dimension=384),
            self._convert_format(target_format="jpeg", quality=65)
        ])
    elif bandwidth == "medium":
        # Moderate optimization
        return await self._apply_transformations(image_data, [
            self._resize_image(max_dimension=512),
            self._convert_format(target_format="jpeg", quality=75)
        ])
    else:
        # High bandwidth - minimal optimization
        return await self._apply_transformations(image_data, [
            self._resize_image(max_dimension=768),
            self._convert_format(target_format="jpeg", quality=85)
        ])
```

## 7. Integration with LLM Pipeline

### 7.1 Multimodal Message Construction

```python
def construct_multimodal_request(self, text_query, image_data, model):
    """Construct multimodal message for different backends"""
    if model == "gemini-thinking":
        # Gemini API format
        return {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": text_query},
                        {"inline_data": {
                            "mime_type": "image/jpeg",
                            "data": self.encode_image_for_api(image_data, prefix=False)
                        }}
                    ]
                }
            ]
        }
    elif model == "llava":
        # Ollama format for LLaVA
        return {
            "model": Config.LLAVA_MODEL,
            "prompt": text_query,
            "images": [self.encode_image_for_api(image_data, prefix=False)]
        }
    else:
        # Default format
        return {
            "query": text_query,
            "image": self.encode_image_for_api(image_data)
        }
```

## 8. Error Handling

```python
class ImageProcessingError(Exception):
    """Base class for image processing errors"""
    pass

class InvalidImageError(ImageProcessingError):
    """Invalid image data or format"""
    pass

class ImageTooLargeError(ImageProcessingError):
    """Image exceeds size limits"""
    pass

class ProcessingFailedError(ImageProcessingError):
    """Generic processing failure"""
    pass

async def handle_processing_error(self, error, image_context):
    """Handle image processing errors gracefully"""
    if isinstance(error, InvalidImageError):
        return {"error": "Invalid image format or corrupted data"}
    elif isinstance(error, ImageTooLargeError):
        return {"error": f"Image too large. Maximum size: {Config.MAX_IMAGE_SIZE/1024/1024}MB"}
    else:
        # Log unexpected errors
        logger.error(f"Image processing error: {error}", exc_info=True)
        return {"error": "Failed to process image"}
```

## 9. Future Enhancements

The image processing pipeline roadmap includes:

1. **Content-Aware Processing**: Adjusting processing based on image content (text, faces, etc.)
2. **Progressive Image Loading**: Sending low-res versions first, then upgrading
3. **Format-Specific Optimizations**: Custom processing for WebP, AVIF, etc.
4. **ML-Based Image Analysis**: Pre-classification of images before sending to LLMs
5. **Animated GIF/WebP Support**: Handling of animated content

This image processing pipeline provides Opossum Search with robust multimodal capabilities while ensuring optimal performance, security, and compatibility with various LLM backends.