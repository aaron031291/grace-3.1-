"""
Oracle Source Code Index - Self-Awareness Layer

Grace reads her OWN source code into the Oracle (read-only) so every
subsystem can query "what's in the system?" and "what code handles X?"

This is how Grace becomes self-aware of her own infrastructure:
- The LLM can read source code to ground its answers
- The healing system knows what code to fix
- The building system knows what exists before creating
- The hallucination guard verifies claims against actual code
- Any subsystem queries the Oracle to check what's real

Read-only: no subsystem can modify source code through this index.
Modifications go through the normal file management / git flow.

The index stores:
- Module names and paths
- Function/class signatures
- Docstrings and comments
- Import relationships
- Configuration values
- Database schema references
"""

import logging
import re
import hashlib
import uuid
from typing import Dict, Any, Optional, List, Tuple, Set
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from pathlib import PurePosixPath

logger = logging.getLogger(__name__)


class CodeElementType(str, Enum):
    """Types of indexed code elements."""
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    IMPORT = "import"
    CONSTANT = "constant"
    CONFIG = "config"
    DOCSTRING = "docstring"
    COMMENT = "comment"
    SCHEMA = "schema"


@dataclass
class CodeElement:
    """An indexed element from the source code."""
    element_id: str
    element_type: CodeElementType
    name: str
    file_path: str
    line_number: int = 0
    signature: str = ""
    docstring: str = ""
    content: str = ""
    parent_element: Optional[str] = None  # parent class/module
    imports: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    content_hash: str = ""
    indexed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ModuleIndex:
    """Index of a single module/file."""
    file_path: str
    module_name: str
    classes: List[str] = field(default_factory=list)  # element_ids
    functions: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    constants: List[str] = field(default_factory=list)
    docstring: str = ""
    line_count: int = 0
    content_hash: str = ""


@dataclass
class SourceCodeQuery:
    """Result of querying the source code index."""
    query: str
    results: List[CodeElement]
    total_matches: int
    query_type: str  # "function", "class", "module", "keyword", "capability"


