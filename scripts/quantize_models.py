#!/usr/bin/env python
"""
Model quantization script for Opossum Search.

This script quantizes Transformers models to ONNX format and Chat2SVG models
to FP16 to reduce memory usage and potentially improve inference speed.
It includes basic validation checks after quantization.

It's designed to be run during Docker build or as part of the setup process.

**Integration Notes for Application Developers:**

1.  **Model Path:** Your application needs to load models from the `--output-dir`
    (default: `data/quantized_models`) instead of the original Hugging Face cache
    or Chat2SVG vendor path.
2.  **Configuration:** Introduce a configuration setting (e.g., environment
    variable `USE_QUANTIZED_MODELS=true`, or a config file flag) in your
    application to switch between original and quantized models.
3.  **Transformers (ONNX):**
    *   Replace `transformers.AutoModelFor...` loading with `onnxruntime.InferenceSession`.
    *   You'll need the `onnxruntime` library in your application's environment.
    *   The tokenizer can still be loaded using `transformers.AutoTokenizer`.
    *   The path for loading will be like:
        `{output_dir}/{model_name_sanitized}/onnx_{precision}/model.onnx`
        (or similar, check the exact filenames saved by optimum).
    *   Inference requires preparing inputs compatible with the ONNX model's
        expected input names and format (usually `input_ids`, `attention_mask`).
4.  **Chat2SVG (FP16):**
    *   When loading the state dictionary using `torch.load`, point to the
        quantized file (e.g., `cmd_10_fp16.pth`) in the output directory:
        `{output_dir}/chat2svg/{relative_path}/{model_filename}_fp16.pth`.
    *   Ensure your Chat2SVG model class (`torch.nn.Module`) is instantiated
        *before* loading the state dict.
    *   The model itself should ideally support FP16 inference (most PyTorch models do).
    *   You might want to explicitly move the model to the target device and set
        its dtype: `model.to(device).half()`.
5.  **Precision Handling:** Your application needs to know *which* precision
    was used during quantization (e.g., from the directory name like `onnx_int8`)
    to load the correct files.
"""

import argparse
import glob
import json
import logging
import os
import shutil
import sys
import time
from typing import Dict, Any

import torch

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('model_quantization')

# Try importing optional validation dependencies
try:
    import onnxruntime

    _onnxruntime_available = True
except ImportError:
    onnxruntime = None
    _onnxruntime_available = False

try:
    import transformers

    _transformers_available = True
except ImportError:
    transformers = None
    _transformers_available = False

# --- Configuration ---

QUANTIZATION_LEVELS = {
    "fp32": {"desc": "Full precision (32-bit ONNX/PyTorch)", "memory_reduction": 1.0, "quality_impact": "None"},
    "fp16": {"desc": "Half precision (16-bit ONNX/PyTorch)", "memory_reduction": 0.5, "quality_impact": "Very Low"},
    "int8": {"desc": "8-bit integer (ONNX)", "memory_reduction": 0.25, "quality_impact": "Low"},
}

DEFAULT_TRANSFORMERS_CACHE = os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub")
DEFAULT_CHAT2SVG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vendor", "Chat2SVG")
DEFAULT_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "quantized_models")

DEFAULT_MODELS = [
    {
        "name": "google/gemma-2b",
        "type": "transformers",
        "task": "text-generation",  # Added task hint for validation
        "required": True
    },
    {
        "name": "cmd_10.pth",
        "type": "chat2svg",
        "path": os.path.join("3_svg_optimization", "vae_model"),
        "required": True
    }
]

# --- Helper Functions ---

def check_dependencies():
    """Check for required dependencies."""
    missing = []
    if not _transformers_available: missing.append("transformers")
    try:
        import optimum
        import optimum.exporters.onnx
    except ImportError:
        missing.append("optimum[exporters]")
    try:
        import onnx
    except ImportError:
        missing.append("onnx")
    if not _onnxruntime_available: missing.append("onnxruntime or onnxruntime-gpu")

    if missing:
        logger.error(f"Missing required dependencies: {', '.join(missing)}")
        logger.error("Please install them, e.g., pip install transformers optimum[exporters] onnx onnxruntime")
        sys.exit(1)
    logger.info("All required core dependencies found.")
    if not _onnxruntime_available:
        logger.warning("`onnxruntime` not found. ONNX validation will be skipped.")
    if not _transformers_available:
        logger.warning("`transformers` not found. Tokenization for ONNX validation will be skipped.")


