#!/usr/bin/env python3
"""
Multi-OS Migration Script
=========================

Automatically migrates OS checks and path operations to use OS adapter.

Usage:
    python scripts/migrate_to_multi_os.py [--dry-run] [--file <path>]
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict
import argparse


class OSMigrationTool:
    """Tool to migrate OS checks and path operations."""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.changes_made = []
        self.errors = []
        
        # Patterns to find and replace
        self.patterns = [
            # OS checks
            (r'sys\.platform\s*==\s*["\']win32["\']', 'OS.is_windows'),
            (r'sys\.platform\s*==\s*["\']linux["\']', 'OS.is_linux'),
            (r'sys\.platform\s*==\s*["\']darwin["\']', 'OS.is_macos'),
            (r'platform\.system\(\)\s*==\s*["\']Windows["\']', 'OS.is_windows'),
            (r'platform\.system\(\)\s*==\s*["\']Linux["\']', 'OS.is_linux'),
            (r'platform\.system\(\)\s*==\s*["\']Darwin["\']', 'OS.is_macos'),
            (r'os\.name\s*==\s*["\']nt["\']', 'OS.is_windows'),
            (r'os\.name\s*==\s*["\']posix["\']', 'OS.is_unix'),
        ]
        
        # Path operations (more complex, need context)
        self.path_patterns = [
            (r'os\.path\.join\(([^)]+)\)', self._replace_os_path_join),
            (r'os\.path\.dirname\(([^)]+)\)', self._replace_os_path_dirname),
            (r'os\.path\.abspath\(([^)]+)\)', self._replace_os_path_abspath),
        ]
    
    def _replace_os_path_join(self, match) -> str:
        """Replace os.path.join() with Path operations."""
        args = match.group(1)
        # Simple case: os.path.join("a", "b", "c") -> Path("a") / "b" / "c"
        parts = [p.strip().strip('"\'') for p in args.split(',')]
        if all(p.startswith('"') or p.startswith("'") for p in parts):
            # All string literals
            path_parts = ' / '.join(parts)
            return f'Path({path_parts})'
        else:
            # Complex case, use paths adapter
            return f'paths.join({args})'
    
    def _replace_os_path_dirname(self, match) -> str:
        """Replace os.path.dirname() with Path operations."""
        arg = match.group(1).strip()
        if arg == '__file__':
            return 'Path(__file__).parent'
        elif arg.startswith('"') or arg.startswith("'"):
            return f'Path({arg}).parent'
        else:
            return f'Path({arg}).parent'
    
    def _replace_os_path_abspath(self, match) -> str:
        """Replace os.path.abspath() with Path operations."""
        arg = match.group(1).strip()
        if arg.startswith('"') or arg.startswith("'"):
            return f'Path({arg}).resolve()'
        else:
            return f'paths.resolve({arg})'
    
    def find_os_checks(self, content: str) -> List[Tuple[int, str, str]]:
        """Find all OS checks in content."""
        issues = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            for pattern, replacement in self.patterns:
                if re.search(pattern, line):
                    issues.append((i, line.strip(), replacement))
        
        return issues
    
    def find_path_operations(self, content: str) -> List[Tuple[int, str, str]]:
        """Find all os.path operations in content."""
        issues = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            for pattern, replacer in self.path_patterns:
                if re.search(pattern, line):
                    if callable(replacer):
                        new_line = re.sub(pattern, replacer, line)
                        issues.append((i, line.strip(), new_line.strip()))
                    else:
                        issues.append((i, line.strip(), replacer))
        
        return issues
    
    def check_imports(self, content: str) -> Tuple[bool, List[str]]:
        """Check if OS adapter is imported."""
        has_os_adapter = 'from backend.utils.os_adapter import' in content
        has_pathlib = 'from pathlib import Path' in content
        
        missing = []
        if not has_os_adapter and ('OS.is_windows' in content or 'OS.is_linux' in content):
            missing.append('from backend.utils.os_adapter import OS, paths')
        if not has_pathlib and 'Path(' in content:
            missing.append('from pathlib import Path')
        
        return len(missing) == 0, missing
    
    def migrate_file(self, file_path: Path) -> Dict:
        """Migrate a single file."""
        result = {
            'file': str(file_path),
            'os_checks': [],
            'path_operations': [],
            'imports_needed': [],
            'modified': False,
            'error': None
        }
        
        try:
            content = file_path.read_text(encoding='utf-8')
            original_content = content
            
            # Find issues
            os_checks = self.find_os_checks(content)
            path_ops = self.find_path_operations(content)
            has_imports, missing_imports = self.check_imports(content)
            
            result['os_checks'] = os_checks
            result['path_operations'] = path_ops
            result['imports_needed'] = missing_imports
            
            if not os_checks and not path_ops and has_imports:
                return result  # No changes needed
            
            # Apply migrations
            if os_checks or path_ops:
                # Add imports if needed
                if missing_imports:
                    # Find first import line
                    import_line = 0
                    for i, line in enumerate(content.split('\n')):
                        if line.startswith('import ') or line.startswith('from '):
                            import_line = i
                            break
                    
                    if import_line > 0:
                        lines = content.split('\n')
                        lines.insert(import_line + 1, '\n'.join(missing_imports))
                        content = '\n'.join(lines)
                
                # Replace OS checks
                for pattern, replacement in self.patterns:
                    content = re.sub(pattern, replacement, content)
                
                # Replace path operations
                for pattern, replacer in self.path_patterns:
                    if callable(replacer):
                        content = re.sub(pattern, replacer, content)
                
                result['modified'] = True
                
                if not self.dry_run:
                    file_path.write_text(content, encoding='utf-8')
                    self.changes_made.append(str(file_path))
                else:
                    print(f"[DRY RUN] Would modify: {file_path}")
        
        except Exception as e:
            result['error'] = str(e)
            self.errors.append((str(file_path), str(e)))
        
        return result
    
    def scan_directory(self, directory: Path) -> List[Dict]:
        """Scan directory for Python files."""
        results = []
        
        # Find all Python files
        for py_file in directory.rglob('*.py'):
            # Skip certain directories
            if any(skip in str(py_file) for skip in ['__pycache__', '.git', 'venv', 'node_modules']):
                continue
            
            result = self.migrate_file(py_file)
            if result['modified'] or result['os_checks'] or result['path_operations']:
                results.append(result)
        
        return results
    
    def print_report(self, results: List[Dict]):
        """Print migration report."""
        print("\n" + "=" * 70)
        print("MULTI-OS MIGRATION REPORT")
        print("=" * 70)
        
        total_files = len(results)
        modified_files = sum(1 for r in results if r['modified'])
        total_os_checks = sum(len(r['os_checks']) for r in results)
        total_path_ops = sum(len(r['path_operations']) for r in results)
        
        print(f"\nFiles scanned: {total_files}")
        print(f"Files modified: {modified_files}")
        print(f"OS checks found: {total_os_checks}")
        print(f"Path operations found: {total_path_ops}")
        
        if self.errors:
            print(f"\nErrors: {len(self.errors)}")
            for file, error in self.errors:
                print(f"  {file}: {error}")
        
        if results:
            print("\nDetailed Results:")
            for result in results:
                if result['os_checks'] or result['path_operations']:
                    print(f"\n  {result['file']}:")
                    if result['os_checks']:
                        print(f"    OS checks: {len(result['os_checks'])}")
                        for line_num, old, new in result['os_checks'][:3]:
                            print(f"      Line {line_num}: {old[:60]}...")
                    if result['path_operations']:
                        print(f"    Path operations: {len(result['path_operations'])}")
                        for line_num, old, new in result['path_operations'][:3]:
                            print(f"      Line {line_num}: {old[:60]}...")
                    if result['imports_needed']:
                        print(f"    Imports needed: {', '.join(result['imports_needed'])}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Migrate codebase to multi-OS')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be changed')
    parser.add_argument('--file', type=str, help='Migrate specific file')
    parser.add_argument('--directory', type=str, default='backend', help='Directory to scan')
    
    args = parser.parse_args()
    
    tool = OSMigrationTool(dry_run=args.dry_run)
    
    if args.file:
        # Migrate single file
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"Error: File not found: {file_path}")
            sys.exit(1)
        
        result = tool.migrate_file(file_path)
        tool.print_report([result])
    else:
        # Scan directory
        directory = Path(args.directory)
        if not directory.exists():
            print(f"Error: Directory not found: {directory}")
            sys.exit(1)
        
        results = tool.scan_directory(directory)
        tool.print_report(results)
    
    if tool.errors:
        sys.exit(1)


if __name__ == '__main__':
    main()
