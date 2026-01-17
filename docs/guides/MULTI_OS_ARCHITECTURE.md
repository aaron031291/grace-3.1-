# Multi-OS Architecture

GRACE is designed to run consistently across multiple operating systems (Windows, macOS, Linux) without branching logic, fragile hacks, or OS-specific rewrites.

## Core Principles

### OS-Agnostic Core

**Business logic, intelligence, orchestration, and state management do not depend on the OS.**

All core functionality is written in portable runtimes (Python, Node, Rust, JVM) and uses OS abstractions instead of platform checks.

### Thin OS Adapters

**Small boundary layers handle OS-specific concerns:**

- File system paths (handled by `PathAdapter`)
- Process spawning (handled by `ProcessAdapter`)
- Permissions (handled by `PermissionAdapter`)
- Hardware access (audio, GPU, sensors) - isolated to adapters

Everything OS-specific is isolated in `backend/utils/os_adapter.py` and replaceable.

### Unified Execution Model

**Same startup flow everywhere:**

```
launcher → backend → services → UI
```

OS differences are resolved at boot via capability detection, not conditionals scattered through code.

### Portable Packaging

**Common approaches:**

- Single binary (PyInstaller, Nuitka, Rust)
- Containerized services (Docker where allowed)
- OS-native wrappers only at the edge (.exe, .app, ELF)

### Consistent Developer & User Experience

**Same commands, same logs, same behavior.**

No "works on my machine" drift.

## Architecture

### OS Adapter Layer

Located in `backend/utils/os_adapter.py`:

```python
from backend.utils.os_adapter import OS, paths, process, shell, permissions

# OS detection (done once at import)
OS.family          # OSFamily.WINDOWS | LINUX | MACOS
OS.is_windows      # True/False
OS.is_linux        # True/False
OS.is_macos        # True/False
OS.is_unix         # True/False

# Path operations (always portable)
paths.join("dir", "sub", "file.txt")
paths.resolve("../relative")
paths.ensure_dir("path/to/dir")

# Process spawning (handles OS flags)
proc = process.spawn(["python", "script.py"], cwd="/path")
process.terminate(proc, timeout=5.0)
process.kill_process_tree(pid)

# Shell commands (finds appropriate shell)
shell.find_shell()           # ("cmd", ["/c"]) or ("bash", [])
shell.build_command(script)  # Builds command list for current OS

# Permissions
permissions.make_executable("script.sh")  # No-op on Windows
```

### No Platform Checks in Business Logic

**❌ Bad (OS checks everywhere):**

```python
if sys.platform == "win32":
    command = ["cmd", "/c", script]
else:
    command = ["bash", script]
```

**✅ Good (OS adapter):**

```python
from backend.utils.os_adapter import shell
command = shell.build_command(script)
```

### Path Handling

**❌ Bad (hard-coded paths):**

```python
if sys.platform == "win32":
    path = "C:\\Users\\grace\\data"
else:
    path = "/home/grace/data"
```

**✅ Good (portable paths):**

```python
from backend.utils.os_adapter import paths
data_dir = paths.join(project_root, "data")
data_dir = paths.resolve(data_dir)  # Always absolute, OS-aware
```

### Process Management

**❌ Bad (OS-specific flags):**

```python
if sys.platform == "win32":
    proc = subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)
else:
    proc = subprocess.Popen(cmd)
```

**✅ Good (OS adapter):**

```python
from backend.utils.os_adapter import process
proc = process.spawn(cmd)  # Handles OS flags automatically
```

## Supported Operating Systems

### Primary Support

- **Windows 10/11** (tested)
- **macOS** (10.14+, tested)
- **Ubuntu Linux** (20.04+, tested)
- **Debian** (10+, tested)

### Secondary Support (should work, may need minor adjustments)

- **Fedora** (32+, Red Hat upstream)
- **Arch Linux** (rolling release)
- **CentOS / Rocky Linux / AlmaLinux** (7+, enterprise)
- **Linux Mint** (20+, Ubuntu-based)
- **Kali Linux** (for security/penetration testing)