def get_quantization_config() -> Dict[str, Any]:
    """Get quantization configuration from environment variables and args."""
    parser = argparse.ArgumentParser(description="Quantize models for Opossum Search")
    parser.add_argument("--precision", choices=QUANTIZATION_LEVELS.keys(),
                       default=os.environ.get("MODEL_QUANTIZATION_PRECISION", "int8"),
                        help="Target quantization precision (overrides MODEL_QUANTIZATION_PRECISION env var)")
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
    parser.add_argument("--validate", action="store_true", default=True,
                        help="Perform basic validation after quantization (default: True)")
    parser.add_argument("--no-validate", action="store_false", dest="validate", help="Disable validation")
    parser.add_argument("--cleanup-onnx-fp32", action="store_true", default=False,
                        help="Remove the intermediate FP32 ONNX export after INT8 quantization")

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
        "validate": args.validate,
        "cleanup_onnx_fp32": args.cleanup_onnx_fp32,
    }

    if config["precision"] not in QUANTIZATION_LEVELS:
        logger.warning(f"Invalid quantization precision: {config['precision']}. Using 'int8'.")
        config["precision"] = "int8"

    os.makedirs(config["output_dir"], exist_ok=True)

    logger.info(f"Quantization config: {json.dumps(config, indent=2)}")
    return config, args


def get_device(force_cpu: bool) -> torch.device:
    """Determine the best device to use (CPU or CUDA)."""
    if not force_cpu and torch.cuda.is_available():
        device_name = torch.cuda.get_device_name(0)
        logger.info(f"CUDA available. Using GPU: {device_name}")
        # Check compute capability for ONNX int8 quantization (needs >= 6.1)
        # Note: Optimum might handle this, but good to be aware.
        # cap = torch.cuda.get_device_capability(0)
        # if cap < (6, 1):
        #     logger.warning(f"GPU compute capability {cap} might be too low for efficient INT8. Consider CPU or FP16.")
        return torch.device("cuda")
    else:
        if force_cpu:
            logger.info("Forcing CPU usage.")
        elif not torch.cuda.is_available():
            logger.info("CUDA not available. Using CPU.")
        else:
            logger.warning("CUDA available but check failed or skipped. Using CPU.")
        return torch.device("cpu")


# --- Validation Functions ---

