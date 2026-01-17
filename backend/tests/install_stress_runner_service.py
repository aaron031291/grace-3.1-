"""
Install Continuous Stress Test Runner as a System Service

This script installs the stress test runner to run on boot.
"""

import sys
import os
import platform
from pathlib import Path

def install_windows_service():
    """Install as Windows service using NSSM (Non-Sucking Service Manager)."""
    project_root = Path(__file__).parent.parent.parent
    script_path = project_root / "backend" / "tests" / "continuous_stress_runner.py"
    python_exe = sys.executable
    
    print("=" * 80)
    print("Installing Continuous Stress Test Runner as Windows Service")
    print("=" * 80)
    print(f"Project root: {project_root}")
    print(f"Script: {script_path}")
    print(f"Python: {python_exe}")
    print()
    
    # Check if NSSM is available
    import subprocess
    try:
        result = subprocess.run(["nssm", "version"], capture_output=True, text=True)
        if result.returncode != 0:
            print("ERROR: NSSM (Non-Sucking Service Manager) not found!")
            print("Please install NSSM from: https://nssm.cc/download")
            print()
            print("Or run manually with:")
            print(f'  python "{script_path}"')
            return False
    except FileNotFoundError:
        print("ERROR: NSSM (Non-Sucking Service Manager) not found!")
        print("Please install NSSM from: https://nssm.cc/download")
        print()
        print("Or run manually with:")
        print(f'  python "{script_path}"')
        return False
    
    # Install service
    service_name = "GraceStressTestRunner"
    
    print(f"Installing service: {service_name}")
    
    commands = [
        ["nssm", "install", service_name, python_exe, str(script_path)],
        ["nssm", "set", service_name, "AppDirectory", str(project_root)],
        ["nssm", "set", service_name, "DisplayName", "Grace Continuous Stress Test Runner"],
        ["nssm", "set", service_name, "Description", "Runs aggressive stress tests every 30 minutes to find breaking points"],
        ["nssm", "set", service_name, "Start", "SERVICE_AUTO_START"],
        ["nssm", "set", service_name, "AppStdout", str(project_root / "backend" / "logs" / "stress_runner_service.log")],
        ["nssm", "set", service_name, "AppStderr", str(project_root / "backend" / "logs" / "stress_runner_service_error.log")],
    ]
    
    for cmd in commands:
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"ERROR: {result.stderr}")
            return False
    
    print()
    print("Service installed successfully!")
    print()
    print("To start the service:")
    print(f"  nssm start {service_name}")
    print()
    print("To stop the service:")
    print(f"  nssm stop {service_name}")
    print()
    print("To remove the service:")
    print(f"  nssm remove {service_name} confirm")
    
    return True


def install_linux_service():
    """Install as Linux systemd service."""
    project_root = Path(__file__).parent.parent.parent
    script_path = project_root / "backend" / "tests" / "continuous_stress_runner.py"
    python_exe = sys.executable
    
    print("=" * 80)
    print("Installing Continuous Stress Test Runner as Linux systemd Service")
    print("=" * 80)
    print(f"Project root: {project_root}")
    print(f"Script: {script_path}")
    print(f"Python: {python_exe}")
    print()
    
    service_content = f"""[Unit]
Description=Grace Continuous Stress Test Runner
After=network.target

[Service]
Type=simple
User={os.getenv('USER', 'root')}
WorkingDirectory={project_root}
ExecStart={python_exe} {script_path}
Restart=always
RestartSec=10
StandardOutput=append:{project_root}/backend/logs/stress_runner_service.log
StandardError=append:{project_root}/backend/logs/stress_runner_service_error.log

[Install]
WantedBy=multi-user.target
"""
    
    service_file = Path("/etc/systemd/system/grace-stress-runner.service")
    
    print("Service file content:")
    print(service_content)
    print()
    
    if os.geteuid() != 0:
        print("ERROR: Must run as root to install systemd service")
        print()
        print("Please run:")
        print(f"  sudo python {__file__}")
        print()
        print("Or create the service file manually:")
        print(f"  sudo nano {service_file}")
        print("Then copy the service content above")
        print()
        print("Then enable and start:")
        print("  sudo systemctl daemon-reload")
        print("  sudo systemctl enable grace-stress-runner")
        print("  sudo systemctl start grace-stress-runner")
        return False
    
    # Write service file
    try:
        service_file.write_text(service_content)
        print(f"Service file written to: {service_file}")
    except Exception as e:
        print(f"ERROR: Could not write service file: {e}")
        return False
    
    # Reload systemd and enable service
    import subprocess
    commands = [
        ["systemctl", "daemon-reload"],
        ["systemctl", "enable", "grace-stress-runner"],
        ["systemctl", "start", "grace-stress-runner"],
    ]
    
    for cmd in commands:
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"ERROR: {result.stderr}")
            return False
    
    print()
    print("Service installed and started successfully!")
    print()
    print("To check status:")
    print("  sudo systemctl status grace-stress-runner")
    print()
    print("To stop the service:")
    print("  sudo systemctl stop grace-stress-runner")
    print()
    print("To disable the service:")
    print("  sudo systemctl disable grace-stress-runner")
    
    return True


def main():
    """Main installation function."""
    system = platform.system()
    
    if system == "Windows":
        install_windows_service()
    elif system == "Linux":
        install_linux_service()
    else:
        print(f"Automatic service installation not supported for {system}")
        print()
        print("Please run manually:")
        project_root = Path(__file__).parent.parent.parent
        script_path = project_root / "backend" / "tests" / "continuous_stress_runner.py"
        print(f"  python {script_path}")


if __name__ == "__main__":
    main()
