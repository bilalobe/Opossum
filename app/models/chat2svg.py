"""Chat2SVG Integration for advanced SVG generation capabilities.

This module provides integration with the Chat2SVG project to generate
high-quality SVG graphics from text descriptions using a three-stage pipeline:
1. Template Generation with LLMs
2. Detail Enhancement with diffusion models
3. SVG Optimization with VAE models
"""
import asyncio
import os
import sys
import logging
import base64
import tempfile
import re
import datetime
import hashlib
import psutil
from typing import Dict, Any, Optional

import cairosvg
import yaml

from app.config import Config
from app.utils.infrastructure.cache import get_from_cache, add_to_cache

logger = logging.getLogger(__name__)

# Resource threshold configurations
RESOURCE_THRESHOLDS = {
    "high": {
        "cpu_percent_available": 50,  # At least 50% CPU available
        "memory_percent_available": 40,  # At least 40% memory available
        "detail_level": "high",
    },
    "medium": {
        "cpu_percent_available": 30,
        "memory_percent_available": 20,
        "detail_level": "medium",
    },
    "low": {
        "cpu_percent_available": 10,
        "memory_percent_available": 10,
        "detail_level": "low",
    },
    "minimal": {
        "cpu_percent_available": 0,
        "memory_percent_available": 0,
        "detail_level": "minimal",
    }
}

class SVGTemplate:
    """Represents an SVG template generated from a text prompt."""

    def __init__(self, svg_content: str, prompt: str, style: Optional[str] = None):
        """Initialize an SVG template.

        Args:
            svg_content: The SVG content as a string
            prompt: The original prompt used to generate the SVG
            style: Optional style guidance used during generation
        """
        self.svg_content = svg_content
        self.prompt = prompt
        self.style = style or "default"

    def __repr__(self) -> str:
        """Return a string representation of the SVG template."""
        return f"SVGTemplate(prompt='{self.prompt[:20]}...', style='{self.style}', size={len(self.svg_content)} bytes)"

    def to_base64(self) -> str:
        """Convert the SVG to a base64 string representation using cairosvg."""
        # This is potentially CPU-bound. If it becomes a bottleneck,
        # consider running it in a separate thread using asyncio.to_thread
        try:
            png_data = cairosvg.svg2png(bytestring=self.svg_content.encode('utf-8'))
            return base64.b64encode(png_data).decode('utf-8')
        except Exception as e:
            logger.error(f"Error converting SVG to base64: {str(e)}")
            # Consider returning a placeholder base64 image or raising error
            return ""

class PromptManager:
    """Manages prompts for SVG generation based on YAML configuration."""

    def __init__(self, prompts_path: Optional[str] = None):
        """Initialize the prompt manager with prompts from YAML file."""
        self.prompts = {}

        if not prompts_path:
            # Default to Chat2SVG's prompts.yaml
            prompts_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'Chat2SVG-main',
                'prompts.yaml'
            )

        try:
            if os.path.exists(prompts_path):
                with open(prompts_path, 'r') as f:
                    self.prompts = yaml.safe_load(f)
                logger.info(f"Loaded prompts from {prompts_path}")
            else:
                logger.warning(f"Prompts file not found at {prompts_path}, using defaults")
                # Load default prompts
                self._load_default_prompts()
        except Exception as e:
            logger.error(f"Error loading prompts: {str(e)}")
            self._load_default_prompts()

    def _load_default_prompts(self):
        """Load default prompts if YAML file is unavailable."""
        self.prompts = {
            "system": "You are a vector graphics designer tasked with creating SVG from text.",
            "expand_text_prompt": "Expand the following prompt into a detailed description: {prompt}",
            "write_svg_code": "Create SVG code for the following description: {description}",
            "svg_refine": "Refine the following SVG code: {svg_content}"
        }

    def get_prompt(self, prompt_type: str, **kwargs) -> str:
        """Get a prompt of a specific type with variables filled in.
        
        Supports both {key} format and <KEY> format placeholders.
        
        Args:
            prompt_type: The type of prompt to retrieve
            **kwargs: Variables to substitute in the prompt
        
        Returns:
            Formatted prompt string
        """
        prompt_template = self.prompts.get(prompt_type, "")
        if not prompt_template:
            logger.warning(f"Prompt type '{prompt_type}' not found")
            return ""
        
        # Make a copy of the template to avoid modifying the original
        formatted_prompt = prompt_template
        
        # First try standard Python formatting for {key} style placeholders
        try:
            formatted_prompt = prompt_template.format(**kwargs)
        except KeyError as e:
            logger.debug(f"Standard format placeholders not matched: {e}")
            # If standard formatting fails, we'll try the <KEY> format next
            pass
        except Exception as e:
            logger.warning(f"Error in standard format: {e}")
        
        # Then handle <KEY> style placeholders (Chat2SVG style)
        for key, value in kwargs.items():
            uppercase_key = key.upper()
            placeholder = f"<{uppercase_key}>"
            if placeholder in formatted_prompt:
                formatted_prompt = formatted_prompt.replace(placeholder, str(value))
        
        # Check if any <KEY> placeholders remain unfilled
        remaining_placeholders = re.findall(r'<[A-Z_]+>', formatted_prompt)
        if remaining_placeholders:
            logger.warning(f"Unfilled placeholders in prompt: {remaining_placeholders}")
        
        return formatted_prompt

    def __repr__(self) -> str:
        """Return a string representation of the prompt manager."""
        return f"PromptManager(types={list(self.prompts.keys())})"