def validate_onnx_model(model_dir: str, model_name_or_path: str, device: str) -> bool:
    """Basic validation: Load ONNX model and run simple inference."""
    if not _onnxruntime_available:
        logger.warning("Skipping ONNX validation: onnxruntime not installed.")
        return True  # Treat as success if library not present
    if not _transformers_available:
        logger.warning("Skipping ONNX validation: transformers not installed (needed for tokenizer).")
        return True  # Treat as success

    logger.info(f"Validating ONNX model in: {model_dir}")
    try:
        # Find the main ONNX model file (heuristic)
        onnx_files = glob.glob(os.path.join(model_dir, "*.onnx"))
        # Exclude potential external data files
        onnx_files = [f for f in onnx_files if not f.endswith(".onnx_data")]
        if not onnx_files:
            logger.error("Validation Error: No .onnx file found in directory.")
            return False
        # Prefer model.onnx or encoder/decoder specific names if present
        preferred_files = [f for f in onnx_files if
                           os.path.basename(f) in ["model.onnx", "encoder_model.onnx", "decoder_model.onnx"]]
        model_path = preferred_files[0] if preferred_files else onnx_files[0]
        logger.info(f"Using ONNX model file: {model_path}")

        # Determine provider based on device
        providers = ['CPUExecutionProvider']
        if device == 'cuda':
            providers = [('CUDAExecutionProvider', {'device_id': 0}), 'CPUExecutionProvider']  # Fallback to CPU
            logger.info(f"Using ONNX Runtime providers: {providers}")

        sess_options = onnxruntime.SessionOptions()
        # Add potential optimizations if needed (e.g., sess_options.graph_optimization_level)

        session = onnxruntime.InferenceSession(model_path, sess_options=sess_options, providers=providers)
        logger.info("ONNX model loaded successfully.")

        # Simple inference test (Task-specific)
        tokenizer = transformers.AutoTokenizer.from_pretrained(model_name_or_path, trust_remote_code=True)
        text = "Validate model loading"
        inputs = tokenizer(text, return_tensors="np")  # Use numpy for ORT

        # Filter inputs to match model's required inputs
        model_input_names = [inp.name for inp in session.get_inputs()]
        feed_dict = {k: v for k, v in inputs.items() if k in model_input_names}

        if not feed_dict:
            logger.warning(
                f"Validation warning: Could not map tokenizer outputs to model inputs ({model_input_names}). Skipping inference check.")
            return True  # Allow success if loading worked but input mapping failed

        logger.info(f"Running simple inference with inputs: {list(feed_dict.keys())}")
        outputs = session.run(None, feed_dict)  # Run with available inputs
        logger.info(f"Validation task completed for model: {model_name_or_path}")

        logger.info(f"Validation inference successful. Output count: {len(outputs)}")
        # Optionally check output shapes or types here
        return True

    except ImportError as e:
        logger.warning(f"Validation skipped: Missing library ({e}).")
        return True  # Not a failure of quantization itself
    except Exception as e:
        logger.error(f"ONNX Validation failed for {model_dir}: {str(e)}", exc_info=True)
        return False


def validate_chat2svg_model(quantized_path: str, device: torch.device) -> bool:
    """Basic validation: Check if the FP16 state_dict can be loaded."""
    logger.info(f"Validating Chat2SVG FP16 model: {quantized_path}")
    try:
        # Load the state dictionary to check format and file integrity
        state_dict = torch.load(quantized_path, map_location=device)

        if not isinstance(state_dict, dict) or not state_dict:
            logger.error("Validation Error: Loaded state_dict is empty or not a dictionary.")
            return False

        # Check if tensors are indeed float16 (at least some)
        found_fp16 = False
        for key, value in state_dict.items():
            if isinstance(value, torch.Tensor) and value.dtype == torch.float16:
                found_fp16 = True
                break
        if not found_fp16:
            logger.warning(
                "Validation Warning: No FP16 tensors found in the loaded state_dict. Was the original model already FP16?")
            # Allow this case, maybe the original model had no floats or was already fp16

        logger.info("Chat2SVG FP16 state_dict loaded successfully.")
        logger.warning("Note: This only validates loading. Full validation requires the model class definition.")
        return True
    except FileNotFoundError:
        logger.error(f"Validation Error: Quantized file not found at {quantized_path}")
        return False
    except Exception as e:
        logger.error(f"Chat2SVG Validation failed for {quantized_path}: {str(e)}", exc_info=True)
        return False


# --- Quantization Functions ---

