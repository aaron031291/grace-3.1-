"""
Deterministic System Introspection Engine
==========================================
Catalogs EVERYTHING in the Grace system so anyone new can come in,
search, and understand the entire architecture without context.

Indexes:
- Every Python file with classes, functions, imports
- Every API endpoint (routers, paths, methods)
- Every model/weight reference
- Every configuration setting
- Every connector and its actions
- Every data flow relationship
- Every LLM client (Kimi, Opus, Ollama, etc.)

All deterministic. No LLM needed. Pure AST + structural analysis.
"""

import ast
import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).parent


@dataclass
class FileIndex:
    """Index entry for a single Python file."""
    path: str
    category: str
    classes: List[str]
    functions: List[str]
    imports: List[str]
    docstring: Optional[str]
    line_count: int
    has_router: bool = False
    router_prefix: Optional[str] = None
    has_tests: bool = False


@dataclass
class APIEndpoint:
    """A discovered API endpoint."""
    method: str
    path: str
    function_name: str
    file: str
    tags: List[str]
    description: Optional[str] = None


@dataclass
class ConnectorInfo:
    """A Layer 1 connector with its actions."""
    name: str
    file: str
    component_type: str
    autonomous_actions: List[str]
    request_handlers: List[str]
    subscriptions: List[str]
    description: Optional[str] = None


@dataclass
class SystemIndex:
    """Complete searchable index of the Grace system."""
    timestamp: str
    files: List[FileIndex]
    endpoints: List[APIEndpoint]
    connectors: List[ConnectorInfo]
    models: Dict[str, Any]
    settings: Dict[str, Any]
    data_flows: List[Dict[str, str]]
    file_count: int
    total_classes: int
    total_functions: int
    total_endpoints: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "file_count": self.file_count,
            "total_classes": self.total_classes,
            "total_functions": self.total_functions,
            "total_endpoints": self.total_endpoints,
            "files": [asdict(f) for f in self.files],
            "endpoints": [asdict(e) for e in self.endpoints],
            "connectors": [asdict(c) for c in self.connectors],
            "models": self.models,
            "settings": self.settings,
            "data_flows": self.data_flows,
        }

    def search(self, query: str) -> Dict[str, Any]:
        """Search the index for a query string."""
        q = query.lower()
        terms = [t for t in q.split() if len(t) > 1]

        results = {
            "query": query,
            "files": [],
            "endpoints": [],
            "connectors": [],
            "classes": [],
            "functions": [],
            "settings": [],
        }

        for f in self.files:
            score = 0
            for term in terms:
                if term in f.path.lower():
                    score += 3
                if f.docstring and term in f.docstring.lower():
                    score += 2
                if term in f.category.lower():
                    score += 1
                for cls in f.classes:
                    if term in cls.lower():
                        score += 2
                        results["classes"].append({"class": cls, "file": f.path})
                for fn in f.functions:
                    if term in fn.lower():
                        score += 1
                        results["functions"].append({"function": fn, "file": f.path})
            if score > 0:
                results["files"].append({"path": f.path, "category": f.category,
                                         "relevance": score, "docstring": (f.docstring or "")[:200]})

        for ep in self.endpoints:
            score = 0
            for term in terms:
                if term in ep.path.lower():
                    score += 3
                if term in ep.function_name.lower():
                    score += 2
                if ep.description and term in ep.description.lower():
                    score += 1
                for tag in ep.tags:
                    if term in tag.lower():
                        score += 1
            if score > 0:
                results["endpoints"].append({"method": ep.method, "path": ep.path,
                                              "function": ep.function_name, "file": ep.file,
                                              "relevance": score})

        for c in self.connectors:
            score = 0
            for term in terms:
                if term in c.name.lower() or term in c.component_type.lower():
                    score += 3
                if c.description and term in c.description.lower():
                    score += 2
            if score > 0:
                results["connectors"].append({"name": c.name, "type": c.component_type,
                                               "file": c.file, "relevance": score})

        for key, val in self.settings.items():
            for term in terms:
                if term in key.lower():
                    results["settings"].append({"key": key, "value": str(val)[:100]})

        for key in results:
            if isinstance(results[key], list):
                results[key] = sorted(results[key],
                                       key=lambda x: x.get("relevance", 0),
                                       reverse=True)[:20]

        results["total_results"] = sum(len(v) for v in results.values() if isinstance(v, list))
        return results


# ---------------------------------------------------------------------------
# Indexing Functions
# ---------------------------------------------------------------------------

