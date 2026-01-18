import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import re

logger = logging.getLogger(__name__)


class IssueType(str, Enum):
    """Types of issues the healing system can fix."""
    SQLALCHEMY_TABLE_REDEFINITION = "sqlalchemy_table_redefinition"
    MISSING_IMPORT = "missing_import"
    SYNTAX_ERROR = "syntax_error"
    TYPE_ERROR = "type_error"
    ATTRIBUTE_ERROR = "attribute_error"
    INDENTATION_ERROR = "indentation_error"
    CIRCULAR_IMPORT = "circular_import"
    DATABASE_CONNECTION = "database_connection"
    MISSING_DEPENDENCY = "missing_dependency"
    CONFIGURATION_ERROR = "configuration_error"
    CONNECTION_TIMEOUT = "connection_timeout"
    PERMISSION_ERROR = "permission_error"
    FILE_NOT_FOUND = "file_not_found"
    MEMORY_ERROR = "memory_error"
    KEY_ERROR = "key_error"
    DATABASE_DATATYPE_MISMATCH = "database_datatype_mismatch"
    PORT_CONFLICT = "port_conflict"
    MISSING_FILE = "missing_file"
    MISSING_DIRECTORY = "missing_directory"
    PROCESS_FAILURE = "process_failure"
    CONNECTION_ERROR = "connection_error"
    # New issue types from backend fixes
    WRONG_IMPORT_PATH = "wrong_import_path"
    MISSING_FACTORY_FUNCTION = "missing_factory_function"
    LOGGER_IN_CLASS = "logger_in_class"
    MISSING_ROUTER_DEFINITION = "missing_router_definition"
    PYDANTIC_MODEL_ERROR = "pydantic_model_error"


@dataclass
class FixPattern:
    """A pattern for fixing a specific issue type."""
    issue_type: IssueType
    pattern: str  # Regex pattern to detect the issue
    fix_template: str  # Template for the fix
    confidence: float  # Confidence level (0.0-1.0)
    description: str
    examples: List[str]  # Example error messages


@dataclass
class CodePatch:
    """A code patch to apply."""
    file_path: str
    line_number: int
    old_code: str
    new_code: str
    reason: str
    confidence: float