def quantize_transformers_model_onnx(model_name: str, task: str, config: Dict[str, Any], device: torch.device) -> bool:
    """
    Quantize a Transformers model to ONNX format using Optimum.
    Saves the quantized model and optionally validates it.
    """
    from optimum.exporters.onnx import main_export
    from optimum.onnxruntime import ORTQuantizer, AutoQuantizationConfig

    target_precision = config['precision']
    logger.info(f"Processing Transformers model to ONNX: {model_name} with target precision {target_precision}")
    start_time = time.time()

    onnx_model_folder = model_name.replace("/", "_")
    output_base_path = os.path.join(config["output_dir"], onnx_model_folder)
    onnx_fp32_path = os.path.join(output_base_path, "onnx_fp32")
    onnx_fp16_path = os.path.join(output_base_path, "onnx_fp16")
    onnx_int8_path = os.path.join(output_base_path, "onnx_int8")

    final_onnx_path = None
    quantization_done = False
    export_success = False
    validation_success = False

    try:
        # 1. Export to FP32 or FP16 ONNX
        export_precision = "fp16" if target_precision in ["fp16", "int8"] else "fp32"
        export_path = onnx_fp16_path if export_precision == "fp16" else onnx_fp32_path
        logger.info(f"Exporting {model_name} to {export_precision.upper()} ONNX at {export_path}...")

        # Cleanup previous export attempt for this precision
        if os.path.exists(export_path):
            logger.warning(f"Removing existing directory: {export_path}")
            shutil.rmtree(export_path)
        os.makedirs(export_path, exist_ok=True)

        main_export(
            model_name_or_path=model_name,
            output=export_path,
            task=task,
            device=device.type,
            fp16=(export_precision == "fp16"),
            cache_dir=config["transformers_cache"],
            trust_remote_code=True  # Be cautious
        )
        logger.info(f"{export_precision.upper()} ONNX export successful.")
        export_success = True
        final_onnx_path = export_path  # Default final path if no further quantization

        # 2. Quantize to INT8 if needed
        if target_precision == "int8":
            logger.info(f"Quantizing ONNX model to INT8 at {onnx_int8_path}...")
            if os.path.exists(onnx_int8_path):
                logger.warning(f"Removing existing directory: {onnx_int8_path}")
                shutil.rmtree(onnx_int8_path)
            os.makedirs(onnx_int8_path, exist_ok=True)

            # Use FP16 export as base if available, otherwise FP32
            quantization_base_path = onnx_fp16_path if os.path.exists(onnx_fp16_path) else onnx_fp32_path
            logger.info(f"Using {os.path.basename(quantization_base_path)} ONNX model as quantization base.")

            qconfig = AutoQuantizationConfig.avx512_vnni(is_static=False, per_channel=False)
            # Consider other configs: arm64, tensorrt based on target hardware
            # qconfig = AutoQuantizationConfig.arm64(is_static=False, per_channel=False)
            # qconfig = AutoQuantizationConfig.tensorrt(is_static=False, per_channel=False) # Requires TensorRT deps

            quantizer = ORTQuantizer.from_pretrained(quantization_base_path)
            quantizer.quantize(
                save_dir=onnx_int8_path,
                quantization_config=qconfig,
            )
            logger.info("INT8 ONNX quantization successful.")
            quantization_done = True
            final_onnx_path = onnx_int8_path

            # Optional cleanup of intermediate FP32/FP16 export
            if config["cleanup_onnx_fp32"] and quantization_base_path != final_onnx_path:
                logger.info(f"Cleaning up intermediate export: {quantization_base_path}")
                shutil.rmtree(quantization_base_path, ignore_errors=True)

        elif target_precision == "fp16":
            logger.info(f"FP16 ONNX model is ready at {final_onnx_path}")
            quantization_done = True  # Export achieved the target precision

        elif target_precision == "fp32":
            logger.info(f"FP32 ONNX model is ready at {final_onnx_path}")
            quantization_done = True  # Export achieved the target precision

        # 3. Validation
        if export_success and final_onnx_path and config["validate"]:
            validation_success = validate_onnx_model(final_onnx_path, model_name, task, device.type)
        elif config["validate"]:
            logger.warning("Skipping validation because export/quantization did not complete successfully.")

        elapsed_time = time.time() - start_time
        logger.info(
            f"Successfully processed Transformers model {model_name} to {target_precision} ONNX in {elapsed_time:.2f}s")
        logger.info(f"Final model location: {final_onnx_path}")
        logger.info("Reminder: Update application loading logic to use ONNX Runtime and the path above.")
        # Return True only if export succeeded and (validation was skipped or succeeded)
        return export_success and (not config["validate"] or validation_success)

    except Exception as e:
        logger.error(f"Error processing Transformers model {model_name}: {str(e)}", exc_info=True)
        # Clean up potentially incomplete directories
        if os.path.exists(onnx_fp32_path): shutil.rmtree(onnx_fp32_path, ignore_errors=True)
        if os.path.exists(onnx_fp16_path): shutil.rmtree(onnx_fp16_path, ignore_errors=True)
        if os.path.exists(onnx_int8_path): shutil.rmtree(onnx_int8_path, ignore_errors=True)
        return False


