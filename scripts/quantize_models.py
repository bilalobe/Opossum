#!/usr/bin/env python
"""
Model quantization script for Opossum Search.

This script quantizes Transformers models to ONNX format and Chat2SVG models
to FP16 to reduce memory usage and potentially improve inference speed.
It's designed to be run during Docker build or as part of the setup process.
"""

import os
import sys
import glob
import json
import logging
import argparse
from typing import Dict, Any, List, Optional
import torch
import time
import shutil
import subprocess

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('model_quantization')

# --- Configuration ---

# Define quantization levels and their properties
# Note: 'int8' and 'int4' for Transformers now refer to ONNX export quantization
QUANTIZATION_LEVELS = {
    "fp32": {"desc": "Full precision (32-bit)", "memory_reduction": 1.0, "quality_impact": "None"},
    "fp16": {"desc": "Half precision (16-bit)", "memory_reduction": 0.5, "quality_impact": "Very Low"},
    "int8": {"desc": "8-bit integer (ONNX)", "memory_reduction": 0.25, "quality_impact": "Low"},
    # "int4": {"desc": "4-bit integer (ONNX - Experimental)", "memory_reduction": 0.125, "quality_impact": "Medium"} # ONNX 4-bit support is less mature
}

# Path configurations
DEFAULT_TRANSFORMERS_CACHE = os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub")
DEFAULT_CHAT2SVG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vendor", "Chat2SVG")
DEFAULT_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "quantized_models")

# Model configurations (Simplified discovery)
DEFAULT_MODELS = [
    {
        "name": "google/gemma-2b",
        "type": "transformers",
        "required": True
    },
    # Add other known required/default transformers models here
    # {
    #     "name": "microsoft/phi-2",
    #     "type": "transformers",
    #     "required": False
    # },
    {
        "name": "cmd_10.pth", # Example Chat2SVG model
        "type": "chat2svg",
        "path": os.path.join("3_svg_optimization", "vae_model"), # Relative to CHAT2SVG_PATH
        "required": True
    }
    # Add other known required/default Chat2SVG models here
]

# --- Helper Functions ---

def check_dependencies():
    """Check for required dependencies."""
    missing = []
    try:
        import transformers
    except ImportError:
        missing.append("transformers")
    try:
        import optimum
        import optimum.exporters.onnx
    except ImportError:
        missing.append("optimum[exporters]")
    try:
        import onnx
    except ImportError:
        missing.append("onnx")
    try:
        import onnxruntime
    except ImportError:
        missing.append("onnxruntime or onnxruntime-gpu")

    if missing:
        logger.error(f"Missing required dependencies: {', '.join(missing)}")
        logger.error("Please install them, e.g., pip install transformers optimum[exporters] onnx onnxruntime")
        sys.exit(1)
    logger.info("All required dependencies found.")