def _categorize_file(rel_path: str) -> str:
    """Categorize a file by its directory."""
    parts = Path(rel_path).parts
    if not parts:
        return "root"

    category_map = {
        "api": "api",
        "cognitive": "cognitive",
        "core": "core",
        "database": "database",
        "diagnostic_machine": "diagnostics",
        "embedding": "embedding",
        "genesis": "genesis",
        "grace_mcp": "mcp",
        "grace_os": "os_layers",
        "ingestion": "ingestion",
        "layer1": "layer1",
        "librarian": "librarian",
        "llm_orchestrator": "llm",
        "ml_intelligence": "ml_intelligence",
        "models": "models",
        "retrieval": "retrieval",
        "search": "search",
        "security": "security",
        "vector_db": "vector_db",
        "file_manager": "file_manager",
        "tests": "tests",
    }

    return category_map.get(parts[0], parts[0])


def index_python_files(root: Path = BACKEND_ROOT) -> List[FileIndex]:
    """Index every Python file with classes, functions, imports."""
    files = []
    skip_dirs = {'__pycache__', 'venv', 'node_modules', '.git', 'mcp_repos', 'knowledge_base'}

    for py_file in sorted(root.rglob("*.py")):
        if any(skip in py_file.parts for skip in skip_dirs):
            continue

        try:
            source = py_file.read_text(errors="ignore")
            tree = ast.parse(source, filename=str(py_file))
        except (SyntaxError, UnicodeDecodeError):
            continue

        rel_path = str(py_file.relative_to(root))

        classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        functions = [n.name for n in ast.iter_child_nodes(tree)
                     if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]

        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)

        docstring = ast.get_docstring(tree)

        has_router = "router" in source and "APIRouter" in source
        router_prefix = None
        if has_router:
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for t in node.targets:
                        if isinstance(t, ast.Name) and t.id == "router" and isinstance(node.value, ast.Call):
                            for kw in node.value.keywords:
                                if kw.arg == "prefix" and isinstance(kw.value, ast.Constant):
                                    router_prefix = kw.value.value

        files.append(FileIndex(
            path=rel_path,
            category=_categorize_file(rel_path),
            classes=classes[:30],
            functions=functions[:50],
            imports=list(set(imports))[:30],
            docstring=(docstring or "")[:500],
            line_count=source.count("\n") + 1,
            has_router=has_router,
            router_prefix=router_prefix,
            has_tests="test_" in py_file.name or py_file.name.startswith("test"),
        ))

    return files


def index_api_endpoints(root: Path = BACKEND_ROOT) -> List[APIEndpoint]:
    """
    Index all API endpoints by parsing router decorators.
    Finds @router.get, @app.get, @router.post, etc.
    """
    endpoints = []
    skip_dirs = {'__pycache__', 'venv', 'node_modules', '.git'}

    for py_file in root.rglob("*.py"):
        if any(skip in py_file.parts for skip in skip_dirs):
            continue

        try:
            source = py_file.read_text(errors="ignore")
            tree = ast.parse(source, filename=str(py_file))
        except (SyntaxError, UnicodeDecodeError):
            continue

        rel_path = str(py_file.relative_to(root))

        router_prefix = ""
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name) and t.id == "router" and isinstance(node.value, ast.Call):
                        for kw in node.value.keywords:
                            if kw.arg == "prefix" and isinstance(kw.value, ast.Constant):
                                router_prefix = kw.value.value

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for decorator in node.decorator_list:
                    if not isinstance(decorator, ast.Call):
                        continue
                    func = decorator.func
                    method = None
                    if isinstance(func, ast.Attribute):
                        if func.attr in ('get', 'post', 'put', 'delete', 'patch', 'websocket'):
                            method = func.attr.upper()

                    if method and decorator.args:
                        path_arg = decorator.args[0]
                        if isinstance(path_arg, ast.Constant):
                            full_path = router_prefix + path_arg.value

                            tags = []
                            for kw in decorator.keywords:
                                if kw.arg == "tags" and isinstance(kw.value, ast.List):
                                    for elt in kw.value.elts:
                                        if isinstance(elt, ast.Constant):
                                            tags.append(elt.value)

                            docstring = ast.get_docstring(node)

                            endpoints.append(APIEndpoint(
                                method=method,
                                path=full_path,
                                function_name=node.name,
                                file=rel_path,
                                tags=tags,
                                description=(docstring or "")[:200],
                            ))

    return endpoints


