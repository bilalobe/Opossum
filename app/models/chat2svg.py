"""Chat2SVG Integration with Optimized Pipeline Controller.

Applies principles of resource monitoring, greedy stage allocation,
circuit breaking, dynamic parameter tuning, and multi-request optimization
to improve performance and resilience.
"""
import asyncio
import base64
import hashlib
import logging
import os
import re
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

try:
    import psutil
except ImportError:
    psutil = None
    logging.warning("psutil not installed. Resource detection will be limited.")

try:
    import torch
except ImportError:
    torch = None
    logging.debug("torch not installed. GPU detection will be skipped.")

try:
    import cairosvg
except ImportError:
    cairosvg = None
    logging.warning("cairosvg not installed, SVG to PNG conversion will fail")

# Assuming Config and cache utils are in the parent directory structure
try:
    from app.config import Config
    from app.utils.infrastructure.cache import get_from_cache, add_to_cache
except ImportError:
    logging.warning("Could not import from app.* - using fallback Config and cache stubs.")
    class Config:
        CHAT2SVG_PATH = os.path.expanduser("~/vendor/Chat2SVG")
        CHAT2SVG_ENABLED = True
        CHAT2SVG_DETAIL_ENHANCEMENT = True
        CHAT2SVG_OPTIMIZATION = True
        CHAT2SVG_QUANTIZE_MODELS = False
        CHAT2SVG_QUANTIZATION_PRECISION = "fp16"
        CHAT2SVG_CACHE_TTL = 3600
        CHAT2SVG_TIMEOUT = 180
        CHAT2SVG_STREAMING = False
        CHAT2SVG_CLIENT_RENDERING = False
        # Add resource thresholds from BaseConfig
        CHAT2SVG_RESOURCE_THRESHOLDS = {
            "high": {"cpu_percent_available": 50, "memory_percent_available": 40},
            "medium": {"cpu_percent_available": 30, "memory_percent_available": 20},
            "low": {"cpu_percent_available": 10, "memory_percent_available": 10},
            "minimal": {"cpu_percent_available": 0, "memory_percent_available": 0}
        }

    _cache = {}
    def get_from_cache(key): return _cache.get(key)
    def add_to_cache(key, value, ttl): _cache[key] = value

logger = logging.getLogger(__name__)

# Move resource thresholds from constants to Config-based values
RESOURCE_THRESHOLDS = getattr(Config, 'CHAT2SVG_RESOURCE_THRESHOLDS', {
    "high": {"cpu": 50, "memory": 40},
    "medium": {"cpu": 30, "memory": 20},
    "low": {"cpu": 10, "memory": 10},
    "minimal": {"cpu": 0, "memory": 0}
})

STAGE_SPECS = {
    "template": {"cpu": 0.1, "memory": 0.1, "gpu": 0.0, "vram": 0.1, "impact": 0.6, "latency": 15.0},
    "detail": {"cpu": 0.4, "memory": 0.4, "gpu": 0.8, "vram": 0.7, "impact": 0.3, "latency": 60.0},
    "optimize": {"cpu": 0.3, "memory": 0.2, "gpu": 0.3, "vram": 0.4, "impact": 0.1, "latency": 30.0}
}

PIPELINE_CONFIGS = {
    "high": {
        "detail": {"num_inference_steps": 30, "strength": 1.0, "guidance_scale": 7.0, "sam_level": "fine"},
        "optimize": {"iterations": 1000, "quality_level": "high"}
    },
    "medium": {
        "detail": {"num_inference_steps": 25, "strength": 0.9, "guidance_scale": 6.5, "sam_level": "medium"},
        "optimize": {"iterations": 700, "quality_level": "medium"}
    },
    "low": {
        "detail": {"num_inference_steps": 20, "strength": 0.85, "guidance_scale": 6.0, "sam_level": "coarse"},
        "optimize": {"iterations": 500, "quality_level": "low"}
    },
    "minimal": {
        "detail": {},
        "optimize": {}
    }
}


# --- Helper Functions ---


async def _to_thread(func, *args, **kwargs):
    loop = asyncio.get_running_loop()
    # Use default executor (ThreadPoolExecutor)
    return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

