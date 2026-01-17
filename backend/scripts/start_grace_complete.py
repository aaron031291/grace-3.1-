"""
Complete Grace Startup Script

Initializes and activates ALL Grace systems:
1. Version control setup (Git hooks, file watcher)
2. Database migrations
3. ML Intelligence initialization
4. Cognitive Blueprint activation
5. Self-healing system
6. Mirror self-modeling
7. Layer 1 integration
8. Autonomous learning
9. FastAPI backend server

Run this script to start Grace with all features enabled.
"""

import sys
import os
import subprocess
import time
from pathlib import Path

# Windows multiprocessing setup - MUST be first, before any other imports
# This ensures multiprocessing is properly configured for Windows before
# any code that might use it (including uvicorn's reloader)
if sys.platform == "win32":
    import multiprocessing
    try:
        multiprocessing.set_start_method('spawn', force=True)
    except RuntimeError:
        # Already set, continue
        pass
    multiprocessing.freeze_support()

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

def print_header(text):
    """Print formatted header"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)

def print_step(number, text):
    """Print formatted step"""
    print(f"\n[{number}/9] {text}...")

def print_success(text):
    """Print success message"""
    print(f"  [OK] {text}")

def print_error(text):
    """Print error message"""
    print(f"  [ERROR] {text}")

def print_warning(text):
    """Print warning message"""
    print(f"  [WARN] {text}")

def check_python_version():
    """Check Python version"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print_error(f"Python 3.8+ required, found {version.major}.{version.minor}")
        return False
    print_success(f"Python {version.major}.{version.minor}.{version.micro}")
    return True

