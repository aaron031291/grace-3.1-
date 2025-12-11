"""
Tests for embedding model VRAM usage monitoring.
"""

import unittest
import torch
import gc
from pathlib import Path
from embedding.embedder import EmbeddingModel


class TestVRAMUsage(unittest.TestCase):
    """Test cases for monitoring VRAM usage during model operations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.backend_dir = Path(__file__).parent.parent.parent
        self.model_path = str(self.backend_dir / "models" / "embedding" / "qwen_4b")
        
        # Skip all tests if CUDA is not available
        if not torch.cuda.is_available():
            self.skipTest("CUDA not available - GPU required for tests")
    
    def get_vram_usage(self) -> dict:
        """
        Get current VRAM usage.
        
        Returns:
            dict with 'used', 'total', and 'percentage' keys
        """
        torch.cuda.reset_peak_memory_stats()
        torch.cuda.synchronize()
        
        allocated = torch.cuda.memory_allocated() / (1024 ** 3)  # Convert to GB
        total = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)  # Convert to GB
        reserved = torch.cuda.memory_reserved() / (1024 ** 3)  # Convert to GB
        percentage = (allocated / total) * 100
        
        return {
            "allocated_gb": round(allocated, 2),
            "reserved_gb": round(reserved, 2),
            "total_gb": round(total, 2),
            "percentage": round(percentage, 2)
        }
    
    def print_vram_status(self, label: str):
        """Print VRAM usage with a label."""
        usage = self.get_vram_usage()
        print(f"\n{'='*60}")
        print(f"VRAM Status: {label}")
        print(f"{'='*60}")
        print(f"Allocated: {usage['allocated_gb']} GB / {usage['total_gb']} GB ({usage['percentage']}%)")
        print(f"Reserved:  {usage['reserved_gb']} GB")
        print(f"{'='*60}\n")
    
    def test_vram_usage_load_unload_cycle(self):
        """Test VRAM usage: before load -> after load -> after unload."""
        
        # Check initial VRAM usage
        self.print_vram_status("Initial State (Before Model Load)")
        initial_usage = self.get_vram_usage()
        
        # Load the model
        print("Loading model...")
        model = EmbeddingModel(model_path=self.model_path, device="cuda")
        torch.cuda.synchronize()
        gc.collect()
        
        # Check VRAM usage after loading
        self.print_vram_status("After Model Load")
        loaded_usage = self.get_vram_usage()
        
        # Calculate VRAM increase
        vram_increase = loaded_usage["allocated_gb"] - initial_usage["allocated_gb"]
        print(f"VRAM increase after loading: {vram_increase} GB")
        
        # Verify model was loaded and uses significant VRAM
        self.assertGreater(loaded_usage["allocated_gb"], initial_usage["allocated_gb"],
                          "VRAM should increase after loading model")
        self.assertGreater(vram_increase, 0.5,
                          "Model should use at least 0.5 GB of VRAM (Qwen 4B should use ~8-10 GB)")
        
        # Unload the model
        print("Unloading model...")
        model.unload_model()
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
        gc.collect()
        
        # Check VRAM usage after unloading
        self.print_vram_status("After Model Unload")
        unloaded_usage = self.get_vram_usage()
        
        # Calculate VRAM decrease
        vram_decrease = loaded_usage["allocated_gb"] - unloaded_usage["allocated_gb"]
        print(f"VRAM decrease after unloading: {vram_decrease} GB")
        
        # Verify model was unloaded and VRAM was freed
        self.assertLess(unloaded_usage["allocated_gb"], loaded_usage["allocated_gb"],
                       "VRAM should decrease after unloading model")
        
        # Print summary
        print("\nVRAM Usage Summary:")
        print(f"  Before load:  {initial_usage['allocated_gb']} GB")
        print(f"  After load:   {loaded_usage['allocated_gb']} GB (↑ {vram_increase} GB)")
        print(f"  After unload: {unloaded_usage['allocated_gb']} GB (↓ {vram_decrease} GB)")
    


if __name__ == "__main__":
    unittest.main()
