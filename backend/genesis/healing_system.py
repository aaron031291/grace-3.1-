import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from genesis.code_analyzer import get_code_analyzer
from genesis.genesis_key_service import get_genesis_service
from genesis.repo_scanner import get_repo_scanner
from models.genesis_key_models import GenesisKeyType
class HealingSystem:
    logger = logging.getLogger(__name__)
    """
    Scaffolded healing system using Genesis Keys for debugging.

    Features:
    - Detects issues using Genesis Keys
    - Provides contextual fixes
    - Navigates codebase via Genesis Keys
    - Auto-heals broken code
    """

    def __init__(self, repo_path: Optional[str] = None):
        self.repo_path = repo_path or self._get_default_repo_path()
        self.scanner = get_repo_scanner(self.repo_path)
        self.code_analyzer = get_code_analyzer()
        self.genesis_service = get_genesis_service()

        # Load immutable memory
        self.immutable_memory_path = os.path.join(
            self.repo_path,
            ".genesis_immutable_memory.json"
        )
        self.immutable_memory = self._load_immutable_memory()

        # Healing log
        self.healing_log = []

    def _get_default_repo_path(self) -> str:
        """Get default repo path."""
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    def _load_immutable_memory(self) -> Optional[Dict]:
        """Load immutable memory if exists."""
        if os.path.exists(self.immutable_memory_path):
            with open(self.immutable_memory_path, 'r') as f:
                return json.load(f)
        return None

    def scan_for_issues(self, file_genesis_key: Optional[str] = None) -> List[Dict]:
        """
        Scan for issues using Genesis Keys.

        Args:
            file_genesis_key: Optional specific file Genesis Key to scan

        Returns:
            List of detected issues with Genesis Key context
        """
        issues = []

        if file_genesis_key:
            # Scan specific file
            file_issues = self._scan_file_by_genesis_key(file_genesis_key)
            issues.extend(file_issues)
        else:
            # Scan all Python/JavaScript files
            if not self.immutable_memory:
                logger.warning("No immutable memory found. Run scan first.")
                return []

            files_processed = 0
            files_with_errors = 0
            for file_path, file_info in self.immutable_memory["files"].items():
                ext = file_info.get("extension", "")
                if ext in [".py", ".js", ".jsx", ".ts", ".tsx"]:
                    files_processed += 1
                    try:
                        file_issues = self._scan_file_by_genesis_key(file_info["genesis_key"])
                        issues.extend(file_issues)
                    except Exception as e:
                        files_with_errors += 1
                        logger.debug(f"Error scanning {file_path}: {e}")
            
            if files_processed > 0:
                logger.info(f"Scanned {files_processed} files, found {len(issues)} issues, {files_with_errors} errors")
            else:
                logger.warning(f"No code files found to scan in immutable memory ({len(self.immutable_memory.get('files', {}))} total files)")

        return issues

    def _scan_file_by_genesis_key(self, file_genesis_key: str) -> List[Dict]:
        """Scan a specific file by its Genesis Key."""
        # Find file info
        file_result = self.scanner.find_by_genesis_key(file_genesis_key)
        if not file_result or file_result["type"] != "file":
            return []

        file_info = file_result["info"]
        
        # Resolve file path: use relative path from memory combined with current repo_path
        # This handles cases where the repo was moved or the absolute paths are stale
        rel_path = file_info.get("path", "")
        if rel_path:
            # Build path relative to current repo_path
            abs_path = os.path.join(self.repo_path, rel_path)
            # Normalize path separators
            abs_path = os.path.normpath(abs_path)
        else:
            # Fallback to absolute_path from memory if relative path not available
            abs_path = file_info.get("absolute_path", "")
        
        # Verify file exists
        if not os.path.exists(abs_path):
            # Try the absolute path from memory as fallback
            old_abs_path = file_info.get("absolute_path", "")
            if old_abs_path and os.path.exists(old_abs_path):
                abs_path = old_abs_path
            else:
                logger.warning(f"File not found: {abs_path} (from path: {rel_path})")
                return []

        # Read file content
        try:
            with open(abs_path, 'r', encoding='utf-8') as f:
                code = f.read()
        except Exception as e:
            logger.error(f"Failed to read file {abs_path}: {e}")
            return []

        # Analyze code
        ext = file_info.get("extension", "")
        if ext == ".py":
            code_issues = self.code_analyzer.analyze_python_code(code, abs_path)
        elif ext in [".js", ".jsx", ".ts", ".tsx"]:
            code_issues = self.code_analyzer.analyze_javascript_code(code, abs_path)
        else:
            return []

        # Add Genesis Key context to issues
        issues = []
        for issue in code_issues:
            issues.append({
                "file_genesis_key": file_genesis_key,
                "file_path": file_info["path"],
                "file_name": file_info["name"],
                "directory_genesis_key": file_info["directory_genesis_key"],
                "issue_type": issue.issue_type,
                "severity": issue.severity,
                "line_number": issue.line_number,
                "column": issue.column,
                "message": issue.message,
                "suggested_fix": issue.suggested_fix,
                "fix_confidence": issue.fix_confidence,
                "context": issue.context,
                "detected_at": datetime.utcnow().isoformat()
            })

        return issues

    def heal_file(
        self,
        file_genesis_key: str,
        user_id: Optional[str] = None,
        auto_apply: bool = False
    ) -> Dict[str, Any]:
        """
        Heal a file using its Genesis Key.

        Args:
            file_genesis_key: Genesis Key of file to heal
            user_id: User performing healing
            auto_apply: Whether to automatically apply fixes

        Returns:
            Healing results
        """
        # Get issues for file
        issues = self._scan_file_by_genesis_key(file_genesis_key)

        if not issues:
            return {
                "file_genesis_key": file_genesis_key,
                "status": "healthy",
                "issues_found": 0,
                "fixes_applied": 0
            }

        # Find file info
        file_result = self.scanner.find_by_genesis_key(file_genesis_key)
        if not file_result:
            return {"error": "File not found"}

        file_info = file_result["info"]
        abs_path = file_info["absolute_path"]

        # Read current code
        with open(abs_path, 'r', encoding='utf-8') as f:
            original_code = f.read()

        # Apply fixes if auto_apply
        fixes_applied = 0
        if auto_apply:
            fixed_code = original_code
            for issue in sorted(issues, key=lambda x: x["line_number"], reverse=True):
                if issue["suggested_fix"] and issue["fix_confidence"] > 0.8:
                    # Apply fix
                    fixed_code = self._apply_fix(fixed_code, issue)
                    fixes_applied += 1

            if fixes_applied > 0:
                # Save fixed code
                with open(abs_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_code)

                # Create healing Genesis Key
                self.genesis_service.create_key(
                    key_type=GenesisKeyType.FIX,
                    what_description=f"Auto-healed file: {file_info['name']} ({fixes_applied} fixes)",
                    who_actor=user_id or "healing_system",
                    where_location=file_info["path"],
                    why_reason="Scaffolded healing system auto-repair",
                    how_method="Genesis Key guided healing",
                    file_path=file_info["path"],
                    code_before=original_code,
                    code_after=fixed_code,
                    context_data={
                        "file_genesis_key": file_genesis_key,
                        "directory_genesis_key": file_info["directory_genesis_key"],
                        "fixes_applied": fixes_applied,
                        "issues_found": len(issues)
                    },
                    tags=["healing", "auto_fix", "scaffolded_healing"]
                )

        # Log healing
        healing_record = {
            "file_genesis_key": file_genesis_key,
            "file_path": file_info["path"],
            "issues_found": len(issues),
            "fixes_applied": fixes_applied,
            "healed_at": datetime.utcnow().isoformat(),
            "issues": issues
        }
        self.healing_log.append(healing_record)

        return {
            "file_genesis_key": file_genesis_key,
            "file_path": file_info["path"],
            "status": "healed" if fixes_applied > 0 else "analyzed",
            "issues_found": len(issues),
            "fixes_applied": fixes_applied,
            "issues": issues
        }

    def _apply_fix(self, code: str, issue: Dict) -> str:
        """Apply a fix to code."""
        if not issue["suggested_fix"]:
            return code

        lines = code.split('\n')
        line_idx = issue["line_number"] - 1

        if 0 <= line_idx < len(lines):
            lines[line_idx] = issue["suggested_fix"]

        return '\n'.join(lines)

    def heal_directory(
        self,
        dir_genesis_key: str,
        user_id: Optional[str] = None,
        auto_apply: bool = False,
        recursive: bool = True
    ) -> Dict[str, Any]:
        """
        Heal all files in a directory using Genesis Key.

        Args:
            dir_genesis_key: Genesis Key of directory
            user_id: User performing healing
            auto_apply: Whether to automatically apply fixes
            recursive: Whether to heal subdirectories

        Returns:
            Healing results for directory
        """
        # Find directory
        dir_result = self.scanner.find_by_genesis_key(dir_genesis_key)
        if not dir_result or dir_result["type"] != "directory":
            return {"error": "Directory not found"}

        dir_info = dir_result["info"]
        results = {
            "directory_genesis_key": dir_genesis_key,
            "directory_path": dir_info["path"],
            "files_healed": [],
            "total_issues": 0,
            "total_fixes": 0
        }

        # Heal all files in directory
        for file_key in dir_info["files"]:
            file_result = self.heal_file(file_key, user_id, auto_apply)
            results["files_healed"].append(file_result)
            results["total_issues"] += file_result.get("issues_found", 0)
            results["total_fixes"] += file_result.get("fixes_applied", 0)

        # Heal subdirectories if recursive
        if recursive:
            for subdir_key in dir_info["subdirectories"]:
                subdir_result = self.heal_directory(subdir_key, user_id, auto_apply, recursive)
                results["files_healed"].extend(subdir_result.get("files_healed", []))
                results["total_issues"] += subdir_result.get("total_issues", 0)
                results["total_fixes"] += subdir_result.get("total_fixes", 0)

        return results

    def navigate_to_issue(self, file_genesis_key: str, issue_line: int) -> Dict[str, Any]:
        """
        Navigate to an issue using Genesis Key.

        Returns file path and context for debugging.
        """
        file_result = self.scanner.find_by_genesis_key(file_genesis_key)
        if not file_result:
            return {"error": "File not found"}

        file_info = file_result["info"]

        # Get file content around issue
        try:
            with open(file_info["absolute_path"], 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Get context (5 lines before and after)
            start = max(0, issue_line - 6)
            end = min(len(lines), issue_line + 5)
            context_lines = lines[start:end]

            return {
                "file_genesis_key": file_genesis_key,
                "file_path": file_info["path"],
                "absolute_path": file_info["absolute_path"],
                "directory_genesis_key": file_info["directory_genesis_key"],
                "issue_line": issue_line,
                "context": {
                    "start_line": start + 1,
                    "end_line": end,
                    "lines": [
                        {
                            "line_number": start + i + 1,
                            "content": line.rstrip(),
                            "is_issue_line": (start + i + 1 == issue_line)
                        }
                        for i, line in enumerate(context_lines)
                    ]
                }
            }
        except Exception as e:
            return {"error": str(e)}

    def get_healing_summary(self) -> Dict[str, Any]:
        """Get summary of healing operations."""
        total_files = len(self.healing_log)
        total_issues = sum(h["issues_found"] for h in self.healing_log)
        total_fixes = sum(h["fixes_applied"] for h in self.healing_log)

        return {
            "total_files_healed": total_files,
            "total_issues_found": total_issues,
            "total_fixes_applied": total_fixes,
            "healing_rate": (total_fixes / total_issues * 100) if total_issues > 0 else 0,
            "healing_log": self.healing_log
        }

    def export_healing_report(self, output_path: Optional[str] = None) -> str:
        """Export healing report to JSON."""
        if not output_path:
            output_path = os.path.join(
                self.repo_path,
                f".genesis_healing_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            )

        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "summary": self.get_healing_summary(),
            "detailed_log": self.healing_log
        }

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        logger.info(f"Healing report exported to: {output_path}")
        return output_path


# Global healing system instance
_healing_system: Optional[HealingSystem] = None


def get_healing_system(repo_path: Optional[str] = None) -> HealingSystem:
    """Get or create global healing system instance."""
    global _healing_system
    if _healing_system is None or repo_path is not None:
        _healing_system = HealingSystem(repo_path=repo_path)
    return _healing_system
