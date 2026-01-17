#!/usr/bin/env python3
"""
Create Desktop Shortcut for Grace Launcher
===========================================
Creates a desktop shortcut that launches Grace.

Run this script once to create the shortcut on your desktop.
"""

import os
import sys
from pathlib import Path
import win32com.client  # pywin32

def create_shortcut():
    """Create desktop shortcut for Grace launcher."""
    
    # Get paths
    script_dir = Path(__file__).parent.resolve()
    launcher_bat = script_dir / "launch_grace.bat"
    desktop = Path.home() / "Desktop"
    
    # Check if launcher_bat exists
    if not launcher_bat.exists():
        print(f"Error: {launcher_bat} not found!")
        return False
    
    # Create shortcut
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut_path = desktop / "Grace.lnk"
    shortcut = shell.CreateShortCut(str(shortcut_path))
    
    # Set shortcut properties
    shortcut.Targetpath = str(launcher_bat)
    shortcut.WorkingDirectory = str(script_dir)
    shortcut.Description = "Launch Grace - AI Knowledge System"
    shortcut.IconLocation = "C:\\Windows\\System32\\shell32.dll,137"  # Folder icon
    
    # Save shortcut
    shortcut.save()
    
    print(f"✓ Desktop shortcut created: {shortcut_path}")
    print(f"  Target: {launcher_bat}")
    print(f"  Working Directory: {script_dir}")
    print("")
    print("You can now double-click 'Grace' on your desktop to launch!")
    
    return True

if __name__ == "__main__":
    try:
        create_shortcut()
    except ImportError:
        print("Error: pywin32 is required to create shortcuts.")
        print("Install it with: pip install pywin32")
        print("")
        print("Alternatively, manually create a shortcut:")
        print(f"  1. Right-click on your desktop")
        print(f"  2. New > Shortcut")
        print(f"  3. Target: {Path(__file__).parent / 'launch_grace.bat'}")
        print(f"  4. Name it 'Grace'")
        sys.exit(1)
    except Exception as e:
        print(f"Error creating shortcut: {e}")
        sys.exit(1)