class Chat2SVGGenerator:
    """Integration with Chat2SVG for advanced SVG generation from text descriptions."""

    def __init__(self):
        """Initialize the Chat2SVG generator with proper paths and configuration."""
        # Base path to Chat2SVG directory
        self.chat2svg_path = Config.CHAT2SVG_PATH
        
        # Default script paths based on standard installation structure
        self.template_gen_script = os.path.join(self.chat2svg_path, "1_template_generation", "main.py")
        
        # Check for executable scripts (binary/installed mode)
        self.executable_mode = False
        executable_path = os.path.join(self.chat2svg_path, "bin", "chat2svg-generate")
        if os.path.exists(executable_path) and os.access(executable_path, os.X_OK):
            self.template_gen_script = executable_path
            self.executable_mode = True
            logger.info("Using Chat2SVG in executable mode")
        
        # Cache configuration
        self.cache_ttl = Config.CHAT2SVG_CACHE_TTL if hasattr(Config, 'CHAT2SVG_CACHE_TTL') else 3600 # Cache SVGs for 1 hour default
        
        # Feature flags
        self.enabled = Config.CHAT2SVG_ENABLED if hasattr(Config, 'CHAT2SVG_ENABLED') else False
        self.use_detail_enhancement = Config.CHAT2SVG_DETAIL_ENHANCEMENT if hasattr(Config, 'CHAT2SVG_DETAIL_ENHANCEMENT') else False
        self.use_optimization = Config.CHAT2SVG_OPTIMIZATION if hasattr(Config, 'CHAT2SVG_OPTIMIZATION') else True # Default to simple optimization (base64)

        # Model quantization settings
        self.quantize_models = Config.CHAT2SVG_QUANTIZE_MODELS if hasattr(Config, 'CHAT2SVG_QUANTIZE_MODELS') else True
        self.quantization_precision = Config.CHAT2SVG_QUANTIZATION_PRECISION if hasattr(Config, 'CHAT2SVG_QUANTIZATION_PRECISION') else "int8"
        
        # Available quantization levels
        self.quantization_levels = {
            "fp32": {"desc": "Full precision (32-bit)", "memory_reduction": 1.0, "quality_impact": "None"},
            "fp16": {"desc": "Half precision (16-bit)", "memory_reduction": 0.5, "quality_impact": "Very Low"},
            "int8": {"desc": "8-bit integer", "memory_reduction": 0.25, "quality_impact": "Low"},
            "int4": {"desc": "4-bit integer", "memory_reduction": 0.125, "quality_impact": "Medium"}
        }
        
        # Streaming configuration
        self.streaming_enabled = Config.CHAT2SVG_STREAMING if hasattr(Config, 'CHAT2SVG_STREAMING') else True
        self.stream_chunk_size = Config.CHAT2SVG_STREAM_CHUNK_SIZE if hasattr(Config, 'CHAT2SVG_STREAM_CHUNK_SIZE') else 10
        self.min_svg_size_for_streaming = 50000  # Only stream SVGs larger than ~50KB
        
        # Client-side rendering configuration
        self.client_rendering_enabled = Config.CHAT2SVG_CLIENT_RENDERING if hasattr(Config, 'CHAT2SVG_CLIENT_RENDERING') else True
        self.client_rendering_threshold = Config.CHAT2SVG_CLIENT_RENDERING_THRESHOLD if hasattr(Config, 'CHAT2SVG_CLIENT_RENDERING_THRESHOLD') else 70
        self.client_max_complexity = Config.CHAT2SVG_CLIENT_MAX_COMPLEXITY if hasattr(Config, 'CHAT2SVG_CLIENT_MAX_COMPLEXITY') else 5000  # Max path data points

        # Subprocess timeout
        self.subprocess_timeout = Config.CHAT2SVG_TIMEOUT if hasattr(Config, 'CHAT2SVG_TIMEOUT') else 60 # 60 seconds default

        # Check if Chat2SVG is installed and configured
        self._is_available = self.enabled and os.path.exists(self.chat2svg_path) and os.path.exists(self.template_gen_script)
        if not self.enabled:
            logger.info("Chat2SVG integration is disabled via configuration.")
        elif not self._is_available:
            logger.warning("Chat2SVG directory or main script not found at expected paths: %s, %s", self.chat2svg_path, self.template_gen_script)
        else:
            logger.info("Chat2SVG found at: %s", self.chat2svg_path)
            # Model availability check is basic, full check depends on Chat2SVG scripts
            self._check_model_availability()

        # Initialize the prompt manager
        self.prompt_manager = PromptManager()
        
        # Log quantization settings
        if self._is_available and self.quantize_models:
            quant = self.quantization_levels[self.quantization_precision]
            logger.info(f"Using {self.quantization_precision} quantization ({quant['desc']}) "
                       f"for {quant['memory_reduction'] * 100:.1f}% memory usage")
    
    def __repr__(self) -> str:
        """Return a string representation of the generator."""
        status = "available" if self.is_available() else "unavailable"
        features = []
        if self.use_detail_enhancement: features.append("detail_enhancement (stub)")
        if self.use_optimization: features.append("optimization (stub/simplified)")

        return f"Chat2SVGGenerator(status={status}, features={features})"

    def _check_model_availability(self) -> bool:
        """Basic check for *some* model files. Full check depends on Chat2SVG scripts."""
        # This check is very basic and might not cover all dependencies of Chat2SVG.
        required_paths = [
            os.path.join(self.chat2svg_path, '3_svg_optimization', 'vae_model', 'cmd_10.pth'),
            # Add other critical model paths if known
        ]

        missing = [path for path in required_paths if not os.path.exists(path)]

        if missing:
            logger.warning(f"Chat2SVG models potentially missing: {missing}")
            logger.info("Run download/setup scripts in Chat2SVG-main directory if generation fails.")
            # Don't mark as unavailable solely based on this basic check
            return False

        return True

    def is_available(self) -> bool:
        """Check if Chat2SVG is enabled and seems available for use."""
        return self._is_available

    async def generate_svg_from_prompt(self, prompt: str, style: Optional[str] = None) -> Dict[str, Any]:
        """Generate an SVG from a text prompt using the Chat2SVG pipeline.

        Args:
            prompt: Text description to generate SVG from
            style: Optional style guidance (e.g., "cartoon", "minimalist")

        Returns:
            Dict containing svg_content, base64_image and metadata
        """
        # Check cache first
        cache_key = f"chat2svg_{prompt}_{style or 'default'}"
        cached_result = get_from_cache(cache_key)
        if cached_result:
            logger.info(f"Cache hit for SVG generation: {prompt[:30]}...")
            return cached_result

        if not self.is_available():
            logger.warning("Chat2SVG not available or disabled, using fallback SVG generation")
            svg_content = self._fallback_svg(prompt)
            base64_image = await self._svg_to_base64(svg_content) # Generate base64 even for fallback
            return {
                "svg_content": svg_content,
                "base64_image": base64_image,
                "metadata": {
                    "prompt": prompt,
                    "error": "Chat2SVG not available or disabled",
                    "fallback": True
                }
            }

        try:
            # Stage 1: Template Generation
            template_svg = await self._generate_template(prompt, style)
            if not template_svg: # Check if fallback was returned due to error
                 raise ValueError("Template generation failed")

            # Stage 2: Detail Enhancement (optional based on config - currently stubbed)
            if self.use_detail_enhancement:
                enhanced_svg = await self._enhance_details(template_svg, prompt)
            else:
                enhanced_svg = template_svg

            # Stage 3: SVG Optimization (optional based on config - currently simplified)
            if self.use_optimization:
                final_svg, base64_image = await self._optimize_svg(enhanced_svg)
            else:
                final_svg = enhanced_svg
                base64_image = await self._svg_to_base64(final_svg) # Convert final SVG

            if not final_svg:
                 raise ValueError("SVG Optimization failed")

            result = {
                "svg_content": final_svg,
                "base64_image": base64_image,
                "metadata": {
                    "prompt": prompt,
                    "style": style,
                    "pipeline_stages": "template" +
                        ("-detail_stub" if self.use_detail_enhancement else "") +
                        ("-optimization_simple" if self.use_optimization else ""),
                    "fallback": False
                }
            }

            # Cache the result
            add_to_cache(cache_key, result, ttl=self.cache_ttl)

            return result

        except Exception as e:
            logger.error(f"Error in Chat2SVG pipeline for prompt '{prompt[:30]}...': {str(e)}", exc_info=True)
            # Fallback to simpler SVG generation on any pipeline error
            svg_content = self._fallback_svg(prompt)
            base64_image = await self._svg_to_base64(svg_content)
            return {
                "svg_content": svg_content,
                "base64_image": base64_image,
                "metadata": {
                    "prompt": prompt,
                    "error": str(e),
                    "fallback": True
                }
            }

    async def _generate_template(self, prompt: str, style: Optional[str] = None) -> Optional[str]:
        """Run the first stage of Chat2SVG pipeline (external script) to generate a template SVG.

        Args:
            prompt: Text description to generate SVG from
            style: Optional style guidance

        Returns:
            SVG template as a string, or None if generation fails.
        """
        logger.info(f"Generating SVG template for prompt: {prompt[:30]}...")

        # Create a temporary directory to store the output
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = os.path.join(temp_dir, "output.svg")

            try:
                # Construct the command arguments
                if self.executable_mode:
                    # Use the executable interface
                    cmd = [
                        self.template_gen_script,
                        "--prompt", prompt,
                        "--output", output_file,
                    ]
                    if style:
                        cmd.extend(["--style", style])
                else:
                    # Use the Python module interface
                    cmd = [
                        sys.executable,
                        self.template_gen_script,
                        "--target", prompt,
                        "--output", output_file,
                    ]
                    # if style:
                    #     cmd.extend(["--style", style])

                logger.debug(f"Running Chat2SVG command: {' '.join(cmd)}")

                # Run the command asynchronously via a subprocess
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                # Wait for the process to complete with a timeout
                try:
                    stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=self.subprocess_timeout)
                except asyncio.TimeoutError:
                    logger.error(f"Chat2SVG template generation timed out after {self.subprocess_timeout}s for prompt: {prompt[:30]}...")
                    process.kill()
                    await process.wait()
                    return None

                stdout_decoded = stdout.decode().strip()
                stderr_decoded = stderr.decode().strip()

                if stdout_decoded: logger.debug(f"Chat2SVG stdout: {stdout_decoded}")
                if stderr_decoded: logger.warning(f"Chat2SVG stderr: {stderr_decoded}") # Log stderr as warning

                if process.returncode != 0:
                    logger.error(f"Chat2SVG template generation script failed with code {process.returncode} for prompt: {prompt[:30]}...")
                    return None

                # Read the generated SVG
                if os.path.exists(output_file):
                    # Use async file reading if files can be large
                    # For typical SVGs, sync read is often fine within async context
                    with open(output_file, "r", encoding='utf-8') as f:
                        svg_content = f.read()
                    logger.info(f"Successfully generated SVG template for prompt: {prompt[:30]}...")
                    return svg_content
                else:
                    logger.error(f"Output file '{output_file}' not found after Chat2SVG script execution.")
                    return None

            except FileNotFoundError:
                 logger.error(f"Chat2SVG script or Python executable not found. Script: {self.template_gen_script}, Python: {sys.executable}", exc_info=True)
                 return None
            except Exception as e:
                logger.error(f"Unexpected error running Chat2SVG template generation: {str(e)}", exc_info=True)
                return None

    async def _detect_available_resources(self) -> str:
        """Detect available system resources and determine appropriate detail level.
        
        Returns:
            String representing resource level: 'high', 'medium', 'low', or 'minimal'
        """
        try:
            # Get available CPU and memory
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            
            # Calculate available resources (inverted percentages)
            cpu_available = 100 - cpu_percent
            memory_available = 100 - memory.percent
            
            logger.debug(f"Available resources - CPU: {cpu_available}%, Memory: {memory_available}%")
            
            # Determine resource level based on thresholds
            if (cpu_available >= RESOURCE_THRESHOLDS["high"]["cpu_percent_available"] and 
                    memory_available >= RESOURCE_THRESHOLDS["high"]["memory_percent_available"]):
                return "high"
            elif (cpu_available >= RESOURCE_THRESHOLDS["medium"]["cpu_percent_available"] and 
                    memory_available >= RESOURCE_THRESHOLDS["medium"]["memory_percent_available"]):
                return "medium"
            elif (cpu_available >= RESOURCE_THRESHOLDS["low"]["cpu_percent_available"] and 
                    memory_available >= RESOURCE_THRESHOLDS["low"]["memory_percent_available"]):
                return "low"
            else:
                return "minimal"
        except Exception as e:
            logger.warning(f"Error detecting system resources: {str(e)}")
            return "minimal"  # Most conservative option on error

    async def _enhance_details(self, svg_content: str, prompt: str) -> str:
        """Run the second stage of Chat2SVG pipeline to enhance SVG details with diffusion models.
        
        This implementation now scales detail enhancement based on available system resources.
        
        Args:
            svg_content: SVG template content
            prompt: Original prompt for context
        
        Returns:
            Enhanced SVG content
        """
        logger.info(f"Enhancing SVG details for prompt: {prompt[:30]}...")
        
        # Determine resource level and corresponding detail level
        resource_level = await self._detect_available_resources()
        detail_level = RESOURCE_THRESHOLDS[resource_level]["detail_level"]
        
        logger.info(f"Using {detail_level} detail level based on available resources ({resource_level})")
        
        # This is a stub implementation that demonstrates the planned workflow
        try:
            # 1. Extract key objects/elements from the SVG
            extracted_elements = self._extract_svg_elements(svg_content)
            if not extracted_elements:
                logger.info("No major elements found for enhancement")
                return svg_content
                
            # 2. Create diffusion model prompts for detailed enhancements
            detail_prompts = {}
            
            # Adjust number of elements to process based on resource level
            max_elements = {
                "high": len(extracted_elements),  # Process all elements
                "medium": min(len(extracted_elements), 10),  # Process up to 10 elements
                "low": min(len(extracted_elements), 5),      # Process up to 5 elements
                "minimal": 0                                 # Skip enhancement
            }
            
            # If minimal resources, skip enhancement entirely
            if resource_level == "minimal":
                logger.warning("Insufficient resources for detail enhancement, skipping")
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                comment = f"\n<!-- SVG detail enhancement skipped due to limited resources at {timestamp} -->\n"
                if "</svg>" in svg_content:
                    return svg_content.replace("</svg>", f"{comment}</svg>")
                return svg_content + comment
            
            # Select elements to enhance based on resource level
            elements_to_enhance = list(extracted_elements.items())[:max_elements[resource_level]]
            
            # Create targeted prompts based on detail level
            for element_id, element_type in elements_to_enhance:
                if detail_level == "high":
                    detail_prompts[element_id] = f"Highly detailed {element_type} for '{prompt}' with texture and depth"
                elif detail_level == "medium":
                    detail_prompts[element_id] = f"Moderately detailed {element_type} for '{prompt}'"
                else:  # low
                    detail_prompts[element_id] = f"Simple {element_type} for '{prompt}'"
            
            logger.info(f"Would enhance {len(detail_prompts)} elements using diffusion models at {detail_level} detail")
            
            # 3. In a real implementation, this would call the diffusion model API with appropriate parameters
            # enhanced_elements = await self._run_diffusion_enhancement(detail_prompts, detail_level=detail_level)
            
            # 4. Mock the merging of enhanced elements
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            comment = f"\n<!-- SVG processed through detail enhancement stage (stub) at {timestamp} -->\n"
            comment += f"<!-- Resource level: {resource_level}, Detail level: {detail_level} -->\n"
            comment += f"<!-- Would enhance {len(detail_prompts)}/{len(extracted_elements)} elements -->\n"
            
            if "</svg>" in svg_content:
                enhanced_svg = svg_content.replace("</svg>", f"{comment}</svg>")
            else:
                enhanced_svg = svg_content + comment
                
            logger.info("Detail enhancement stage completed (stub implementation)")
            return enhanced_svg
            
        except Exception as e:
            logger.error(f"Error in detail enhancement (stub): {str(e)}", exc_info=True)
            # Return original content on error
            return svg_content

    async def _extract_svg_elements(self, svg_content: str) -> Dict[str, Dict[str, Any]]:
        """Extract major elements from SVG for potential enhancement.
        
        Analyzes the SVG structure to identify key elements that could be enhanced
        with diffusion models in a full implementation.
        
        Args:
            svg_content: The SVG content to analyze
    
        Returns:
            Dictionary mapping element IDs to information about each element
        """
        if not svg_content:
            return {}
    
        extracted_elements = {}
    
        try:
            # Use regex to find path elements with IDs
            path_pattern = r'<path\s+([^>]*id=["\']([^"\']+)["\'][^>]*)>'
            path_matches = re.finditer(path_pattern, svg_content)
        
            for match in path_matches:
                attrs = match.group(1)
                element_id = match.group(2)
            
                # Extract any d attribute (path data)
                d_match = re.search(r'd=["\']([^"\']+)["\']', attrs)
                d_value = d_match.group(1) if d_match else ""
            
                # Extract fill color if present
                fill_match = re.search(r'fill=["\']([^"\']+)["\']', attrs)
                fill = fill_match.group(1) if fill_match else "none"
            
                # Try to guess what this path represents based on attributes
                description = "unknown shape"
                if "circle" in element_id.lower() or (d_value and d_value.startswith("M") and "A" in d_value):
                    description = "circle"
                elif "rect" in element_id.lower() or (d_value and d_value.count("L") == 3 and d_value.count("Z") == 1):
                    description = "rectangle"
                elif "line" in element_id.lower():
                    description = "line"
            
                extracted_elements[element_id] = {
                    "type": "path",
                    "description": description,
                    "fill": fill,
                    "d": d_value[:20] + "..." if len(d_value) > 20 else d_value,
                    "hash": self._hash_element(d_value, fill)  # Hash for caching
                }
            
            # Extract text elements
            text_pattern = r'<text\s+([^>]*id=["\']([^"\']+)["\'][^>]*)>(.*?)</text>'
            text_matches = re.finditer(text_pattern, svg_content, re.DOTALL)
        
            for match in text_matches:
                attrs = match.group(1)
                element_id = match.group(2)
                content = match.group(3).strip()
            
                # Extract style or font attributes if present
                style_match = re.search(r'style=["\']([^"\']+)["\']', attrs)
                style = style_match.group(1) if style_match else ""
            
                extracted_elements[element_id] = {
                    "type": "text",
                    "content": content[:30] + "..." if len(content) > 30 else content,
                    "description": "text element",
                    "style": style,
                    "hash": self._hash_element(content, style)  # Hash for caching
                }
            
            # Extract group elements with IDs
            group_pattern = r'<g\s+([^>]*id=["\']([^"\']+)["\'][^>]*)>'
            group_matches = re.finditer(group_pattern, svg_content)
        
            for match in group_matches:
                attrs = match.group(1)
                element_id = match.group(2)
            
                # Try to determine group purpose from ID
                description = "group"
                for purpose in ["background", "foreground", "body", "head", "tail", "eyes", "legs", "arms"]:
                    if purpose in element_id.lower():
                        description = purpose
                        break
            
                extracted_elements[element_id] = {
                    "type": "group",
                    "description": description,
                    "hash": self._hash_element(element_id, description)  # Hash for caching
                }
        
            logger.info(f"Extracted {len(extracted_elements)} elements from SVG")
            return extracted_elements
        
        except Exception as e:
            logger.error(f"Error extracting SVG elements: {str(e)}", exc_info=True)
            return {}

    def _hash_element(self, *args) -> str:
        """Generate a hash for an element to use as a cache key.
        
        Args:
            *args: Element attributes to include in the hash
        
        Returns:
            A hash string representing the element
        """
        # Concatenate all arguments as strings
        content = "".join(str(arg) for arg in args)
    
        # Generate a hash
        return hashlib.md5(content.encode()).hexdigest()
        

# Create a singleton instance for easy import and use
chat2svg_generator = Chat2SVGGenerator()
