"""
OS Adapter - Thin Boundary Layer for Multi-OS Support
======================================================

Core principle: Make the operating system irrelevant to business logic.

This module provides OS-agnostic interfaces for:
- File system paths
- Process spawning and management
- Permissions
- Hardware access (where needed)

All OS-specific logic is isolated here. Business logic never checks platform.
"""

import os
import sys
import subprocess
import signal
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
import platform as platform_module


class OSFamily(str, Enum):
    """Operating system family."""
    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"
    UNKNOWN = "unknown"


class OSType:
    """
    OS type detection and capabilities.
    
    Detected once at import time, never changes during runtime.
    """
    
    # Detection
    _platform_system = platform_module.system().lower()
    _platform_family = None
    
    if _platform_system == "windows":
        _platform_family = OSFamily.WINDOWS
    elif _platform_system == "linux":
        _platform_family = OSFamily.LINUX
    elif _platform_system == "darwin":
        _platform_family = OSFamily.MACOS
    else:
        _platform_family = OSFamily.UNKNOWN
    
    # Cached properties
    family: OSFamily = _platform_family
    is_windows: bool = (family == OSFamily.WINDOWS)
    is_linux: bool = (family == OSFamily.LINUX)
    is_macos: bool = (family == OSFamily.MACOS)
    is_unix: bool = (family in [OSFamily.LINUX, OSFamily.MACOS])
    
    # Capabilities (detected at import)
    supports_posix_signals: bool = is_unix
    supports_symlinks: bool = True  # All modern OSes
    default_encoding: str = "utf-8"
    
    @classmethod
    def detect_console_encoding(cls) -> str:
        """Detect console encoding for safe printing."""
        if cls.is_windows:
            # Windows console might use cp1252
            try:
                encoding = sys.stdout.encoding or "utf-8"
                # Test if UTF-8 works
                if encoding.lower() in ["cp1252", "cp437", "latin1"]:
                    return encoding
                return "utf-8"
            except Exception:
                return "utf-8"
        else:
            # Unix-like systems typically use UTF-8
            return sys.stdout.encoding or "utf-8"


# Global OS instance
OS = OSType()


class PathAdapter:
    """
    Portable path operations.
    
    Always use Path objects internally, convert at boundaries.
    """
    
    @staticmethod
    def join(*parts: str) -> str:
        """Join path parts portably."""
        return str(Path(*parts))
    
    @staticmethod
    def normalize(path: str) -> str:
        """Normalize path separators."""
        return str(Path(path))
    
    @staticmethod
    def resolve(path: str) -> str:
        """Resolve absolute path."""
        return str(Path(path).resolve())
    
    @staticmethod
    def is_absolute(path: str) -> bool:
        """Check if path is absolute."""
        return Path(path).is_absolute()
    
    @staticmethod
    def relative_to(path: str, base: str) -> str:
        """Get relative path."""
        return str(Path(path).relative_to(Path(base)))
    
    @staticmethod
    def parent(path: str) -> str:
        """Get parent directory."""
        return str(Path(path).parent)
    
    @staticmethod
    def name(path: str) -> str:
        """Get filename or directory name."""
        return Path(path).name
    
    @staticmethod
    def ensure_dir(path: str) -> None:
        """Ensure directory exists, create if needed."""
        Path(path).mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def exists(path: str) -> bool:
        """Check if path exists."""
        return Path(path).exists()
    
    @staticmethod
    def is_file(path: str) -> bool:
        """Check if path is a file."""
        return Path(path).is_file()
    
    @staticmethod
    def is_dir(path: str) -> bool:
        """Check if path is a directory."""
        return Path(path).is_dir()


