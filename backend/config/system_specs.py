"""
System Specifications Module
============================

Loads host machine specs and enforces build constraints.
Grace will NOT build outside these hardware/platform constraints.

Usage:
    from config.system_specs import SystemSpecs
    
    if SystemSpecs.can_build_for("arm64"):
        # This will be False - arm64 not supported
        pass
    
    max_jobs = SystemSpecs.max_parallel_jobs()
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

# Find specs file relative to project root
_PROJECT_ROOT = Path(__file__).parent.parent.parent
_SPECS_FILE = _PROJECT_ROOT / ".system_specs.json"


class SystemSpecs:
    """
    System specifications - loaded from .system_specs.json
    
    This is IMMUTABLE - Grace cannot modify these constraints.
    Build operations check these before attempting compilation.
    """
    
    _specs: Optional[Dict[str, Any]] = None
    _loaded: bool = False
    
    @classmethod
    def _load(cls) -> Dict[str, Any]:
        """Load specs from JSON file."""
        if cls._loaded and cls._specs:
            return cls._specs
        
        if not _SPECS_FILE.exists():
            logger.warning(f"System specs file not found: {_SPECS_FILE}")
            cls._specs = cls._default_specs()
        else:
            try:
                with open(_SPECS_FILE, "r") as f:
                    cls._specs = json.load(f)
                logger.info(f"Loaded system specs: {cls._specs.get('cpu', {}).get('model', 'Unknown')}")
            except Exception as e:
                logger.error(f"Failed to load system specs: {e}")
                cls._specs = cls._default_specs()
        
        cls._loaded = True
        return cls._specs
    
    @classmethod
    def _default_specs(cls) -> Dict[str, Any]:
        """Default specs if file not found."""
        return {
            "os": {"type": "unknown"},
            "cpu": {"cores": 4, "threads": 8},
            "memory": {"total_gb": 16, "max_allocation_gb": 12},
            "gpu": {"primary": {"cuda_capable": False}},
            "build_constraints": {
                "max_parallel_jobs": 4,
                "supported_architectures": ["x86_64"],
                "supported_platforms": ["windows", "linux"]
            },
            "forbidden_builds": {
                "architectures": [],
                "platforms": []
            }
        }
    
    # =========================================================================
    # Hardware Info
    # =========================================================================
    
    @classmethod
    def cpu_model(cls) -> str:
        """Get CPU model name."""
        return cls._load().get("cpu", {}).get("model", "Unknown")
    
    @classmethod
    def cpu_cores(cls) -> int:
        """Get number of physical CPU cores."""
        return cls._load().get("cpu", {}).get("cores", 4)
    
    @classmethod
    def cpu_threads(cls) -> int:
        """Get number of logical threads."""
        return cls._load().get("cpu", {}).get("threads", 8)
    
    @classmethod
    def total_memory_gb(cls) -> int:
        """Get total system RAM in GB."""
        return cls._load().get("memory", {}).get("total_gb", 16)
    
    @classmethod
    def max_memory_allocation_gb(cls) -> int:
        """Get max memory Grace can allocate."""
        return cls._load().get("memory", {}).get("max_allocation_gb", 12)
    
    @classmethod
    def gpu_model(cls) -> str:
        """Get primary GPU model."""
        return cls._load().get("gpu", {}).get("primary", {}).get("model", "None")
    
    @classmethod
    def gpu_vram_gb(cls) -> int:
        """Get GPU VRAM in GB."""
        return cls._load().get("gpu", {}).get("primary", {}).get("vram_gb", 0)
    
    @classmethod
    def has_cuda(cls) -> bool:
        """Check if CUDA is available."""
        return cls._load().get("gpu", {}).get("primary", {}).get("cuda_capable", False)
    
    # =========================================================================
    # Build Constraints
    # =========================================================================
    
    @classmethod
    def max_parallel_jobs(cls) -> int:
        """Get max parallel build jobs."""
        return cls._load().get("build_constraints", {}).get("max_parallel_jobs", 4)
    
    @classmethod
    def max_memory_per_job_gb(cls) -> int:
        """Get max memory per build job."""
        return cls._load().get("build_constraints", {}).get("max_memory_per_job_gb", 4)
    
    @classmethod
    def max_gpu_memory_gb(cls) -> int:
        """Get max GPU memory for operations."""
        return cls._load().get("build_constraints", {}).get("max_gpu_memory_gb", 0)
    
    @classmethod
    def supported_architectures(cls) -> List[str]:
        """Get list of supported CPU architectures."""
        return cls._load().get("build_constraints", {}).get("supported_architectures", ["x86_64"])
    
    @classmethod
    def supported_platforms(cls) -> List[str]:
        """Get list of supported platforms."""
        return cls._load().get("build_constraints", {}).get("supported_platforms", ["windows"])
    
    @classmethod
    def forbidden_architectures(cls) -> List[str]:
        """Get list of forbidden architectures."""
        return cls._load().get("forbidden_builds", {}).get("architectures", [])
    
    @classmethod
    def forbidden_platforms(cls) -> List[str]:
        """Get list of forbidden platforms."""
        return cls._load().get("forbidden_builds", {}).get("platforms", [])
    
    # =========================================================================
    # Build Checks
    # =========================================================================
    
    @classmethod
    def can_build_for(cls, architecture: str = None, platform: str = None) -> bool:
        """
        Check if Grace can build for the given architecture/platform.
        
        Args:
            architecture: Target architecture (e.g., "arm64", "x86_64")
            platform: Target platform (e.g., "windows", "macos", "linux")
        
        Returns:
            True if build is allowed, False otherwise
        """
        if architecture:
            arch_lower = architecture.lower()
            if arch_lower in [a.lower() for a in cls.forbidden_architectures()]:
                logger.warning(f"Build forbidden for architecture: {architecture}")
                return False
            if arch_lower not in [a.lower() for a in cls.supported_architectures()]:
                logger.warning(f"Architecture not supported: {architecture}")
                return False
        
        if platform:
            plat_lower = platform.lower()
            if plat_lower in [p.lower() for p in cls.forbidden_platforms()]:
                logger.warning(f"Build forbidden for platform: {platform}")
                return False
            if plat_lower not in [p.lower() for p in cls.supported_platforms()]:
                logger.warning(f"Platform not supported: {platform}")
                return False
        
        return True
    
    @classmethod
    def validate_build_request(cls, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a build request against system constraints.
        
        Returns dict with 'allowed' bool and 'reason' if denied.
        """
        arch = request.get("architecture") or request.get("arch")
        platform = request.get("platform") or request.get("os")
        memory_gb = request.get("memory_gb", 0)
        parallel_jobs = request.get("parallel_jobs", 1)
        
        # Check architecture/platform
        if not cls.can_build_for(arch, platform):
            return {
                "allowed": False,
                "reason": f"Cannot build for {arch or 'unknown'}/{platform or 'unknown'} - not supported by host system"
            }
        
        # Check memory
        if memory_gb > cls.max_memory_allocation_gb():
            return {
                "allowed": False,
                "reason": f"Requested {memory_gb}GB exceeds max allocation of {cls.max_memory_allocation_gb()}GB"
            }
        
        # Check parallel jobs
        if parallel_jobs > cls.max_parallel_jobs():
            return {
                "allowed": False,
                "reason": f"Requested {parallel_jobs} jobs exceeds max of {cls.max_parallel_jobs()}"
            }
        
        return {"allowed": True}
    
    @classmethod
    def get_all_specs(cls) -> Dict[str, Any]:
        """Get all system specs as dict."""
        return cls._load()
    
    @classmethod
    def summary(cls) -> str:
        """Get human-readable summary of specs."""
        specs = cls._load()
        return (
            f"CPU: {cls.cpu_model()} ({cls.cpu_cores()}c/{cls.cpu_threads()}t)\n"
            f"RAM: {cls.total_memory_gb()}GB (max alloc: {cls.max_memory_allocation_gb()}GB)\n"
            f"GPU: {cls.gpu_model()} ({cls.gpu_vram_gb()}GB VRAM, CUDA: {cls.has_cuda()})\n"
            f"Supported: {', '.join(cls.supported_platforms())} on {', '.join(cls.supported_architectures())}\n"
            f"Forbidden: {', '.join(cls.forbidden_platforms())} / {', '.join(cls.forbidden_architectures())}"
        )


# Auto-load on import
_specs = SystemSpecs._load()
