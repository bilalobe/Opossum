"""Core SVG generation functionality."""
import asyncio
import logging
from typing import Dict, Any, Optional, List

from .pipeline import PipelineState
from .monitoring.resources import ResourceMonitor
from .optimizer.hybrid import HybridOptimizer
from .utils.helpers import encode_svg_to_png_base64

logger = logging.getLogger(__name__)


class Chat2SVGGenerator:
    """Main generator class for SVG creation."""
    
    def __init__(self):
        self.resource_monitor = ResourceMonitor()
        self.optimizer = HybridOptimizer()
        self.pending_requests: List[PipelineState] = []
        self.processing = False
        self._batch_lock = asyncio.Lock()
        
    async def generate(self, prompt: str, style: Optional[str] = None) -> Dict[str, Any]:
        """Generate SVG from text prompt."""
        state = PipelineState(prompt, style)
        
        try:
            # Add to pending batch
            async with self._batch_lock:
                self.pending_requests.append(state)
                
            # Trigger batch processing if not already running
            if not self.processing:
                asyncio.create_task(self._process_batch())
                
            # Wait for completion
            while not state.error and not any([
                state.template_svg,
                state.enhanced_svg,
                state.optimized_svg
            ]):
                await asyncio.sleep(0.1)
                
            if state.error:
                return {
                    "error": state.error,
                    "detail": state.error_detail
                }
                
            # Convert final SVG to PNG if requested
            final_svg = (
                state.optimized_svg or 
                state.enhanced_svg or 
                state.template_svg
            )
            png_base64 = encode_svg_to_png_base64(final_svg)
            
            return {
                "svg": final_svg,
                "png_base64": png_base64,
                "stages_run": state.stages_run,
                "durations": state.stage_durations
            }
            
        except Exception as e:
            logger.error(f"Error generating SVG: {e}")
            return {
                "error": "Generation failed",
                "detail": str(e)
            }
            
    async def _process_batch(self) -> None:
        """Process pending requests in batches."""
        if self.processing:
            return
            
        self.processing = True
        try:
            while self.pending_requests:
                async with self._batch_lock:
                    batch = self.pending_requests[:50]
                    self.pending_requests = self.pending_requests[50:]
                    
                # Get current resource availability
                resources = await self.resource_monitor.get_resources()
                
                # Optimize batch processing
                solution = await self.optimizer.solve(batch, resources)
                
                # Process each request according to optimization
                for request, stages in solution:
                    try:
                        await self._process_request(request, stages)
                    except Exception as e:
                        logger.error(f"Error processing request: {e}")
                        request.set_error("Processing failed", str(e))
                        
        finally:
            self.processing = False
            
    async def _process_request(self, state: PipelineState, stages: List[str]) -> None:
        """Process individual request through selected stages."""
        state.stages_to_run = stages
        
        try:
            if "template" in stages:
                await self._run_template_stage(state)
                
            if "detail" in stages and not state.error:
                await self._run_detail_stage(state)
                
            if "optimize" in stages and not state.error:
                await self._run_optimize_stage(state)
                
        except Exception as e:
            logger.error(f"Stage processing error: {e}")
            state.set_error("Stage processing failed", str(e))
            
    async def _run_template_stage(self, state: PipelineState) -> None:
        """Generate initial SVG template."""
        # Template generation implementation
        pass
        
    async def _run_detail_stage(self, state: PipelineState) -> None:
        """Enhance SVG with details."""
        # Detail enhancement implementation
        pass
        
    async def _run_optimize_stage(self, state: PipelineState) -> None:
        """Optimize final SVG."""
        # SVG optimization implementation
        pass