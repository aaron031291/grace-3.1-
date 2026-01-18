"""
Download Open-Source LLM Weights for Knowledge Distillation

NOTE: GPT, Claude, and Gemini weights are NOT available (closed source).
Only open-source models can be downloaded.

Recommended models for Grace distillation:
1. Phi-3-mini (3.8B) - Smallest, fastest, MIT license
2. Mistral-7B - Good quality, Apache 2.0
3. Llama-3-8B - Best quality, needs Meta approval
4. DeepSeek-Coder - Best for code
5. Qwen2 - Good multilingual
"""

import os
import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

AVAILABLE_MODELS = {
    # Smallest - Good for testing
    "phi3-mini": {
        "name": "microsoft/Phi-3-mini-4k-instruct",
        "size": "3.8B",
        "license": "MIT",
        "disk_space": "~8GB",
        "gpu_memory": "~4GB (4-bit)",
        "best_for": "Fast distillation, general purpose"
    },
    
    # Medium - Good balance
    "mistral-7b": {
        "name": "mistralai/Mistral-7B-Instruct-v0.3",
        "size": "7B", 
        "license": "Apache 2.0",
        "disk_space": "~15GB",
        "gpu_memory": "~6GB (4-bit)",
        "best_for": "General purpose, reasoning"
    },
    
    # Code-focused
    "deepseek-coder": {
        "name": "deepseek-ai/deepseek-coder-6.7b-instruct",
        "size": "6.7B",
        "license": "Permissive",
        "disk_space": "~14GB",
        "gpu_memory": "~6GB (4-bit)",
        "best_for": "Code generation, HumanEval"
    },
    
    # Strong reasoning
    "llama3-8b": {
        "name": "meta-llama/Meta-Llama-3-8B-Instruct",
        "size": "8B",
        "license": "Meta Llama 3",
        "disk_space": "~16GB",
        "gpu_memory": "~7GB (4-bit)",
        "best_for": "Best reasoning, needs Meta approval",
        "note": "Requires accepting Meta's license at huggingface.co"
    },
    
    # Multilingual
    "qwen2-7b": {
        "name": "Qwen/Qwen2-7B-Instruct",
        "size": "7B",
        "license": "Apache 2.0",
        "disk_space": "~15GB",
        "gpu_memory": "~6GB (4-bit)",
        "best_for": "Multilingual, general purpose"
    },
    
    # Google's open model
    "gemma2-9b": {
        "name": "google/gemma-2-9b-it",
        "size": "9B",
        "license": "Gemma License",
        "disk_space": "~18GB",
        "gpu_memory": "~8GB (4-bit)",
        "best_for": "Strong reasoning",
        "note": "Requires accepting Google's license"
    },
    
    # Code-focused from Meta
    "codellama-7b": {
        "name": "codellama/CodeLlama-7b-Instruct-hf",
        "size": "7B",
        "license": "Llama 2",
        "disk_space": "~15GB",
        "gpu_memory": "~6GB (4-bit)",
        "best_for": "Code generation"
    },
    
    # Smaller Phi for very limited resources
    "phi2": {
        "name": "microsoft/phi-2",
        "size": "2.7B",
        "license": "MIT",
        "disk_space": "~6GB",
        "gpu_memory": "~3GB (4-bit)",
        "best_for": "Very fast, limited resources"
    },
}

# Models that are NOT available (closed source)
UNAVAILABLE_MODELS = {
    "gpt-4": "OpenAI - Closed source, API only at api.openai.com",
    "gpt-3.5": "OpenAI - Closed source, API only at api.openai.com", 
    "claude-3": "Anthropic - Closed source, API only at api.anthropic.com",
    "claude-2": "Anthropic - Closed source, API only at api.anthropic.com",
    "gemini-pro": "Google - Closed source, API only at ai.google.dev",
    "gemini-ultra": "Google - Closed source, API only at ai.google.dev",
}


