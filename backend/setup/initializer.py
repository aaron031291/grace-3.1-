"""
Environment initializer module that handles:
- Virtual environment detection and creation
- Dependency installation with error recovery
- Ollama service detection and startup
"""

import os
import sys
import subprocess
import shutil
import re
from pathlib import Path


class EnvironmentInitializer:
    """Handles environment setup and dependency installation."""
    
    def __init__(self):
        self.backend_dir = Path(__file__).parent.parent
        self.project_root = self.backend_dir.parent
        self.venv_path = self.backend_dir / "venv"
        self.requirements_file = self.backend_dir / "requirements.txt"
        self.requirements_backup = self.backend_dir / "requirements.txt.bak"
    
    def detect_or_create_venv(self) -> bool:
        """
        Detect if virtual environment exists, create one if not.
        
        Returns:
            bool: True if venv exists or was created successfully, False otherwise
        """
        if self.venv_path.exists():
            print(f"✓ Virtual environment found at {self.venv_path}")
            return True
        
        print(f"⚠ Virtual environment not found. Creating at {self.venv_path}...")
        try:
            subprocess.run(
                [sys.executable, "-m", "venv", str(self.venv_path)],
                check=True,
                capture_output=True
            )
            print(f"✓ Virtual environment created successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to create virtual environment: {e}")
            return False
    
    def get_pip_executable(self) -> str:
        """Get the pip executable path for the virtual environment."""
        if sys.platform == "win32":
            return str(self.venv_path / "Scripts" / "pip")
        return str(self.venv_path / "bin" / "pip")
    
    def install_requirements(self) -> bool:
        """
        Install requirements from requirements.txt.
        
        Returns:
            bool: True if installation successful, False otherwise
        """
        pip_exe = self.get_pip_executable()
        
        if not os.path.exists(pip_exe):
            print("✗ pip executable not found in virtual environment")
            return False
        
        print("📦 Installing requirements...")
        try:
            subprocess.run(
                [pip_exe, "install", "-r", str(self.requirements_file)],
                check=True,
                capture_output=True
            )
            print("✓ Requirements installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to install requirements: {e}")
            return False
    
    def cleanup_version_pins(self) -> bool:
        """
        Remove version pins from requirements.txt (e.g., ==, >=, <=).
        Creates a backup first.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Backup original requirements
            with open(self.requirements_file, 'r') as f:
                original_content = f.read()
            
            with open(self.requirements_backup, 'w') as f:
                f.write(original_content)
            
            # Remove version specifications
            cleaned_lines = []
            for line in original_content.split('\n'):
                line = line.strip()
                if not line or line.startswith('#'):
                    cleaned_lines.append(line)
                else:
                    # Remove version specifiers (==, >=, <=, ~=, >, <)
                    cleaned_package = re.split(r'[=!<>~]', line)[0].strip()
                    if cleaned_package:
                        cleaned_lines.append(cleaned_package)
            
            cleaned_content = '\n'.join(cleaned_lines)
            with open(self.requirements_file, 'w') as f:
                f.write(cleaned_content)
            
            print("✓ Cleaned version pins from requirements.txt")
            return True
        except Exception as e:
            print(f"✗ Failed to clean version pins: {e}")
            return False
    
    def restore_requirements(self) -> bool:
        """Restore requirements.txt from backup."""
        try:
            if self.requirements_backup.exists():
                with open(self.requirements_backup, 'r') as f:
                    content = f.read()
                with open(self.requirements_file, 'w') as f:
                    f.write(content)
                print("✓ Restored original requirements.txt")
                return True
        except Exception as e:
            print(f"✗ Failed to restore requirements: {e}")
        return False
    
    def uninstall_requirements(self) -> bool:
        """
        Uninstall all packages from requirements.txt.
        
        Returns:
            bool: True if successful, False otherwise
        """
        pip_exe = self.get_pip_executable()
        
        if not os.path.exists(pip_exe):
            return False
        
        print("🗑 Uninstalling requirements...")
        try:
            subprocess.run(
                [pip_exe, "uninstall", "-r", str(self.requirements_file), "-y"],
                check=True,
                capture_output=True
            )
            print("✓ Requirements uninstalled successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"⚠ Warning during uninstall: {e}")
            return False
    
    def install_dependencies(self) -> bool:
        """
        Install dependencies with error recovery.
        If installation fails, attempt recovery by cleaning version pins.
        
        Returns:
            bool: True if installation successful, False otherwise
        """
        if not self.install_requirements():
            print("\n⚠ Initial installation failed. Attempting recovery...")
            
            # Uninstall what was partially installed
            self.uninstall_requirements()
            
            # Clean version pins and retry
            if self.cleanup_version_pins():
                print("🔄 Retrying installation with cleaned requirements...")
                if self.install_requirements():
                    print("✓ Installation successful after cleanup")
                    return True
            
            # If still failing, restore original and report
            self.restore_requirements()
            print("✗ Installation failed even after recovery attempt")
            return False
        
        return True
    
    def check_ollama_running(self) -> bool:
        """
        Check if Ollama service is running.
        
        Returns:
            bool: True if Ollama is running, False otherwise
        """
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def ollama_exists(self) -> bool:
        """Check if ollama command is available in PATH."""
        return shutil.which("ollama") is not None
    
    def start_ollama(self) -> bool:
        """
        Attempt to start Ollama serve.
        
        Returns:
            bool: True if started successfully, False otherwise
        """
        print("🚀 Starting Ollama serve...")
        try:
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print("✓ Ollama serve started")
            return True
        except FileNotFoundError:
            return False
        except Exception as e:
            print(f"✗ Failed to start Ollama: {e}")
            return False
    
    def setup_ollama(self) -> bool:
        """
        Check and setup Ollama service.
        
        Returns:
            bool: True if Ollama is running or was started, False otherwise
        """
        print("\n🔍 Checking Ollama service...")
        
        if not self.ollama_exists():
            print("✗ Ollama is not installed")
            print("\n📥 Please download and install Ollama from: https://ollama.ai")
            return False
        
        if self.check_ollama_running():
            print("✓ Ollama is already running")
            return True
        
        if self.start_ollama():
            print("✓ Ollama service started successfully")
            return True
        
        print("✗ Failed to start Ollama service")
        return False
    
    def initialize(self) -> bool:
        """
        Run full environment initialization.
        
        Returns:
            bool: True if all steps successful, False otherwise
        """
        print("=" * 60)
        print("Grace Environment Initialization")
        print("=" * 60)
        
        # Step 1: Virtual Environment
        if not self.detect_or_create_venv():
            return False
        
        # Step 2: Install Dependencies
        if not self.install_dependencies():
            return False
        
        # Step 3: Setup Ollama
        if not self.setup_ollama():
            print("\n⚠ Warning: Ollama setup failed, but proceeding...")
        
        print("\n" + "=" * 60)
        print("✓ Environment initialization complete!")
        print("=" * 60)
        return True


def main():
    """Main entry point for environment initialization."""
    initializer = EnvironmentInitializer()
    success = initializer.initialize()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
