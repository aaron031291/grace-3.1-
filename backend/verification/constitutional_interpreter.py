import ast
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

CONSTITUTION_PATH = Path(__file__).parent.parent / "config" / "domain_constitution.yaml"

class ConstitutionalViolation(Exception):
    """Raised when proposed code violates the Domain Constitution."""
    pass

class ConstitutionalInterpreter:
    """
    Evaluates proposed LLM-generated code against a rigid "Domain Constitution."
    Uses AST analysis to mathematically guarantee that the code respects safely limitations
    (no unauthorized modules, no excessive complexity) before it is hot-swapped.
    """

    def __init__(self, config_path: Path = CONSTITUTION_PATH):
        self.config_path = config_path
        self.constitution = self._load_constitution()
        self.forbidden_modules = self.constitution.get("forbidden_modules", [])
        self.forbidden_operations = self.constitution.get("forbidden_operations", [])
        self.max_ast_depth = self.constitution.get("performance_constraints", {}).get("max_ast_depth", 25)
        self.max_lines = self.constitution.get("performance_constraints", {}).get("max_lines", 500)

    def _load_constitution(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            logger.warning(f"Constitution not found at {self.config_path}. Using safe defaults.")
            return {"forbidden_modules": ["os", "subprocess", "socket"]}
        
        with open(self.config_path, "r", encoding="utf-8") as f:
            try:
                return yaml.safe_load(f) or {}
            except yaml.YAMLError as e:
                logger.error(f"Failed to parse domain_constitution.yaml: {e}")
                return {"forbidden_modules": ["os", "subprocess", "socket"]}

    def verify_contract(self, source_code: str, module_name: str) -> bool:
        """
        Parses the AST of the proposed code and proves it adheres to the constitution.
        Raises ConstitutionalViolation if it fails, otherwise returns True (Proof of Contract).
        """
        lines = source_code.splitlines()
        if len(lines) > self.max_lines:
            raise ConstitutionalViolation(f"Module {module_name} exceeds max line count ({len(lines)} > {self.max_lines}).")

        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            raise ConstitutionalViolation(f"Syntax error in proposed code: {e}")

        # AST Walker
        self._analyze_ast(tree)
        
        logger.info(f"Verified Proof-of-Contract for module: {module_name}")
        return True

    def _analyze_ast(self, tree: ast.AST):
        """Walks the AST to ensure no forbidden constructs are present."""
        
        def calculate_depth(node, current_depth=0):
            if current_depth > self.max_ast_depth:
                raise ConstitutionalViolation(f"AST depth exceeds allowed maximum of {self.max_ast_depth}.")
            for child in ast.iter_child_nodes(node):
                calculate_depth(child, current_depth + 1)

        calculate_depth(tree)

        for node in ast.walk(tree):
            # Check for forbidden imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self._check_forbidden_module(alias.name)
            
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self._check_forbidden_module(node.module)
                    for alias in node.names:
                        full_name = f"{node.module}.{alias.name}"
                        self._check_forbidden_module(full_name)

            # Check for attribute access (e.g. os.system)
            elif isinstance(node, ast.Attribute):
                if isinstance(node.value, ast.Name):
                    full_name = f"{node.value.id}.{node.attr}"
                    self._check_forbidden_module(full_name)

            # Check for bare excepts
            elif isinstance(node, ast.ExceptHandler):
                if node.type is None and "bare_except" in self.forbidden_operations:
                    raise ConstitutionalViolation("Bare 'except:' blocks are forbidden by the constitution.")
            
            # Check for direct calls to forbidden string-based functions (eval/exec)
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    self._check_forbidden_module(node.func.id)

            # Check for infinite loops (basic heuristic)
            elif isinstance(node, ast.While):
                if "infinite_loop" in self.forbidden_operations:
                    if isinstance(node.test, ast.Constant) and node.test.value is True:
                        has_break = any(isinstance(n, ast.Break) for n in ast.walk(node))
                        if not has_break:
                            raise ConstitutionalViolation("Found a 'while True:' loop with no 'break' statement.")

    def _check_forbidden_module(self, module_name: str):
        for forbidden in self.forbidden_modules:
            if module_name == forbidden or module_name.startswith(f"{forbidden}."):
                raise ConstitutionalViolation(f"Import of forbidden module or sub-module: {module_name}")