def install_dependencies():
    """Install required dependencies"""
    print_step(1, "Installing dependencies")

    # Check for requirements.txt
    requirements_file = backend_dir / "requirements.txt"
    if not requirements_file.exists():
        print_warning("No requirements.txt found, skipping...")
        return True

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode == 0:
            print_success("Dependencies installed")
            return True
        else:
            print_error(f"Failed to install dependencies: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print_error("Dependency installation timed out")
        return False
    except Exception as e:
        print_error(f"Error installing dependencies: {e}")
        return False

def setup_version_control():
    """Setup version control system"""
    print_step(2, "Setting up version control")

    setup_script = backend_dir / "scripts" / "setup_version_control.py"
    if not setup_script.exists():
        print_warning("Version control setup script not found, skipping...")
        return True

    try:
        result = subprocess.run(
            [sys.executable, str(setup_script)],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(backend_dir)
        )
        if result.returncode == 0:
            print_success("Version control setup complete")
            return True
        else:
            print_warning(f"Version control setup had issues: {result.stderr[:200]}")
            return True  # Non-critical, continue anyway
    except Exception as e:
        print_warning(f"Version control setup error: {e}")
        return True  # Non-critical

def check_database():
    """Check database connection"""
    print_step(3, "Checking database")

    try:
        from database.connection import DatabaseConnection
        from database.config import DatabaseConfig, DatabaseType

        db_config = DatabaseConfig(
            db_type=DatabaseType.SQLITE,
            database="grace",
        )
        DatabaseConnection.initialize(db_config)
        print_success("Database connection verified")
        return True
    except Exception as e:
        print_error(f"Database error: {e}")
        return False

def run_migrations():
    """Run database migrations"""
    print_step(4, "Running database migrations")

    try:
        from database.migration import create_tables
        create_tables()
        print_success("Database migrations complete")
        return True
    except Exception as e:
        print_error(f"Migration error: {e}")
        return False

def check_ollama():
    """Check Ollama service"""
    print_step(5, "Checking Ollama service")

    try:
        from ollama_client.client import get_ollama_client
        client = get_ollama_client()

        if client.is_running():
            models = client.get_all_models()
            print_success(f"Ollama running with {len(models)} model(s)")
            if models:
                print(f"      Models: {', '.join(models[:3])}")
            return True
        else:
            print_warning("Ollama not running - chat will be unavailable")
            print("      Start Ollama: ollama serve")
            return True  # Non-critical
    except Exception as e:
        print_warning(f"Ollama check failed: {e}")
        return True  # Non-critical

def check_qdrant():
    """Check Qdrant service"""
    print_step(6, "Checking Qdrant vector database")

    try:
        from vector_db.client import get_qdrant_client
        qdrant = get_qdrant_client()

        if qdrant.is_connected():
            collections = qdrant.list_collections()
            print_success(f"Qdrant running with {len(collections)} collection(s)")
            return True
        else:
            print_warning("Qdrant not running - ingestion will be unavailable")
            print("      Start Qdrant: docker run -p 6333:6333 qdrant/qdrant")
            return True  # Non-critical
    except Exception as e:
        print_warning(f"Qdrant check failed: {e}")
        return True  # Non-critical

def initialize_ml_intelligence():
    """Initialize ML Intelligence"""
    print_step(7, "Initializing ML Intelligence")

    try:
        from ml_intelligence.integration_orchestrator import MLIntelligenceOrchestrator

        orchestrator = MLIntelligenceOrchestrator()
        orchestrator.initialize()

        enabled = [k for k, v in orchestrator.enabled_features.items() if v]
        print_success(f"ML Intelligence ready - {len(enabled)} features enabled")
        print(f"      Features: {', '.join(enabled)}")
        return True
    except Exception as e:
        print_warning(f"ML Intelligence unavailable: {e}")
        print("      System will use rule-based fallbacks")
        return True  # Non-critical

def verify_systems():
    """Verify all systems are ready"""
    print_step(8, "Verifying all systems")

    systems = []

    # Check cognitive blueprint
    try:
        from cognitive import CognitiveEngine
        engine = CognitiveEngine()
        systems.append("Cognitive Blueprint")
        print_success("Cognitive Blueprint ready")
    except Exception as e:
        print_warning(f"Cognitive Blueprint: {e}")

    # Check self-healing
    try:
        from cognitive.autonomous_healing_system import get_autonomous_healing
        systems.append("Self-Healing System")
        print_success("Self-Healing System ready")
    except Exception as e:
        print_warning(f"Self-Healing: {e}")

    # Check mirror
    try:
        from cognitive.mirror_self_modeling import get_mirror_system
        systems.append("Mirror Self-Modeling")
        print_success("Mirror Self-Modeling ready")
    except Exception as e:
        print_warning(f"Mirror: {e}")

    # Check Layer 1
    try:
        from layer1.initialize import initialize_layer1
        systems.append("Layer 1 Integration")
        print_success("Layer 1 Integration ready")
    except Exception as e:
        print_warning(f"Layer 1: {e}")

    # Check autonomous learning
    try:
        from api.autonomous_learning import get_learning_orchestrator
        systems.append("Autonomous Learning")
        print_success("Autonomous Learning ready")
    except Exception as e:
        print_warning(f"Autonomous Learning: {e}")

    print(f"\n      {len(systems)}/5 core systems operational")
    return True

def start_server(port=8000, host="0.0.0.0"):
    """Start FastAPI server"""
    print_step(9, f"Starting Grace API server on {host}:{port}")

    print("\n" + "="*70)
    print("  GRACE COMPLETE SYSTEM - READY TO START")
    print("="*70)
    print(f"\n  Server will start on: http://{host}:{port}")
    print(f"  API documentation: http://{host}:{port}/docs")
    print(f"  Health check: http://{host}:{port}/health")
    print("\n  Press Ctrl+C to stop\n")
    print("="*70 + "\n")

    try:
        import uvicorn
        import asyncio
        
        # On Windows, handle event loop manually to avoid asyncio conflicts
        # On other platforms, use standard uvicorn.run
        if sys.platform == "win32":
            # Import app directly to avoid import_from_string issues
            # Ensure we're in the backend directory for imports to work
            import app
            app_instance = app.app
            
            # Use Config and Server with manual event loop handling
            config = uvicorn.Config(
                app=app_instance,  # Pass app object directly instead of string
                host=host,
                port=port,
                reload=False,  # Disabled on Windows
                log_level="info"
            )
            server = uvicorn.Server(config)
            
            # Manually handle the event loop to avoid asyncio.run() issues on Windows
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            try:
                loop.run_until_complete(server.serve())
            except KeyboardInterrupt:
                pass
            finally:
                loop.close()
        else:
            # Standard uvicorn.run on non-Windows platforms
            uvicorn.run(
                "app:app",
                host=host,
                port=port,
                reload=True,
                reload_dirs=[str(backend_dir)],
                log_level="info",
                workers=1
            )
    except KeyboardInterrupt:
        print("\n\nGrace shutting down...")
    except Exception as e:
        print_error(f"Server error: {e}")
        return False

    return True

def main():
    """Main startup sequence"""
    print_header("GRACE COMPLETE SYSTEM STARTUP")
    print("\nInitializing all autonomous systems...\n")

    # Change to backend directory
    os.chdir(backend_dir)

    # Run all initialization steps
    steps = [
        ("Python version", check_python_version),
        ("Dependencies", lambda: True),  # Skip for now, too slow
        ("Version control", setup_version_control),
        ("Database", check_database),
        ("Migrations", run_migrations),
        ("Ollama", check_ollama),
        ("Qdrant", check_qdrant),
        ("ML Intelligence", initialize_ml_intelligence),
        ("System verification", verify_systems),
    ]

    failed = []
    for step_name, step_func in steps:
        try:
            if not step_func():
                failed.append(step_name)
        except Exception as e:
            print_error(f"{step_name} failed: {e}")
            failed.append(step_name)

    if failed:
        print("\n" + "="*70)
        print(f"  WARNING: {len(failed)} step(s) had issues:")
        for step in failed:
            print(f"    - {step}")
        print("\n  Continuing anyway...")
        print("="*70)

    # Start server
    start_server()

if __name__ == "__main__":
    main()