def list_models():
    """List all available models."""
    print("\n" + "=" * 80)
    print("AVAILABLE OPEN-SOURCE MODELS (Weights Downloadable)")
    print("=" * 80)
    
    for key, info in AVAILABLE_MODELS.items():
        print(f"\n📦 {key}")
        print(f"   Model: {info['name']}")
        print(f"   Size: {info['size']} | License: {info['license']}")
        print(f"   Disk: {info['disk_space']} | GPU: {info['gpu_memory']}")
        print(f"   Best for: {info['best_for']}")
        if 'note' in info:
            print(f"   ⚠️  Note: {info['note']}")
    
    print("\n" + "=" * 80)
    print("CLOSED-SOURCE MODELS (Weights NOT Available)")
    print("=" * 80)
    
    for key, info in UNAVAILABLE_MODELS.items():
        print(f"   ❌ {key}: {info}")
    
    print("\n")


def download_model(model_key: str, cache_dir: str = "./models", quantization: str = "4bit"):
    """Download a model from HuggingFace."""
    
    if model_key not in AVAILABLE_MODELS:
        logger.error(f"Unknown model: {model_key}")
        logger.info(f"Available: {', '.join(AVAILABLE_MODELS.keys())}")
        return False
    
    model_info = AVAILABLE_MODELS[model_key]
    model_name = model_info["name"]
    
    logger.info(f"Downloading: {model_name}")
    logger.info(f"Size: {model_info['size']} | Disk: {model_info['disk_space']}")
    
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    except ImportError:
        logger.error("Required packages not installed. Run:")
        logger.error("  pip install torch transformers accelerate bitsandbytes")
        return False
    
    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)
    
    try:
        logger.info("Downloading tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            cache_dir=str(cache_path),
            trust_remote_code=True
        )
        logger.info("✓ Tokenizer downloaded")
        
        logger.info(f"Downloading model with {quantization} quantization...")
        
        if quantization == "4bit":
            quant_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16
            )
            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                cache_dir=str(cache_path),
                device_map="auto",
                quantization_config=quant_config,
                trust_remote_code=True
            )
        elif quantization == "8bit":
            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                cache_dir=str(cache_path),
                device_map="auto",
                load_in_8bit=True,
                trust_remote_code=True
            )
        else:
            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                cache_dir=str(cache_path),
                device_map="auto",
                torch_dtype=torch.float16,
                trust_remote_code=True
            )
        
        logger.info("✓ Model downloaded successfully!")
        logger.info(f"  Cached at: {cache_path}")
        
        # Test generation
        logger.info("Testing model...")
        inputs = tokenizer("Hello, I am", return_tensors="pt").to(model.device)
        with torch.no_grad():
            outputs = model.generate(**inputs, max_new_tokens=10)
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        logger.info(f"  Test output: {response}")
        
        return True
        
    except Exception as e:
        logger.error(f"Download failed: {e}")
        if "gated" in str(e).lower() or "access" in str(e).lower():
            logger.error("This model requires accepting a license agreement.")
            logger.error(f"Visit: https://huggingface.co/{model_name}")
            logger.error("Accept the license, then run: huggingface-cli login")
        return False


def download_for_distillation(cache_dir: str = "./models"):
    """Download recommended models for knowledge distillation."""
    
    logger.info("=" * 60)
    logger.info("GRACE KNOWLEDGE DISTILLATION - MODEL DOWNLOAD")
    logger.info("=" * 60)
    
    # Recommended order: smallest first for testing
    recommended = ["phi3-mini"]  # Start with smallest
    
    for model_key in recommended:
        logger.info(f"\nDownloading {model_key}...")
        success = download_model(model_key, cache_dir)
        if success:
            logger.info(f"✓ {model_key} ready for distillation")
            return model_key
        else:
            logger.warning(f"✗ {model_key} failed, trying next...")
    
    logger.error("No models could be downloaded")
    return None


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Download LLM weights for Grace")
    parser.add_argument("--list", action="store_true", help="List available models")
    parser.add_argument("--model", type=str, help="Model to download (e.g., phi3-mini)")
    parser.add_argument("--cache-dir", type=str, default="./models", help="Cache directory")
    parser.add_argument("--quantization", type=str, default="4bit", 
                       choices=["4bit", "8bit", "none"], help="Quantization level")
    parser.add_argument("--auto", action="store_true", help="Auto-download best model for distillation")
    
    args = parser.parse_args()
    
    if args.list or (not args.model and not args.auto):
        list_models()
        return
    
    if args.auto:
        download_for_distillation(args.cache_dir)
    elif args.model:
        download_model(args.model, args.cache_dir, args.quantization)


if __name__ == "__main__":
    main()