def get_quantization_config() -> Dict[str, Any]:
    """Get quantization configuration from environment variables and args."""
    parser = argparse.ArgumentParser(description="Quantize models for Opossum Search")
    parser.add_argument("--precision", choices=QUANTIZATION_LEVELS.keys(),
                       default=os.environ.get("MODEL_QUANTIZATION_PRECISION", "int8"),
                       help="Quantization precision (overrides MODEL_QUANTIZATION_PRECISION env var)")
    parser.add_argument("--disable", action="store_true",
                       default=os.environ.get("MODEL_QUANTIZATION_DISABLE", "false").lower() == "true",
                       help="Disable quantization (overrides MODEL_QUANTIZATION_DISABLE env var)")
    parser.add_argument("--list-models", action="store_true", help="List models to be quantized and exit")
    parser.add_argument("--model", help="Quantize only the specified model name (e.g., 'google/gemma-2b' or 'cmd_10.pth')")
    parser.add_argument("--skip-transformers", action="store_true", help="Skip transformers models")
    parser.add_argument("--skip-chat2svg", action="store_true", help="Skip Chat2SVG models")
    parser.add_argument("--transformers-cache",
                        default=os.environ.get("TRANSFORMERS_CACHE", DEFAULT_TRANSFORMERS_CACHE),
                        help="Path to Hugging Face cache directory")
    parser.add_argument("--chat2svg-path",
                        default=os.environ.get("CHAT2SVG_PATH", DEFAULT_CHAT2SVG_PATH),
                        help="Path to Chat2SVG installation/vendor directory")
    parser.add_argument("--output-dir",
                        default=os.environ.get("QUANTIZED_MODEL_OUTPUT_DIR", DEFAULT_OUTPUT_DIR),
                        help="Directory to save quantized models")
    parser.add_argument("--force-cpu", action="store_true", help="Force using CPU even if GPU is available")

    args = parser.parse_args()

    config = {
        "enabled": not args.disable,
        "precision": args.precision,
        "transformers_cache": args.transformers_cache,
        "chat2svg_path": args.chat2svg_path,
        "output_dir": args.output_dir,
        "list_models": args.list_models,
        "target_model": args.model,
        "skip_transformers": args.skip_transformers,
        "skip_chat2svg": args.skip_chat2svg,
        "force_cpu": args.force_cpu,
    }

    # Validate precision
    if config["precision"] not in QUANTIZATION_LEVELS:
        logger.warning(f"Invalid quantization precision: {config['precision']}. Using 'int8'.")
        config["precision"] = "int8"

    # Ensure output directory exists
    os.makedirs(config["output_dir"], exist_ok=True)

    logger.info(f"Quantization config: {json.dumps(config, indent=2)}")
    return config, args


def get_device(force_cpu: bool) -> torch.device:
    """Determine the best device to use (CPU or CUDA)."""
    if not force_cpu and torch.cuda.is_available():
        logger.info(f"CUDA available. Using GPU: {torch.cuda.get_device_name(0)}")
        return torch.device("cuda")
    else:
        if force_cpu:
            logger.info("Forcing CPU usage.")
        else:
            logger.warning("CUDA not available or check failed. Using CPU.")
        return torch.device("cpu")

# --- Quantization Functions ---

def quantize_transformers_model_onnx(model_name: str, config: Dict[str, Any], device: torch.device) -> bool:
    """
    Quantize a Transformers model to ONNX format using Optimum.
    Saves the quantized model to a subdirectory within config['output_dir'].
    """
    from optimum.exporters.onnx import main_export
    from optimum.onnxruntime import ORTQuantizer, AutoQuantizationConfig

    logger.info(f"Quantizing Transformers model to ONNX: {model_name} with precision {config['precision']}")
    start_time = time.time()

    # Define output path for the ONNX model
    onnx_model_folder = model_name.replace("/", "_") # Sanitize name
    output_base_path = os.path.join(config["output_dir"], onnx_model_folder)
    onnx_export_path = os.path.join(output_base_path, "onnx_fp32") # Export FP32 first
    quantized_onnx_path = os.path.join(output_base_path, f"onnx_{config['precision']}")

    os.makedirs(onnx_export_path, exist_ok=True)
    os.makedirs(quantized_onnx_path, exist_ok=True)

    try:
        # 1. Export to FP32 ONNX first
        logger.info(f"Exporting {model_name} to FP32 ONNX at {onnx_export_path}...")
        main_export(
            model_name_or_path=model_name,
            output=onnx_export_path,
            task="text-generation", # Adjust task if needed
            device=device.type,
            fp16=True if config['precision'] == 'fp16' else False, # Use fp16 export if target is fp16
            cache_dir=config["transformers_cache"],
            trust_remote_code=True # Be cautious with this flag
        )
        logger.info("FP32 ONNX export successful.")

        # 2. Quantize if target is int8 (or potentially int4 in future)
        if config["precision"] == "int8":
            logger.info(f"Quantizing ONNX model to INT8 at {quantized_onnx_path}...")

            # Define quantization strategy (e.g., AVX512 for CPU)
            # Adjust optimization level and strategy as needed
            qconfig = AutoQuantizationConfig.avx512_vnni(is_static=False, per_channel=False)
            # For GPU quantization, explore options like AutoQuantizationConfig.tensorrt()

            quantizer = ORTQuantizer.from_pretrained(onnx_export_path)

            quantizer.quantize(
                save_dir=quantized_onnx_path,
                quantization_config=qconfig,
            )
            logger.info("INT8 ONNX quantization successful.")

        elif config["precision"] == "fp16":
            # If target was fp16, the initial export already handled it.
            # We can just move/rename the fp16 exported model if needed,
            # or simply note that the fp16 version is in the onnx_export_path.
            # For simplicity, let's just log it.
            logger.info(f"FP16 ONNX model available at {onnx_export_path}")
            # Optionally copy to the final quantized path for consistency:
            # shutil.copytree(onnx_export_path, quantized_onnx_path, dirs_exist_ok=True)

        elif config["precision"] == "fp32":
             logger.info(f"FP32 ONNX model available at {onnx_export_path}")
             # Optionally copy:
             # shutil.copytree(onnx_export_path, quantized_onnx_path, dirs_exist_ok=True)


        elapsed_time = time.time() - start_time
        logger.info(f"Successfully processed Transformers model {model_name} to {config['precision']} ONNX in {elapsed_time:.2f}s")
        logger.info(f"Quantized model saved in: {quantized_onnx_path if config['precision'] != 'fp16' else onnx_export_path}")
        logger.warning("NOTE: Application loading logic needs to be updated to load ONNX models from the output directory.")
        return True

    except Exception as e:
        logger.error(f"Error processing Transformers model {model_name}: {str(e)}", exc_info=True)
        # Clean up potentially incomplete directories
        if os.path.exists(onnx_export_path): shutil.rmtree(onnx_export_path, ignore_errors=True)
        if os.path.exists(quantized_onnx_path): shutil.rmtree(quantized_onnx_path, ignore_errors=True)
        return False