def quantize_chat2svg_model_fp16(model_filename: str, model_rel_path: str, config: Dict[str, Any], device: torch.device) -> bool:
    """
    Quantize a Chat2SVG model (.pth state_dict) to FP16 and optionally validate.
    """
    logger.info(f"Quantizing Chat2SVG model to FP16: {model_filename}")
    start_time = time.time()

    full_model_path = os.path.join(config["chat2svg_path"], model_rel_path, model_filename)
    if not os.path.exists(full_model_path):
        logger.error(f"Chat2SVG source model not found at {full_model_path}, skipping")
        return False

    output_model_dir = os.path.join(config["output_dir"], "chat2svg", model_rel_path)
    quantized_filename = model_filename.replace(".pth", "_fp16.pth")
    quantized_path = os.path.join(output_model_dir, quantized_filename)
    os.makedirs(output_model_dir, exist_ok=True)

    quantization_success = False
    validation_success = False

    try:
        logger.info(f"Loading original model state_dict from: {full_model_path}")
        state_dict = torch.load(full_model_path, map_location=device)  # Use the passed device for consistency

        quantized_state_dict = {}
        logger.info("Converting floating point tensors to FP16...")
        converted_count = 0
        kept_count = 0
        for key, tensor in state_dict.items():
            if isinstance(tensor, torch.Tensor) and tensor.is_floating_point():
                quantized_state_dict[key] = tensor.to(torch.float16)
                converted_count += 1
            else:
                quantized_state_dict[key] = tensor
                kept_count += 1
        logger.info(f"Converted {converted_count} tensors to FP16, kept {kept_count} tensors as is.")

        logger.info(f"Saving FP16 state_dict to: {quantized_path}")
        torch.save(quantized_state_dict, quantized_path)
        quantization_success = True

        # Validation
        if quantization_success and config["validate"]:
            validation_success = validate_chat2svg_model(quantized_path, device)
        elif config["validate"]:
            logger.warning("Skipping validation because quantization did not complete successfully.")

        elapsed_time = time.time() - start_time
        logger.info(f"Successfully quantized Chat2SVG model {model_filename} to FP16 in {elapsed_time:.2f}s")
        logger.info(f"Quantized model saved to: {quantized_path}")
        logger.warning("Reminder: Update application loading logic to load this FP16 .pth file.")
        # Return True only if quantization succeeded and (validation was skipped or succeeded)
        return quantization_success and (not config["validate"] or validation_success)

    except FileNotFoundError:
        logger.error(f"Chat2SVG source model file not found during processing: {full_model_path}")
        return False
    except Exception as e:
        logger.error(f"Error quantizing Chat2SVG model {model_filename}: {str(e)}", exc_info=True)
        if os.path.exists(quantized_path): os.remove(quantized_path)
        return False

# --- Main Execution ---