def index_connectors(root: Path = BACKEND_ROOT) -> List[ConnectorInfo]:
    """Index all Layer 1 connectors and their capabilities."""
    connectors = []
    connector_dir = root / "layer1" / "components"

    if not connector_dir.exists():
        return connectors

    for py_file in connector_dir.glob("*_connector.py"):
        try:
            source = py_file.read_text(errors="ignore")
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError):
            continue

        rel_path = str(py_file.relative_to(root))
        docstring = ast.get_docstring(tree) or ""

        classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        main_class = classes[0] if classes else None

        autonomous_actions = []
        request_handlers = []
        subscriptions = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute):
                    if func.attr == "register_autonomous_action":
                        for kw in node.keywords:
                            if kw.arg == "description" and isinstance(kw.value, ast.Constant):
                                autonomous_actions.append(kw.value.value)
                    elif func.attr == "register_request_handler":
                        for kw in node.keywords:
                            if kw.arg == "topic" and isinstance(kw.value, ast.Constant):
                                request_handlers.append(kw.value.value)
                    elif func.attr == "subscribe":
                        for kw in node.keywords:
                            if kw.arg == "topic" and isinstance(kw.value, ast.Constant):
                                subscriptions.append(kw.value.value)

        component_type = py_file.stem.replace("_connector", "")

        connectors.append(ConnectorInfo(
            name=main_class.name if main_class else py_file.stem,
            file=rel_path,
            component_type=component_type,
            autonomous_actions=autonomous_actions,
            request_handlers=request_handlers,
            subscriptions=subscriptions,
            description=docstring[:300],
        ))

    return connectors


def index_models_and_weights(root: Path = BACKEND_ROOT) -> Dict[str, Any]:
    """Index all model references, weights, and LLM configurations."""
    models = {
        "llm_providers": [],
        "embedding_models": [],
        "ml_models": [],
        "configured_models": {},
    }

    # LLM clients
    llm_dir = root / "llm_orchestrator"
    if llm_dir.exists():
        for py_file in llm_dir.glob("*_client.py"):
            name = py_file.stem.replace("_client", "")
            try:
                source = py_file.read_text(errors="ignore")
                docstring_match = source.split('"""')[1] if '"""' in source else ""
                models["llm_providers"].append({
                    "name": name,
                    "file": str(py_file.relative_to(root)),
                    "description": docstring_match[:200].strip(),
                })
            except Exception:
                models["llm_providers"].append({"name": name, "file": str(py_file.relative_to(root))})

    # Embedding models
    try:
        from settings import settings
        models["embedding_models"].append({
            "name": getattr(settings, 'EMBEDDING_DEFAULT', 'all-MiniLM-L6-v2'),
            "device": getattr(settings, 'EMBEDDING_DEVICE', 'cpu'),
            "path": getattr(settings, 'EMBEDDING_MODEL_PATH', ''),
        })
        models["configured_models"] = {
            "primary_llm": getattr(settings, 'LLM_MODEL', '') or getattr(settings, 'OLLAMA_LLM_DEFAULT', 'mistral:7b'),
            "provider": getattr(settings, 'LLM_PROVIDER', 'ollama'),
            "kimi_model": getattr(settings, 'KIMI_MODEL', 'kimi-k2.5'),
            "opus_model": getattr(settings, 'OPUS_MODEL', 'claude-sonnet-4-20250514'),
            "code_model": getattr(settings, 'OLLAMA_MODEL_CODE', 'qwen3.5-coder:7b'),
            "reasoning_model": getattr(settings, 'OLLAMA_MODEL_REASON', 'deepseek-r1:7b'),
            "fast_model": getattr(settings, 'OLLAMA_MODEL_FAST', 'qwen3.5:7b'),
        }
    except ImportError:
        pass

    # ML/DL models
    ml_dir = root / "ml_intelligence"
    if ml_dir.exists():
        for py_file in ml_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            try:
                source = py_file.read_text(errors="ignore")
                if "torch" in source or "nn.Module" in source or "sklearn" in source:
                    models["ml_models"].append({
                        "name": py_file.stem,
                        "file": str(py_file.relative_to(root)),
                        "type": "pytorch" if "torch" in source else "sklearn",
                    })
            except Exception:
                pass

    dl_file = root / "core" / "deep_learning.py"
    if dl_file.exists():
        models["ml_models"].append({
            "name": "deep_learning",
            "file": "core/deep_learning.py",
            "type": "pytorch",
            "description": "3-head MLP predicting success/risk/trust from Genesis keys",
        })

    return models


def index_settings(root: Path = BACKEND_ROOT) -> Dict[str, Any]:
    """Index all configuration settings."""
    settings_file = root / "settings.py"
    if not settings_file.exists():
        return {}

    settings_map = {}
    try:
        source = settings_file.read_text(errors="ignore")
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                name = node.target.id
                if name.isupper():
                    value = None
                    if isinstance(node.value, ast.Constant):
                        value = node.value.value
                    elif isinstance(node.value, ast.Call):
                        value = "(computed)"
                    settings_map[name] = {
                        "line": node.lineno,
                        "default": str(value)[:100] if value else "(computed)",
                    }
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        value = None
                        if isinstance(node.value, ast.Constant):
                            value = node.value.value
                        settings_map[target.id] = {
                            "line": node.lineno,
                            "default": str(value)[:100] if value else "(computed)",
                        }
    except Exception:
        pass

    return settings_map


