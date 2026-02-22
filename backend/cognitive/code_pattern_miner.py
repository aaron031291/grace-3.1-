"""
Code Pattern Miner - Extracts actionable coding knowledge from source code.

What a coding agent actually needs (not "Docker is a container platform"):
  1. Code patterns with full imports, types, error handling
  2. API signatures: function(param: type) -> return_type
  3. Error-solution pairs: common error → fix with code
  4. Framework idioms: how THIS codebase uses FastAPI/SQLAlchemy/Qdrant
  5. Architectural patterns: how modules connect, dependency flow

This mines Grace's OWN codebase + generates framework-specific patterns
that a coding agent can retrieve and USE to write code.
"""

import ast
import os
import re
import logging
import hashlib
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime, timezone
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import func

logger = logging.getLogger(__name__)


class CodePatternMiner:
    """
    Mines source code into actionable patterns a coding agent can use.

    Extracts:
    - Function signatures with full type hints
    - Class patterns (init params, methods, inheritance)
    - Import graphs (what imports what)
    - Error handling patterns (try/except blocks)
    - Decorator usage (FastAPI routes, pytest fixtures)
    - SQLAlchemy model patterns
    - Common code idioms specific to this codebase
    """

    def __init__(self, session_factory):
        self.session_factory = session_factory
        self._stats = {
            "files_mined": 0,
            "functions_extracted": 0,
            "classes_extracted": 0,
            "patterns_stored": 0,
            "error_patterns": 0,
            "api_signatures": 0,
        }

    def mine_codebase(self, root_path: str, domains: Optional[List[str]] = None) -> Dict[str, Any]:
        """Mine an entire codebase for actionable code patterns."""
        session = self.session_factory()
        results = {"files": 0, "patterns": 0, "errors": []}

        py_files = []
        for dirpath, _, filenames in os.walk(root_path):
            if "__pycache__" in dirpath or ".git" in dirpath:
                continue
            for f in filenames:
                if f.endswith(".py"):
                    py_files.append(os.path.join(dirpath, f))

        for filepath in py_files:
            try:
                rel_path = os.path.relpath(filepath, root_path)
                domain = self._infer_domain(rel_path)

                if domains and domain not in domains:
                    continue

                with open(filepath, "r", errors="ignore") as fh:
                    source = fh.read()

                if len(source) < 50:
                    continue

                tree = ast.parse(source, filename=filepath)
                self._extract_from_ast(session, tree, source, rel_path, domain)
                results["files"] += 1
                self._stats["files_mined"] += 1

            except SyntaxError:
                pass
            except Exception as e:
                results["errors"].append(f"{filepath}: {str(e)[:60]}")

        session.commit()
        results["patterns"] = self._stats["patterns_stored"]
        session.close()
        return results

    def mine_framework_patterns(self) -> Dict[str, Any]:
        """Generate framework-specific patterns for FastAPI, SQLAlchemy, pytest, Qdrant."""
        session = self.session_factory()
        count = 0

        for pattern in self._get_framework_patterns():
            self._store_code_pattern(session, **pattern)
            count += 1

        session.commit()
        session.close()
        return {"patterns_stored": count}

    def mine_error_solutions(self) -> Dict[str, Any]:
        """Generate error-solution pairs for common Python/framework errors."""
        session = self.session_factory()
        count = 0

        for pair in self._get_error_solution_pairs():
            self._store_code_pattern(session, **pair)
            count += 1
            self._stats["error_patterns"] += 1

        session.commit()
        session.close()
        return {"error_solutions_stored": count}

    def _extract_from_ast(self, session: Session, tree: ast.AST, source: str, filepath: str, domain: str):
        """Extract patterns from a parsed AST."""
        lines = source.split("\n")

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                self._extract_function(session, node, lines, filepath, domain)

            elif isinstance(node, ast.ClassDef):
                self._extract_class(session, node, lines, filepath, domain)

            elif isinstance(node, ast.Try):
                self._extract_error_pattern(session, node, lines, filepath, domain)

    def _extract_function(self, session: Session, node, lines: List[str], filepath: str, domain: str):
        """Extract a function signature with types, decorators, and docstring."""
        is_async = isinstance(node, ast.AsyncFunctionDef)
        prefix = "async def" if is_async else "def"

        # Build signature
        args = []
        for arg in node.args.args:
            name = arg.arg
            annotation = ""
            if arg.annotation:
                annotation = f": {ast.unparse(arg.annotation)}"
            args.append(f"{name}{annotation}")

        returns = ""
        if node.returns:
            returns = f" -> {ast.unparse(node.returns)}"

        signature = f"{prefix} {node.name}({', '.join(args)}){returns}"

        # Get decorators
        decorators = []
        for dec in node.decorator_list:
            decorators.append(f"@{ast.unparse(dec)}")

        # Get docstring
        docstring = ast.get_docstring(node) or ""

        # Get the actual code (first 15 lines)
        start = node.lineno - 1
        end = min(node.end_lineno or start + 15, start + 20)
        code_block = "\n".join(lines[start:end])

        pattern_text = ""
        if decorators:
            pattern_text += "\n".join(decorators) + "\n"
        pattern_text += signature
        if docstring:
            pattern_text += f'\n    """{docstring[:200]}"""'

        self._store_code_pattern(
            session,
            subject=f"{filepath}::{node.name}",
            predicate="function_signature",
            code=pattern_text,
            full_code=code_block,
            domain=domain,
            confidence=0.95,
            tags={
                "type": "function",
                "async": is_async,
                "decorators": [ast.unparse(d) for d in node.decorator_list],
                "has_docstring": bool(docstring),
                "file": filepath,
                "line": node.lineno,
            },
        )
        self._stats["functions_extracted"] += 1
        self._stats["api_signatures"] += 1

    def _extract_class(self, session: Session, node: ast.ClassDef, lines: List[str], filepath: str, domain: str):
        """Extract class pattern: bases, init, methods."""
        bases = [ast.unparse(b) for b in node.bases]
        docstring = ast.get_docstring(node) or ""

        methods = []
        init_params = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(item.name)
                if item.name == "__init__":
                    for arg in item.args.args:
                        if arg.arg != "self":
                            ann = f": {ast.unparse(arg.annotation)}" if arg.annotation else ""
                            init_params.append(f"{arg.arg}{ann}")

        class_sig = f"class {node.name}"
        if bases:
            class_sig += f"({', '.join(bases)})"
        class_sig += ":"
        if docstring:
            class_sig += f'\n    """{docstring[:200]}"""'
        if init_params:
            class_sig += f"\n    def __init__(self, {', '.join(init_params)})"

        start = node.lineno - 1
        end = min(node.end_lineno or start + 30, start + 40)
        code_block = "\n".join(lines[start:end])

        self._store_code_pattern(
            session,
            subject=f"{filepath}::{node.name}",
            predicate="class_pattern",
            code=class_sig,
            full_code=code_block,
            domain=domain,
            confidence=0.95,
            tags={
                "type": "class",
                "bases": bases,
                "methods": methods[:20],
                "init_params": init_params,
                "has_docstring": bool(docstring),
                "file": filepath,
                "method_count": len(methods),
            },
        )
        self._stats["classes_extracted"] += 1

    def _extract_error_pattern(self, session: Session, node: ast.Try, lines: List[str], filepath: str, domain: str):
        """Extract try/except patterns as error-handling knowledge."""
        for handler in node.handlers:
            if handler.type:
                exc_type = ast.unparse(handler.type)
                start = handler.lineno - 1
                end = min(handler.end_lineno or start + 5, start + 8)
                handler_code = "\n".join(lines[start:end])

                # Get the try block too
                try_start = node.lineno - 1
                try_end = min(handler.lineno - 1, try_start + 8)
                try_code = "\n".join(lines[try_start:try_end])

                self._store_code_pattern(
                    session,
                    subject=f"{filepath}::catch_{exc_type}",
                    predicate="error_handling",
                    code=f"try:\n{try_code}\nexcept {exc_type}:\n{handler_code}",
                    domain=domain,
                    confidence=0.85,
                    tags={
                        "type": "error_handling",
                        "exception": exc_type,
                        "file": filepath,
                    },
                )
                self._stats["error_patterns"] += 1

    def _store_code_pattern(
        self, session: Session, subject: str, predicate: str,
        code: str, domain: str, confidence: float = 0.9,
        full_code: str = "", tags: Optional[Dict] = None,
    ):
        """Store a code pattern as a compiled fact."""
        try:
            from cognitive.knowledge_compiler import CompiledFact

            fact = CompiledFact(
                subject=subject[:256],
                predicate=predicate[:256],
                object_value=code[:2000],
                object_type="code",
                confidence=confidence,
                domain=domain,
                source_text=full_code[:500] if full_code else code[:500],
                tags=tags or {},
                verified=True,
            )
            session.add(fact)
            self._stats["patterns_stored"] += 1
        except Exception as e:
            logger.debug(f"Store error: {e}")

    def _infer_domain(self, filepath: str) -> str:
        """Infer domain from file path."""
        parts = filepath.replace("\\", "/").split("/")
        if len(parts) >= 2:
            return parts[0]
        return "general"

    def _get_framework_patterns(self) -> List[Dict[str, Any]]:
        """Framework-specific code patterns a coding agent needs."""
        return [
            # FastAPI
            {
                "subject": "fastapi::route_get",
                "predicate": "code_pattern",
                "code": (
                    "from fastapi import APIRouter, Depends, HTTPException, Query\n"
                    "from sqlalchemy.orm import Session\n"
                    "from database.session import get_db\n\n"
                    "router = APIRouter(prefix='/items', tags=['Items'])\n\n"
                    "@router.get('/{item_id}')\n"
                    "async def get_item(item_id: int, db: Session = Depends(get_db)):\n"
                    "    item = db.query(Item).filter(Item.id == item_id).first()\n"
                    "    if not item:\n"
                    "        raise HTTPException(status_code=404, detail='Item not found')\n"
                    "    return item"
                ),
                "domain": "fastapi",
                "confidence": 0.98,
                "tags": {"type": "framework_pattern", "framework": "fastapi", "pattern": "get_endpoint"},
            },
            {
                "subject": "fastapi::route_post",
                "predicate": "code_pattern",
                "code": (
                    "from fastapi import APIRouter, Depends, HTTPException\n"
                    "from pydantic import BaseModel, Field\n"
                    "from sqlalchemy.orm import Session\n"
                    "from database.session import get_db\n\n"
                    "class CreateItemRequest(BaseModel):\n"
                    "    name: str = Field(..., min_length=1, max_length=256)\n"
                    "    description: Optional[str] = None\n\n"
                    "@router.post('/', status_code=201)\n"
                    "async def create_item(request: CreateItemRequest, db: Session = Depends(get_db)):\n"
                    "    item = Item(**request.model_dump())\n"
                    "    db.add(item)\n"
                    "    db.commit()\n"
                    "    db.refresh(item)\n"
                    "    return item"
                ),
                "domain": "fastapi",
                "confidence": 0.98,
                "tags": {"type": "framework_pattern", "framework": "fastapi", "pattern": "post_endpoint"},
            },
            {
                "subject": "fastapi::middleware",
                "predicate": "code_pattern",
                "code": (
                    "from fastapi import Request\n"
                    "from starlette.middleware.base import BaseHTTPMiddleware\n\n"
                    "class TimingMiddleware(BaseHTTPMiddleware):\n"
                    "    async def dispatch(self, request: Request, call_next):\n"
                    "        import time\n"
                    "        start = time.time()\n"
                    "        response = await call_next(request)\n"
                    "        duration = time.time() - start\n"
                    "        response.headers['X-Process-Time'] = str(duration)\n"
                    "        return response\n\n"
                    "app.add_middleware(TimingMiddleware)"
                ),
                "domain": "fastapi",
                "confidence": 0.95,
                "tags": {"type": "framework_pattern", "framework": "fastapi", "pattern": "middleware"},
            },
            # SQLAlchemy
            {
                "subject": "sqlalchemy::model_definition",
                "predicate": "code_pattern",
                "code": (
                    "from sqlalchemy import Column, String, Integer, Float, Boolean, Text, JSON, DateTime, Index, ForeignKey\n"
                    "from sqlalchemy.orm import relationship\n"
                    "from database.base import BaseModel\n\n"
                    "class User(BaseModel):\n"
                    "    __tablename__ = 'users'\n\n"
                    "    username = Column(String(128), unique=True, nullable=False, index=True)\n"
                    "    email = Column(String(256), unique=True, nullable=False)\n"
                    "    is_active = Column(Boolean, default=True)\n"
                    "    metadata_json = Column(JSON, nullable=True)\n\n"
                    "    posts = relationship('Post', back_populates='author', lazy='dynamic')\n\n"
                    "    __table_args__ = (\n"
                    "        Index('idx_user_email', 'email'),\n"
                    "    )"
                ),
                "domain": "sqlalchemy",
                "confidence": 0.98,
                "tags": {"type": "framework_pattern", "framework": "sqlalchemy", "pattern": "model"},
            },
            {
                "subject": "sqlalchemy::query_patterns",
                "predicate": "code_pattern",
                "code": (
                    "from sqlalchemy import func, and_, or_, desc\n\n"
                    "# Get by ID\n"
                    "item = session.query(Item).filter(Item.id == item_id).first()\n\n"
                    "# Filter with multiple conditions\n"
                    "items = session.query(Item).filter(\n"
                    "    and_(Item.status == 'active', Item.price > 10)\n"
                    ").order_by(desc(Item.created_at)).limit(20).all()\n\n"
                    "# Aggregation\n"
                    "count = session.query(func.count(Item.id)).filter(\n"
                    "    Item.domain == domain\n"
                    ").scalar() or 0\n\n"
                    "# Group by\n"
                    "stats = session.query(\n"
                    "    Item.domain, func.count(Item.id)\n"
                    ").group_by(Item.domain).all()\n\n"
                    "# Update\n"
                    "session.query(Item).filter(Item.id == item_id).update(\n"
                    "    {'status': 'archived'}\n"
                    ")\n"
                    "session.commit()"
                ),
                "domain": "sqlalchemy",
                "confidence": 0.98,
                "tags": {"type": "framework_pattern", "framework": "sqlalchemy", "pattern": "queries"},
            },
            {
                "subject": "sqlalchemy::session_management",
                "predicate": "code_pattern",
                "code": (
                    "from sqlalchemy.orm import sessionmaker\n"
                    "from sqlalchemy import create_engine\n\n"
                    "# Session factory pattern\n"
                    "engine = create_engine('sqlite:///data.db')\n"
                    "SessionLocal = sessionmaker(bind=engine)\n\n"
                    "# FastAPI dependency\n"
                    "def get_db():\n"
                    "    db = SessionLocal()\n"
                    "    try:\n"
                    "        yield db\n"
                    "    finally:\n"
                    "        db.close()\n\n"
                    "# Manual session usage\n"
                    "session = SessionLocal()\n"
                    "try:\n"
                    "    session.add(item)\n"
                    "    session.commit()\n"
                    "except Exception:\n"
                    "    session.rollback()\n"
                    "    raise\n"
                    "finally:\n"
                    "    session.close()"
                ),
                "domain": "sqlalchemy",
                "confidence": 0.98,
                "tags": {"type": "framework_pattern", "framework": "sqlalchemy", "pattern": "session"},
            },
            # Qdrant
            {
                "subject": "qdrant::vector_operations",
                "predicate": "code_pattern",
                "code": (
                    "from qdrant_client import QdrantClient\n"
                    "from qdrant_client.models import PointStruct, VectorParams, Distance\n\n"
                    "# Initialize\n"
                    "client = QdrantClient(path='/path/to/storage')\n\n"
                    "# Create collection\n"
                    "client.create_collection(\n"
                    "    collection_name='documents',\n"
                    "    vectors_config=VectorParams(size=2048, distance=Distance.COSINE),\n"
                    ")\n\n"
                    "# Upsert vectors\n"
                    "import hashlib\n"
                    "vid = hashlib.md5(text.encode()).hexdigest()\n"
                    "client.upsert(\n"
                    "    collection_name='documents',\n"
                    "    points=[PointStruct(id=vid, vector=embedding, payload={'text': text})],\n"
                    ")\n\n"
                    "# Search\n"
                    "results = client.query_points(\n"
                    "    collection_name='documents', query=query_vector, limit=10,\n"
                    ")\n"
                    "for point in results.points:\n"
                    "    print(f'Score: {point.score}, Text: {point.payload[\"text\"]}')"
                ),
                "domain": "qdrant",
                "confidence": 0.95,
                "tags": {"type": "framework_pattern", "framework": "qdrant", "pattern": "vector_ops"},
            },
            # Pytest
            {
                "subject": "pytest::test_patterns",
                "predicate": "code_pattern",
                "code": (
                    "import pytest\n"
                    "from unittest.mock import MagicMock, patch\n"
                    "from sqlalchemy import create_engine\n"
                    "from sqlalchemy.orm import sessionmaker\n"
                    "from sqlalchemy.pool import StaticPool\n"
                    "from database.base import Base\n\n"
                    "@pytest.fixture\n"
                    "def db_session():\n"
                    "    engine = create_engine(\n"
                    "        'sqlite:///:memory:',\n"
                    "        connect_args={'check_same_thread': False},\n"
                    "        poolclass=StaticPool,\n"
                    "    )\n"
                    "    Base.metadata.create_all(bind=engine)\n"
                    "    Session = sessionmaker(bind=engine)\n"
                    "    session = Session()\n"
                    "    yield session\n"
                    "    session.close()\n"
                    "    Base.metadata.drop_all(bind=engine)\n\n"
                    "@pytest.fixture\n"
                    "def mock_service():\n"
                    "    service = MagicMock()\n"
                    "    service.is_available.return_value = True\n"
                    "    return service\n\n"
                    "class TestMyFeature:\n"
                    "    def test_creates_record(self, db_session):\n"
                    "        item = Item(name='test')\n"
                    "        db_session.add(item)\n"
                    "        db_session.commit()\n"
                    "        assert db_session.query(Item).count() == 1\n\n"
                    "    def test_handles_error(self, mock_service):\n"
                    "        mock_service.process.side_effect = ValueError('bad')\n"
                    "        with pytest.raises(ValueError):\n"
                    "            process(mock_service)"
                ),
                "domain": "pytest",
                "confidence": 0.98,
                "tags": {"type": "framework_pattern", "framework": "pytest", "pattern": "test_structure"},
            },
            # Pydantic
            {
                "subject": "pydantic::model_validation",
                "predicate": "code_pattern",
                "code": (
                    "from pydantic import BaseModel, Field, validator\n"
                    "from typing import Optional, List\n\n"
                    "class CreateUserRequest(BaseModel):\n"
                    "    name: str = Field(..., min_length=1, max_length=100)\n"
                    "    email: str = Field(..., pattern=r'^[\\w.-]+@[\\w.-]+\\.\\w+$')\n"
                    "    age: Optional[int] = Field(default=None, ge=0, le=150)\n"
                    "    tags: List[str] = Field(default_factory=list)\n\n"
                    "    @validator('name')\n"
                    "    def name_must_not_be_empty(cls, v):\n"
                    "        if not v.strip():\n"
                    "            raise ValueError('name cannot be blank')\n"
                    "        return v.strip()\n\n"
                    "    class Config:\n"
                    "        json_schema_extra = {\n"
                    "            'example': {'name': 'Grace', 'email': 'grace@example.com'}\n"
                    "        }"
                ),
                "domain": "pydantic",
                "confidence": 0.98,
                "tags": {"type": "framework_pattern", "framework": "pydantic", "pattern": "validation"},
            },
            # Python async
            {
                "subject": "python::async_patterns",
                "predicate": "code_pattern",
                "code": (
                    "import asyncio\n"
                    "from typing import List\n\n"
                    "# Gather multiple async operations\n"
                    "async def fetch_all(urls: List[str]):\n"
                    "    async with aiohttp.ClientSession() as session:\n"
                    "        tasks = [session.get(url) for url in urls]\n"
                    "        responses = await asyncio.gather(*tasks, return_exceptions=True)\n"
                    "        return [r for r in responses if not isinstance(r, Exception)]\n\n"
                    "# Semaphore for rate limiting\n"
                    "sem = asyncio.Semaphore(10)\n"
                    "async def limited_fetch(url: str):\n"
                    "    async with sem:\n"
                    "        return await fetch(url)\n\n"
                    "# Timeout\n"
                    "async def with_timeout(coro, seconds: float = 5.0):\n"
                    "    try:\n"
                    "        return await asyncio.wait_for(coro, timeout=seconds)\n"
                    "    except asyncio.TimeoutError:\n"
                    "        return None"
                ),
                "domain": "python_async",
                "confidence": 0.95,
                "tags": {"type": "framework_pattern", "framework": "asyncio", "pattern": "async"},
            },
            # Python typing
            {
                "subject": "python::typing_patterns",
                "predicate": "code_pattern",
                "code": (
                    "from typing import Dict, Any, List, Optional, Set, Tuple, Union\n"
                    "from typing import TypeVar, Generic, Protocol\n"
                    "from dataclasses import dataclass, field\n\n"
                    "T = TypeVar('T')\n\n"
                    "# Dataclass with defaults\n"
                    "@dataclass\n"
                    "class Config:\n"
                    "    host: str = 'localhost'\n"
                    "    port: int = 8000\n"
                    "    debug: bool = False\n"
                    "    tags: List[str] = field(default_factory=list)\n"
                    "    metadata: Dict[str, Any] = field(default_factory=dict)\n\n"
                    "# Protocol for duck typing\n"
                    "class Searchable(Protocol):\n"
                    "    def search(self, query: str) -> List[Dict[str, Any]]: ...\n\n"
                    "# Generic container\n"
                    "class Repository(Generic[T]):\n"
                    "    def __init__(self) -> None:\n"
                    "        self._items: List[T] = []\n"
                    "    def add(self, item: T) -> None:\n"
                    "        self._items.append(item)\n"
                    "    def get_all(self) -> List[T]:\n"
                    "        return list(self._items)"
                ),
                "domain": "python_typing",
                "confidence": 0.95,
                "tags": {"type": "framework_pattern", "framework": "python", "pattern": "typing"},
            },
        ]

    def _get_error_solution_pairs(self) -> List[Dict[str, Any]]:
        """Common error-solution pairs for Python development."""
        return [
            {
                "subject": "error::ImportError",
                "predicate": "error_solution",
                "code": (
                    "# ERROR: ImportError: No module named 'xyz'\n"
                    "# CAUSE: Package not installed or not in PYTHONPATH\n"
                    "# FIX:\n"
                    "pip install xyz\n"
                    "# OR add to sys.path:\n"
                    "import sys\n"
                    "sys.path.insert(0, '/path/to/module')\n"
                    "# OR use try/except for optional deps:\n"
                    "try:\n"
                    "    import xyz\n"
                    "    XYZ_AVAILABLE = True\n"
                    "except ImportError:\n"
                    "    XYZ_AVAILABLE = False"
                ),
                "domain": "python_errors",
                "confidence": 0.95,
                "tags": {"type": "error_solution", "error": "ImportError"},
            },
            {
                "subject": "error::DetachedInstanceError",
                "predicate": "error_solution",
                "code": (
                    "# ERROR: sqlalchemy.orm.exc.DetachedInstanceError\n"
                    "# CAUSE: Accessing ORM attributes after session.close()\n"
                    "# FIX: Capture values BEFORE closing session\n"
                    "result_status = tracker.status  # capture before close\n"
                    "result_count = tracker.count\n"
                    "session.commit()\n"
                    "session.close()\n"
                    "return {'status': result_status, 'count': result_count}\n\n"
                    "# OR use expire_on_commit=False:\n"
                    "Session = sessionmaker(bind=engine, expire_on_commit=False)"
                ),
                "domain": "sqlalchemy_errors",
                "confidence": 0.98,
                "tags": {"type": "error_solution", "error": "DetachedInstanceError"},
            },
            {
                "subject": "error::CircularImport",
                "predicate": "error_solution",
                "code": (
                    "# ERROR: ImportError: cannot import name 'X' from partially initialized module\n"
                    "# CAUSE: Circular imports between modules\n"
                    "# FIX: Use lazy imports inside functions\n"
                    "def my_function():\n"
                    "    from other_module import OtherClass  # import inside function\n"
                    "    return OtherClass()\n\n"
                    "# OR use TYPE_CHECKING for type hints:\n"
                    "from __future__ import annotations\n"
                    "from typing import TYPE_CHECKING\n"
                    "if TYPE_CHECKING:\n"
                    "    from other_module import OtherClass"
                ),
                "domain": "python_errors",
                "confidence": 0.95,
                "tags": {"type": "error_solution", "error": "CircularImport"},
            },
            {
                "subject": "error::AsyncContextManager",
                "predicate": "error_solution",
                "code": (
                    "# ERROR: TypeError: object async_generator can't be used in 'await' expression\n"
                    "# CAUSE: Using yield in async function without proper handling\n"
                    "# FIX: Use async context manager pattern\n"
                    "from contextlib import asynccontextmanager\n\n"
                    "@asynccontextmanager\n"
                    "async def get_connection():\n"
                    "    conn = await create_connection()\n"
                    "    try:\n"
                    "        yield conn\n"
                    "    finally:\n"
                    "        await conn.close()\n\n"
                    "# Usage:\n"
                    "async with get_connection() as conn:\n"
                    "    result = await conn.execute(query)"
                ),
                "domain": "python_errors",
                "confidence": 0.95,
                "tags": {"type": "error_solution", "error": "AsyncContextManager"},
            },
            {
                "subject": "error::QdrantLock",
                "predicate": "error_solution",
                "code": (
                    "# ERROR: RuntimeError: Storage folder is already accessed by another Qdrant instance\n"
                    "# CAUSE: .lock file from crashed process or concurrent access\n"
                    "# FIX: Remove lock file before connecting\n"
                    "import os\n"
                    "lock_path = os.path.join(qdrant_path, '.lock')\n"
                    "if os.path.exists(lock_path):\n"
                    "    os.remove(lock_path)\n"
                    "client = QdrantClient(path=qdrant_path)\n\n"
                    "# BETTER FIX: Always close client properly\n"
                    "try:\n"
                    "    client = QdrantClient(path=qdrant_path)\n"
                    "    # ... operations ...\n"
                    "finally:\n"
                    "    client.close()"
                ),
                "domain": "qdrant_errors",
                "confidence": 0.98,
                "tags": {"type": "error_solution", "error": "QdrantLock"},
            },
            {
                "subject": "error::PydanticValidation",
                "predicate": "error_solution",
                "code": (
                    "# ERROR: pydantic.ValidationError: 1 validation error for Model\n"
                    "# CAUSE: Input data doesn't match Pydantic model schema\n"
                    "# FIX: Use Optional for nullable fields, default values\n"
                    "from pydantic import BaseModel, Field\n"
                    "from typing import Optional\n\n"
                    "class MyModel(BaseModel):\n"
                    "    required_field: str\n"
                    "    optional_field: Optional[str] = None\n"
                    "    with_default: int = Field(default=0, ge=0)\n\n"
                    "# Safe parsing:\n"
                    "try:\n"
                    "    model = MyModel(**data)\n"
                    "except ValidationError as e:\n"
                    "    errors = e.errors()\n"
                    "    for err in errors:\n"
                    "        print(f'{err[\"loc\"]}: {err[\"msg\"]}')"
                ),
                "domain": "pydantic_errors",
                "confidence": 0.95,
                "tags": {"type": "error_solution", "error": "PydanticValidation"},
            },
        ]

    def get_stats(self) -> Dict[str, Any]:
        return dict(self._stats)


_miner: Optional[CodePatternMiner] = None

def get_code_pattern_miner(session_factory=None) -> CodePatternMiner:
    global _miner
    if _miner is None:
        if not session_factory:
            from database.session import SessionLocal
            session_factory = SessionLocal
        _miner = CodePatternMiner(session_factory)
    return _miner
