"""
Environment initializer module that handles:
- Virtual environment detection and creation
- Dependency installation with error recovery
- Ollama service detection and startup
- Model availability checking and pulling
"""

import os
import sys
import subprocess
import shutil
import re
import socket
from pathlib import Path

try:
    from huggingface_hub import snapshot_download
except ImportError:
    snapshot_download = None


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
        else:
            if self.start_ollama():
                print("✓ Ollama service started successfully")
            else:
                print("✗ Failed to start Ollama service")
                return False
        
        # Check and pull default LLM model
        if not self.ensure_llm_model():
            print("⚠ Warning: Failed to ensure default LLM model")
        
        # Check and pull embedding model
        if not self.ensure_embedding_model():
            print("⚠ Warning: Failed to ensure embedding model")
        
        return True
    
    def ensure_llm_model(self) -> bool:
        """
        Check if the default LLM model is available, pull it if not.
        
        Returns:
            bool: True if model is available or was pulled successfully
        """
        try:
            from settings import settings
            model_name = settings.OLLAMA_LLM_DEFAULT
        except (ImportError, AttributeError):
            model_name = "mistral:7b"
        
        print(f"\n🔍 Checking for default LLM model: {model_name}")
        
        try:
            # Check if model is available
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                timeout=10,
                text=True
            )
            
            if result.returncode == 0 and model_name in result.stdout:
                print(f"✓ Model '{model_name}' is already available")
                return True
            
            # Model not found, pull it
            print(f"📥 Pulling model '{model_name}'. This may take a while...")
            result = subprocess.run(
                ["ollama", "pull", model_name],
                capture_output=True,
                timeout=3600,  # 1 hour timeout for pulling
                text=True
            )
            
            if result.returncode == 0:
                print(f"✓ Model '{model_name}' pulled successfully")
                return True
            else:
                print(f"✗ Failed to pull model '{model_name}'")
                if result.stderr:
                    print(f"  Error: {result.stderr}")
                return False
        
        except subprocess.TimeoutExpired:
            print(f"✗ Timeout while pulling model '{model_name}'")
            return False
        except Exception as e:
            print(f"✗ Error checking/pulling LLM model: {e}")
            return False
    
    def ensure_embedding_model(self) -> bool:
        """
        Check if embedding model exists locally, download from HuggingFace if not.
        
        Returns:
            bool: True if model exists or was downloaded successfully
        """
        embedding_dir = self.backend_dir / "models" / "embedding" / "qwen_4b"
        
        print(f"\n🔍 Checking embedding model at {embedding_dir}")
        
        # Check if model already exists
        if embedding_dir.exists() and (embedding_dir / "config.json").exists():
            print(f"✓ Embedding model already exists")
            return True
        
        # Create directory if it doesn't exist
        embedding_dir.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"📥 Downloading Qwen3-4B embedding model from HuggingFace...")
        print(f"   This may take a few minutes on first run...")
        
        try:
            if snapshot_download is None:
                print("✗ huggingface-hub not available. Please install it with: pip install huggingface-hub")
                return False
            
            # Download model from HuggingFace
            model_repo = "Qwen/Qwen3-4B"
            snapshot_download(
                repo_id=model_repo,
                local_dir=str(embedding_dir),
                local_dir_use_symlinks=False
            )
            
            print(f"✓ Embedding model downloaded to {embedding_dir}")
            return True
        
        except Exception as e:
            print(f"✗ Failed to download embedding model: {e}")
            print(f"  You can manually download from: https://huggingface.co/{model_repo}")
            return False
    
    def check_qdrant_running(self) -> bool:
        """
        Check if Qdrant service is running on port 6333.
        
        Returns:
            bool: True if Qdrant is running, False otherwise
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('localhost', 6333))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    def docker_engine_running(self) -> bool:
        """
        Check if Docker engine is running.
        
        Returns:
            bool: True if Docker is running, False otherwise
        """
        try:
            result = subprocess.run(
                ["docker", "ps"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def docker_exists(self) -> bool:
        """Check if docker command is available in PATH."""
        return shutil.which("docker") is not None
    
    def start_qdrant(self) -> bool:
        """
        Start Qdrant container using Docker.
        
        Returns:
            bool: True if started successfully, False otherwise
        """
        print("🚀 Starting Qdrant container...")
        try:
            subprocess.run(
                [
                    "docker", "run","-d", "-p", "6333:6333",
                    "-v", "qdrant_storage:/qdrant/storage",
                    "qdrant/qdrant"
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True
            )
            print("✓ Qdrant container started")
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to start Qdrant container: {e}")
            return False
        except Exception as e:
            print(f"✗ Error starting Qdrant: {e}")
            return False
    
    def setup_qdrant(self) -> bool:
        """
        Check and setup Qdrant vector database service.
        
        Returns:
            bool: True if Qdrant is running or was started, False otherwise
        """
        print("\n🔍 Checking Qdrant service...")
        
        if self.check_qdrant_running():
            print("✓ Qdrant is already running on port 6333")
            return True
        
        print("⚠ Qdrant is not running on port 6333")
        
        if not self.docker_exists():
            print("✗ Docker is not installed")
            print("\n📥 Please download and install Docker from: https://www.docker.com/products/docker-desktop")
            return False
        
        if not self.docker_engine_running():
            print("✗ Docker engine is not running")
            print("\n📥 Please start Docker Desktop or Docker daemon before running this program")
            return False
        
        if self.start_qdrant():
            print("✓ Qdrant container started successfully")
            return True
        else:
            print("✗ Failed to start Qdrant container")
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
        
        # Step 4: Setup Qdrant
        if not self.setup_qdrant():
            print("\n✗ Error: Qdrant setup failed")
            return False
        
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