class HealingKnowledgeBase:
    """
    Knowledge base of common fixes and patterns for autonomous healing.
    """
    
    def __init__(self):
        self.fix_patterns = self._load_fix_patterns()
        self.script_templates = self._load_script_templates()
    
    def _load_fix_patterns(self) -> List[FixPattern]:
        """Load all fix patterns."""
        return [
            # SQLAlchemy Table Redefinition
            FixPattern(
                issue_type=IssueType.SQLALCHEMY_TABLE_REDEFINITION,
                pattern=r"(Table ['\"](\w+)['\"] is already defined|table redefinition|already defined.*MetaData)",
                fix_template="""# Fix: Add extend_existing=True to table definition
# Find: {table_name} = Table(...)
# Replace with: {table_name} = Table(..., extend_existing=True)

# Or if using declarative base:
# Find: class {TableName}(Base):
#     __tablename__ = '{table_name}'
# Replace with: class {TableName}(Base):
#     __tablename__ = '{table_name}'
#     __table_args__ = {{'extend_existing': True}}""",
                confidence=0.95,
                description="SQLAlchemy table redefinition - add extend_existing=True",
                examples=[
                    "Table 'users' is already defined for this MetaData instance",
                    "Table 'learning_examples' is already defined",
                    "Table redefinition errors - SQLAlchemy metadata issue"
                ]
            ),
            
            # Missing Import
            FixPattern(
                issue_type=IssueType.MISSING_IMPORT,
                pattern=r"No module named ['\"](\w+)['\"]",
                fix_template="""# Fix: Add missing import
# Add at top of file:
from {module_name} import {item_name}

# Or if it's a relative import:
from .{module_name} import {item_name}""",
                confidence=0.85,
                description="Missing module import",
                examples=[
                    "No module named 'database'",
                    "No module named 'models.database_models'"
                ]
            ),
            
            # Syntax Error
            FixPattern(
                issue_type=IssueType.SYNTAX_ERROR,
                pattern=r"SyntaxError.*line (\d+)",
                fix_template="""# Fix: Syntax error at line {line_number}
# Review the code at line {line_number} for:
# - Missing colons (:)
# - Unmatched parentheses, brackets, or braces
# - Incorrect indentation
# - Missing quotes or incorrect string formatting""",
                confidence=0.70,
                description="Python syntax error",
                examples=[
                    "SyntaxError: invalid syntax",
                    "SyntaxError: unexpected EOF while parsing"
                ]
            ),
            
            # Attribute Error
            FixPattern(
                issue_type=IssueType.ATTRIBUTE_ERROR,
                pattern=r"'(\w+)' object has no attribute ['\"](\w+)['\"]",
                fix_template="""# Fix: Attribute error
# Object '{object_name}' doesn't have attribute '{attribute_name}'
# Check:
# 1. Is the attribute name spelled correctly?
# 2. Is the object the correct type?
# 3. Should it be a method call instead? (add parentheses)
# 4. Is the import correct?""",
                confidence=0.75,
                description="Object missing attribute",
                examples=[
                    "'NoneType' object has no attribute 'get'",
                    "'str' object has no attribute 'append'"
                ]
            ),
            
            # Database Connection
            FixPattern(
                issue_type=IssueType.DATABASE_CONNECTION,
                pattern=r"(database|Database).*connection.*(failed|error|unavailable)",
                fix_template="""# Fix: Database connection issue
# 1. Check database is running
# 2. Verify connection settings in settings.py
# 3. Check database path exists
# 4. Try reconnecting:
from database.connection import DatabaseConnection
DatabaseConnection.reconnect()""",
                confidence=0.80,
                description="Database connection failure",
                examples=[
                    "Database connection failed",
                    "Database unavailable"
                ]
            ),
            
            # Circular Import
            FixPattern(
                issue_type=IssueType.CIRCULAR_IMPORT,
                pattern=r"ImportError: cannot import name ['\"](\w+)['\"] from partially initialized module",
                fix_template="""# Fix: Break circular import
# Option 1: Move import inside function
# Before: from module_a import something
# After: 
#   def function():
#       from module_a import something

# Option 2: Use lazy import
# Before: from module_a import something
# After: import module_a; something = module_a.something

# Option 3: Reorganize modules to break cycle""",
                confidence=0.80,
                description="Circular import - break dependency cycle",
                examples=[
                    "ImportError: cannot import name 'X' from partially initialized module",
                    "Circular import detected"
                ]
            ),
            
            # Connection Timeout
            FixPattern(
                issue_type=IssueType.CONNECTION_TIMEOUT,
                pattern=r"(Connection timeout|Operation timed out|TimeoutError|timeout)",
                fix_template="""# Fix: Connection timeout
# 1. Increase timeout value
#    connection.timeout = 30  # seconds

# 2. Check network connectivity
# 3. Optimize query performance
# 4. Add retry logic with exponential backoff""",
                confidence=0.75,
                description="Connection timeout - increase timeout or optimize",
                examples=[
                    "Connection timeout",
                    "Operation timed out",
                    "TimeoutError: Connection timed out"
                ]
            ),
            
            # Missing Dependency
            FixPattern(
                issue_type=IssueType.MISSING_DEPENDENCY,
                pattern=r"ModuleNotFoundError: No module named ['\"](\w+)['\"]",
                fix_template="""# Fix: Install missing dependency
# 1. Install package:
#    pip install {module_name}

# 2. Add to requirements.txt:
#    {module_name}>=version

# 3. Check virtual environment is activated
# 4. Verify PYTHONPATH includes package location""",
                confidence=0.90,
                description="Missing Python package - install dependency",
                examples=[
                    "ModuleNotFoundError: No module named 'external_package'",
                    "No module named 'requests'"
                ]
            ),
            
            # Database Datatype Mismatch
            FixPattern(
                issue_type=IssueType.DATABASE_DATATYPE_MISMATCH,
                pattern=r"(datatype mismatch|IntegrityError.*datatype|column.*datatype|SQLite.*datatype)",
                fix_template="""# Fix: Database datatype mismatch
# This usually means database schema is out of sync with models

# Option 1: Delete and recreate database (development only)
# 1. Stop the backend
# 2. Delete: backend/data/grace.db
# 3. Restart backend (tables will be recreated)

# Option 2: Run database migration
# from database.migration import create_tables
# create_tables()

# Option 3: Manual schema fix
# Check SQLAlchemy model types match database column types
# Common issues:
# - String vs TEXT vs VARCHAR length
# - Integer vs BigInteger
# - Float vs Numeric
# - JSON stored as TEXT (needs proper serialization)""",
                confidence=0.95,
                description="Database schema mismatch - recreate or migrate database",
                examples=[
                    "sqlite3.IntegrityError: datatype mismatch",
                    "IntegrityError: datatype mismatch",
                    "column trust_score datatype mismatch"
                ]
            ),
            
            # Indentation Error
            FixPattern(
                issue_type=IssueType.INDENTATION_ERROR,
                pattern=r"IndentationError.*(expected|unexpected indent)",
                fix_template="""# Fix: Indentation error
# Python requires consistent indentation (usually 4 spaces)

# Common fixes:
# 1. Ensure all blocks use same indentation (4 spaces recommended)
# 2. Check for mixed tabs and spaces (use spaces only)
# 3. Verify try/except/finally blocks are properly indented
# 4. Check if/elif/else blocks are aligned
# 5. Verify function/class definitions have proper indentation

# Example fix:
# Before: if condition:
#     try:
#     code  # Wrong indentation
# After: if condition:
#     try:
#         code  # Correct indentation (4 spaces)""",
                confidence=0.90,
                description="Python indentation error - fix spacing/indentation",
                examples=[
                    "IndentationError: expected an indented block",
                    "IndentationError: unexpected indent"
                ]
            ),
            
            # Port Conflict
            FixPattern(
                issue_type=IssueType.PORT_CONFLICT,
                pattern=r"(port.*already in use|address already in use|port.*occupied)",
                fix_template="""# Fix: Port conflict
# Another process is using the required port

# Option 1: Find and stop the process using the port
# Windows: netstat -ano | findstr :{port}
# Linux/Mac: lsof -i :{port}
# Then kill the process

# Option 2: Use a different port
# Change port in configuration:
# backend_port = {new_port}  # Use any available port (8001, 8002, etc.)

# Option 3: Automatic port selection
# The launcher can automatically find an available port""",
                confidence=0.95,
                description="Port conflict - find available port or stop conflicting process",
                examples=[
                    "Port 8000 is already in use",
                    "address already in use",
                    "port conflict"
                ]
            ),
            
            # Missing File
            FixPattern(
                issue_type=IssueType.MISSING_FILE,
                pattern=r"(file.*not found|No such file|FileNotFoundError|missing.*file)",
                fix_template="""# Fix: Missing file
# The required file doesn't exist

# Option 1: Restore from backup or version control
# git checkout <file_path>

# Option 2: Recreate the file if it's auto-generated
# Restart the service - it may recreate the file

# Option 3: Create missing file manually
# Create the file at the expected location with required content

# For critical files (like app.py):
# - Ensure you're running from correct directory
# - Check file permissions
# - Verify installation is complete""",
                confidence=0.85,
                description="Missing file - restore, recreate, or create manually",
                examples=[
                    "FileNotFoundError: app.py not found",
                    "No such file or directory",
                    "missing backend file"
                ]
            ),
            
            # Missing Directory
            FixPattern(
                issue_type=IssueType.MISSING_DIRECTORY,
                pattern=r"(directory.*not found|No such directory|directory.*does not exist)",
                fix_template="""# Fix: Missing directory
# The required directory doesn't exist

# Create the directory:
# import os
# from pathlib import Path
# Path('{directory_path}').mkdir(parents=True, exist_ok=True)

# Or:
# os.makedirs('{directory_path}', exist_ok=True)

# Common missing directories:
# - backend/
# - backend/logs/
# - backend/data/
# - knowledge_base/""",
                confidence=0.95,
                description="Missing directory - create with parents=True",
                examples=[
                    "directory 'backend' does not exist",
                    "No such directory",
                    "missing directory"
                ]
            ),
            
            # Process Failure
            FixPattern(
                issue_type=IssueType.PROCESS_FAILURE,
                pattern=r"(process.*died|process.*exited|process.*failed|process.*crash)",
                fix_template="""# Fix: Process failure
# A process crashed or exited unexpectedly

# Option 1: Check logs for error details
# backend/logs/*.log or check process output

# Option 2: Restart the process
# The launcher should automatically retry

# Option 3: Check resource constraints
# - Memory (RAM) available
# - Disk space
# - File permissions
# - Port availability

# Option 4: Verify dependencies
# - Python version correct
# - All packages installed
# - Environment variables set

# Option 5: Check for syntax/runtime errors
# Review recent code changes
# Run syntax check: python -m py_compile <file>""",
                confidence=0.80,
                description="Process crash - check logs, restart, verify resources",
                examples=[
                    "process died unexpectedly",
                    "process exited with code 1",
                    "backend process crash"
                ]
            ),
            
            # Wrong Import Path (backend.xxx instead of xxx)
            FixPattern(
                issue_type=IssueType.WRONG_IMPORT_PATH,
                pattern=r"ModuleNotFoundError: No module named ['\"]backend\.(\w+)['\"]",
                fix_template="""# Fix: Wrong import path when running from backend directory
# When running from within the backend directory, imports should be relative
# Change: from backend.xxx import yyy
# To:     from xxx import yyy

# Example:
# Before: from backend.database.session import get_session
# After:  from database.session import get_session

# Before: from backend.cognitive.learning_memory import LearningMemoryManager  
# After:  from cognitive.learning_memory import LearningMemoryManager

# The backend directory IS the package root when running from within it""",
                confidence=0.95,
                description="Wrong import path - remove 'backend.' prefix for relative imports",
                examples=[
                    "ModuleNotFoundError: No module named 'backend.database'",
                    "ModuleNotFoundError: No module named 'backend.cognitive'",
                    "ModuleNotFoundError: No module named 'backend.models'"
                ]
            ),
            
            # Missing Factory Function
            FixPattern(
                issue_type=IssueType.MISSING_FACTORY_FUNCTION,
                pattern=r"ImportError: cannot import name ['\"]get_(\w+)['\"]",
                fix_template="""# Fix: Missing factory function (get_xxx pattern)
# A factory function is expected but not defined in the module

# Add a factory function at the end of the module:
_instance = None

def get_{class_name_lower}(**kwargs) -> {ClassName}:
    \"\"\"Get or create the {ClassName} singleton.\"\"\"
    global _instance
    
    if _instance is None:
        _instance = {ClassName}(**kwargs)
    
    return _instance

# This creates a singleton pattern that:
# 1. Creates the instance once on first call
# 2. Returns the same instance on subsequent calls
# 3. Accepts optional initialization parameters""",
                confidence=0.90,
                description="Missing factory function - add get_xxx() singleton pattern",
                examples=[
                    "ImportError: cannot import name 'get_memory_mesh_integration'",
                    "ImportError: cannot import name 'get_llm_orchestrator'"
                ]
            ),
            
            # Logger Defined Inside Class (Pydantic/Enum Error)
            FixPattern(
                issue_type=IssueType.LOGGER_IN_CLASS,
                pattern=r"(PydanticUserError.*logger|logger.*non-annotated attribute|class.*logger.*ClassVar)",
                fix_template="""# Fix: Logger incorrectly defined inside class
# Python loggers must be defined at module level, not inside classes

# WRONG - inside class:
# class MyClass(BaseModel):
#     logger = logging.getLogger(__name__)  # ERROR!
#     field: str

# CORRECT - at module level:
# logger = logging.getLogger(__name__)
#
# class MyClass(BaseModel):
#     field: str

# Move the logger = logging.getLogger(__name__) line BEFORE the class definition
# and remove it from inside the class body""",
                confidence=0.98,
                description="Logger inside class - move to module level",
                examples=[
                    "PydanticUserError: A non-annotated attribute was detected: `logger`",
                    "All model fields require a type annotation; if `logger` is not meant to be a field"
                ]
            ),
            
            # Missing Router Definition in FastAPI
            FixPattern(
                issue_type=IssueType.MISSING_ROUTER_DEFINITION,
                pattern=r"NameError: name ['\"]router['\"] is not defined",
                fix_template="""# Fix: Missing FastAPI router definition
# API endpoints require a router to be defined before use

# Add at the top of the file (after imports):
from fastapi import APIRouter

router = APIRouter(prefix="/your-prefix", tags=["your-tag"])

# Then you can use:
# @router.get("/endpoint")
# @router.post("/endpoint")
# etc.

# Common prefixes based on file name:
# - health.py -> prefix="/health"
# - auth.py -> prefix="/auth"  
# - chat_orchestrator_endpoint.py -> prefix="/chat"
""",
                confidence=0.95,
                description="Missing router definition - add APIRouter",
                examples=[
                    "NameError: name 'router' is not defined",
                    "@router.post without router defined"
                ]
            ),
            
            # Pydantic Model Field Error
            FixPattern(
                issue_type=IssueType.PYDANTIC_MODEL_ERROR,
                pattern=r"pydantic.*model.*field.*annotation|PydanticUserError",
                fix_template="""# Fix: Pydantic model field error
# All fields in Pydantic models must have type annotations

# Common issues:
# 1. Logger inside model (move to module level)
# 2. Class variable without ClassVar annotation
# 3. Field without type hint

# WRONG:
# class MyModel(BaseModel):
#     my_field = "default"  # Missing type!

# CORRECT:
# class MyModel(BaseModel):
#     my_field: str = "default"

# For class variables that shouldn't be fields:
# from typing import ClassVar
# class MyModel(BaseModel):
#     class_var: ClassVar[str] = "not a field"
""",
                confidence=0.90,
                description="Pydantic field error - add type annotations",
                examples=[
                    "pydantic.errors.PydanticUserError: A non-annotated attribute was detected",
                    "All model fields require a type annotation"
                ]
            ),
        ]
    
    def _load_script_templates(self) -> Dict[str, str]:
        """Load script templates for automated fixes."""
        return {
            "fix_sqlalchemy_tables": """#!/usr/bin/env python3
\"\"\"
Auto-generated script to fix SQLAlchemy table redefinition issues.
\"\"\"
import re
from pathlib import Path

def fix_table_redefinition(file_path: str) -> bool:
    \"\"\"Fix table redefinition in a file.\"\"\"
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Pattern 1: Table() constructor
        pattern1 = r'(Table\s*\([^)]*[\'"]{table_name}[\'"][^)]*)\)'
        replacement1 = r'\\1, extend_existing=True)'
        
        # Pattern 2: Declarative base with __tablename__
        pattern2 = r'(class\\s+\\w+\\s*\\([^)]*Base[^)]*\\):.*?__tablename__\\s*=\\s*[\'"]{table_name}[\'"])'
        replacement2 = r'\\1\\n    __table_args__ = {{\\'extend_existing\\': True}}'
        
        # Apply fixes
        for table_name in {table_names}:
            # Fix Table() constructor
            content = re.sub(
                pattern1.format(table_name=table_name),
                replacement1,
                content,
                flags=re.MULTILINE | re.DOTALL
            )
            
            # Fix declarative base
            content = re.sub(
                pattern2.format(table_name=table_name),
                replacement2,
                content,
                flags=re.MULTILINE | re.DOTALL
            )
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error fixing {{file_path}}: {{e}}")
        return False

# Files to fix
files_to_fix = {file_paths}

fixed_count = 0
for file_path in files_to_fix:
    if fix_table_redefinition(file_path):
        print(f"Fixed: {{file_path}}")
        fixed_count += 1

print(f"\\nFixed {{fixed_count}} file(s)")
""",
            
            "fix_missing_imports": """#!/usr/bin/env python3
\"\"\"
Auto-generated script to fix missing imports.
\"\"\"
from pathlib import Path
import ast
import sys

def add_import(file_path: str, import_statement: str) -> bool:
    \"\"\"Add import statement to file.\"\"\"
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Check if import already exists
        if import_statement.strip() in ''.join(lines):
            return False
        
        # Find insertion point (after existing imports)
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                insert_idx = i + 1
            elif line.strip() and not line.strip().startswith('#'):
                break
        
        # Insert import
        lines.insert(insert_idx, import_statement + '\\n')
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        return True
    except Exception as e:
        print(f"Error adding import to {{file_path}}: {{e}}")
        return False

# Imports to add
imports_to_add = {imports}

fixed_count = 0
for file_path, import_stmt in imports_to_add:
    if add_import(file_path, import_stmt):
        print(f"Added import to {{file_path}}: {{import_stmt}}")
        fixed_count += 1

print(f"\\nFixed {{fixed_count}} file(s)")
""",
            
            "apply_patch": """#!/usr/bin/env python3
\"\"\"
Auto-generated script to apply code patches.
\"\"\"
from pathlib import Path

def apply_patch(file_path: str, line_number: int, old_code: str, new_code: str) -> bool:
    \"\"\"Apply a patch to a file.\"\"\"
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if line_number < 1 or line_number > len(lines):
            print(f"Line {{line_number}} out of range in {{file_path}}")
            return False
        
        # Check if old_code matches
        line_idx = line_number - 1
        current_line = lines[line_idx].rstrip()
        
        if old_code.strip() not in current_line:
            print(f"Line {{line_number}} doesn't match expected code in {{file_path}}")
            print(f"Expected: {{old_code}}")
            print(f"Found: {{current_line}}")
            return False
        
        # Apply patch
        lines[line_idx] = new_code + '\\n'
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        return True
    except Exception as e:
        print(f"Error applying patch to {{file_path}}: {{e}}")
        return False

# Patches to apply
patches = {patches}

fixed_count = 0
for patch in patches:
    if apply_patch(patch['file_path'], patch['line_number'], 
                   patch['old_code'], patch['new_code']):
        print(f"Applied patch to {{patch['file_path']}}:{{patch['line_number']}}")
        fixed_count += 1

print(f"\\nApplied {{fixed_count}} patch(es))
""",
            
            # THREAD ISSUES: Script templates for thread-related fixes
            "fix_indentation_errors": """#!/usr/bin/env python3
\"\"\"
Auto-generated script to fix indentation errors.
\"\"\"
import ast
import re
from pathlib import Path

def fix_indentation(file_path: str) -> bool:
    \"\"\"Fix indentation errors in a Python file.\"\"\"
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        original_content = ''.join(lines)
        fixed_lines = []
        indent_stack = [0]  # Track indentation levels
        
        for i, line in enumerate(lines, 1):
            stripped = line.lstrip()
            if not stripped or stripped.startswith('#'):
                fixed_lines.append(line)
                continue
            
            # Determine correct indentation
            current_indent = len(line) - len(stripped)
            
            # Check for control structures that should increase indent
            if any(stripped.startswith(kw + ' ') or stripped.startswith(kw + ':') 
                   for kw in ['if', 'elif', 'else', 'for', 'while', 'def', 'class', 
                             'try', 'except', 'finally', 'with']):
                # Next line should be indented
                fixed_lines.append(line)
            elif line.strip().endswith(':'):
                # Line ends with colon - next should be indented
                fixed_lines.append(line)
            else:
                # Regular line - maintain consistent indentation
                # Use 4 spaces per level (Python standard)
                expected_indent = indent_stack[-1]
                fixed_line = ' ' * expected_indent + stripped
                fixed_lines.append(fixed_line)
        
        # Try to parse to verify fix
        try:
            ast.parse(''.join(fixed_lines))
            # Write fixed content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(fixed_lines)
            return True
        except SyntaxError:
            # Still has errors - may need manual fix
            return False
            
    except Exception as e:
        print(f"Error fixing indentation in {{file_path}}: {{e}}")
        return False

# Files to fix
files_to_fix = {file_paths}

fixed_count = 0
for file_path in files_to_fix:
    if fix_indentation(file_path):
        print(f"Fixed indentation: {{file_path}}")
        fixed_count += 1

print(f"\\nFixed {{fixed_count}} file(s)")
""",
            
            "fix_database_datatype_mismatch": """#!/usr/bin/env python3
\"\"\"
Auto-generated script to fix database datatype mismatch by recreating database.
\"\"\"
import shutil
from pathlib import Path
import sys

def recreate_database(db_path: str, backup: bool = True) -> bool:
    \"\"\"Recreate database to fix schema mismatches.\"\"\"
    try:
        db_file = Path(db_path)
        
        if not db_file.exists():
            print(f"Database file not found: {{db_path}}")
            return False
        
        # Create backup
        if backup:
            backup_path = db_file.with_suffix('.db.backup')
            shutil.copy2(db_file, backup_path)
            print(f"Created backup: {{backup_path}}")
        
        # Delete database
        db_file.unlink()
        print(f"Deleted database: {{db_path}}")
        
        # Database will be recreated on next startup
        print("Database will be recreated automatically on backend startup")
        return True
        
    except Exception as e:
        print(f"Error recreating database: {{e}}")
        return False

# Database path
db_path = {db_path}

if recreate_database(db_path):
    print("\\n✓ Database recreated successfully")
    print("Restart the backend to recreate tables")
else:
    print("\\n✗ Failed to recreate database")
    sys.exit(1)
""",
            
            "fix_port_conflict": """#!/usr/bin/env python3
\"\"\"
Auto-generated script to find and use an available port.
\"\"\"
import socket

def find_available_port(start_port: int = 8000, max_attempts: int = 100) -> int:
    \"\"\"Find an available port starting from start_port.\"\"\"
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('localhost', port))
                if result != 0:  # Port is available
                    return port
        except Exception:
            continue
    return None

# Find available port
new_port = find_available_port({start_port})

if new_port:
    print(f"Available port found: {{new_port}}")
    print(f"Update configuration to use port {{new_port}}")
    print(f"Or set environment variable: BACKEND_PORT={{new_port}}")
else:
    print(f"Could not find available port starting from {{start_port}}")
""",
            
            "create_missing_directory": """#!/usr/bin/env python3
\"\"\"
Auto-generated script to create missing directories.
\"\"\"
from pathlib import Path

def create_directory(dir_path: str, parents: bool = True) -> bool:
    \"\"\"Create directory if it doesn't exist.\"\"\"
    try:
        path = Path(dir_path)
        path.mkdir(parents=parents, exist_ok=True)
        print(f"Created directory: {{dir_path}}")
        return True
    except Exception as e:
        print(f"Error creating directory {{dir_path}}: {{e}}")
        return False

# Directories to create
directories = {directories}

created_count = 0
for dir_path in directories:
    if create_directory(dir_path):
        created_count += 1

print(f"\\nCreated {{created_count}} directory/directories")
""",
            
            # New fix scripts for backend import issues
            "fix_backend_import_paths": """#!/usr/bin/env python3
\"\"\"
Auto-generated script to fix 'from backend.xxx' import paths.
When running from within the backend directory, imports should not have 'backend.' prefix.
\"\"\"
import re
from pathlib import Path
from typing import List, Tuple

def fix_import_paths(file_path: str) -> Tuple[bool, int]:
    \"\"\"Fix 'from backend.' imports to relative imports.\"\"\"
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        fix_count = 0
        
        # Pattern to match 'from backend.xxx import yyy'
        pattern = r'from backend\.(\S+) import'
        
        def replace_import(match):
            nonlocal fix_count
            fix_count += 1
            module_path = match.group(1)
            return f'from {module_path} import'
        
        content = re.sub(pattern, replace_import, content)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, fix_count
        return False, 0
    except Exception as e:
        print(f"Error fixing {{file_path}}: {{e}}")
        return False, 0

def scan_and_fix_directory(directory: str) -> dict:
    \"\"\"Scan directory and fix all Python files with wrong imports.\"\"\"
    results = {{'files_fixed': 0, 'imports_fixed': 0, 'files_scanned': 0}}
    
    for py_file in Path(directory).rglob('*.py'):
        if '__pycache__' in str(py_file) or '.backup' in str(py_file):
            continue
        
        results['files_scanned'] += 1
        fixed, count = fix_import_paths(str(py_file))
        if fixed:
            results['files_fixed'] += 1
            results['imports_fixed'] += count
            print(f"Fixed {{count}} imports in {{py_file}}")
    
    return results

# Run fix on backend directory
backend_dir = "{backend_directory}"
results = scan_and_fix_directory(backend_dir)
print(f"\\nSummary:")
print(f"  Files scanned: {{results['files_scanned']}}")
print(f"  Files fixed: {{results['files_fixed']}}")
print(f"  Imports fixed: {{results['imports_fixed']}}")
""",
            
            "fix_logger_in_class": """#!/usr/bin/env python3
\"\"\"
Auto-generated script to fix logger defined inside class (moves to module level).
\"\"\"
import re
from pathlib import Path
from typing import Tuple

def fix_logger_placement(file_path: str) -> Tuple[bool, str]:
    \"\"\"Move logger from inside class to module level.\"\"\"
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        original_content = ''.join(lines)
        
        # Find class definitions with logger inside
        class_pattern = re.compile(r'^class\\s+(\\w+).*:\\s*$')
        logger_pattern = re.compile(r'^\\s+logger\\s*=\\s*logging\\.getLogger\\(__name__\\)')
        
        # Track if we need to add logger at module level
        has_module_logger = any('logger = logging.getLogger(__name__)' in line 
                                and not line.startswith(' ') for line in lines)
        
        fixed_lines = []
        lines_to_remove = []
        
        for i, line in enumerate(lines):
            # Check if this is a logger line inside a class
            if logger_pattern.match(line):
                # Check if previous non-blank line is a class definition or docstring
                # This means logger is incorrectly inside the class
                lines_to_remove.append(i)
                continue
            
            fixed_lines.append(line)
        
        if lines_to_remove and not has_module_logger:
            # Add module-level logger after imports
            # Find the last import line
            last_import_idx = 0
            for i, line in enumerate(fixed_lines):
                if line.startswith('import ') or line.startswith('from '):
                    last_import_idx = i
            
            # Insert logger after imports
            fixed_lines.insert(last_import_idx + 1, '\\nlogger = logging.getLogger(__name__)\\n')
        
        new_content = ''.join(fixed_lines)
        
        if new_content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True, f"Moved logger to module level in {{file_path}}"
        return False, "No changes needed"
    except Exception as e:
        return False, f"Error: {{e}}"

# Fix file
file_to_fix = "{file_path}"
success, message = fix_logger_placement(file_to_fix)
print(message)
""",
            
            "add_missing_factory_function": """#!/usr/bin/env python3
\"\"\"
Auto-generated script to add a missing factory function (get_xxx pattern).
\"\"\"
from pathlib import Path

def add_factory_function(file_path: str, class_name: str) -> bool:
    \"\"\"Add a factory function for a class.\"\"\"
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Generate factory function name
        # CamelCase to snake_case
        import re
        snake_case = re.sub('(.)([A-Z][a-z]+)', r'\\1_\\2', class_name)
        snake_case = re.sub('([a-z0-9])([A-Z])', r'\\1_\\2', snake_case).lower()
        func_name = f"get_{{snake_case}}"
        
        # Check if factory function already exists
        if func_name in content:
            print(f"Factory function {{func_name}} already exists")
            return False
        
        # Add factory function at end of file
        factory_code = f'''

# Factory function for getting {{class_name}} instance
_{{snake_case}}_instance = None


def {{func_name}}(**kwargs) -> {{class_name}}:
    \"\"\"Get or create the {{class_name}} singleton.\"\"\"
    global _{{snake_case}}_instance
    
    if _{{snake_case}}_instance is None:
        _{{snake_case}}_instance = {{class_name}}(**kwargs)
    
    return _{{snake_case}}_instance
'''
        
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(factory_code)
        
        print(f"Added factory function {{func_name}} to {{file_path}}")
        return True
    except Exception as e:
        print(f"Error adding factory function: {{e}}")
        return False

# Add factory function
file_path = "{file_path}"
class_name = "{class_name}"
add_factory_function(file_path, class_name)
""",
            
            "add_missing_router": """#!/usr/bin/env python3
\"\"\"
Auto-generated script to add missing FastAPI router definition.
\"\"\"
import re
from pathlib import Path

def add_router_definition(file_path: str, prefix: str = None, tag: str = None) -> bool:
    \"\"\"Add router definition to a FastAPI endpoint file.\"\"\"
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if router already defined
        if 'router = APIRouter' in content:
            print("Router already defined")
            return False
        
        # Determine prefix and tag from filename
        if prefix is None:
            file_name = Path(file_path).stem
            prefix = '/' + file_name.replace('_endpoint', '').replace('_api', '').replace('_', '-')
        
        if tag is None:
            tag = Path(file_path).stem.replace('_', '-')
        
        # Find where to insert router (after imports, before first function/class)
        lines = content.split('\\n')
        insert_line = 0
        
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                insert_line = i + 1
            elif line.startswith('def ') or line.startswith('class ') or line.startswith('@'):
                break
        
        # Check if APIRouter import exists
        if 'from fastapi import' in content and 'APIRouter' not in content:
            # Add APIRouter to existing import
            content = re.sub(
                r'from fastapi import ([^\\n]+)',
                r'from fastapi import \\1, APIRouter',
                content,
                count=1
            )
        elif 'from fastapi import' not in content:
            lines.insert(0, 'from fastapi import APIRouter')
            insert_line += 1
        
        # Add router definition
        router_line = f'\\nrouter = APIRouter(prefix="{{prefix}}", tags=["{{tag}}"])\\n'
        lines.insert(insert_line, router_line)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\\n'.join(lines))
        
        print(f"Added router definition to {{file_path}}")
        return True
    except Exception as e:
        print(f"Error adding router: {{e}}")
        return False

# Add router
file_path = "{file_path}"
add_router_definition(file_path, prefix="{prefix}", tag="{tag}")
"""
        }
    
    def identify_issue_type(self, error_message: str) -> Optional[Tuple[IssueType, FixPattern]]:
        """Identify the issue type from an error message."""
        for pattern in self.fix_patterns:
            if re.search(pattern.pattern, error_message, re.IGNORECASE):
                return pattern.issue_type, pattern
        return None
    
    def generate_fix_suggestion(
        self,
        issue_type: IssueType,
        error_message: str,
        file_path: Optional[str] = None,
        line_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """Generate a fix suggestion for an issue."""
        pattern = next((p for p in self.fix_patterns if p.issue_type == issue_type), None)
        if not pattern:
            return {
                "fix_available": False,
                "reason": "No fix pattern found for this issue type"
            }
        
        # Extract context from error message
        context = {}
        if issue_type == IssueType.SQLALCHEMY_TABLE_REDEFINITION:
            match = re.search(r"Table ['\"](\w+)['\"]", error_message)
            if match:
                context["table_name"] = match.group(1)
                context["TableName"] = match.group(1).title().replace('_', '')
            else:
                # Default values if table name can't be extracted
                context["table_name"] = "table"
                context["TableName"] = "Table"
        
        # Generate fix - use safe formatting to handle missing keys
        try:
            fix_text = pattern.fix_template.format(**context)
        except KeyError as e:
            # If template has keys not in context, use safe substitution
            fix_text = pattern.fix_template
            for key, value in context.items():
                fix_text = fix_text.replace(f"{{{key}}}", str(value))
            # Remove any remaining {key} patterns
            import re
            fix_text = re.sub(r'\{[^}]+\}', '', fix_text)
        
        return {
            "fix_available": True,
            "issue_type": issue_type.value,
            "confidence": pattern.confidence,
            "description": pattern.description,
            "fix_text": fix_text,
            "file_path": file_path,
            "line_number": line_number,
            "context": context
        }
    
    def generate_script(
        self,
        script_type: str,
        parameters: Dict[str, Any]
    ) -> str:
        """Generate a Python script for automated fixing."""
        template = self.script_templates.get(script_type)
        if not template:
            raise ValueError(f"Unknown script type: {script_type}")
        
        return template.format(**parameters)
    
    def generate_patch(
        self,
        file_path: str,
        issue_type: IssueType,
        error_message: str,
        line_number: Optional[int] = None
    ) -> Optional[CodePatch]:
        """Generate a code patch for an issue."""
        pattern = next((p for p in self.fix_patterns if p.issue_type == issue_type), None)
        if not pattern:
            return None
        
        # Read file to get context
        try:
            from pathlib import Path
            file = Path(file_path)
            if not file.exists():
                return None
            
            with open(file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if line_number and 1 <= line_number <= len(lines):
                old_code = lines[line_number - 1].rstrip()
            else:
                # Try to find the issue
                old_code = ""
                for i, line in enumerate(lines, 1):
                    if re.search(pattern.pattern, line, re.IGNORECASE):
                        old_code = line.rstrip()
                        line_number = i
                        break
            
            if not old_code:
                return None
            
            # Generate new code based on pattern
            new_code = self._generate_new_code(old_code, pattern, error_message)
            
            if new_code and new_code != old_code:
                return CodePatch(
                    file_path=file_path,
                    line_number=line_number or 1,
                    old_code=old_code,
                    new_code=new_code,
                    reason=pattern.description,
                    confidence=pattern.confidence
                )
        except Exception as e:
            logger.error(f"Error generating patch: {e}")
        
        return None
    
    def _generate_new_code(
        self,
        old_code: str,
        pattern: FixPattern,
        error_message: str
    ) -> Optional[str]:
        """Generate new code from old code using pattern."""
        if pattern.issue_type == IssueType.SQLALCHEMY_TABLE_REDEFINITION:
            # Extract table name (try multiple patterns)
            match = re.search(r"Table ['\"](\w+)['\"]", error_message)
            if not match:
                # Try alternative pattern
                match = re.search(r"table['\"]?\s*:?\s*['\"]?(\w+)['\"]", error_message, re.IGNORECASE)
            
            # Check if it's a Table() constructor
            if "Table(" in old_code and "extend_existing" not in old_code:
                # Add extend_existing=True
                if old_code.rstrip().endswith(')'):
                    return old_code.rstrip()[:-1] + ", extend_existing=True)"
                else:
                    return old_code + ", extend_existing=True"
            
            # For declarative base, we can't fix a single line - need script
            # Return None to trigger script generation instead
            return None
        
        return None
    
    def get_all_fix_patterns(self) -> List[FixPattern]:
        """Get all available fix patterns."""
        return self.fix_patterns


# Global instance
_healing_kb: Optional[HealingKnowledgeBase] = None


def get_healing_knowledge_base() -> HealingKnowledgeBase:
    """Get or create global healing knowledge base."""
    global _healing_kb
    if _healing_kb is None:
        _healing_kb = HealingKnowledgeBase()
    return _healing_kb