## Startup Flow

### Unified Startup Script

**Same script works everywhere:**

```bash
python start_grace.py [backend|frontend|all]
```

The script uses the OS adapter to:
1. Detect OS capabilities
2. Find appropriate executables (Python, npm, etc.)
3. Build commands for current OS
4. Spawn processes with correct flags
5. Handle termination portably

### Launcher

The enterprise launcher (`launcher/launcher.py`) uses the OS adapter for:

- Process spawning (handles Windows/Unix differences)
- Process termination (graceful → force kill)
- Signal handling (SIGTERM/SIGINT on Unix, taskkill on Windows)
- Path resolution (portable paths everywhere)

## Migration Guide

### Replacing Platform Checks

**Before:**
```python
import sys
import platform

if sys.platform == "win32":
    # Windows code
elif platform.system() == "Linux":
    # Linux code
else:
    # macOS code
```

**After:**
```python
from backend.utils.os_adapter import OS

if OS.is_windows:
    # Windows code (rare, should use adapter instead)
elif OS.is_linux:
    # Linux code (rare, should use adapter instead)
elif OS.is_macos:
    # macOS code (rare, should use adapter instead)
```

**Better: Use adapter methods:**
```python
from backend.utils.os_adapter import process

# Adapter handles OS differences automatically
proc = process.spawn(cmd)
```

### Replacing Hard-coded Paths

**Before:**
```python
import os

if os.name == "nt":
    config_dir = os.path.expanduser("~\\AppData\\Roaming\\grace")
else:
    config_dir = os.path.expanduser("~/.config/grace")
```

**After:**
```python
from backend.utils.os_adapter import paths
from pathlib import Path

config_dir = paths.join(Path.home(), ".config", "grace")
# or use appdirs library for proper config directories
```

### Replacing Process Spawning

**Before:**
```python
import subprocess
import os

if os.name == "nt":
    proc = subprocess.Popen(
        cmd,
        shell=True,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
else:
    proc = subprocess.Popen(cmd)
```

**After:**
```python
from backend.utils.os_adapter import process

proc = process.spawn(cmd)  # Handles all OS differences
```

## Testing Multi-OS Compatibility

### Local Testing

1. **Windows:** Run on Windows 10/11
2. **macOS:** Run on macOS 10.14+
3. **Linux:** Run on Ubuntu 20.04+ (or use Docker)

### CI/CD Testing

```yaml
# Example GitHub Actions matrix
strategy:
  matrix:
    os: [ubuntu-latest, windows-latest, macos-latest]
    python-version: [3.9, 3.10, 3.11]

steps:
  - name: Run tests
    run: python -m pytest
```

## Common Pitfalls

### 1. Platform Checks in Business Logic

**❌ Don't:**
```python
def process_file(path):
    if sys.platform == "win32":
        # Windows-specific logic
    else:
        # Unix logic
```

**✅ Do:**
```python
from backend.utils.os_adapter import paths

def process_file(path):
    resolved = paths.resolve(path)  # Handles OS differences
    # Business logic (no OS checks)
```

### 2. Hard-coded Paths

**❌ Don't:**
```python
data_file = "C:\\Users\\grace\\data.txt"  # Windows only
```

**✅ Do:**
```python
from backend.utils.os_adapter import paths
data_file = paths.join(project_root, "data.txt")
```

### 3. OS-Specific Process Flags

**❌ Don't:**
```python
flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
```

**✅ Do:**
```python
from backend.utils.os_adapter import process
proc = process.spawn(cmd)  # Flags handled automatically
```

## Why Multi-OS Matters

1. **Adoption:** Users don't change OS for software
2. **Security:** Fewer OS-specific exploits when logic is centralized
3. **Velocity:** One codebase, one mental model
4. **Longevity:** OSes change; abstractions survive

## One-Line Definition

**Multi-OS is not "supporting many operating systems"; it's making the operating system irrelevant to the system's intelligence and behavior.**

The OS adapter makes GRACE's core logic OS-agnostic, with all OS-specific concerns isolated to thin boundary layers.