def _encode_svg_to_png_base64(svg_content: str) -> str:
    if cairosvg is None:
        logger.error("cairosvg is not installed, cannot encode SVG to PNG.")
        return ""
    try:
        if not svg_content:
            logger.warning("Attempted to encode empty SVG content.")
            return ""
        # Add explicit width/height if missing, as cairosvg might need it
        if 'width=' not in svg_content or 'height=' not in svg_content:
             # Basic check, might need improvement
             logger.debug("SVG lacks width/height, adding defaults for PNG conversion.")
             svg_content = re.sub(r'(<svg[^>]*)', r'\1 width="512px" height="512px"', svg_content, count=1)

        png_data = cairosvg.svg2png(bytestring=svg_content.encode('utf-8'), output_width=512, output_height=512) # Specify output size
        return base64.b64encode(png_data).decode('utf-8')
    except Exception as e:
        logger.error(f"Error converting SVG to base64 PNG: {e}. SVG start: '{svg_content[:150]}...'")
        return ""

async def _read_file_async(filepath: str) -> Optional[str]:
    try:
        with open(filepath, "r", encoding='utf-8') as f:
             content = await _to_thread(f.read)
        return content
    except FileNotFoundError:
        logger.error(f"File not found: {filepath}")
        return None
    except Exception as e:
        logger.error(f"Error reading file {filepath}: {e}")
        return None


# --- Circuit Breaker State ---
class CircuitState(Enum):
    CLOSED = "CLOSED"     # Normal operation
    OPEN = "OPEN"         # Not accepting requests
    HALF_OPEN = "HALF_OPEN" # Testing recovery

class PipelineError(Exception):
    """Custom exception for pipeline stage failures."""
    pass

class PipelineState:
    """Holds the intermediate data passed between stages in memory."""
    def __init__(self, prompt: str, style: Optional[str]):
        self.prompt: str = prompt
        self.style: Optional[str] = style
        self.target_name: str = _sanitize_filename(prompt)
        
        # Stage outputs (data, not paths)
        self.template_svg: Optional[str] = None
        self.enhanced_svg: Optional[str] = None
        self.target_png_bytes: Optional[bytes] = None
        self.optimized_svg: Optional[str] = None
        
        # Resource info
        self.resource_level: str = "low"
        self.gpu_available: bool = False
        self.vram_available: Optional[float] = None
        
        # Pipeline state
        self.pipeline_config: Dict[str, Dict] = {}
        self.stages_to_run: List[str] = []
        self.stages_run: List[str] = []
        self.stage_durations: Dict[str, float] = {}
        self.error: Optional[str] = None
        self.error_detail: Optional[str] = None
        self.fallback_used: bool = False
        self.is_half_open_trial: bool = False
        self.resource_allocation: Optional[Dict[str, float]] = None

    def update_stage_duration(self, stage_name: str, duration: float):
        """Record the duration of a stage execution."""
        self.stage_durations[stage_name] = duration
        
    def set_error(self, message: str, detail: Optional[str] = None):
        """Set error with optional detailed information."""
        self.error = message
        if detail:
            self.error_detail = detail.strip()
            if len(self.error_detail) > 1000:  # Truncate very long error details
                self.error_detail = self.error_detail[:997] + "..."