class ProcessAdapter:
    """
    Portable process spawning and management.
    
    Handles OS differences transparently.
    """
    
    @staticmethod
    def spawn(
        command: List[str],
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        stdout: Any = subprocess.PIPE,
        stderr: Any = subprocess.PIPE,
        shell: bool = False,
        **kwargs
    ) -> subprocess.Popen:
        """
        Spawn a process portably.
        
        Args:
            command: Command and arguments as list
            cwd: Working directory
            env: Environment variables (merged with current env)
            stdout: stdout handling
            stderr: stderr handling
            shell: Use shell (rarely needed, prefer command list)
            **kwargs: Additional subprocess.Popen arguments
            
        Returns:
            subprocess.Popen instance
        """
        # Prepare environment
        process_env = os.environ.copy()
        if env:
            process_env.update(env)
        
        # OS-specific process creation flags
        creation_flags = 0
        if OS.is_windows:
            # Windows: prevent window creation for background processes
            if stdout == subprocess.PIPE or stderr == subprocess.PIPE:
                creation_flags = subprocess.CREATE_NO_WINDOW
        
        # Add creation flags for Windows
        if OS.is_windows and creation_flags:
            kwargs['creationflags'] = creation_flags
        
        # Spawn process
        return subprocess.Popen(
            command,
            cwd=cwd,
            env=process_env,
            stdout=stdout,
            stderr=stderr,
            shell=shell,
            **kwargs
        )
    
    @staticmethod
    def terminate(process: subprocess.Popen, timeout: float = 5.0) -> bool:
        """
        Gracefully terminate a process.
        
        Args:
            process: subprocess.Popen instance
            timeout: Seconds to wait before force kill
            
        Returns:
            True if process terminated gracefully
        """
        if process.poll() is not None:
            # Already dead
            return True
        
        try:
            # Try graceful termination
            process.terminate()
            
            # Wait for termination
            try:
                process.wait(timeout=timeout)
                return True
            except subprocess.TimeoutExpired:
                # Force kill
                process.kill()
                process.wait()
                return False
        except Exception:
            # Process may already be dead
            try:
                process.kill()
            except Exception:
                pass
            return False
    
    @staticmethod
    def kill_process_tree(pid: int) -> None:
        """
        Kill process and all children (OS-specific).
        
        Args:
            pid: Process ID to kill
        """
        try:
            if OS.is_windows:
                # Windows: use taskkill to kill process tree
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    capture_output=True,
                    timeout=5
                )
            else:
                # Unix: use SIGTERM to process group
                os.killpg(os.getpgid(pid), signal.SIGTERM)
                # Wait briefly, then force kill
                import time
                time.sleep(0.5)
                try:
                    os.killpg(os.getpgid(pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass  # Already dead
        except (ProcessLookupError, subprocess.TimeoutExpired):
            pass  # Process may already be dead
        except Exception:
            # Fallback: try to kill just the process
            try:
                if OS.is_windows:
                    subprocess.run(
                        ["taskkill", "/F", "/PID", str(pid)],
                        capture_output=True,
                        timeout=5
                    )
                else:
                    os.kill(pid, signal.SIGKILL)
            except Exception:
                pass
    
    @staticmethod
    def check_process_alive(pid: int) -> bool:
        """
        Check if process is still running.
        
        Args:
            pid: Process ID to check
            
        Returns:
            True if process is alive
        """
        try:
            if OS.is_windows:
                # Windows: use tasklist (fallback to signal)
                try:
                    os.kill(pid, 0)
                    return True
                except ProcessLookupError:
                    return False
                except OSError:
                    return False
            else:
                # Unix: send signal 0 (doesn't kill, just checks)
                os.kill(pid, 0)
                return True
        except (ProcessLookupError, OSError):
            return False


class ShellAdapter:
    """
    Portable shell command execution.
    
    Handles finding shell executables and constructing commands.
    """
    
    @staticmethod
    def find_shell() -> Tuple[str, List[str]]:
        """
        Find appropriate shell for current OS.
        
        Returns:
            Tuple of (shell_executable, [args])
        """
        if OS.is_windows:
            # Windows: use cmd.exe
            return "cmd", ["/c"]
        else:
            # Unix: use bash (or sh if bash not available)
            if shutil.which("bash"):
                return "bash", []
            else:
                return "sh", []
    
    @staticmethod
    def find_executable(name: str) -> Optional[str]:
        """
        Find executable in PATH.
        
        Args:
            name: Executable name
            
        Returns:
            Full path if found, None otherwise
        """
        return shutil.which(name)
    
    @staticmethod
    def build_command(script_path: str, *args: str) -> List[str]:
        """
        Build command to execute a script.
        
        Args:
            script_path: Path to script
            *args: Arguments to pass to script
            
        Returns:
            Command list ready for subprocess
        """
        shell_exe, shell_args = ShellAdapter.find_shell()
        
        if OS.is_windows:
            # Windows: cmd /c script.bat args
            if script_path.endswith(('.bat', '.cmd')):
                return [shell_exe] + shell_args + [script_path] + list(args)
            elif script_path.endswith('.py'):
                # Python script on Windows
                python = sys.executable
                return [python, script_path] + list(args)
            else:
                # Try to execute directly
                return [script_path] + list(args)
        else:
            # Unix: bash script.sh args or python script.py args
            if script_path.endswith(('.sh', '.bash')):
                return [shell_exe] + shell_args + [script_path] + list(args)
            elif script_path.endswith('.py'):
                # Python script on Unix
                python = sys.executable
                return [python, script_path] + list(args)
            else:
                # Make executable and run directly
                os.chmod(script_path, 0o755)
                return [script_path] + list(args)


class PermissionAdapter:
    """
    Portable permission and security operations.
    """
    
    @staticmethod
    def make_executable(path: str) -> None:
        """
        Make file executable (Unix only, no-op on Windows).
        
        Args:
            path: File path
        """
        if OS.is_unix:
            os.chmod(path, 0o755)
        # Windows: files are executable by extension
    
    @staticmethod
    def check_readable(path: str) -> bool:
        """
        Check if path is readable.
        
        Args:
            path: Path to check
            
        Returns:
            True if readable
        """
        return os.access(path, os.R_OK)
    
    @staticmethod
    def check_writable(path: str) -> bool:
        """
        Check if path is writable.
        
        Args:
            path: Path to check
            
        Returns:
            True if writable
        """
        return os.access(path, os.W_OK)


# Convenience instances
paths = PathAdapter()
process = ProcessAdapter()
shell = ShellAdapter()
permissions = PermissionAdapter()


def get_os_info() -> Dict[str, Any]:
    """
    Get OS information for diagnostics.
    
    Returns:
        Dictionary with OS information
    """
    return {
        "family": OS.family.value,
        "system": platform_module.system(),
        "release": platform_module.release(),
        "version": platform_module.version(),
        "machine": platform_module.machine(),
        "processor": platform_module.processor(),
        "python_version": sys.version,
        "is_windows": OS.is_windows,
        "is_linux": OS.is_linux,
        "is_macos": OS.is_macos,
        "is_unix": OS.is_unix,
        "console_encoding": OSType.detect_console_encoding(),
    }
