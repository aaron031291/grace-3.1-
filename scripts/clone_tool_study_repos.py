#!/usr/bin/env python3
"""
Clone and set up repositories for studying testing/debugging tools code.
This helps you understand how proven tools work to build your own.
"""

import subprocess
import os
import sys
from pathlib import Path
from typing import Dict, List

# Fix encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Repository information
REPOSITORIES = {
    "semgrep": {
        "url": "https://github.com/semgrep/semgrep.git",
        "description": "Pattern-based static analysis (fast, easy to understand)",
        "key_files": [
            "src/engine/Match_rules.ml",
            "src/matching/Generic_vs_generic.ml",
            "libs/ast_generic/AST_generic.ml",
        ],
        "language": "OCaml (core) + Python (CLI)",
        "study_order": 2,  # Second (after Bandit)
    },
    "codeql": {
        "url": "https://github.com/github/codeql.git",
        "description": "Semantic code analysis (data flow, taint tracking)",
        "key_files": [
            "ql/queries/security/cwe/SqlInjection.ql",
            "ql/<language>/src/DataFlow.qll",
            "ql/<language>/src/Ast.qll",
        ],
        "language": "QL (query language)",
        "study_order": 4,  # Fourth (advanced)
    },
    "pytest": {
        "url": "https://github.com/pytest-dev/pytest.git",
        "description": "Test framework with AST transformation",
        "key_files": [
            "src/_pytest/assertion/rewrite.py",
            "src/_pytest/assertion/util.py",
            "src/_pytest/plugin.py",
        ],
        "language": "Python",
        "study_order": 3,  # Third
    },
    "bandit": {
        "url": "https://github.com/PyCQA/bandit.git",
        "description": "Python security scanner (simplest to understand)",
        "key_files": [
            "bandit/core/visitor.py",
            "bandit/core/tester.py",
            "bandit/plugins/blacklist_calls.py",
        ],
        "language": "Python",
        "study_order": 1,  # First (easiest)
    },
    "sonarqube": {
        "url": "https://github.com/SonarSource/sonarqube.git",
        "description": "Code quality platform (full-featured, complex)",
        "key_files": [
            "server/sonar-core/src/main/java/org/sonar/core/issue/",
            "sonar-plugin-api/src/main/java/org/sonar/api/",
        ],
        "language": "Java + JavaScript",
        "study_order": 5,  # Fifth (most complex)
    },
}

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
RESET = '\033[0m'


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}{text.center(70)}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")


def print_success(text: str):
    """Print success message."""
    print(f"{GREEN}✓ {text}{RESET}")


def print_error(text: str):
    """Print error message."""
    print(f"{RED}✗ {text}{RESET}")


def print_info(text: str):
    """Print info message."""
    print(f"{CYAN}i {text}{RESET}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{YELLOW}⚠ {text}{RESET}")