class SourceCodeIndex:
    """
    Read-only index of Grace's own source code.

    Any subsystem can query this to understand what exists in the system.
    The LLM uses this to ground answers in actual infrastructure.
    The hallucination guard verifies claims against this index.

    Features:
    - Index Python modules, classes, functions, imports
    - Extract docstrings and signatures
    - Track import dependencies between modules
    - Search by name, capability, or keyword
    - Read-only: no modification through this interface
    - Content hashing to detect when re-indexing is needed
    """

    # Patterns for Python code parsing
    CLASS_PATTERN = re.compile(r'^class\s+(\w+)(?:\(([^)]*)\))?:', re.MULTILINE)
    FUNC_PATTERN = re.compile(r'^(?:    )?(?:async\s+)?def\s+(\w+)\s*\(([^)]*)\)(?:\s*->\s*(\S+))?:', re.MULTILINE)
    IMPORT_PATTERN = re.compile(r'^(?:from\s+(\S+)\s+)?import\s+(.+)', re.MULTILINE)
    CONSTANT_PATTERN = re.compile(r'^([A-Z][A-Z_0-9]+)\s*=\s*(.+)', re.MULTILINE)
    DOCSTRING_PATTERN = re.compile(r'"""(.*?)"""', re.DOTALL)

    def __init__(self):
        self.elements: Dict[str, CodeElement] = {}
        self.modules: Dict[str, ModuleIndex] = {}
        self._name_index: Dict[str, List[str]] = {}  # name -> [element_ids]
        self._type_index: Dict[CodeElementType, List[str]] = {
            t: [] for t in CodeElementType
        }
        self._file_index: Dict[str, List[str]] = {}  # file_path -> [element_ids]
        self._capability_index: Dict[str, List[str]] = {}  # keyword -> [element_ids]
        logger.info("[SOURCE-INDEX] Source Code Index initialized (read-only)")

    def index_source_code(
        self, file_path: str, content: str, module_name: Optional[str] = None
    ) -> ModuleIndex:
        """
        Index a source code file (read-only scan).

        Extracts classes, functions, imports, constants, docstrings.

        Args:
            file_path: Path to the source file
            content: Source code content
            module_name: Module name (auto-detected if not provided)

        Returns:
            ModuleIndex for the file
        """
        if not module_name:
            module_name = PurePosixPath(file_path).stem

        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        # Skip if already indexed with same hash
        if file_path in self.modules:
            if self.modules[file_path].content_hash == content_hash:
                return self.modules[file_path]

        module = ModuleIndex(
            file_path=file_path,
            module_name=module_name,
            line_count=content.count("\n") + 1,
            content_hash=content_hash,
        )

        # Extract module docstring
        doc_match = self.DOCSTRING_PATTERN.search(content[:500])
        if doc_match:
            module.docstring = doc_match.group(1).strip()

        # Extract classes
        for match in self.CLASS_PATTERN.finditer(content):
            class_name = match.group(1)
            bases = match.group(2) or ""
            line_num = content[:match.start()].count("\n") + 1

            # Find class docstring
            class_doc = ""
            after_class = content[match.end():]
            doc_match = self.DOCSTRING_PATTERN.search(after_class[:300])
            if doc_match:
                class_doc = doc_match.group(1).strip()

            elem = CodeElement(
                element_id=f"ce-{uuid.uuid4().hex[:12]}",
                element_type=CodeElementType.CLASS,
                name=class_name,
                file_path=file_path,
                line_number=line_num,
                signature=f"class {class_name}({bases})" if bases else f"class {class_name}",
                docstring=class_doc,
                parent_element=module_name,
                metadata={"bases": bases},
            )
            self._register_element(elem)
            module.classes.append(elem.element_id)

        # Extract functions
        for match in self.FUNC_PATTERN.finditer(content):
            func_name = match.group(1)
            params = match.group(2) or ""
            return_type = match.group(3) or ""
            line_num = content[:match.start()].count("\n") + 1

            # Find function docstring
            func_doc = ""
            after_func = content[match.end():]
            doc_match = self.DOCSTRING_PATTERN.search(after_func[:300])
            if doc_match:
                func_doc = doc_match.group(1).strip()

            # Determine if it's a method (indented) or function
            is_method = content[match.start() - 1:match.start()] == " " if match.start() > 0 else False
            elem_type = CodeElementType.METHOD if is_method else CodeElementType.FUNCTION

            sig = f"def {func_name}({params})"
            if return_type:
                sig += f" -> {return_type}"

            elem = CodeElement(
                element_id=f"ce-{uuid.uuid4().hex[:12]}",
                element_type=elem_type,
                name=func_name,
                file_path=file_path,
                line_number=line_num,
                signature=sig,
                docstring=func_doc,
                parent_element=module_name,
                metadata={"params": params, "return_type": return_type},
            )
            self._register_element(elem)
            module.functions.append(elem.element_id)

        # Extract imports
        for match in self.IMPORT_PATTERN.finditer(content):
            from_module = match.group(1) or ""
            imported = match.group(2).strip()
            line_num = content[:match.start()].count("\n") + 1

            import_str = f"from {from_module} import {imported}" if from_module else f"import {imported}"

            elem = CodeElement(
                element_id=f"ce-{uuid.uuid4().hex[:12]}",
                element_type=CodeElementType.IMPORT,
                name=imported.split(",")[0].strip().split(" as ")[0].strip(),
                file_path=file_path,
                line_number=line_num,
                signature=import_str,
                parent_element=module_name,
                dependencies=[from_module] if from_module else [imported.split(".")[0]],
            )
            self._register_element(elem)
            module.imports.append(elem.element_id)

        # Extract constants
        for match in self.CONSTANT_PATTERN.finditer(content):
            const_name = match.group(1)
            const_value = match.group(2).strip()[:100]
            line_num = content[:match.start()].count("\n") + 1

            elem = CodeElement(
                element_id=f"ce-{uuid.uuid4().hex[:12]}",
                element_type=CodeElementType.CONSTANT,
                name=const_name,
                file_path=file_path,
                line_number=line_num,
                signature=f"{const_name} = {const_value}",
                content=const_value,
                parent_element=module_name,
            )
            self._register_element(elem)
            module.constants.append(elem.element_id)

        self.modules[file_path] = module
        logger.info(
            f"[SOURCE-INDEX] Indexed {file_path}: "
            f"{len(module.classes)} classes, {len(module.functions)} functions, "
            f"{len(module.imports)} imports"
        )

        return module

    def _register_element(self, elem: CodeElement) -> None:
        """Register an element in all indices."""
        self.elements[elem.element_id] = elem

        # Name index
        name_lower = elem.name.lower()
        if name_lower not in self._name_index:
            self._name_index[name_lower] = []
        self._name_index[name_lower].append(elem.element_id)

        # Type index
        self._type_index[elem.element_type].append(elem.element_id)

        # File index
        if elem.file_path not in self._file_index:
            self._file_index[elem.file_path] = []
        self._file_index[elem.file_path].append(elem.element_id)

        # Capability index (index words from docstring and name)
        keywords = set()
        keywords.update(name_lower.split("_"))
        if elem.docstring:
            words = elem.docstring.lower().split()
            keywords.update(w.strip(".,!?:;()") for w in words if len(w) > 3)
        for kw in keywords:
            if kw not in self._capability_index:
                self._capability_index[kw] = []
            self._capability_index[kw].append(elem.element_id)

    # =========================================================================
    # READ-ONLY QUERY INTERFACE
    # =========================================================================

    def query_by_name(self, name: str) -> SourceCodeQuery:
        """Find code elements by name."""
        name_lower = name.lower()
        element_ids = self._name_index.get(name_lower, [])
        elements = [self.elements[eid] for eid in element_ids if eid in self.elements]
        return SourceCodeQuery(
            query=name, results=elements,
            total_matches=len(elements), query_type="name",
        )

    def query_by_type(self, element_type: CodeElementType) -> SourceCodeQuery:
        """Find all elements of a specific type."""
        element_ids = self._type_index.get(element_type, [])
        elements = [self.elements[eid] for eid in element_ids if eid in self.elements]
        return SourceCodeQuery(
            query=element_type.value, results=elements,
            total_matches=len(elements), query_type="type",
        )

    def query_by_capability(self, capability: str) -> SourceCodeQuery:
        """
        Find code elements by capability keyword.

        Searches docstrings and names for capability-related terms.
        This is how subsystems ask "what can handle X?"
        """
        keywords = capability.lower().split()
        all_ids: Set[str] = set()
        for kw in keywords:
            ids = self._capability_index.get(kw, [])
            all_ids.update(ids)

        elements = [self.elements[eid] for eid in all_ids if eid in self.elements]

        # Score by relevance (how many keywords match)
        scored: List[Tuple[CodeElement, int]] = []
        for elem in elements:
            text = f"{elem.name} {elem.docstring}".lower()
            matches = sum(1 for kw in keywords if kw in text)
            scored.append((elem, matches))
        scored.sort(key=lambda x: x[1], reverse=True)

        sorted_elements = [e for e, _ in scored]
        return SourceCodeQuery(
            query=capability, results=sorted_elements,
            total_matches=len(sorted_elements), query_type="capability",
        )

    def query_by_file(self, file_path: str) -> SourceCodeQuery:
        """Find all elements in a specific file."""
        element_ids = self._file_index.get(file_path, [])
        elements = [self.elements[eid] for eid in element_ids if eid in self.elements]
        return SourceCodeQuery(
            query=file_path, results=elements,
            total_matches=len(elements), query_type="file",
        )

    def query_keyword(self, keyword: str, limit: int = 20) -> SourceCodeQuery:
        """Search across all elements for a keyword."""
        keyword_lower = keyword.lower()
        results: List[CodeElement] = []

        for elem in self.elements.values():
            searchable = f"{elem.name} {elem.signature} {elem.docstring} {elem.content}".lower()
            if keyword_lower in searchable:
                results.append(elem)
                if len(results) >= limit:
                    break

        return SourceCodeQuery(
            query=keyword, results=results,
            total_matches=len(results), query_type="keyword",
        )

    def get_module_info(self, file_path: str) -> Optional[ModuleIndex]:
        """Get module index info."""
        return self.modules.get(file_path)

    def get_all_modules(self) -> List[ModuleIndex]:
        """Get all indexed modules."""
        return list(self.modules.values())

    def get_dependency_graph(self) -> Dict[str, List[str]]:
        """
        Build a dependency graph from import statements.

        Returns dict mapping module -> [dependencies].
        This is how Grace understands her own architecture.
        """
        graph: Dict[str, List[str]] = {}
        for file_path, module in self.modules.items():
            deps: Set[str] = set()
            for imp_id in module.imports:
                if imp_id in self.elements:
                    elem = self.elements[imp_id]
                    deps.update(elem.dependencies)
            graph[module.module_name] = list(deps)
        return graph

    def what_handles(self, capability: str) -> List[Dict[str, Any]]:
        """
        Answer: "What code handles X?"

        Returns modules and functions that handle a capability.
        Used by LLM to ground answers, by healing to find fix targets.
        """
        query_result = self.query_by_capability(capability)
        handlers: List[Dict[str, Any]] = []
        for elem in query_result.results[:10]:
            handlers.append({
                "name": elem.name,
                "type": elem.element_type.value,
                "file": elem.file_path,
                "line": elem.line_number,
                "signature": elem.signature,
                "docstring": elem.docstring[:200] if elem.docstring else "",
            })
        return handlers

    def what_exists(self, name: str) -> bool:
        """
        Answer: "Does X exist in the system?"

        Used by hallucination guard to verify claims about code.
        """
        return name.lower() in self._name_index

    def get_function_signature(self, func_name: str) -> Optional[str]:
        """Get the signature of a function by name."""
        query = self.query_by_name(func_name)
        for elem in query.results:
            if elem.element_type in (CodeElementType.FUNCTION, CodeElementType.METHOD):
                return elem.signature
        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        return {
            "total_modules": len(self.modules),
            "total_elements": len(self.elements),
            "classes": len(self._type_index[CodeElementType.CLASS]),
            "functions": len(self._type_index[CodeElementType.FUNCTION]),
            "methods": len(self._type_index[CodeElementType.METHOD]),
            "imports": len(self._type_index[CodeElementType.IMPORT]),
            "constants": len(self._type_index[CodeElementType.CONSTANT]),
            "total_lines": sum(m.line_count for m in self.modules.values()),
            "capability_keywords": len(self._capability_index),
        }
