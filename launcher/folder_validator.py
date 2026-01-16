"""
Folder Contract Validator
==========================
Validates that folders meet their required schemas/contracts.

Philosophy:
- Folders are editable
- Schemas are NOT optional
- If a folder breaks the contract, Grace flags it—not crashes quietly
"""

from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from enum import Enum
import json
import logging

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Validation issue severity."""
    ERROR = "error"      # Must fix, system cannot proceed
    WARNING = "warning"  # Should fix, system can proceed with degraded functionality
    INFO = "info"        # Informational, no action required


@dataclass
class ValidationIssue:
    """A validation issue found in a folder."""
    folder: Path
    severity: ValidationSeverity
    message: str
    expected: Optional[str] = None
    found: Optional[str] = None
    
    def is_fatal(self) -> bool:
        """Check if this issue is fatal (must fix)."""
        return self.severity == ValidationSeverity.ERROR


class FolderValidator:
    """
    Validates folder contracts.
    
    Dumb by design: just checks schemas, no business logic.
    """
    
    def __init__(self, root_path: Path):
        """
        Initialize folder validator.
        
        Args:
            root_path: Root path of the Grace installation
        """
        self.root_path = Path(root_path).resolve()
    
    def validate_knowledge_base(self, kb_path: Optional[Path] = None) -> List[ValidationIssue]:
        """
        Validate knowledge_base folder contract.
        
        Contract:
        - Must exist
        - Must be a directory
        - Should contain .md or .txt files (optional, but expected)
        - Should not contain critical system files in root
        
        Args:
            kb_path: Path to knowledge base (defaults to root_path/knowledge_base)
            
        Returns:
            List of validation issues
        """
        issues = []
        
        if kb_path is None:
            kb_path = self.root_path / "knowledge_base"
        
        kb_path = Path(kb_path)
        
        # Must exist
        if not kb_path.exists():
            issues.append(ValidationIssue(
                folder=kb_path,
                severity=ValidationSeverity.ERROR,
                message="Knowledge base folder does not exist",
                expected="Directory at knowledge_base/",
                found="Not found"
            ))
            return issues  # Can't check further if it doesn't exist
        
        # Must be a directory
        if not kb_path.is_dir():
            issues.append(ValidationIssue(
                folder=kb_path,
                severity=ValidationSeverity.ERROR,
                message="Knowledge base path exists but is not a directory",
                expected="Directory",
                found=f"{'File' if kb_path.is_file() else 'Other'}"
            ))
            return issues
        
        # Should contain some content files (warning if empty)
        content_files = list(kb_path.glob("*.md")) + list(kb_path.glob("*.txt"))
        if len(content_files) == 0:
            issues.append(ValidationIssue(
                folder=kb_path,
                severity=ValidationSeverity.WARNING,
                message="Knowledge base folder is empty (no .md or .txt files)",
                expected="At least some content files",
                found="0 files"
            ))
        
        # Should not contain critical system files in root
        forbidden_files = {"app.py", "config.json", "settings.py"}
        for forbidden in forbidden_files:
            if (kb_path / forbidden).exists():
                issues.append(ValidationIssue(
                    folder=kb_path,
                    severity=ValidationSeverity.ERROR,
                    message=f"Knowledge base root contains forbidden file: {forbidden}",
                    expected="Only content files",
                    found=f"{forbidden} (system file)"
                ))
        
        return issues
    
    def validate_data_folder(self, data_path: Optional[Path] = None) -> List[ValidationIssue]:
        """
        Validate data/ folder contract.
        
        Contract:
        - Should exist (warning if missing)
        - Must be a directory if it exists
        - Should have expected subdirectories (optional)
        
        Args:
            data_path: Path to data folder (defaults to root_path/data)
            
        Returns:
            List of validation issues
        """
        issues = []
        
        if data_path is None:
            data_path = self.root_path / "data"
        
        data_path = Path(data_path)
        
        # Should exist (warning if missing, not error)
        if not data_path.exists():
            issues.append(ValidationIssue(
                folder=data_path,
                severity=ValidationSeverity.WARNING,
                message="Data folder does not exist (system will create if needed)",
                expected="Directory at data/",
                found="Not found"
            ))
            return issues
        
        # Must be a directory if it exists
        if not data_path.is_dir():
            issues.append(ValidationIssue(
                folder=data_path,
                severity=ValidationSeverity.ERROR,
                message="Data path exists but is not a directory",
                expected="Directory",
                found=f"{'File' if data_path.is_file() else 'Other'}"
            ))
        
        return issues
    
    def validate_backend_folder(self, backend_path: Optional[Path] = None) -> List[ValidationIssue]:
        """
        Validate backend/ folder contract.
        
        Contract:
        - Must exist
        - Must contain app.py
        - Must be a directory
        
        Args:
            backend_path: Path to backend folder (defaults to root_path/backend)
            
        Returns:
            List of validation issues
        """
        issues = []
        
        if backend_path is None:
            backend_path = self.root_path / "backend"
        
        backend_path = Path(backend_path)
        
        # Must exist
        if not backend_path.exists():
            issues.append(ValidationIssue(
                folder=backend_path,
                severity=ValidationSeverity.ERROR,
                message="Backend folder does not exist",
                expected="Directory at backend/",
                found="Not found"
            ))
            return issues
        
        # Must be a directory
        if not backend_path.is_dir():
            issues.append(ValidationIssue(
                folder=backend_path,
                severity=ValidationSeverity.ERROR,
                message="Backend path exists but is not a directory",
                expected="Directory",
                found=f"{'File' if backend_path.is_file() else 'Other'}"
            ))
            return issues
        
        # Must contain app.py
        app_py = backend_path / "app.py"
        if not app_py.exists():
            issues.append(ValidationIssue(
                folder=backend_path,
                severity=ValidationSeverity.ERROR,
                message="Backend folder missing app.py (main application file)",
                expected="app.py",
                found="Not found"
            ))
        
        return issues
    
    def validate_config_schema(self, config_path: Path, required_keys: Set[str]) -> List[ValidationIssue]:
        """
        Validate a config file schema.
        
        Args:
            config_path: Path to config file
            required_keys: Set of required JSON keys
            
        Returns:
            List of validation issues
        """
        issues = []
        
        if not config_path.exists():
            issues.append(ValidationIssue(
                folder=config_path.parent,
                severity=ValidationSeverity.ERROR,
                message=f"Config file does not exist: {config_path.name}",
                expected=f"File at {config_path}",
                found="Not found"
            ))
            return issues
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            issues.append(ValidationIssue(
                folder=config_path.parent,
                severity=ValidationSeverity.ERROR,
                message=f"Config file is not valid JSON: {config_path.name}",
                expected="Valid JSON",
                found=f"JSON error: {str(e)}"
            ))
            return issues
        
        # Check required keys
        missing_keys = required_keys - set(config.keys())
        if missing_keys:
            issues.append(ValidationIssue(
                folder=config_path.parent,
                severity=ValidationSeverity.ERROR,
                message=f"Config file missing required keys: {', '.join(missing_keys)}",
                expected=f"Keys: {', '.join(required_keys)}",
                found=f"Missing: {', '.join(missing_keys)}"
            ))
        
        return issues
    
    def validate_all(self, strict: bool = True) -> List[ValidationIssue]:
        """
        Run all folder validations.
        
        Args:
            strict: If True, return errors even if warnings-only
            
        Returns:
            List of all validation issues
            
        Raises:
            RuntimeError: If strict=True and any fatal issues found
        """
        logger.info("Validating folder contracts...")
        
        all_issues = []
        
        # Validate critical folders
        all_issues.extend(self.validate_backend_folder())
        all_issues.extend(self.validate_knowledge_base())
        all_issues.extend(self.validate_data_folder())
        
        # Count issues by severity
        errors = [i for i in all_issues if i.severity == ValidationSeverity.ERROR]
        warnings = [i for i in all_issues if i.severity == ValidationSeverity.WARNING]
        
        logger.info(f"Folder validation: {len(errors)} errors, {len(warnings)} warnings")
        
        if strict and errors:
            error_messages = "\n".join(f"  - {i.message}" for i in errors)
            raise RuntimeError(
                f"Folder contract validation failed:\n{error_messages}\n"
                f"Fix these issues before starting Grace."
            )
        
        # Log warnings
        for warning in warnings:
            logger.warning(f"⚠ Folder validation warning: {warning.message}")
        
        return all_issues
