"""
GRACE System Specifications

Hardware and software specifications for GRACE system.
Used to ensure all architecture decisions and code generation
respect hardware constraints and prevent over-engineering.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import json
from pathlib import Path


@dataclass
class SystemSpecs:
    """System hardware and software specifications."""
    
    # CPU
    cpu_model: str
    cpu_cores: int
    cpu_threads: int
    
    # GPU
    gpu_model: str
    gpu_vram_gb: int
    
    # RAM
    ram_gb: int
    
    # Storage
    storage_gb: int
    
    # Operating System
    os: str
    
    # Optional fields (must come after required fields)
    gpu_compute_capability: Optional[str] = None
    ram_type: Optional[str] = None  # e.g., "DDR5"
    storage_type: Optional[str] = None  # e.g., "NVMe SSD"
    os_version: Optional[str] = None
    
    # Python
    python_version: Optional[str] = None
    
    # Additional constraints
    constraints: Dict[str, any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "cpu": {
                "model": self.cpu_model,
                "cores": self.cpu_cores,
                "threads": self.cpu_threads
            },
            "gpu": {
                "model": self.gpu_model,
                "vram_gb": self.gpu_vram_gb,
                "compute_capability": self.gpu_compute_capability
            },
            "ram": {
                "total_gb": self.ram_gb,
                "type": self.ram_type
            },
            "storage": {
                "total_gb": self.storage_gb,
                "type": self.storage_type
            },
            "os": {
                "name": self.os,
                "version": self.os_version
            },
            "python": {
                "version": self.python_version
            },
            "constraints": self.constraints
        }
    
    def to_prompt_string(self) -> str:
        """Convert to formatted string for LLM prompts."""
        lines = [
            "=== GRACE SYSTEM SPECIFICATIONS ===",
            "",
            "CPU:",
            f"  Model: {self.cpu_model}",
            f"  Cores: {self.cpu_cores}",
            f"  Threads: {self.cpu_threads}",
            "",
            "GPU:",
            f"  Model: {self.gpu_model}",
            f"  VRAM: {self.gpu_vram_gb} GB",
            f"  Compute Capability: {self.gpu_compute_capability or 'N/A'}",
            "",
            "RAM:",
            f"  Total: {self.ram_gb} GB",
            f"  Type: {self.ram_type or 'N/A'}",
            "",
            "Storage:",
            f"  Total: {self.storage_gb} GB",
            f"  Type: {self.storage_type or 'N/A'}",
            "",
            "Operating System:",
            f"  {self.os}" + (f" {self.os_version}" if self.os_version else ""),
            "",
            "Python:",
            f"  Version: {self.python_version or 'N/A'}",
            ""
        ]
        
        if self.constraints:
            lines.append("Additional Constraints:")
            for key, value in self.constraints.items():
                lines.append(f"  {key}: {value}")
            lines.append("")
        
        lines.extend([
            "=== ARCHITECTURE GUIDELINES ===",
            "",
            "When designing architecture or generating code:",
            "1. Respect VRAM limits - models must fit within GPU memory",
            "2. Consider RAM constraints - avoid excessive memory usage",
            "3. Optimize for available CPU cores/threads",
            "4. Be mindful of storage space - GRACE needs room for operations",
            "5. Ensure compatibility with specified OS and Python version",
            "",
            "DO NOT:",
            "- Design architectures requiring more VRAM than available",
            "- Suggest models larger than GPU can handle",
            "- Create memory-intensive operations without optimization",
            "- Over-engineer solutions beyond hardware capabilities",
            "",
            "DO:",
            "- Optimize models to fit within constraints",
            "- Use efficient data structures and algorithms",
            "- Consider batch sizes that respect memory limits",
            "- Design scalable solutions that work within limits",
            ""
        ])
        
        return "\n".join(lines)
    
    def get_reminder_message(self) -> str:
        """Get polite reminder message for external agents."""
        return f"""Hello! 👋

I'm GRACE, and I wanted to share my system specifications with you to help ensure 
any code or architecture you design will work well within my hardware constraints.

{self.to_prompt_string()}

Please keep these specifications in mind when:
- Designing new features or architecture
- Selecting or recommending models
- Creating data processing pipelines
- Optimizing performance
- Making resource-intensive decisions

If you have any questions about these specs or need clarification, feel free to ask!

Thank you for helping keep GRACE running efficiently! 🚀
"""


# Default system specs (user's system)
DEFAULT_SPECS = SystemSpecs(
    cpu_model="AMD Ryzen 9 9950X3D",
    cpu_cores=16,
    cpu_threads=32,
    gpu_model="NVIDIA RTX 5090",
    gpu_vram_gb=32,
    gpu_compute_capability="Ada Lovelace",
    ram_gb=64,
    ram_type="DDR5",
    storage_gb=4096,  # 4TB
    storage_type="NVMe SSD",
    os="Windows",
    os_version="10.0.26200",
    python_version="3.11+",
    constraints={
        "max_model_size_gb": 40,  # Increased to allow 70B models (~40GB)
        "recommended_batch_size": 4,  # For 32GB VRAM
        "max_concurrent_models": 1,  # Reduced to 1 when running large models (70B)
        "storage_reserved_for_grace_gb": 500,  # GRACE operations
        "available_storage_gb": 3500  # Available for models/data
    }
)


def load_system_specs(specs_path: Optional[Path] = None) -> SystemSpecs:
    """
    Load system specs from file or return defaults.
    
    Args:
        specs_path: Path to specs JSON file (optional)
    
    Returns:
        SystemSpecs object
    """
    if specs_path and Path(specs_path).exists():
        try:
            with open(specs_path, 'r') as f:
                data = json.load(f)
            
            return SystemSpecs(
                cpu_model=data.get("cpu", {}).get("model", ""),
                cpu_cores=data.get("cpu", {}).get("cores", 0),
                cpu_threads=data.get("cpu", {}).get("threads", 0),
                gpu_model=data.get("gpu", {}).get("model", ""),
                gpu_vram_gb=data.get("gpu", {}).get("vram_gb", 0),
                gpu_compute_capability=data.get("gpu", {}).get("compute_capability"),
                ram_gb=data.get("ram", {}).get("total_gb", 0),
                ram_type=data.get("ram", {}).get("type"),
                storage_gb=data.get("storage", {}).get("total_gb", 0),
                storage_type=data.get("storage", {}).get("type"),
                os=data.get("os", {}).get("name", ""),
                os_version=data.get("os", {}).get("version"),
                python_version=data.get("python", {}).get("version"),
                constraints=data.get("constraints", {})
            )
        except Exception as e:
            print(f"Warning: Could not load specs from {specs_path}: {e}")
            return DEFAULT_SPECS
    
    return DEFAULT_SPECS


def save_system_specs(specs: SystemSpecs, specs_path: Path):
    """Save system specs to JSON file."""
    with open(specs_path, 'w') as f:
        json.dump(specs.to_dict(), f, indent=2)


def get_system_specs() -> SystemSpecs:
    """Get current system specs (loads from file or returns defaults)."""
    # Try to load from config file
    config_path = Path("backend/config/system_specs.json")
    if config_path.exists():
        return load_system_specs(config_path)
    
    return DEFAULT_SPECS