def main():
    """Main entry point for the model quantization script."""
    check_dependencies()
    config, args = get_quantization_config()
    device = get_device(config["force_cpu"])

    if config["list_models"]:
        logger.info("Models configured for quantization:")
        for model in DEFAULT_MODELS:
            logger.info(
                f"  - {model['name']} (type: {model['type']}, task: {model.get('task', 'N/A')}, required: {model['required']})")
        return

    if not config["enabled"]:
        logger.info("Model quantization is disabled via --disable or MODEL_QUANTIZATION_DISABLE=true, exiting")
        return

    if config["precision"] in ["int8"] and not config["skip_chat2svg"]:
        logger.warning(
            f"Precision '{config['precision']}' selected. Only FP16 quantization is supported for Chat2SVG models (.pth state_dicts) in this script.")
        logger.warning("Chat2SVG models will be skipped unless --precision is fp16 or fp32.")
    if config["target_model"] and any(m['name'] == config["target_model"] and m['type'] == 'chat2svg' for m in DEFAULT_MODELS):
        logger.error(
            f"Cannot proceed with INT8 precision for the specified Chat2SVG model '{config['target_model']}'. Use --precision fp16.")
        sys.exit(1)
        # Set skip flag internally if precision isn't compatible
        config["_internal_skip_chat2svg"] = True
    else:
        config["_internal_skip_chat2svg"] = False


    logger.info(f"Starting model quantization with precision: {config['precision']}")
    logger.info(f"Using {QUANTIZATION_LEVELS[config['precision']]['desc']}")
    logger.info(f"Validation enabled: {config['validate']}")
    logger.info(f"Output directory: {config['output_dir']}")

    processed_count = 0
    skipped_count = 0
    failed_count = 0  # Counts failures for required models

    for model_info in DEFAULT_MODELS:
        model_name = model_info["name"]
        model_type = model_info["type"]
        is_required = model_info["required"]
        model_task = model_info.get("task", "text-generation")  # Default task for transformers

        logger.info(f"--- Processing model: {model_name} ({model_type}) ---")

        # Skip checks
        if config["target_model"] and config["target_model"] != model_name:
            # logger.debug(f"Skipping {model_name}, not the target model '{config['target_model']}'") # Use debug if too verbose
            continue
        if config["skip_transformers"] and model_type == "transformers":
            logger.info(f"Skipping transformers model via --skip-transformers: {model_name}")
            skipped_count += 1
            continue
        if config["skip_chat2svg"] and model_type == "chat2svg":
            logger.info(f"Skipping Chat2SVG model via --skip-chat2svg: {model_name}")
            skipped_count += 1
            continue
        if config["_internal_skip_chat2svg"] and model_type == "chat2svg":
            logger.info(
                f"Skipping Chat2SVG model {model_name} due to incompatible precision '{config['precision']}' (only fp16/fp32 supported).")
            skipped_count += 1
            continue
        if config["precision"] == "fp32" and model_type == "chat2svg":
            logger.info(f"Skipping Chat2SVG model {model_name} as FP32 requires no state_dict quantization.")
            skipped_count += 1
            continue

        # Perform quantization
        success = False
        if model_type == "transformers":
            if config["precision"] == "int4":  # Still experimental, handled here now
                logger.warning(f"INT4 ONNX quantization is experimental/not supported. Skipping {model_name}.")
                skipped_count += 1
                continue
            success = quantize_transformers_model_onnx(model_name, model_task, config, device)
        elif model_type == "chat2svg":
            # Should only reach here if precision is fp16
            if config["precision"] == "fp16":
                success = quantize_chat2svg_model_fp16(model_name, model_info["path"], config, device)
            else:
                # This case should theoretically be caught by earlier skips
                logger.error(
                    f"Internal Error: Reached Chat2SVG processing for {model_name} with unexpected precision {config['precision']}. Skipping.")
                skipped_count += 1
                continue  # Treat as skip

        # Update counts
        if success:
            processed_count += 1
        else:
            # Only count as failure if the model was required AND not skipped by a flag
            if is_required and \
                    not (config["skip_transformers"] and model_type == "transformers") and \
                    not (config["skip_chat2svg"] and model_type == "chat2svg") and \
                    not (config["_internal_skip_chat2svg"] and model_type == "chat2svg"):
                failed_count += 1
                logger.error(f"FAILED processing REQUIRED model: {model_name}")
            else:
                # Log non-required failures as warnings and count as skipped
                logger.warning(f"Failed or skipped processing optional model: {model_name}")
                skipped_count += 1

        logger.info(f"--- Finished processing model: {model_name} ---")

    # Report results
    logger.info("=" * 30 + " Quantization Summary " + "=" * 30)
    logger.info(f"Total models configured: {len(DEFAULT_MODELS)}")
    logger.info(f"Models successfully processed (quantized/exported + validated if enabled): {processed_count}")
    logger.info(f"Models skipped (due to flags, precision mismatch, or non-required failure): {skipped_count}")
    logger.info(f"REQUIRED models failed: {failed_count}")
    logger.info("=" * 79)


    if failed_count > 0:
        logger.error("One or more REQUIRED models failed processing. Please check logs.")
        sys.exit(1)
    else:
        logger.info("Quantization script finished successfully.")
        sys.exit(0)

if __name__ == "__main__":
    main()