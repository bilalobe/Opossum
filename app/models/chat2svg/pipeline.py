"""Core pipeline components for Chat2SVG generation."""
import datetime
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from .utils.enums import CircuitState
from .utils.helpers import sanitize_filename

logger = logging.getLogger(__name__)


class PipelineError(Exception):
    """Custom exception for pipeline stage failures."""
    pass


@dataclass
class PipelineState:
    """Holds the intermediate data passed between stages in memory."""
    prompt: str
    style: Optional[str]
    
    def __init__(self, prompt: str, style: Optional[str] = None):
        self.prompt = prompt
        self.style = style
        self.target_name = sanitize_filename(prompt)
        
        # Stage outputs
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
        
    def update_stage_duration(self, stage_name: str, duration: float) -> None:
        """Record the duration of a stage execution."""
        self.stage_durations[stage_name] = duration
        
    def set_error(self, message: str, detail: Optional[str] = None) -> None:
        """Set error with optional detailed information."""
        self.error = message
        if detail:
            self.error_detail = detail.strip()
            if len(self.error_detail) > 1000:
                self.error_detail = self.error_detail[:997] + "..."


# Pipeline configuration constants
STAGE_SPECS = {
    "template": {
        "cpu": 0.1, "memory": 0.1, "gpu": 0.0, "vram": 0.1,
        "impact": 0.6, "latency": 15.0
    },
    "detail": {
        "cpu": 0.4, "memory": 0.4, "gpu": 0.8, "vram": 0.7,
        "impact": 0.3, "latency": 60.0
    },
    "optimize": {
        "cpu": 0.3, "memory": 0.2, "gpu": 0.3, "vram": 0.4,
        "impact": 0.1, "latency": 30.0
    }
}

PIPELINE_CONFIGS = {
    "high": {
        "detail": {
            "num_inference_steps": 30,
            "strength": 1.0,
            "guidance_scale": 7.0,
            "sam_level": "fine"
        },
        "optimize": {
            "iterations": 1000,
            "quality_level": "high"
        }
    },
    "medium": {
        "detail": {
            "num_inference_steps": 25,
            "strength": 0.9,
            "guidance_scale": 6.5,
            "sam_level": "medium"
        },
        "optimize": {
            "iterations": 700,
            "quality_level": "medium"
        }
    },
    "low": {
        "detail": {
            "num_inference_steps": 20,
            "strength": 0.85,
            "guidance_scale": 6.0,
            "sam_level": "coarse"
        },
        "optimize": {
            "iterations": 500,
            "quality_level": "low"
        }
    },
    "minimal": {
        "detail": {},
        "optimize": {}
    }
}