def quantize_chat2svg_model_fp16(model_filename: str, model_rel_path: str, config: Dict[str, Any], device: torch.device) -> bool:
    """
    Quantize a Chat2SVG model (.pth state_dict) to FP16.
    Saves the quantized model to a subdirectory within config['output_dir'].
    """
    logger.info(f"Quantizing Chat2SVG model to FP16: {model_filename}")
    start_time = time.time()

    full_model_path = os.path.join(config["chat2svg_path"], model_rel_path, model_filename)
    if not os.path.exists(full_model_path):
        logger.warning(f"Chat2SVG model not found at {full_model_path}, skipping")
        return False

    # Define output path
    output_model_dir = os.path.join(config["output_dir"], "chat2svg", model_rel_path)
    quantized_filename = model_filename.replace(".pth", "_fp16.pth")
    quantized_path = os.path.join(output_model_dir, quantized_filename)
    os.makedirs(output_model_dir, exist_ok=True)

    try:
        # Load the state dictionary
        state_dict = torch.load(full_model_path, map_location=device) # Load to target device

        # Convert tensors to fp16
        quantized_state_dict = {}
        for key, tensor in state_dict.items():
            if isinstance(tensor, torch.Tensor) and tensor.is_floating_point():
                quantized_state_dict[key] = tensor.to(torch.float16)
            else:
                quantized_state_dict[key] = tensor # Keep non-float tensors as is

        # Save the quantized state dictionary
        torch.save(quantized_state_dict, quantized_path)

        elapsed_time = time.time() - start_time
        logger.info(f"Successfully quantized Chat2SVG model {model_filename} to FP16 in {elapsed_time:.2f}s")
        logger.info(f"Quantized model saved to: {quantized_path}")
        logger.warning("NOTE: Application loading logic needs to be updated to load FP16 models from the output directory.")
        return True

    except FileNotFoundError:
        logger.error(f"Chat2SVG model file not found: {full_model_path}")
        return False
    except Exception as e:
        logger.error(f"Error quantizing Chat2SVG model {model_filename}: {str(e)}", exc_info=True)
        if os.path.exists(quantized_path): os.remove(quantized_path) # Clean up partial file
        return False

# --- Main Execution ---