class Chat2SVGGenerator:
    """Orchestrates the optimized Chat2SVG pipeline with circuit breaker."""

    def __init__(self):
        """Initialize the Chat2SVG generator."""
        self.chat2svg_path = getattr(Config, 'CHAT2SVG_PATH', os.path.expanduser("~/vendor/Chat2SVG"))
        self.enabled = getattr(Config, 'CHAT2SVG_ENABLED', False)
        
        if not self.chat2svg_path or not os.path.isdir(self.chat2svg_path):
            logger.error(f"Config.CHAT2SVG_PATH ('{self.chat2svg_path}') is not a valid directory.")
            self._is_available = False
            self.enabled = False
            return

        # Script paths
        self.template_gen_script = os.path.join(self.chat2svg_path, "1_template_generation", "main.py")
        self.detail_enhance_script = os.path.join(self.chat2svg_path, "2_detail_enhancement", "main.py")
        self.optimization_script = os.path.join(self.chat2svg_path, "3_svg_optimization", "main.py")

        # Feature flags
        self.use_detail_enhancement = getattr(Config, 'CHAT2SVG_DETAIL_ENHANCEMENT', False)
        self.use_optimization = getattr(Config, 'CHAT2SVG_OPTIMIZATION', True)
        
        # Resource and performance settings
        self.max_svg_size = getattr(Config, 'CHAT2SVG_MAX_SVG_SIZE', 1024)
        self.max_prompt_length = getattr(Config, 'CHAT2SVG_MAX_PROMPT_LENGTH', 500)
        self.resource_mode = getattr(Config, 'CHAT2SVG_RESOURCE_MODE', 'adaptive')
        
        # Model quantization settings
        self.quantize_models = getattr(Config, 'CHAT2SVG_QUANTIZE_MODELS', False)
        self.quantization_precision = getattr(Config, 'CHAT2SVG_QUANTIZATION_PRECISION', 'fp16')
        
        # Determine quantized model directory
        _chat2svg_parent_dir = os.path.dirname(os.path.normpath(self.chat2svg_path))
        self.quantized_model_dir = getattr(Config, 'QUANTIZED_MODEL_DIR', 
            os.path.join(_chat2svg_parent_dir, "data", "quantized_models"))

        # Cache and timeout settings
        self.cache_ttl = getattr(Config, 'CHAT2SVG_CACHE_TTL', 3600)
        self.cache_maxsize = getattr(Config, 'CHAT2SVG_CACHE_MAXSIZE', 50)
        self.subprocess_timeout = getattr(Config, 'CHAT2SVG_TIMEOUT', 180)
        
        # Output directories
        self.output_dir = getattr(Config, 'CHAT2SVG_OUTPUT_DIR', os.path.join(self.chat2svg_path, 'output'))
        self.temp_dir = getattr(Config, 'CHAT2SVG_TEMP_DIR', tempfile.gettempdir())

        # Style settings
        self.default_style = getattr(Config, 'CHAT2SVG_DEFAULT_STYLE', 'modern')
        self.default_theme = getattr(Config, 'CHAT2SVG_DEFAULT_THEME', 'light')
        self.default_color_palette = getattr(Config, 'CHAT2SVG_DEFAULT_COLOR_PALETTE', 'default')
        self.path_simplification = getattr(Config, 'CHAT2SVG_PATH_SIMPLIFICATION', 0.2)
        self.enable_animations = getattr(Config, 'CHAT2SVG_ENABLE_ANIMATIONS', False)

        # Availability Check
        scripts_ok = os.path.exists(self.template_gen_script)
        if self.use_detail_enhancement and not os.path.exists(self.detail_enhance_script):
            logger.warning(f"Detail enhancement enabled but script not found: {self.detail_enhance_script}")
            scripts_ok = False
        if self.use_optimization and not os.path.exists(self.optimization_script):
            logger.warning(f"Optimization enabled but script not found: {self.optimization_script}")
            scripts_ok = False

        self._is_available = self.enabled and scripts_ok

        # Log status and configuration
        status_msg = "disabled" if not self.enabled else "unavailable (scripts missing)" if not scripts_ok else "enabled"
        logger.info(f"Chat2SVG status: {status_msg}")
        if self._is_available:
            if not self._check_model_availability():
                logger.warning("Chat2SVG model files might be missing")
            if self.quantize_models:
                logger.info(f"Model quantization enabled: {self.quantization_precision}")
                logger.info(f"Quantized models directory: {self.quantized_model_dir}")
            logger.info(f"Resource mode: {self.resource_mode}")
            logger.info(f"Output directory: {self.output_dir}")

        # Initialize prompt manager
        self.prompt_manager = PromptManager(os.path.join(self.chat2svg_path, 'prompts.yaml'))

    def is_available(self) -> bool:
        """Check if the generator is available for use."""
        return self._is_available

    def _check_model_availability(self) -> bool:
        """Check for required model files."""
        missing_files = []
        
        # Stage 1 models/configs
        template_configs = [
            os.path.join(self.chat2svg_path, "1_template_generation", "config.yaml"),
            os.path.join(self.chat2svg_path, "1_template_generation", "prompts.yaml")
        ]
        
        # Stage 2 models (if enabled)
        if self.use_detail_enhancement:
            detail_models = [
                os.path.join(self.chat2svg_path, "2_detail_enhancement", "models", "diffusion.pt"),
                os.path.join(self.chat2svg_path, "2_detail_enhancement", "models", "sam.pt")
            ]
            template_configs.extend(detail_models)
            
        # Stage 3 models (if enabled)
        if self.use_optimization:
            vae_path = os.path.join(self.chat2svg_path, "3_svg_optimization", "vae_model", "cmd_10.pth")
            if self.quantize_models:
                # Check quantized model instead
                quant_suffix = f"_{self.quantization_precision}" if self.quantization_precision != "fp32" else ""
                vae_path = os.path.join(self.quantized_model_dir, "chat2svg", "3_svg_optimization", 
                                      "vae_model", f"cmd_10{quant_suffix}.pth")
            template_configs.append(vae_path)
            
        for file_path in template_configs:
            if not os.path.exists(file_path):
                missing_files.append(os.path.basename(file_path))
                
        if missing_files:
            logger.warning(f"Missing model/config files: {', '.join(missing_files)}")
            return False
            
        return True

    async def _detect_available_resources(self) -> Dict[str, float]:
        """Enhanced resource detection including GPU and Swap if available."""
        resources = {"cpu": 10.0, "memory": 10.0, "swap": 0.0}  # Initialize swap
        if psutil is None:
            return resources

        try:
            cpu_usage = await _to_thread(psutil.cpu_percent, interval=0.1)
            memory = await _to_thread(psutil.virtual_memory)
            swap = await _to_thread(psutil.swap_memory)  # Get swap info
            resources["cpu"] = 100.0 - cpu_usage
            resources["memory"] = memory.available / memory.total * 100.0
            resources["swap"] = swap.percent  # Store swap percentage

            if torch is not None and torch.cuda.is_available():
                try:
                    with torch.cuda.device(0):
                        total = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                        used = torch.cuda.memory_allocated() / (1024**3)
                        resources["gpu"] = 100.0
                        resources["vram"] = ((total - used) / total) * 100.0
                except RuntimeError as e:
                    logger.warning(f"Runtime error during GPU detection: {e}")
                except Exception as e:
                    logger.debug(f"Unexpected GPU detection error: {e}")

            logger.debug(
                f"Available resources: CPU={resources['cpu']:.1f}%, Mem={resources['memory']:.1f}%, Swap={resources['swap']:.1f}%, GPU={'Yes' if 'gpu' in resources else 'No'}"
            )  # Updated log
            return resources
        except Exception as e:
            logger.warning(f"Resource detection error: {e}")
            return resources

    def _configure_pipeline_params(self, state: PipelineState, available_resources: Dict[str, float]):
        """Dynamic parameter configuration based on available resources."""
        state.resource_level = self._get_resource_level(available_resources)
        base_config = PIPELINE_CONFIGS.get(state.resource_level, PIPELINE_CONFIGS["low"])
        state.pipeline_config = base_config.copy()

        # Dynamic parameter tuning
        if "detail" in state.pipeline_config:
            mem_factor = min(max(available_resources.get("memory", 10) / 50.0, 0.0), 1.0)
            cpu_factor = min(max(available_resources.get("cpu", 10) / 60.0, 0.0), 1.0)
            gpu_factor = min(max(available_resources.get("gpu", 0) / 70.0, 0.0), 1.0) if "gpu" in available_resources else 0.0
            
            # Weighted combination of factors
            combined_factor = (mem_factor * 0.3 + cpu_factor * 0.3 + gpu_factor * 0.4)
            
            # Adjust parameters based on resources
            steps = max(15, min(35, int(15 + 20 * combined_factor)))
            strength = max(0.7, min(1.0, 0.7 + 0.3 * combined_factor))
            guidance = max(5.0, min(7.5, 5.0 + 2.5 * combined_factor))
            
            state.pipeline_config["detail"].update({
                "num_inference_steps": steps,
                "strength": strength,
                "guidance_scale": guidance
            })

        if "optimize" in state.pipeline_config:
            # Scale optimization iterations based on resources
            base_iterations = state.pipeline_config["optimize"].get("iterations", 500)
            scaled_iterations = int(base_iterations * max(0.5, min(1.0, combined_factor)))
            state.pipeline_config["optimize"]["iterations"] = scaled_iterations

        logger.info(f"Configured pipeline for level '{state.resource_level}' with detail steps: {state.pipeline_config.get('detail',{}).get('num_inference_steps','N/A')}")

    def _get_resource_level(self, resources: Dict[str, float]) -> str:
        """Determine resource level string, considering swap usage."""
        level = "minimal"  # Start with lowest
        for lvl in ["high", "medium", "low"]:
             thresholds = RESOURCE_THRESHOLDS[lvl]
             if (resources.get("cpu", 0) >= thresholds["cpu"] and
                 resources.get("memory", 0) >= thresholds["memory"]):
                 level = lvl
                 break # Found highest possible level based on CPU/Mem

        # Downgrade based on swap usage
        swap_percent = resources.get("swap", 0)
        original_level = level
        if swap_percent > 75 and level != "minimal":
            level = "minimal"
        elif swap_percent > 50 and level == "high":
            level = "medium"
        elif swap_percent > 30 and level in ["high", "medium"]:
             level = "low"

        if level != original_level:
            logger.warning(f"Swap usage ({swap_percent:.1f}%) caused resource level downgrade from '{original_level}' to '{level}'.")

        return level

    async def generate_svg_from_prompt(self, prompt: str, style: Optional[str] = None) -> Dict[str, Any]:
        """Generate SVG using optimized pipeline with circuit breaker protection."""
        if not self.is_available():
            return await self._generate_fallback(prompt, "Service Unavailable")

        # Circuit Breaker Check
        if not await self._allow_request():
            return await self._generate_fallback(prompt, "Circuit Breaker Open")

        # Cache Check
        cache_key = f"chat2svg_opt_{hashlib.md5(f'{prompt}_{style or 'default'}'.encode()).hexdigest()}"
        if cached_result := await _to_thread(get_from_cache, cache_key):
            return cached_result

        # Pipeline Execution
        pipeline_start_time = time.monotonic()
        state = PipelineState(prompt, style)
        pipeline_temp_dir = None

        try:
            # Initialize Pipeline
            resources = await self._detect_available_resources()
            self._configure_pipeline_params(state, resources)
            state.stages_to_run = self._decide_stages_to_run(state)
            pipeline_temp_dir = tempfile.mkdtemp(prefix=f"chat2svg_pipe_{state.target_name}_")

            # --- Stage Execution ---
            if "template" in state.stages_to_run:
                if not await self._execute_stage_1(state, pipeline_temp_dir):
                    raise PipelineError("Stage 1 failed")

            if "detail" in state.stages_to_run:
                if not await self._execute_stage_2(state, pipeline_temp_dir):
                    raise PipelineError("Stage 2 failed")

            if "optimize" in state.stages_to_run:
                if not await self._execute_stage_3(state, pipeline_temp_dir, state.enhanced_svg, state.target_png_bytes):
                    raise PipelineError("Stage 3 failed")

            # --- Success ---
            if state.optimized_svg:
                # Cache result
                add_to_cache(cache_key, {
                    "svg_content": state.optimized_svg,
                    "base64_image": _encode_svg_to_png_base64(state.optimized_svg),
                    "metadata": {
                        "prompt": prompt,
                        "style": style,
                        "error": state.error,
                        "error_detail": state.error_detail if state.error_detail else None,
                        "fallback": state.fallback_used,
                        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
                    }
                }, self.cache_ttl)

            return {
                "svg_content": state.optimized_svg,
                "base64_image": _encode_svg_to_png_base64(state.optimized_svg),
                "metadata": {
                    "prompt": prompt,
                    "style": style,
                    "error": state.error,
                    "error_detail": state.error_detail if state.error_detail else None,
                    "fallback": state.fallback_used,
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
                }
            }

        except PipelineError as pe:
            await self._record_failure()
            return await self._generate_fallback(prompt, str(pe))
        except Exception as e:
            await self._record_failure()
            return await self._generate_fallback(prompt, f"Unexpected error: {type(e).__name__}")
        finally:
            if pipeline_temp_dir:
                await _to_thread(shutil.rmtree, pipeline_temp_dir, ignore_errors=True)

    async def _execute_stage_1(self, state: PipelineState, pipeline_temp_dir: str) -> bool:
        """Runs Stage 1: Template Generation script."""
        stage_start_time = time.monotonic()

        exec_result = await self._run_chat2svg_script(self.template_gen_script, [state.prompt, state.style], {
            "template_svg": os.path.join(pipeline_temp_dir, "template.svg")
        })

        success = False
        if exec_result["success"] and "template_svg" in exec_result["output_files"]:
            state.template_svg = await _read_file_async(exec_result["output_files"]["template_svg"])
            if state.template_svg:
                success = True
            else:
                state.set_error("Stage 1 output file empty")
        else:
            state.set_error("Stage 1 failed", exec_result["stderr"])

        state.update_stage_duration("template", time.monotonic() - stage_start_time)
        return success

    async def _execute_stage_2(self, state: PipelineState, pipeline_temp_dir: str) -> bool:
        """Runs Stage 2: Detail Enhancement script."""
        stage_start_time = time.monotonic()

        exec_result = await self._run_chat2svg_script(self.detail_enhance_script, [state.prompt, state.style], {
            "enhanced_svg": os.path.join(pipeline_temp_dir, "enhanced.svg"),
            "target_png": os.path.join(pipeline_temp_dir, "target.png")
        })

        success = False
        if exec_result["success"]:
            if "enhanced_svg" in exec_result["output_files"]:
                state.enhanced_svg = await _read_file_async(exec_result["output_files"]["enhanced_svg"])
            if "target_png" in exec_result["output_files"]:
                with open(exec_result["output_files"]["target_png"], "rb") as f:
                    state.target_png_bytes = await _to_thread(f.read)

            if state.enhanced_svg and state.target_png_bytes:
                success = True
            else:
                state.set_error("Stage 2 missing essential outputs")
        else:
            state.set_error("Stage 2 failed", exec_result["stderr"])

        state.update_stage_duration("detail", time.monotonic() - stage_start_time)
        return success

    async def _execute_stage_3(self, state: PipelineState, pipeline_temp_dir: str, svg_input: str, png_input_bytes: bytes) -> bool:
        """Run Stage 3: SVG Optimization using VAE."""
        stage_start_time = time.monotonic()

        stage3_svg_folder = os.path.join(pipeline_temp_dir, f"s3_{state.target_name}")
        os.makedirs(stage3_svg_folder, exist_ok=True)

        # Write provided content to files
        stage3_input_svg = os.path.join(stage3_svg_folder, f"{state.target_name}_with_new_path.svg")
        stage3_target_png = os.path.join(stage3_svg_folder, f"{state.target_name}_target.png")

        try:
            with open(stage3_input_svg, "w", encoding='utf-8') as f:
                await _to_thread(f.write, svg_input)
            with open(stage3_target_png, "wb") as f:
                await _to_thread(f.write, png_input_bytes)
        except Exception as e:
            state.set_error(f"Failed to write Stage 3 input files: {e}")
            return False

        exec_result = await self._run_chat2svg_script(self.optimization_script, [state.prompt, state.style], {
            "input_svg": stage3_input_svg,
            "target_png": stage3_target_png,
            "optimized_svg": os.path.join(stage3_svg_folder, f"{state.target_name}_optimized.svg")
        })

        success = False
        if exec_result["success"] and "optimized_svg" in exec_result["output_files"]:
            state.optimized_svg = await _read_file_async(exec_result["output_files"]["optimized_svg"])
            if state.optimized_svg:
                success = True
        else:
            state.set_error("Stage 3 failed", exec_result["stderr"])

        state.update_stage_duration("optimize", time.monotonic() - stage_start_time)
        return success

    async def _run_chat2svg_script(self, script_path: str, args: list, output_paths: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Helper to run a Chat2SVG script with improved logging."""
        result = {"success": False, "stdout": "", "stderr": "", "returncode": -1}
        if not os.path.exists(script_path):
            logger.error(f"Script not found: {script_path}")
            result["stderr"] = "Script not found."
            return result

        cmd = [sys.executable, script_path] + args
        script_name = os.path.basename(script_path)
        logger.info(f"Running {script_name} with args: {' '.join(args)}")

        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            cwd=os.path.dirname(script_path)
        )

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=self.subprocess_timeout)
            result["returncode"] = process.returncode
        except asyncio.TimeoutError:
            logger.error(f"Script '{script_name}' timed out after {self.subprocess_timeout}s.")
            result["stderr"] = f"Timeout after {self.subprocess_timeout}s."
            try: process.kill(); await process.wait()
            except: pass
            return result

        result["stdout"] = stdout.decode(errors='ignore').strip()
        result["stderr"] = stderr.decode(errors='ignore').strip()

        # Log stdout only on debug and only if not too long
        if result["stdout"]:
            stdout_preview = result["stdout"][:500] + ("..." if len(result["stdout"]) > 500 else "")
            logger.debug(f"{script_name} stdout:\n{stdout_preview}")
        
        # Log stderr as warning only if script failed
        if result["stderr"] and result["returncode"] != 0:
            stderr_preview = result["stderr"][:500] + ("..." if len(result["stderr"]) > 500 else "")
            logger.warning(f"{script_name} stderr:\n{stderr_preview}")

        if result["returncode"] != 0:
            return result

        result["success"] = True
        if output_paths:
            result["output_files"] = {}
            for key, path in output_paths.items():
                if os.path.exists(path):
                    result["output_files"][key] = path
                else:
                    logger.error(f"Missing output '{key}': {path}")
                    result["success"] = False
                    result["stderr"] += f"\nMissing output: {key}"

        return result

    async def _generate_fallback(self, prompt: str, error: Optional[str] = None) -> Dict[str, Any]:
        """Generate fallback SVG with standardized result structure."""
        logger.warning(f"Generating fallback SVG for prompt: {prompt[:30]}...")
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        escaped_prompt = re.sub(r'[<>&]', '', prompt)[:60]
        escaped_error = re.sub(r'[<>&]', '', error or "Chat2SVG failed or unavailable.")[:100]
        
        svg_content = f"""<svg viewBox="0 0 300 100" xmlns="http://www.w3.org/2000/svg">
<rect width="100%" height="100%" fill="#f8f8f8" stroke="#e0e0e0" stroke-width="1"/>
<text x="10" y="25" font-family="sans-serif" font-size="14" fill="#d9534f" font-weight="bold">Fallback SVG</text>
<text x="10" y="45" font-family="sans-serif" font-size="10" fill="#333">Prompt: {escaped_prompt}{'...' if len(prompt) > 60 else ''}</text>
<text x="10" y="60" font-family="sans-serif" font-size="10" fill="#777">Reason: {escaped_error}{'...' if len(error or '') > 100 else ''}</text>
<text x="10" y="80" font-family="sans-serif" font-size="8" fill="#999">Generated: {timestamp}</text>
</svg>"""

        base64_image = await _to_thread(_encode_svg_to_png_base64, svg_content)
        
        return {
            "svg_content": svg_content,
            "base64_image": base64_image,
            "metadata": {
                "prompt": prompt,
                "error": error,
                "error_detail": error_detail if error_detail else None,
                "fallback": True,
                "timestamp": timestamp
            }
        }


# --- Singleton Instance ---
try:
    chat2svg_generator = Chat2SVGGenerator()
except Exception as e:
    logger.critical(f"Failed to initialize Chat2SVGGenerator: {e}", exc_info=True)
    class DummyGenerator:
        def is_available(self): return False
        async def generate_svg_from_prompt(self, prompt, style=None):
             return {"svg_content": self._generate_fallback(prompt), "base64_image": "", "metadata": {"fallback": True, "error": "Generator Initialization Failed"}}
        def _generate_fallback(self, prompt): return f'<svg viewBox="0 0 100 50"><text x="5" y="20" font-size="8">Chat2SVG Init Failed</text><text x="5" y="35" font-size="6">{prompt[:20]}...</text></svg>'
    chat2svg_generator = DummyGenerator()


class MultiRequestOptimizer:
    """Optimizes concurrent SVG generation requests using max-flow principles"""
    
    def __init__(self):
        self.active_requests = 0
        self.request_queue = asyncio.Queue()
        # Use Config-based max concurrent requests
        max_concurrent = getattr(Config, 'CHAT2SVG_MAX_CONCURRENT_REQUESTS', 4)
        self.resource_semaphore = asyncio.Semaphore(max_concurrent)
        self.last_resource_check = 0
        self.resource_check_interval = getattr(Config, 'CHAT2SVG_RESOURCE_CHECK_INTERVAL', 5)
        self.resource_status = {
            'cpu': 0.0,
            'memory': 0.0,
            'gpu': False,
            'vram': 0.0
        }

    async def add_request(self, state: PipelineState) -> None:
        """Add a request to the optimization queue"""
        await self.request_queue.put(state)
        await self._process_queue()

    async def _update_resource_status(self) -> None:
        """Update resource availability status"""
        now = time.monotonic()
        if now - self.last_resource_check < 5:  # Only check every 5 seconds
            return

        self.last_resource_check = now
        cpu_pct = await _to_thread(psutil.cpu_percent)
        mem_pct = await _to_thread(psutil.virtual_memory().percent)
        
        self.resource_status.update({
            'cpu': cpu_pct / 100.0,
            'memory': mem_pct / 100.0,
            'gpu': torch.cuda.is_available() if hasattr(torch, 'cuda') else False,
            'vram': torch.cuda.get_device_properties(0).total_memory if self.resource_status['gpu'] else 0.0
        })

    def _calculate_request_priority(self, state: PipelineState) -> float:
        """Calculate priority score for a request based on resource requirements"""
        score = 0.0
        if 'optimize' in state.stages_to_run:
            score += 0.4  # Higher weight for optimization stage
        if state.resource_level == 'high':
            score -= 0.3  # Penalize high resource requests when busy
        return score

    async def _process_queue(self) -> None:
        """Process queued requests based on resource availability"""
        if self.request_queue.empty():
            return

        await self._update_resource_status()
        
        # Stop processing if system is overloaded
        if self.resource_status['cpu'] > 0.9 or self.resource_status['memory'] > 0.9:
            logger.warning("System resources overloaded, delaying request processing")
            return

        # Calculate max requests to process based on resources
        max_concurrent = min(
            4,  # Base limit
            8 if self.resource_status['cpu'] < 0.7 else 2,
            6 if self.resource_status['memory'] < 0.8 else 2
        )

        while not self.request_queue.empty() and self.active_requests < max_concurrent:
            async with self.resource_semaphore:
                state = await self.request_queue.get()
                self.active_requests += 1
                try:
                    # Configure optimal parameters based on system load
                    self._configure_for_load(state)
                    # Process request
                    await self._process_request(state)
                finally:
                    self.active_requests -= 1
                    self.request_queue.task_done()

    def _configure_for_load(self, state: PipelineState) -> None:
        """Adjust pipeline parameters based on current system load"""
        if self.resource_status['cpu'] > 0.8:
            state.resource_level = 'low'
        elif self.resource_status['cpu'] > 0.6:
            state.resource_level = 'medium'

        # Adjust stage parameters based on load
        if 'optimize' in state.pipeline_config:
            config = state.pipeline_config['optimize']
            if self.resource_status['cpu'] > 0.7:
                config['iterations'] = min(config['iterations'], 500)
            if self.resource_status['memory'] > 0.8:
                config['opt_for_quality'] = False

    async def _process_request(self, state: PipelineState) -> None:
        """Process a single request with optimized parameters"""
        try:
            pipeline = SVGPipelineController(state.prompt, state.style)
            await pipeline.initialize()
            await pipeline.execute()
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            state.set_error("Request processing failed", str(e))