def clone_repository(name: str, info: Dict) -> bool:
    """Clone a repository."""
    url = info["url"]
    description = info["description"]
    
    print_info(f"Cloning {name}...")
    print(f"  Description: {description}")
    print(f"  URL: {url}")
    
    try:
        result = subprocess.run(
            ["git", "clone", url, name],
            capture_output=True,
            text=True,
            check=False,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            print_success(f"Cloned {name} successfully")
            return True
        else:
            if "already exists" in result.stderr or os.path.exists(name):
                print_warning(f"{name} already exists, skipping clone")
                return True
            else:
                print_error(f"Failed to clone {name}: {result.stderr}")
                return False
    
    except subprocess.TimeoutExpired:
        print_error(f"Timeout cloning {name}")
        return False
    except Exception as e:
        print_error(f"Error cloning {name}: {e}")
        return False


def create_study_guide(repos_dir: Path, repositories: Dict):
    """Create a study guide file."""
    guide_path = repos_dir / "STUDY_GUIDE.md"
    
    with open(guide_path, "w") as f:
        f.write("# Tool Code Study Guide\n\n")
        f.write("This guide helps you study the cloned repositories.\n\n")
        f.write("## Recommended Study Order\n\n")
        f.write("Study these tools in order for best learning:\n\n")
        
        # Sort by study_order
        sorted_repos = sorted(
            repositories.items(),
            key=lambda x: x[1].get("study_order", 999)
        )
        
        for i, (name, info) in enumerate(sorted_repos, 1):
            f.write(f"### {i}. {name.upper()}\n\n")
            f.write(f"- **Description**: {info['description']}\n")
            f.write(f"- **Language**: {info['language']}\n")
            f.write(f"- **Key Files to Study**:\n")
            for key_file in info.get("key_files", []):
                f.write(f"  - `{key_file}`\n")
            f.write(f"\n")
            f.write(f"**How to explore**:\n")
            f.write(f"```bash\n")
            f.write(f"cd {name}\n")
            f.write(f"# Read the README first\n")
            f.write(f"cat README.md | less\n")
            f.write(f"# Then explore the key files listed above\n")
            f.write(f"```\n\n")
        
        f.write("## Learning Path\n\n")
        f.write("1. **Bandit** - Start here (simplest AST visitor pattern)\n")
        f.write("2. **Semgrep** - Pattern matching (more complex)\n")
        f.write("3. **pytest** - AST transformation (advanced)\n")
        f.write("4. **CodeQL** - Semantic analysis (expert level)\n")
        f.write("5. **SonarQube** - Full platform (most complex)\n\n")
        
        f.write("## Tips\n\n")
        f.write("- Start with the README in each repository\n")
        f.write("- Focus on one key file at a time\n")
        f.write("- Use code search (ripgrep, grep) to find related code\n")
        f.write("- Read tests - they show how the code works\n")
        f.write("- Build small prototypes based on what you learn\n\n")
    
    print_success(f"Created study guide: {guide_path}")


def main():
    """Main function."""
    print_header("Tool Code Study Repository Setup")
    
    print("This script will clone open-source testing/debugging tools")
    print("so you can study their code and build your own.\n")
    
    # Create study directory
    script_dir = Path(__file__).parent.parent
    repos_dir = script_dir / "tool-study"
    repos_dir.mkdir(exist_ok=True)
    
    print(f"Repositories will be cloned to: {repos_dir}\n")
    
    # Show what will be cloned
    print("Repositories to clone:")
    sorted_repos = sorted(
        REPOSITORIES.items(),
        key=lambda x: x[1].get("study_order", 999)
    )
    
    for name, info in sorted_repos:
        print(f"  {info.get('study_order', '?')}. {name}")
        print(f"     {info['description']}")
    
    print()
    # Check if running non-interactively (no stdin or from script)
    auto_approve = '--yes' in sys.argv or '--y' in sys.argv or not sys.stdin.isatty()
    if auto_approve:
        print("Auto-approving (non-interactive mode)...")
        response = 'y'
    else:
        response = input(f"Proceed with cloning? (y/n): ").strip().lower()
    
    if response != 'y':
        print("Cancelled.")
        return
    
    # Change to repos directory
    os.chdir(repos_dir)
    
    # Clone repositories
    results = []
    for name, info in sorted_repos:
        success = clone_repository(name, info)
        results.append((name, success))
    
    # Summary
    print_header("Clone Summary")
    
    success_count = sum(1 for _, success in results if success)
    total_count = len(results)
    
    for name, success in results:
        status = f"{GREEN}✓{RESET}" if success else f"{RED}✗{RESET}"
        print(f"  {status} {name}")
    
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"Cloned: {success_count}/{total_count} repositories")
    
    if success_count == total_count:
        print_success("\nAll repositories cloned successfully!")
        print(f"\nNext steps:")
        print(f"  1. cd {repos_dir}")
        print(f"  2. Start with: cd bandit (simplest)")
        print(f"  3. Read: cat README.md")
        print(f"  4. Explore: bandit/core/visitor.py")
        
        # Create study guide
        create_study_guide(repos_dir, REPOSITORIES)
        
    else:
        print_warning(f"\n{total_count - success_count} repository(ies) failed to clone.")
        print("Check the errors above and try again if needed.")
    
    print()


if __name__ == "__main__":
    main()