def main():
    """Main entry point for the model quantization script."""
    check_dependencies()
    config, args = get_quantization_config()
    device = get_device(config["force_cpu"])

    # List models and exit if requested
    if config["list_models"]:
        logger.info("Models configured for quantization:")
        for model in DEFAULT_MODELS:
            logger.info(f"  - {model['name']} ({model['type']}, required: {model['required']})")
        return

    # Return early if quantization is disabled
    if not config["enabled"]:
        logger.info("Model quantization is disabled, exiting")
        return

    # --- Sanity Check for INT8/INT4 Chat2SVG ---
    if config["precision"] in ["int8", "int4"] and not config["skip_chat2svg"]:
         logger.warning(f"Precision '{config['precision']}' selected, but direct INT8/INT4 quantization for arbitrary Chat2SVG .pth files is complex and not reliably implemented here.")
         logger.warning("Only FP16 quantization is supported for Chat2SVG models in this script.")
         logger.warning("If you intended to quantize Chat2SVG, please use --precision fp16 or fp32.")
         if config["target_model"] and any(m['name'] == config["target_model"] and m['type'] == 'chat2svg' for m in DEFAULT_MODELS):
             logger.error("Cannot proceed with INT8/INT4 for the specified Chat2SVG model.")
             sys.exit(1)
         # Continue, but skip Chat2SVG if INT8/INT4 was chosen generally
         config["skip_chat2svg"] = True


    logger.info(f"Starting model quantization with precision: {config['precision']}")
    logger.info(f"Using {QUANTIZATION_LEVELS[config['precision']]['desc']} precision")
    logger.info(f"Output directory: {config['output_dir']}")

    quantized_count = 0
    skipped_count = 0
    failed_count = 0

    for model_info in DEFAULT_MODELS:
        model_name = model_info["name"]
        model_type = model_info["type"]
        is_required = model_info["required"]

        # Skip if not the specified model
        if config["target_model"] and config["target_model"] != model_name:
            continue

        # Skip based on type flags
        if config["skip_transformers"] and model_type == "transformers":
            logger.info(f"Skipping transformers model via flag: {model_name}")
            skipped_count += 1
            continue
        if config["skip_chat2svg"] and model_type == "chat2svg":
            logger.info(f"Skipping Chat2SVG model via flag: {model_name}")
            skipped_count += 1
            continue

        # Quantize the model based on type
        success = False
        if model_type == "transformers":
            # Transformers only support ONNX export here (fp32, fp16, int8)
            if config["precision"] == "int4":
                 logger.warning(f"INT4 ONNX quantization is experimental/not fully supported here. Skipping {model_name}.")
                 skipped_count += 1
                 continue
            success = quantize_transformers_model_onnx(model_name, config, device)
        elif model_type == "chat2svg":
            # Chat2SVG only supports fp16 here
            if config["precision"] == "fp16":
                success = quantize_chat2svg_model_fp16(model_name, model_info["path"], config, device)
            elif config["precision"] == "fp32":
                 logger.info(f"Skipping Chat2SVG model {model_name} as FP32 requires no quantization.")
                 skipped_count += 1
                 continue # Not a failure, just no action needed
            else:
                 # Should have been caught earlier, but double-check
                 logger.warning(f"Skipping Chat2SVG model {model_name} due to unsupported precision '{config['precision']}'. Use 'fp16'.")
                 skipped_count += 1
                 continue


        # Update counts
        if success:
            quantized_count += 1
        else:
            # Don't count skips as failures unless required
            if not (config["skip_transformers"] and model_type == "transformers") and \
               not (config["skip_chat2svg"] and model_type == "chat2svg"):
                if is_required:
                    failed_count += 1
                    logger.error(f"Failed to quantize REQUIRED model: {model_name}")
                else:
                    # Log as warning if optional model failed
                    logger.warning(f"Failed to quantize optional model: {model_name}")
                    skipped_count += 1 # Treat non-required failures as skips for exit code

    # Report results
    logger.info(f"Quantization complete: {quantized_count} models processed, {skipped_count} models skipped, {failed_count} required models failed")

    # Exit with error if any required models failed
    if failed_count > 0:
        logger.error("One or more REQUIRED models failed to quantize.")
        sys.exit(1)
    else:
        logger.info("Quantization script finished successfully.")
        sys.exit(0)

if __name__ == "__main__":
    main()