def get_data_flows() -> List[Dict[str, str]]:
    """Return known data flow relationships in the system."""
    return [
        {"from": "user_input", "to": "brain_api", "via": "HTTP/WebSocket", "data": "Chat queries, commands"},
        {"from": "brain_api", "to": "llm_orchestrator", "via": "function call", "data": "LLM requests"},
        {"from": "brain_api", "to": "retrieval", "via": "function call", "data": "RAG queries"},
        {"from": "retrieval", "to": "qdrant", "via": "vector search", "data": "Embedding vectors"},
        {"from": "retrieval", "to": "embedding", "via": "function call", "data": "Text to embed"},
        {"from": "ingestion", "to": "qdrant", "via": "upsert", "data": "Document chunks + embeddings"},
        {"from": "ingestion", "to": "genesis_keys", "via": "Layer 1 bus", "data": "File provenance"},
        {"from": "genesis_keys", "to": "memory_mesh", "via": "Layer 1 bus", "data": "Learning linkage"},
        {"from": "memory_mesh", "to": "llm_orchestration", "via": "Layer 1 bus", "data": "Procedural skills"},
        {"from": "memory_mesh", "to": "autonomous_learning", "via": "Layer 1 bus", "data": "Pattern detection"},
        {"from": "file_watcher", "to": "version_control", "via": "Layer 1 bus", "data": "File changes"},
        {"from": "diagnostic_engine", "to": "healing_executor", "via": "action router", "data": "Healing commands"},
        {"from": "diagnostic_engine", "to": "websocket", "via": "event emitter", "data": "Health events"},
        {"from": "autonomous_loop", "to": "diagnostic_engine", "via": "function call", "data": "Cycle triggers"},
        {"from": "continuous_learning", "to": "memory_mesh", "via": "function call", "data": "Learning ingestion"},
        {"from": "consensus_engine", "to": "kimi_client", "via": "HTTP API", "data": "Reasoning requests"},
        {"from": "consensus_engine", "to": "opus_client", "via": "HTTP API", "data": "Audit + reasoning"},
        {"from": "consensus_engine", "to": "ollama_client", "via": "HTTP API", "data": "Local model requests"},
        {"from": "serpapi_service", "to": "knowledge_base", "via": "auto-ingest", "data": "Search results"},
        {"from": "llm_orchestrator", "to": "database", "via": "SQLAlchemy", "data": "Chat persistence"},
        {"from": "ml_intelligence", "to": "memory_mesh", "via": "trust scoring", "data": "KPI and trust"},
        {"from": "governance_engine", "to": "brain_api", "via": "approval workflow", "data": "Action approvals"},
        {"from": "coding_pipeline", "to": "deterministic_bridge", "via": "function call", "data": "Bug detection"},
        {"from": "coding_pipeline", "to": "safety", "via": "function call", "data": "Security scans"},
    ]


# ---------------------------------------------------------------------------
# Main Introspection
# ---------------------------------------------------------------------------

def build_system_index(root: Path = BACKEND_ROOT) -> SystemIndex:
    """Build the complete searchable system index."""
    logger.info("[INTROSPECTOR] Building system index...")

    files = index_python_files(root)
    endpoints = index_api_endpoints(root)
    connectors = index_connectors(root)
    models = index_models_and_weights(root)
    settings = index_settings(root)
    data_flows = get_data_flows()

    total_classes = sum(len(f.classes) for f in files)
    total_functions = sum(len(f.functions) for f in files)

    index = SystemIndex(
        timestamp=datetime.now(timezone.utc).isoformat(),
        files=files,
        endpoints=endpoints,
        connectors=connectors,
        models=models,
        settings=settings,
        data_flows=data_flows,
        file_count=len(files),
        total_classes=total_classes,
        total_functions=total_functions,
        total_endpoints=len(endpoints),
    )

    logger.info(
        f"[INTROSPECTOR] Index built: {len(files)} files, {total_classes} classes, "
        f"{total_functions} functions, {len(endpoints)} endpoints, "
        f"{len(connectors)} connectors"
    )

    return index


# Cached singleton
_cached_index: Optional[SystemIndex] = None


def get_system_index(force_rebuild: bool = False) -> SystemIndex:
    """Get or build the system index (cached)."""
    global _cached_index
    if _cached_index is None or force_rebuild:
        _cached_index = build_system_index()
    return _cached_index


def search_system(query: str) -> Dict[str, Any]:
    """Search across the entire Grace system."""
    index = get_system_index()
    return index.search(query)
