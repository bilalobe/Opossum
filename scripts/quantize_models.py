#!/usr/bin/env python
"""
Model quantization script for Opossum Search.

This script quantizes both Transformers and Chat2SVG models to reduce memory usage
while maintaining acceptable performance. It's designed to be run during Docker build
or as part of the setup process.
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('model_quantization')

# Define quantization levels and their properties
QUANTIZATION_LEVELS = {
    "fp32": {"desc": "Full precision (32-bit)", "memory_reduction": 1.0, "quality_impact": "None"},
    "fp16": {"desc": "Half precision (16-bit)", "memory_reduction": 0.5, "quality_impact": "Very Low"},
    "int8": {"desc": "8-bit integer", "memory_reduction": 0.25, "quality_impact": "Low"},
    "int4": {"desc": "4-bit integer", "memory_reduction": 0.125, "quality_impact": "Medium"}
}

# Path configurations
DEFAULT_TRANSFORMERS_CACHE = os.path.join(os.path.expanduser("~"), ".cache", "huggingface")
DEFAULT_CHAT2SVG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vendor", "Chat2SVG")

# Model configurations
DEFAULT_MODELS = [
    {
        "name": "google/gemma-2b",
        "type": "transformers",
        "required": True
    },
    {
        "name": "microsoft/phi-2",
        "type": "transformers",
        "required": False
    },
    {
        "name": "cmd_10.pth",
        "type": "chat2svg",
        "path": os.path.join("3_svg_optimization", "vae_model"),
        "required": True
    }
]

def get_quantization_config() -> Dict[str, Any]:
    """Get quantization configuration from environment variables."""
    config = {
        "enabled": os.environ.get("CHAT2SVG_QUANTIZE_MODELS", "true").lower() == "true",
        "precision": os.environ.get("CHAT2SVG_QUANTIZATION_PRECISION", "int8"),
        "transformers_cache": os.environ.get("TRANSFORMERS_CACHE", DEFAULT_TRANSFORMERS_CACHE),
        "transformers_offline": os.environ.get("TRANSFORMERS_OFFLINE", "0") == "1",
        "chat2svg_path": os.environ.get("CHAT2SVG_PATH", DEFAULT_CHAT2SVG_PATH),
    }

    # Validate precision
    if config["precision"] not in QUANTIZATION_LEVELS:
        logger.warning(f"Invalid quantization precision: {config['precision']}. Using 'int8' instead.")
        config["precision"] = "int8"
    
    if not os.path.exists(config["transformers_cache"]):
        os.makedirs(config["transformers_cache"], exist_ok=True)
    
    logger.info(f"Quantization config: {json.dumps(config, indent=2)}")
    return config

def check_pytorch_gpu_availability() -> Dict[str, Any]:
    """Check PyTorch GPU availability and capabilities."""
    gpu_info = {
        "cuda_available": torch.cuda.is_available(),
        "device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
        "devices": []
    }
    
    if gpu_info["cuda_available"]:
        for i in range(gpu_info["device_count"]):
            gpu_info["devices"].append({
                "name": torch.cuda.get_device_name(i),
                "memory": torch.cuda.get_device_properties(i).total_memory,
                "capability": f"{torch.cuda.get_device_capability(i)[0]}.{torch.cuda.get_device_capability(i)[1]}"
            })
        
        logger.info(f"Found {gpu_info['device_count']} CUDA device(s)")
        for i, device in enumerate(gpu_info["devices"]):
            memory_gb = device["memory"] / (1024**3)
            logger.info(f"  Device {i}: {device['name']} ({memory_gb:.2f} GB, capability {device['capability']})")
    else:
        logger.warning("CUDA not available, using CPU for quantization")
    
    return gpu_info

def quantize_transformers_model(model_name: str, config: Dict[str, Any]) -> bool:
    """Quantize a Transformers model to the specified precision."""
    try:
        logger.info(f"Quantizing Transformers model: {model_name}")
        
        # Skip if offline mode is enabled and model doesn't exist
        if config["transformers_offline"]:
            model_dir = os.path.join(config["transformers_cache"], model_name)
            if not os.path.exists(model_dir):
                logger.warning(f"Model {model_name} not found locally and TRANSFORMERS_OFFLINE is enabled, skipping")
                return False
        
        # Import here to avoid loading the modules if not needed
        from transformers import AutoModelForCausalLM, AutoConfig
        
        start_time = time.time()
        
        # Set device configuration
        device_map = "auto"
        torch_dtype = None
        
        # Configure quantization parameters based on precision
        quantization_config = {}
        if config["precision"] == "fp16":
            torch_dtype = torch.float16
        elif config["precision"] == "int8":
            quantization_config["load_in_8bit"] = True
        elif config["precision"] == "int4":
            quantization_config["load_in_4bit"] = True
            quantization_config["bnb_4bit_compute_dtype"] = torch.float16
            quantization_config["bnb_4bit_quant_type"] = "nf4"
        
        # Load and save the model with quantization
        try:
            logger.info(f"Loading model {model_name} with {config['precision']} quantization...")
            
            # Create a custom saving directory
            save_directory = os.path.join(
                config["transformers_cache"],
                f"{model_name.split('/')[-1]}_{config['precision']}"
            )
            
            # Load the model with quantization
            if config["precision"] in ["int8", "int4"]:
                try:
                    model = AutoModelForCausalLM.from_pretrained(
                        model_name,
                        device_map=device_map,
                        **quantization_config
                    )
                except ImportError:
                    logger.warning("bitsandbytes not installed, falling back to fp16")
                    model = AutoModelForCausalLM.from_pretrained(
                        model_name,
                        device_map=device_map,
                        torch_dtype=torch.float16
                    )
            else:
                model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    device_map=device_map,
                    torch_dtype=torch_dtype
                )
            
            # Save quantized model metadata
            if not os.path.exists(save_directory):
                os.makedirs(save_directory, exist_ok=True)
            
            with open(os.path.join(save_directory, "quantization_info.json"), "w") as f:
                json.dump({
                    "original_model": model_name,
                    "precision": config["precision"],
                    "quantized_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "quantization_config": {k: str(v) for k, v in quantization_config.items()}
                }, f, indent=2)
            
            elapsed_time = time.time() - start_time
            logger.info(f"Successfully quantized model {model_name} to {config['precision']} in {elapsed_time:.2f}s")
            
            return True
        
        except Exception as e:
            logger.error(f"Error quantizing model {model_name}: {str(e)}")
            return False
        
    except ImportError:
        logger.warning("transformers package not available, skipping Transformers model quantization")
        return False

def quantize_chat2svg_model(model_path: str, config: Dict[str, Any]) -> bool:
    """Quantize a Chat2SVG model to the specified precision."""
    try:
        full_model_path = os.path.join(config["chat2svg_path"], model_path)
        if not os.path.exists(full_model_path):
            logger.warning(f"Chat2SVG model not found at {full_model_path}, skipping")
            return False
        
        logger.info(f"Quantizing Chat2SVG model: {model_path}")
        start_time = time.time()
        
        # Load the model
        try:
            state_dict = torch.load(full_model_path, map_location="cpu")
            
            # Create quantized version with different approaches based on precision
            if config["precision"] == "fp16":
                # Convert to fp16
                for key in state_dict:
                    if isinstance(state_dict[key], torch.Tensor):
                        state_dict[key] = state_dict[key].to(torch.float16)
            
            elif config["precision"] == "int8":
                # Perform dynamic quantization to int8
                from torch.quantization import quantize_dynamic
                
                # For state dictionaries, we need to quantize each tensor
                for key in state_dict:
                    if isinstance(state_dict[key], torch.Tensor):
                        # Skip non-floating point tensors
                        if not state_dict[key].is_floating_point():
                            continue
                            
                        # Skip small tensors where quantization doesn't make sense
                        if state_dict[key].numel() < 100:
                            continue
                            
                        # Quantize the tensor
                        state_dict[key] = torch.quantize_per_tensor(
                            state_dict[key],
                            scale=state_dict[key].abs().max() / 127.0,
                            zero_point=0,
                            dtype=torch.qint8
                        )
            
            # Save the quantized model
            quantized_path = full_model_path.replace(".pth", f"_{config['precision']}.pth")
            torch.save(state_dict, quantized_path)
            
            # Create a backup of the original model
            backup_path = full_model_path + ".backup"
            if not os.path.exists(backup_path):
                shutil.copy2(full_model_path, backup_path)
            
            # Replace the original model with the quantized version
            shutil.copy2(quantized_path, full_model_path)
            
            elapsed_time = time.time() - start_time
            logger.info(f"Successfully quantized Chat2SVG model {model_path} to {config['precision']} in {elapsed_time:.2f}s")
            
            return True
            
        except Exception as e:
            logger.error(f"Error quantizing Chat2SVG model {model_path}: {str(e)}")
            return False
    
    except Exception as e:
        logger.error(f"Error in Chat2SVG model quantization: {str(e)}")
        return False

def find_models() -> List[Dict[str, Any]]:
    """Find available models in the system."""
    models = []
    
    # Add default models
    for model in DEFAULT_MODELS:
        models.append(model.copy())
    
    # Look for additional transformers models
    try:
        from transformers import AutoTokenizer
        
        # Check for commonly used model directories
        for model_dir in glob.glob(os.path.join(DEFAULT_TRANSFORMERS_CACHE, "*")):
            if os.path.isdir(model_dir) and os.path.basename(model_dir) not in [m["name"] for m in models]:
                if os.path.exists(os.path.join(model_dir, "config.json")):
                    models.append({
                        "name": os.path.basename(model_dir),
                        "type": "transformers",
                        "required": False
                    })
    except ImportError:
        pass
        
    # Look for additional Chat2SVG models
    if os.path.exists(DEFAULT_CHAT2SVG_PATH):
        for model_file in glob.glob(os.path.join(DEFAULT_CHAT2SVG_PATH, "**", "*.pth"), recursive=True):
            rel_path = os.path.relpath(model_file, DEFAULT_CHAT2SVG_PATH)
            if not any(model["name"] == os.path.basename(model_file) for model in models):
                models.append({
                    "name": os.path.basename(model_file),
                    "type": "chat2svg",
                    "path": os.path.dirname(rel_path),
                    "required": False
                })
    
    return models

def main():
    """Main entry point for the model quantization script."""
    parser = argparse.ArgumentParser(description="Quantize models for Opossum Search")
    parser.add_argument("--precision", choices=["fp32", "fp16", "int8", "int4"], 
                       help="Quantization precision (overrides environment variable)")
    parser.add_argument("--disable", action="store_true", help="Disable quantization")
    parser.add_argument("--list-models", action="store_true", help="List available models and exit")
    parser.add_argument("--model", help="Quantize only the specified model")
    parser.add_argument("--skip-transformers", action="store_true", help="Skip transformers models")
    parser.add_argument("--skip-chat2svg", action="store_true", help="Skip Chat2SVG models")
    args = parser.parse_args()
    
    # Get configuration
    config = get_quantization_config()
    
    # Override config with command-line arguments
    if args.precision:
        config["precision"] = args.precision
    if args.disable:
        config["enabled"] = False
    
    # Check GPU availability
    gpu_info = check_pytorch_gpu_availability()
    
    # Find available models
    models = find_models()
    
    # List models and exit if requested
    if args.list_models:
        logger.info("Available models:")
        for model in models:
            logger.info(f"  - {model['name']} ({model['type']}, required: {model['required']})")
        return
    
    # Return early if quantization is disabled
    if not config["enabled"]:
        logger.info("Model quantization is disabled, exiting")
        return
    
    logger.info(f"Starting model quantization with precision: {config['precision']}")
    logger.info(f"Using {QUANTIZATION_LEVELS[config['precision']]['desc']} precision")
    logger.info(f"Expected memory reduction: {QUANTIZATION_LEVELS[config['precision']]['memory_reduction'] * 100:.1f}%")
    logger.info(f"Quality impact: {QUANTIZATION_LEVELS[config['precision']]['quality_impact']}")
    
    # Quantize models
    quantized_count = 0
    skipped_count = 0
    failed_count = 0
    
    for model in models:
        # Skip if not the specified model
        if args.model and args.model != model["name"]:
            continue
        
        # Skip transformers if requested
        if args.skip_transformers and model["type"] == "transformers":
            logger.info(f"Skipping transformers model: {model['name']}")
            skipped_count += 1
            continue
        
        # Skip chat2svg if requested
        if args.skip_chat2svg and model["type"] == "chat2svg":
            logger.info(f"Skipping Chat2SVG model: {model['name']}")
            skipped_count += 1
            continue
        
        # Quantize the model based on type
        success = False
        if model["type"] == "transformers":
            success = quantize_transformers_model(model["name"], config)
        elif model["type"] == "chat2svg":
            success = quantize_chat2svg_model(os.path.join(model["path"], model["name"]), config)
        
        # Update counts
        if success:
            quantized_count += 1
        else:
            if model["required"]:
                failed_count += 1
                logger.error(f"Failed to quantize required model: {model['name']}")
            else:
                skipped_count += 1
    
    # Report results
    logger.info(f"Quantization complete: {quantized_count} models quantized, {skipped_count} models skipped, {failed_count} models failed")
    
    # Exit with error if any required models failed
    if failed_count > 0:
        logger.error("One or more required models failed to quantize")
        sys.exit(1)

if __name__ == "__main__":
    main()