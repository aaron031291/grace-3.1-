"""
Tests for CodePatternMiner - verifies actual code extraction logic,
not just existence. Tests parse real Python code and verify extracted
signatures, types, decorators, error patterns, and framework idioms.
"""

import sys
import os
import tempfile
import warnings

import pytest

warnings.filterwarnings("ignore", category=DeprecationWarning, module="sqlalchemy")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from database.base import Base

from cognitive.code_pattern_miner import CodePatternMiner


@pytest.fixture
def db_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        from cognitive.knowledge_compiler import CompiledFact
    except Exception:
        pass
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def session_factory(db_engine):
    return sessionmaker(bind=db_engine)


@pytest.fixture
def db_session(session_factory):
    s = session_factory()
    yield s
    s.close()


@pytest.fixture
def miner(session_factory):
    return CodePatternMiner(session_factory)


@pytest.fixture
def sample_code_dir():
    """Create a temporary directory with sample Python files."""
    tmpdir = tempfile.mkdtemp()
    # File 1: FastAPI-style endpoint
    with open(os.path.join(tmpdir, "api_example.py"), "w") as f:
        f.write('''
from fastapi import APIRouter, Depends
from typing import List, Optional

router = APIRouter()

class ItemService:
    """Service for managing items."""
    def __init__(self, db_session):
        self.db = db_session
    
    def get_all(self, limit: int = 10) -> List[dict]:
        """Get all items with pagination."""
        return self.db.query(Item).limit(limit).all()

async def get_item(item_id: int, service: ItemService = Depends()) -> dict:
    """Retrieve a single item by ID."""
    try:
        item = service.get_by_id(item_id)
        if not item:
            raise ValueError("Not found")
        return item
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal error")

def compute_score(values: List[float], weights: Optional[List[float]] = None) -> float:
    """Compute weighted score."""
    if weights is None:
        weights = [1.0] * len(values)
    return sum(v * w for v, w in zip(values, weights)) / sum(weights)
''')

    # File 2: SQLAlchemy model
    with open(os.path.join(tmpdir, "model_example.py"), "w") as f:
        f.write('''
from sqlalchemy import Column, String, Integer, Float
from database.base import BaseModel

class Product(BaseModel):
    """A product in the catalog."""
    __tablename__ = "products"
    
    name = Column(String(256), nullable=False, index=True)
    price = Column(Float, default=0.0)
    category = Column(String(64), nullable=True)
    
    def __init__(self, name: str, price: float = 0.0):
        self.name = name
        self.price = price

    def apply_discount(self, percent: float) -> float:
        """Apply percentage discount and return new price."""
        self.price *= (1.0 - percent / 100.0)
        return self.price
''')

    yield tmpdir

    # Cleanup
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)


class TestCodebaseMining:

    def test_mines_python_files(self, miner, sample_code_dir):
        result = miner.mine_codebase(sample_code_dir)
        assert result["files"] == 2
        assert result["patterns"] > 0

    def test_extracts_function_signatures(self, miner, sample_code_dir, db_session):
        miner.mine_codebase(sample_code_dir)

        from cognitive.knowledge_compiler import CompiledFact
        sigs = db_session.query(CompiledFact).filter(
            CompiledFact.predicate == "function_signature"
        ).all()
        assert len(sigs) >= 3  # get_item, compute_score, get_all, apply_discount

        sig_names = [s.subject for s in sigs]
        assert any("get_item" in s for s in sig_names)
        assert any("compute_score" in s for s in sig_names)

    def test_function_signature_includes_types(self, miner, sample_code_dir, db_session):
        miner.mine_codebase(sample_code_dir)

        from cognitive.knowledge_compiler import CompiledFact
        compute = db_session.query(CompiledFact).filter(
            CompiledFact.predicate == "function_signature",
            CompiledFact.subject.like("%compute_score%"),
        ).first()
        assert compute is not None
        assert "List[float]" in compute.object_value
        assert "-> float" in compute.object_value

    def test_function_signature_includes_async(self, miner, sample_code_dir, db_session):
        miner.mine_codebase(sample_code_dir)

        from cognitive.knowledge_compiler import CompiledFact
        get_item = db_session.query(CompiledFact).filter(
            CompiledFact.predicate == "function_signature",
            CompiledFact.subject.like("%get_item%"),
        ).first()
        assert get_item is not None
        assert "async def" in get_item.object_value

    def test_extracts_class_patterns(self, miner, sample_code_dir, db_session):
        miner.mine_codebase(sample_code_dir)

        from cognitive.knowledge_compiler import CompiledFact
        classes = db_session.query(CompiledFact).filter(
            CompiledFact.predicate == "class_pattern"
        ).all()
        assert len(classes) >= 2  # ItemService, Product

        class_names = [c.subject for c in classes]
        assert any("Product" in c for c in class_names)
        assert any("ItemService" in c for c in class_names)

    def test_class_pattern_includes_base(self, miner, sample_code_dir, db_session):
        miner.mine_codebase(sample_code_dir)

        from cognitive.knowledge_compiler import CompiledFact
        product = db_session.query(CompiledFact).filter(
            CompiledFact.predicate == "class_pattern",
            CompiledFact.subject.like("%Product%"),
        ).first()
        assert product is not None
        assert "BaseModel" in product.object_value

    def test_extracts_error_handling_patterns(self, miner, sample_code_dir, db_session):
        miner.mine_codebase(sample_code_dir)

        from cognitive.knowledge_compiler import CompiledFact
        errors = db_session.query(CompiledFact).filter(
            CompiledFact.predicate == "error_handling"
        ).all()
        assert len(errors) >= 1  # ValueError and Exception handlers

        error_types = [e.subject for e in errors]
        assert any("ValueError" in e for e in error_types)

    def test_all_patterns_are_code_type(self, miner, sample_code_dir, db_session):
        miner.mine_codebase(sample_code_dir)

        from cognitive.knowledge_compiler import CompiledFact
        patterns = db_session.query(CompiledFact).filter(
            CompiledFact.object_type == "code"
        ).all()
        assert len(patterns) > 0
        for p in patterns:
            assert p.object_type == "code"

    def test_patterns_have_high_confidence(self, miner, sample_code_dir, db_session):
        miner.mine_codebase(sample_code_dir)

        from cognitive.knowledge_compiler import CompiledFact
        patterns = db_session.query(CompiledFact).filter(
            CompiledFact.object_type == "code"
        ).all()
        for p in patterns:
            assert p.confidence >= 0.85

    def test_infers_domain_from_path(self, miner):
        assert miner._infer_domain("cognitive/engine.py") == "cognitive"
        assert miner._infer_domain("api/routes.py") == "api"
        assert miner._infer_domain("standalone.py") == "general"


