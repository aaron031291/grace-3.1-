"""
Healing Script Generator - Creates and executes scripts/patches for fixes

Generates Python scripts and patches that the self-healing system can
execute to fix code issues autonomously.
"""

import os
import sys
import subprocess
import tempfile
import logging
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from cognitive.healing_knowledge_base import (
    HealingKnowledgeBase,
    IssueType,
    CodePatch,
    get_healing_knowledge_base
)
from genesis.genesis_key_service import get_genesis_service
from models.genesis_key_models import GenesisKeyType

logger = logging.getLogger(__name__)


class HealingScriptGenerator:
    """
    Generates and executes scripts/patches for autonomous healing.
    """
    
    def __init__(self, repo_path: Optional[Path] = None):
        self.repo_path = repo_path or Path(__file__).parent.parent.parent
        self.knowledge_base = get_healing_knowledge_base()
        self.genesis_service = get_genesis_service()
        self.scripts_dir = self.repo_path / ".healing_scripts"
        self.scripts_dir.mkdir(exist_ok=True)
    
    def generate_fix_script(
        self,
        issues: List[Dict[str, Any]],
        script_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a Python script to fix multiple issues.
        
        Args:
            issues: List of issue dictionaries with type, file_path, error_message, etc.
            script_name: Optional name for the script
        
        Returns:
            Dict with script_path and execution info
        """
        if not script_name:
            script_name = f"healing_script_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.py"
        
        script_path = self.scripts_dir / script_name
        
        # Group issues by type
        issues_by_type = {}
        for issue in issues:
            issue_type_str = issue.get("issue_type", "unknown")
            if issue_type_str not in issues_by_type:
                issues_by_type[issue_type_str] = []
            issues_by_type[issue_type_str].append(issue)
        
        # Generate script content
        script_parts = [
            "#!/usr/bin/env python3",
            '"""',
            "Auto-generated healing script",
            f"Generated: {datetime.utcnow().isoformat()}",
            f"Fixes {len(issues)} issue(s)",
            '"""',
            "",
            "import sys",
            "import logging",
            "from pathlib import Path",
            "",
            "# Setup logging",
            "logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')",
            "logger = logging.getLogger(__name__)",
            "",
            "# Add backend to path",
            "repo_root = Path(__file__).parent.parent",
            "backend_path = repo_root / 'backend'",
            "if backend_path.exists():",
            "    sys.path.insert(0, str(backend_path))",
            "",
            "def main():",
            "    fixes_applied = 0",
            "    errors = []",
            ""
        ]
        
        # Generate fix code for each issue type
        for issue_type, type_issues in issues_by_type.items():
            script_parts.append(f"    # Fix {issue_type} issues ({len(type_issues)} issues)")
            
            # THREAD ISSUES: Handle all thread-related issue types
            if issue_type == "sqlalchemy_table_redefinition":
                script_parts.extend(self._generate_sqlalchemy_fix(type_issues))
            elif issue_type == "missing_import":
                script_parts.extend(self._generate_import_fix(type_issues))
            elif issue_type == "syntax_error" or issue_type == "indentation_error" or issue_type == "potential_indentation_error":
                script_parts.extend(self._generate_syntax_fix(type_issues))
            elif issue_type == "database_datatype_mismatch" or issue_type == "database_schema_mismatch":
                script_parts.extend(self._generate_database_fix(type_issues))
            elif issue_type == "port_conflict":
                script_parts.extend(self._generate_port_conflict_fix(type_issues))
            elif issue_type == "missing_file" or issue_type == "missing_backend_file":
                script_parts.extend(self._generate_missing_file_fix(type_issues))
            elif issue_type == "missing_directory":
                script_parts.extend(self._generate_missing_directory_fix(type_issues))
            elif issue_type == "process_failure" or issue_type == "process_crash":
                script_parts.extend(self._generate_process_failure_fix(type_issues))
            else:
                script_parts.extend(self._generate_generic_fix(type_issues))
        
        script_parts.extend([
            "",
            "    logger.info(f'\\nApplied {fixes_applied} fix(es)')",
            "    if errors:",
            "        logger.warning(f'Errors: {len(errors)}')",
            "        for error in errors:",
            "            logger.error(f'  - {error}')",
            "",
            "    return fixes_applied > 0",
            "",
            "if __name__ == '__main__':",
            "    try:",
            "        success = main()",
            "        sys.exit(0 if success else 1)",
            "    except Exception as e:",
            "        logger.error(f'Script failed: {e}')",
            "        import traceback",
            "        traceback.print_exc()",
            "        sys.exit(1)"
        ])
        
        script_content = "\n".join(script_parts)
        
        # Write script
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        # Make executable (Unix)
        if os.name != 'nt':
            os.chmod(script_path, 0o755)
        
        logger.info(f"[HEALING-SCRIPT] Generated script: {script_path}")
        
        return {
            "script_path": str(script_path),
            "script_name": script_name,
            "issues_count": len(issues),
            "script_content": script_content
        }
    
    def _generate_sqlalchemy_fix(self, issues: List[Dict[str, Any]]) -> List[str]:
        """Generate code to fix SQLAlchemy table redefinition."""
        code = [
            "    import re",
            "    import logging",
            "    logging.basicConfig(level=logging.INFO)",
            "    logger = logging.getLogger(__name__)",
            "",
            "    for issue in ["
        ]
        
        # Add issue data - filter out empty file paths
        valid_issues = []
        for issue in issues:
            file_path = issue.get("file_path", "")
            
            # Handle empty file paths - use file_paths if available
            if not file_path and issue.get("file_paths"):
                file_path = issue["file_paths"][0] if issue["file_paths"] else ""
            
            if file_path:
                valid_issues.append(issue)
        
        # If no valid issues, try to find model files
        if not valid_issues:
            logger.warning("[HEALING-SCRIPT] No valid file paths, searching for model files")
            from pathlib import Path
            repo_path = self.repo_path
            model_files = [
                repo_path / "backend" / "models" / "database_models.py",
                repo_path / "backend" / "models" / "genesis_key_models.py"
            ]
            for model_file in model_files:
                if model_file.exists():
                    valid_issues.append({
                        "file_path": str(model_file),
                        "error_message": issues[0].get("error_message", "Table redefinition error") if issues else "Table redefinition error"
                    })
                    break
        
        # Add valid issues to script
        for issue in valid_issues:
            file_path = issue.get("file_path", "")
            error_msg = issue.get("error_message", "")
            
            # Normalize path
            if file_path:
                # Convert to forward slashes for Python
                file_path = file_path.replace('\\', '/')
                # Escape quotes and backslashes for string literal
                file_path_escaped = file_path.replace('\\', '\\\\').replace("'", "\\'")
                error_msg_escaped = error_msg.replace("'", "\\'").replace('"', '\\"')[:200]  # Truncate long errors
                code.append(f"        {{'file_path': r'{file_path_escaped}', 'error': '{error_msg_escaped}'}},")
        
        if not valid_issues:
            # Return early if no valid issues
            code.append("    ]:")
            code.append("        print('No valid file paths found')")
            code.append("        pass")
            code.append("")
            return code
        
        code.extend([
            "    ]:",
            "        try:",
            "            file_path_str = issue.get('file_path', '')",
            "            if not file_path_str:",
            "                continue",
            "            ",
            "            # Convert to Path object",
            "            file_path = Path(file_path_str)",
            "            ",
            "            # Try relative to repo root if absolute path doesn't exist",
            "            if not file_path.exists() and not file_path.is_absolute():",
            "                # Try relative to backend directory",
            "                backend_path = Path(__file__).parent.parent / 'backend' / file_path_str",
            "                if backend_path.exists():",
            "                    file_path = backend_path",
            "                else:",
            "                    # Try as-is from repo root",
            "                    repo_path = Path(__file__).parent.parent",
            "                    file_path = repo_path / file_path_str",
            "            ",
            "            if not file_path.exists():",
            "                logger.warning(f'Skipping non-existent file: {file_path}')",
            "                continue",
            "",
            "            with open(file_path, 'r', encoding='utf-8') as f:",
            "                lines = f.readlines()",
            "",
            "            original_lines = lines.copy()",
            "            modified = False",
            "",
            "            # Fix declarative base classes - add __table_args__ after __tablename__",
            "            i = 0",
            "            while i < len(lines):",
            "                line = lines[i]",
            "                ",
            "                # Check if this is a class definition with BaseModel or Base",
            "                if 'class ' in line and ('BaseModel' in line or 'Base' in line):",
            "                    # Look ahead for __tablename__",
            "                    j = i + 1",
            "                    found_tablename = False",
            "                    tablename_line_idx = None",
            "                    ",
            "                    while j < len(lines):",
            "                        next_line = lines[j]",
            "                        stripped = next_line.strip()",
            "                        ",
            "                        # Stop if we hit another class or function definition",
            "                        if stripped.startswith('class ') or (stripped.startswith('def ') and stripped.endswith(':')):",
            "                            break",
            "                        ",
            "                        # Check for __tablename__",
            "                        if '__tablename__' in stripped:",
            "                            found_tablename = True",
            "                            tablename_line_idx = j",
            "                        ",
            "                        # If we already have __table_args__, skip this class",
            "                        if '__table_args__' in stripped:",
            "                            found_tablename = False",
            "                            break",
            "                        ",
            "                        j += 1",
            "                    ",
            "                    # Add __table_args__ after __tablename__",
            "                    if found_tablename and tablename_line_idx is not None:",
            "                        # Find the indentation level",
            "                        tablename_line = lines[tablename_line_idx]",
            "                        indent = len(tablename_line) - len(tablename_line.lstrip())",
            "                        ",
            "                        # Check if next line already has __table_args__",
            "                        if tablename_line_idx + 1 < len(lines):",
            "                            next_line = lines[tablename_line_idx + 1].strip()",
            "                            if '__table_args__' in next_line:",
            "                                i = j",
            "                                continue",
            "                        ",
            "                        # Insert __table_args__ after __tablename__",
            "                        indent_str = ' ' * indent",
            "                        table_args_line = f\"{indent_str}__table_args__ = {{'extend_existing': True}}\\n\"",
            "                        lines.insert(tablename_line_idx + 1, table_args_line)",
            "                        modified = True",
            "                        print(f'Added __table_args__ to class in {file_path} at line {tablename_line_idx + 1}')",
            "                ",
            "                i += 1",
            "",
            "            # Also fix Table() constructors if any",
            "            content = ''.join(lines)",
            "            original_content = ''.join(original_lines)",
            "            ",
            "            # Fix Table() constructors (less common)",
            "            if 'Table(' in content:",
            "                new_content = re.sub(",
            "                    r'(Table\\s*\\([^)]*)(\\))',",
            "                    r'\\1, extend_existing=True\\2',",
            "                    content",
            "                )",
            "                if new_content != content:",
            "                    lines = new_content.splitlines(keepends=True)",
            "                    modified = True",
            "                    print(f'Fixed Table() constructors in {file_path}')",
            "",
            "            if modified:",
            "                with open(file_path, 'w', encoding='utf-8') as f:",
            "                    f.writelines(lines)",
            "                fixes_applied += 1",
            "                print(f'Fixed: {file_path}')",
            "        except Exception as e:",
            "            import traceback",
            "            errors.append(f'{file_path}: {str(e)}')",
            "            print(f'Error fixing {file_path}: {e}')",
            "            traceback.print_exc()",
            ""
        ])
        
        return code
    
    def _generate_import_fix(self, issues: List[Dict[str, Any]]) -> List[str]:
        """Generate code to fix missing imports."""
        code = [
            "    import re",
            "    for issue in ["
        ]
        
        for issue in issues:
            file_path = issue.get("file_path", "")
            error_msg = issue.get("error_message", "")
            # Try to extract module name from error
            match = re.search(r"No module named ['\"](\w+(?:\.\w+)*)['\"]", error_msg)
            module_name = match.group(1) if match else "unknown"
            
            # Normalize and escape path
            if file_path:
                file_path = file_path.replace('\\', '/').replace("'", "\\'")
            code.append(f"        {{'file_path': r'{file_path}', 'module': '{module_name}'}},")
        
        code.extend([
            "    ]:",
            "        try:",
            "            file_path = Path(issue['file_path'])",
            "            if not file_path.exists():",
            "                continue",
            "",
            "            with open(file_path, 'r', encoding='utf-8') as f:",
            "                lines = f.readlines()",
            "",
            "            module = issue['module']",
            "            # Generate import statement",
            "            if '.' in module:",
            "                parts = module.split('.')",
            "                import_stmt = f'from {'.'.join(parts[:-1])} import {parts[-1]}'",
            "            else:",
            "                import_stmt = f'import {module}'",
            "",
            "            # Check if already imported",
            "            if any(import_stmt in line for line in lines):",
            "                continue",
            "",
            "            # Find insertion point",
            "            insert_idx = 0",
            "            for i, line in enumerate(lines):",
            "                if line.strip().startswith('import ') or line.strip().startswith('from '):",
            "                    insert_idx = i + 1",
            "                elif line.strip() and not line.strip().startswith('#'):",
            "                    break",
            "",
            "            lines.insert(insert_idx, import_stmt + '\\n')",
            "",
            "            with open(file_path, 'w', encoding='utf-8') as f:",
            "                f.writelines(lines)",
            "            fixes_applied += 1",
            "            print(f'Added import to {file_path}: {import_stmt}')",
            "        except Exception as e:",
            "            errors.append(f'{file_path}: {str(e)}')",
            ""
        ])
        
        return code
    
    def _generate_syntax_fix(self, issues: List[Dict[str, Any]]) -> List[str]:
        """Generate code to fix syntax errors (basic)."""
        return [
            "    # Syntax errors require manual review",
            "    for issue in [",
            *[f"        {{'file_path': r'{i.get('file_path', '')}'}}," for i in issues],
            "    ]:",
            "        print(f'Syntax error in {issue[\"file_path\"]} - requires manual review')",
            ""
        ]
    
    def _generate_database_fix(self, issues: List[Dict[str, Any]]) -> List[str]:
        """Generate code to fix database datatype mismatch by recreating database."""
        return [
            "    # Fix database datatype mismatch",
            "    import shutil",
            "    from pathlib import Path",
            "",
            "    db_path = Path(__file__).parent.parent / 'backend' / 'data' / 'grace.db'",
            "    if db_path.exists():",
            "        # Create backup",
            "        backup_path = db_path.with_suffix('.db.backup')",
            "        shutil.copy2(db_path, backup_path)",
            "        logger.info(f'Created backup: {backup_path}')",
            "        # Delete database - will be recreated on startup",
            "        db_path.unlink()",
            "        logger.info('Database deleted - will be recreated on backend startup')",
            "        fixes_applied += 1",
            "    else:",
            "        logger.warning(f'Database file not found: {db_path}')",
            ""
        ]
    
    def _generate_port_conflict_fix(self, issues: List[Dict[str, Any]]) -> List[str]:
        """Generate code to handle port conflicts."""
        return [
            "    # Fix port conflict - find available port",
            "    import socket",
            "",
            "    def find_available_port(start_port=8000, max_attempts=100):",
            "        for port in range(start_port, start_port + max_attempts):",
            "            try:",
            "                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:",
            "                    s.settimeout(1)",
            "                    result = s.connect_ex(('localhost', port))",
            "                    if result != 0:",
            "                        return port",
            "            except Exception:",
            "                continue",
            "        return None",
            "",
            "    new_port = find_available_port()",
            "    if new_port:",
            "        logger.info(f'Available port found: {new_port}')",
            "        logger.info(f'Update launcher to use port {new_port}')",
            "        fixes_applied += 1",
            "    else:",
            "        logger.error('Could not find available port')",
            ""
        ]
    
    def _generate_missing_file_fix(self, issues: List[Dict[str, Any]]) -> List[str]:
        """Generate code to handle missing files."""
        return [
            "    # Handle missing files - cannot auto-create, but log",
            "    for issue in [",
            *[f"        {{'file_path': r'{i.get('file_path', '')}', 'error': '{i.get('error_message', '')[:50]}'}}," for i in issues],
            "    ]:",
            "        logger.warning(f'Missing file detected: {issue[\"file_path\"]}')",
            "        logger.warning('Cannot auto-create missing files - manual intervention required')",
            "        logger.info('Suggestions:')",
            "        logger.info('  1. Check if file was deleted or moved')",
            "        logger.info('  2. Restore from backup or version control')",
            "        logger.info('  3. Verify installation is complete')",
            ""
        ]
    
    def _generate_missing_directory_fix(self, issues: List[Dict[str, Any]]) -> List[str]:
        """Generate code to create missing directories."""
        return [
            "    # Create missing directories",
            "    for issue in [",
            *[f"        {{'directory': r'{i.get('file_path', '') or i.get(\"directory_path\", \"\")}'}}," for i in issues],
            "    ]:",
            "        dir_path = Path(issue['directory'])",
            "        if dir_path and not dir_path.exists():",
            "            dir_path.mkdir(parents=True, exist_ok=True)",
            "            logger.info(f'Created directory: {dir_path}')",
            "            fixes_applied += 1",
            "        else:",
            "            logger.debug(f'Directory already exists or path invalid: {dir_path}')",
            ""
        ]
    
    def _generate_process_failure_fix(self, issues: List[Dict[str, Any]]) -> List[str]:
        """Generate code to handle process failures."""
        return [
            "    # Process failure - log and suggest restart",
            "    for issue in [",
            *[f"        {{'error': '{i.get('error_message', '')[:100]}'}}," for i in issues],
            "    ]:",
            "        logger.warning(f'Process failure detected: {issue[\"error\"][:50]}')",
            "        logger.info('Suggestions:')",
            "        logger.info('  1. Check logs for detailed error messages')",
            "        logger.info('  2. Verify resource availability (RAM, disk space)')",
            "        logger.info('  3. Check for syntax/runtime errors in code')",
            "        logger.info('  4. Restart the process manually if needed')",
            "        # Note: Launcher will automatically retry on next startup",
            ""
        ]
    
    def _generate_generic_fix(self, issues: List[Dict[str, Any]]) -> List[str]:
        """Generate generic fix code."""
        return [
            "    # Generic fixes",
            "    for issue in [",
            *[f"        {{'file_path': r'{i.get('file_path', '')}'}}," for i in issues],
            "    ]:",
            "        print(f'Issue in {issue[\"file_path\"]} - review needed')",
            ""
        ]
    
    def execute_script(
        self,
        script_path: str,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Execute a healing script.
        
        Args:
            script_path: Path to the script
            dry_run: If True, don't actually execute
        
        Returns:
            Execution results
        """
        script_file = Path(script_path)
        if not script_file.exists():
            return {
                "success": False,
                "error": f"Script not found: {script_path}"
            }
        
        if dry_run:
            logger.info(f"[HEALING-SCRIPT] Dry run - would execute: {script_path}")
            return {
                "success": True,
                "dry_run": True,
                "script_path": script_path
            }
        
        try:
            # Create Genesis Key for script execution
            genesis_key = self.genesis_service.create_key(
                key_type=GenesisKeyType.SYSTEM_EVENT,
                what_description=f"Executing healing script: {script_file.name}",
                who_actor="autonomous_healing",
                where_location=str(script_file),
                why_reason="Autonomous healing script execution",
                how_method="healing_script_generator",
                context_data={
                    "script_path": str(script_file),
                    "script_name": script_file.name
                }
            )
            
            # Execute script
            logger.info(f"[HEALING-SCRIPT] Executing: {script_path}")
            
            result = subprocess.run(
                [sys.executable, str(script_file)],
                capture_output=True,
                text=True,
                cwd=self.repo_path,
                timeout=300  # 5 minute timeout
            )
            
            success = result.returncode == 0
            
            # Create result Genesis Key
            self.genesis_service.create_key(
                key_type=GenesisKeyType.FIX if success else GenesisKeyType.ERROR,
                what_description=f"Healing script execution: {script_file.name} - {'SUCCESS' if success else 'FAILED'}",
                who_actor="autonomous_healing",
                where_location=str(script_file),
                why_reason=f"Script execution {'succeeded' if success else 'failed'}",
                how_method="healing_script_generator",
                parent_key_id=genesis_key.key_id,
                context_data={
                    "script_path": str(script_file),
                    "return_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }
            )
            
            return {
                "success": success,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "script_path": script_path,
                "genesis_key_id": genesis_key.key_id
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Script execution timed out",
                "script_path": script_path
            }
        except Exception as e:
            logger.error(f"[HEALING-SCRIPT] Execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "script_path": script_path
            }
    
    def generate_and_execute_patches(
        self,
        issues: List[Dict[str, Any]],
        auto_execute: bool = True
    ) -> Dict[str, Any]:
        """
        Generate patches for issues and optionally execute them.
        
        Args:
            issues: List of issues to fix
            auto_execute: If True, execute the patches immediately
        
        Returns:
            Results of patch generation and execution
        """
        if not issues:
            return {
                "success": False,
                "message": "No issues provided",
                "patches": []
            }
        
        # For SQLAlchemy table redefinition, generate script directly
        sqlalchemy_issues = [i for i in issues if i.get("issue_type") == "sqlalchemy_table_redefinition"]
        
        if sqlalchemy_issues:
            # Filter out issues without valid file paths
            valid_issues = []
            for issue in sqlalchemy_issues:
                file_path = issue.get("file_path", "")
                if file_path and (Path(file_path).exists() or file_path.startswith("backend")):
                    valid_issues.append(issue)
            
            if not valid_issues:
                # If no valid file paths, try to use file_paths from first issue
                if issues and issues[0].get("file_paths"):
                    for fp in issues[0]["file_paths"][:50]:
                        valid_issues.append({
                            "issue_type": "sqlalchemy_table_redefinition",
                            "file_path": fp,
                            "error_message": issues[0].get("error_message", "Table redefinition error")
                        })
            
            if valid_issues:
                # Generate fix script for SQLAlchemy issues
                script_result = self.generate_fix_script(valid_issues)
                
                results = {
                    "patches_generated": len(valid_issues),
                    "patches": [],
                    "script_path": script_result["script_path"],
                    "issues_count": len(valid_issues)
                }
                
                if auto_execute:
                    execution_result = self.execute_script(script_result["script_path"])
                    results["execution"] = execution_result
                    results["success"] = execution_result.get("success", False)
                    if execution_result.get("stdout"):
                        results["stdout"] = execution_result["stdout"]
                    if execution_result.get("stderr"):
                        results["stderr"] = execution_result["stderr"]
                else:
                    results["success"] = True
                    results["message"] = "Script generated but not executed (auto_execute=False)"
                
                return results
            else:
                return {
                    "success": False,
                    "message": "No valid file paths found for SQLAlchemy issues",
                    "patches": []
                }
        
        # For other issues, try to generate patches
        patches = []
        
        for issue in issues:
            issue_type_str = issue.get("issue_type", "")
            file_path = issue.get("file_path", "")
            error_message = issue.get("error_message", "")
            line_number = issue.get("line_number")
            
            try:
                issue_type = IssueType(issue_type_str)
            except ValueError:
                continue
            
            patch = self.knowledge_base.generate_patch(
                file_path=file_path,
                issue_type=issue_type,
                error_message=error_message,
                line_number=line_number
            )
            
            if patch:
                patches.append(patch)
        
        if not patches:
            return {
                "success": False,
                "message": "No patches generated",
                "patches": []
            }
        
        # Generate script to apply patches
        script_result = self.generate_fix_script(
            [{
                "issue_type": "apply_patch",
                "file_path": p.file_path,
                "line_number": p.line_number,
                "old_code": p.old_code,
                "new_code": p.new_code,
                "error_message": p.reason
            } for p in patches]
        )
        
        results = {
            "patches_generated": len(patches),
            "patches": [
                {
                    "file_path": p.file_path,
                    "line_number": p.line_number,
                    "old_code": p.old_code,
                    "new_code": p.new_code,
                    "reason": p.reason,
                    "confidence": p.confidence
                }
                for p in patches
            ],
            "script_path": script_result["script_path"]
        }
        
        if auto_execute:
            execution_result = self.execute_script(script_result["script_path"])
            results["execution"] = execution_result
            results["success"] = execution_result.get("success", False)
        else:
            results["success"] = True
            results["message"] = "Patches generated but not executed (auto_execute=False)"
        
        return results


# Global instance
_script_generator: Optional[HealingScriptGenerator] = None


def get_healing_script_generator(repo_path: Optional[Path] = None) -> HealingScriptGenerator:
    """Get or create global healing script generator."""
    global _script_generator
    if _script_generator is None or repo_path is not None:
        _script_generator = HealingScriptGenerator(repo_path=repo_path)
    return _script_generator