class TestFrameworkPatterns:

    def test_stores_framework_patterns(self, miner, db_session):
        result = miner.mine_framework_patterns()
        assert result["patterns_stored"] >= 10

    def test_fastapi_patterns_have_imports(self, miner, db_session):
        miner.mine_framework_patterns()

        from cognitive.knowledge_compiler import CompiledFact
        fastapi = db_session.query(CompiledFact).filter(
            CompiledFact.subject.like("fastapi%"),
            CompiledFact.predicate == "code_pattern",
        ).all()
        assert len(fastapi) >= 2
        for p in fastapi:
            assert "from fastapi" in p.object_value
            assert "import" in p.object_value

    def test_sqlalchemy_patterns_have_column_definitions(self, miner, db_session):
        miner.mine_framework_patterns()

        from cognitive.knowledge_compiler import CompiledFact
        sqla = db_session.query(CompiledFact).filter(
            CompiledFact.subject.like("sqlalchemy%"),
        ).all()
        assert len(sqla) >= 2
        model_pattern = [p for p in sqla if "Column" in p.object_value]
        assert len(model_pattern) >= 1

    def test_pytest_pattern_has_fixtures(self, miner, db_session):
        miner.mine_framework_patterns()

        from cognitive.knowledge_compiler import CompiledFact
        pytest_p = db_session.query(CompiledFact).filter(
            CompiledFact.subject.like("pytest%"),
        ).first()
        assert pytest_p is not None
        assert "@pytest.fixture" in pytest_p.object_value
        assert "MagicMock" in pytest_p.object_value

    def test_qdrant_pattern_has_vector_ops(self, miner, db_session):
        miner.mine_framework_patterns()

        from cognitive.knowledge_compiler import CompiledFact
        qdrant = db_session.query(CompiledFact).filter(
            CompiledFact.subject.like("qdrant%"),
        ).first()
        assert qdrant is not None
        assert "QdrantClient" in qdrant.object_value
        assert "query_points" in qdrant.object_value


class TestErrorSolutions:

    def test_stores_error_solutions(self, miner, db_session):
        result = miner.mine_error_solutions()
        assert result["error_solutions_stored"] >= 5

    def test_import_error_solution_has_fix(self, miner, db_session):
        miner.mine_error_solutions()

        from cognitive.knowledge_compiler import CompiledFact
        imp = db_session.query(CompiledFact).filter(
            CompiledFact.subject == "error::ImportError",
        ).first()
        assert imp is not None
        assert "pip install" in imp.object_value
        assert "sys.path" in imp.object_value

    def test_detached_instance_error_solution(self, miner, db_session):
        miner.mine_error_solutions()

        from cognitive.knowledge_compiler import CompiledFact
        det = db_session.query(CompiledFact).filter(
            CompiledFact.subject == "error::DetachedInstanceError",
        ).first()
        assert det is not None
        assert "session.close()" in det.object_value
        assert "capture" in det.object_value.lower()

    def test_qdrant_lock_error_solution(self, miner, db_session):
        miner.mine_error_solutions()

        from cognitive.knowledge_compiler import CompiledFact
        ql = db_session.query(CompiledFact).filter(
            CompiledFact.subject == "error::QdrantLock",
        ).first()
        assert ql is not None
        assert ".lock" in ql.object_value
        assert "os.remove" in ql.object_value

    def test_all_solutions_are_code_type(self, miner, db_session):
        miner.mine_error_solutions()

        from cognitive.knowledge_compiler import CompiledFact
        solutions = db_session.query(CompiledFact).filter(
            CompiledFact.predicate == "error_solution",
        ).all()
        for s in solutions:
            assert s.object_type == "code"
            assert s.confidence >= 0.9


class TestStats:

    def test_stats_track_all_categories(self, miner, sample_code_dir):
        miner.mine_codebase(sample_code_dir)
        miner.mine_framework_patterns()
        miner.mine_error_solutions()

        stats = miner.get_stats()
        assert stats["files_mined"] == 2
        assert stats["functions_extracted"] >= 3
        assert stats["classes_extracted"] >= 2
        assert stats["patterns_stored"] > 0
        assert stats["error_patterns"] >= 1
        assert stats["api_signatures"] >= 3
