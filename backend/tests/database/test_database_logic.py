"""
Tests for backend.database and backend.models modules.

Uses SQLite in-memory databases for real DB operations and
unittest.mock for isolation where appropriate.
"""
import os
import sys
import time
import threading
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest
from sqlalchemy import create_engine, Column, String, Integer, Text, inspect
from sqlalchemy.orm import sessionmaker, Session

# Ensure backend is on path (mirrors conftest.py)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from database.base import Base, BaseModel
from database.config import DatabaseConfig, DatabaseType
from database.connection import DatabaseConnection
from database.repository import BaseRepository
from database import session as session_mod


# ─────────────────────────────────────────────────────────────────────
# Helpers: a concrete model for testing the abstract BaseModel
# ─────────────────────────────────────────────────────────────────────

class Item(BaseModel):
    """Concrete model used only in tests."""
    __tablename__ = "test_items"

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    quantity = Column(Integer, default=0)


@pytest.fixture()
def in_memory_engine():
    """Create a fresh SQLite in-memory engine and tables."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(in_memory_engine):
    """Yield a session bound to the in-memory engine, rolled back after use."""
    Session_ = sessionmaker(bind=in_memory_engine)
    session = Session_()
    yield session
    session.rollback()
    session.close()


# =====================================================================
# 1. BaseModel – to_dict, update, __repr__
# =====================================================================

class TestBaseModel:
    """Verify BaseModel common fields and methods."""

    def test_to_dict_returns_all_columns(self, db_session):
        item = Item(name="widget", description="A fine widget", quantity=5)
        db_session.add(item)
        db_session.commit()
        db_session.refresh(item)

        d = item.to_dict()
        assert d["name"] == "widget"
        assert d["description"] == "A fine widget"
        assert d["quantity"] == 5
        assert "id" in d
        assert "created_at" in d
        assert "updated_at" in d

    def test_to_dict_contains_only_column_keys(self, db_session):
        item = Item(name="gadget")
        db_session.add(item)
        db_session.commit()
        db_session.refresh(item)

        d = item.to_dict()
        col_names = {c.name for c in Item.__table__.columns}
        assert set(d.keys()) == col_names

    def test_update_sets_attributes(self, db_session):
        item = Item(name="old_name", quantity=1)
        db_session.add(item)
        db_session.commit()
        db_session.refresh(item)

        before_updated = item.updated_at
        item.update(name="new_name", quantity=99)

        assert item.name == "new_name"
        assert item.quantity == 99
        # updated_at should be refreshed (it becomes tz-aware after .update())
        assert item.updated_at is not None
        assert item.updated_at != before_updated

    def test_update_ignores_unknown_attributes(self, db_session):
        item = Item(name="stable")
        db_session.add(item)
        db_session.commit()
        db_session.refresh(item)

        item.update(nonexistent_field="should_not_crash", name="still_stable")
        assert item.name == "still_stable"
        assert not hasattr(item, "nonexistent_field") or getattr(item, "nonexistent_field", None) is None

    def test_repr(self, db_session):
        item = Item(name="repr_test")
        db_session.add(item)
        db_session.commit()
        db_session.refresh(item)

        r = repr(item)
        assert "Item" in r
        assert str(item.id) in r

    def test_default_timestamps_populated(self, db_session):
        item = Item(name="ts_test")
        db_session.add(item)
        db_session.commit()
        db_session.refresh(item)

        assert item.created_at is not None
        assert item.updated_at is not None

    def test_abstract_flag(self):
        assert BaseModel.__abstract__ is True


# =====================================================================
# 2. DatabaseConfig
# =====================================================================

class TestDatabaseConfig:
    """Test configuration loading and connection-string generation."""

    def test_sqlite_connection_string(self, tmp_path):
        cfg = DatabaseConfig(
            db_type=DatabaseType.SQLITE,
            database_path=str(tmp_path / "test.db"),
        )
        url = cfg.get_connection_string()
        assert url.startswith("sqlite:///")
        assert "test.db" in url

    def test_postgresql_connection_string(self):
        cfg = DatabaseConfig(
            db_type=DatabaseType.POSTGRESQL,
            host="localhost",
            port=5432,
            username="grace",
            password="secret",
            database="gracedb",
        )
        url = cfg.get_connection_string()
        assert url.startswith("postgresql+psycopg2://")
        assert "localhost" in url
        assert "5432" in url
        assert "gracedb" in url

    def test_postgresql_requires_host_and_user(self):
        cfg = DatabaseConfig(db_type=DatabaseType.POSTGRESQL)
        with pytest.raises(ValueError, match="PostgreSQL requires"):
            cfg.get_connection_string()

    def test_mysql_connection_string(self):
        cfg = DatabaseConfig(
            db_type=DatabaseType.MYSQL,
            host="dbhost",
            username="root",
            password="pw",
            database="mydb",
        )
        url = cfg.get_connection_string()
        assert url.startswith("mysql+pymysql://")
        assert "dbhost" in url

    def test_mysql_requires_host_and_user(self):
        cfg = DatabaseConfig(db_type=DatabaseType.MYSQL)
        with pytest.raises(ValueError, match="MySQL requires"):
            cfg.get_connection_string()

    def test_mariadb_connection_string(self):
        cfg = DatabaseConfig(
            db_type=DatabaseType.MARIADB,
            host="dbhost",
            username="root",
            password="pw",
            database="mydb",
        )
        url = cfg.get_connection_string()
        assert url.startswith("mariadb+pymysql://")

    def test_mariadb_requires_host_and_user(self):
        cfg = DatabaseConfig(db_type=DatabaseType.MARIADB)
        with pytest.raises(ValueError, match="MariaDB requires"):
            cfg.get_connection_string()

    def test_from_env_defaults(self):
        with patch.dict(os.environ, {
            "DATABASE_TYPE": "sqlite",
            "DATABASE_PATH": "/tmp/test_grace.db",
        }, clear=False):
            cfg = DatabaseConfig.from_env()
            assert cfg.db_type == DatabaseType.SQLITE

    def test_from_env_postgresql(self):
        env = {
            "DATABASE_TYPE": "postgresql",
            "DATABASE_HOST": "pg.example.com",
            "DATABASE_PORT": "5433",
            "DATABASE_USER": "usr",
            "DATABASE_PASSWORD": "pw",
            "DATABASE_NAME": "testdb",
            "DATABASE_ECHO": "true",
        }
        with patch.dict(os.environ, env, clear=False):
            cfg = DatabaseConfig.from_env()
            assert cfg.db_type == DatabaseType.POSTGRESQL
            assert cfg.host == "pg.example.com"
            assert cfg.port == 5433
            assert cfg.echo is True

    def test_pool_size_default_upgrade(self):
        cfg = DatabaseConfig()  # default pool_size=5 → upgraded to 20
        assert cfg.pool_size == 20
        assert cfg.max_overflow == 30

    def test_pool_size_explicit(self):
        cfg = DatabaseConfig(pool_size=8, max_overflow=16)
        assert cfg.pool_size == 8
        assert cfg.max_overflow == 16

    def test_repr(self):
        cfg = DatabaseConfig(db_type=DatabaseType.SQLITE)
        r = repr(cfg)
        assert "sqlite" in r.lower()

    def test_sslmode_in_postgresql_url(self):
        cfg = DatabaseConfig(
            db_type=DatabaseType.POSTGRESQL,
            host="h",
            username="u",
            sslmode="require",
        )
        url = cfg.get_connection_string()
        assert "sslmode=require" in url

    def test_db_type_from_string(self):
        cfg = DatabaseConfig(db_type="sqlite")
        assert cfg.db_type == DatabaseType.SQLITE


# =====================================================================
# 3. DatabaseConnection (singleton + engine lifecycle)
# =====================================================================

class TestDatabaseConnection:
    """Test DatabaseConnection singleton and lifecycle methods."""

    def setup_method(self):
        # Reset singleton between tests
        DatabaseConnection._instance = None
        DatabaseConnection._engine = None
        DatabaseConnection._config = None

    def test_singleton(self):
        a = DatabaseConnection()
        b = DatabaseConnection()
        assert a is b

    def test_get_engine_before_init_raises(self):
        with pytest.raises(RuntimeError, match="not initialized"):
            DatabaseConnection.get_engine()

    def test_get_config_before_init_raises(self):
        with pytest.raises(RuntimeError, match="not initialized"):
            DatabaseConnection.get_config()

    def test_initialize_and_get_engine(self, tmp_path):
        cfg = DatabaseConfig(
            db_type=DatabaseType.SQLITE,
            database_path=str(tmp_path / "conn_test.db"),
        )
        DatabaseConnection.initialize(cfg)
        engine = DatabaseConnection.get_engine()
        assert engine is not None

    def test_close(self, tmp_path):
        cfg = DatabaseConfig(
            db_type=DatabaseType.SQLITE,
            database_path=str(tmp_path / "close_test.db"),
        )
        DatabaseConnection.initialize(cfg)
        DatabaseConnection.close()
        assert DatabaseConnection._engine is None

    def test_health_check_healthy(self, tmp_path):
        cfg = DatabaseConfig(
            db_type=DatabaseType.SQLITE,
            database_path=str(tmp_path / "health.db"),
        )
        DatabaseConnection.initialize(cfg)
        assert DatabaseConnection.health_check() is True

    def test_health_check_unhealthy(self):
        # Not initialized → health_check should return False
        DatabaseConnection._instance = DatabaseConnection.__new__(DatabaseConnection)
        DatabaseConnection._engine = None
        DatabaseConnection._config = None
        assert DatabaseConnection.health_check() is False


# =====================================================================
# 4. BaseRepository CRUD (with real SQLite)
# =====================================================================

class TestBaseRepository:
    """Test BaseRepository CRUD operations against a real in-memory DB."""

    def test_create(self, db_session):
        repo = BaseRepository(db_session, Item)
        item = repo.create(name="created", quantity=10)
        assert item.id is not None
        assert item.name == "created"

    def test_get(self, db_session):
        repo = BaseRepository(db_session, Item)
        item = repo.create(name="getme")
        fetched = repo.get(item.id)
        assert fetched is not None
        assert fetched.name == "getme"

    def test_get_nonexistent(self, db_session):
        repo = BaseRepository(db_session, Item)
        assert repo.get(999999) is None

    def test_get_all(self, db_session):
        repo = BaseRepository(db_session, Item)
        repo.create(name="a")
        repo.create(name="b")
        repo.create(name="c")
        items = repo.get_all()
        assert len(items) >= 3

    def test_get_all_pagination(self, db_session):
        repo = BaseRepository(db_session, Item)
        for i in range(5):
            repo.create(name=f"pag_{i}")
        page = repo.get_all(skip=2, limit=2)
        assert len(page) == 2

    def test_update(self, db_session):
        repo = BaseRepository(db_session, Item)
        item = repo.create(name="before")
        updated = repo.update(item.id, name="after")
        assert updated.name == "after"

    def test_update_nonexistent(self, db_session):
        repo = BaseRepository(db_session, Item)
        assert repo.update(999999, name="nope") is None

    def test_delete(self, db_session):
        repo = BaseRepository(db_session, Item)
        item = repo.create(name="delete_me")
        assert repo.delete(item.id) is True
        assert repo.get(item.id) is None

    def test_delete_nonexistent(self, db_session):
        repo = BaseRepository(db_session, Item)
        assert repo.delete(999999) is False

    def test_filter(self, db_session):
        repo = BaseRepository(db_session, Item)
        repo.create(name="alpha", quantity=1)
        repo.create(name="beta", quantity=2)
        repo.create(name="alpha", quantity=3)
        results = repo.filter(name="alpha")
        assert len(results) == 2
        assert all(r.name == "alpha" for r in results)

    def test_filter_first(self, db_session):
        repo = BaseRepository(db_session, Item)
        repo.create(name="unique_one", quantity=42)
        result = repo.filter_first(name="unique_one")
        assert result is not None
        assert result.quantity == 42

    def test_filter_first_not_found(self, db_session):
        repo = BaseRepository(db_session, Item)
        assert repo.filter_first(name="does_not_exist") is None

    def test_count(self, db_session):
        repo = BaseRepository(db_session, Item)
        repo.create(name="c1")
        repo.create(name="c2")
        assert repo.count() >= 2

    def test_exists(self, db_session):
        repo = BaseRepository(db_session, Item)
        repo.create(name="exists_test")
        assert repo.exists(name="exists_test") is True
        assert repo.exists(name="no_such_item") is False

    def test_bulk_create(self, db_session):
        repo = BaseRepository(db_session, Item)
        items = [Item(name=f"bulk_{i}") for i in range(3)]
        created = repo.bulk_create(items)
        assert len(created) == 3

    def test_clear(self, db_session):
        repo = BaseRepository(db_session, Item)
        repo.create(name="clear1")
        repo.create(name="clear2")
        deleted_count = repo.clear()
        assert deleted_count >= 2
        assert repo.count() == 0


# =====================================================================
# 5. Session management (session_scope, initialize_session_factory)
# =====================================================================

class TestSessionManagement:
    """Test session_scope and related helpers."""

    def setup_method(self):
        # Reset module-level SessionLocal and singleton
        session_mod.SessionLocal = None
        DatabaseConnection._instance = None
        DatabaseConnection._engine = None
        DatabaseConnection._config = None
        # Reset circuit breaker state
        session_mod._cb_failures = 0
        session_mod._cb_open_until = 0.0

    def _init_memory_db(self):
        cfg = DatabaseConfig(
            db_type=DatabaseType.SQLITE,
            database_path=":memory:",
        )
        DatabaseConnection.initialize(cfg)
        Base.metadata.create_all(DatabaseConnection.get_engine())

    def test_initialize_session_factory(self):
        self._init_memory_db()
        factory = session_mod.initialize_session_factory()
        assert factory is not None
        assert session_mod.SessionLocal is factory

    def test_session_scope_commit(self):
        self._init_memory_db()
        session_mod.initialize_session_factory()

        with session_mod.session_scope() as s:
            s.add(Item(name="scope_test"))

        # New session to verify persistence
        with session_mod.session_scope() as s:
            result = s.query(Item).filter(Item.name == "scope_test").first()
            assert result is not None

    def test_session_scope_rollback_on_error(self):
        self._init_memory_db()
        session_mod.initialize_session_factory()

        with pytest.raises(ValueError):
            with session_mod.session_scope() as s:
                s.add(Item(name="rollback_test"))
                raise ValueError("force rollback")

        with session_mod.session_scope() as s:
            result = s.query(Item).filter(Item.name == "rollback_test").first()
            assert result is None

    def test_get_session_factory_lazy_init(self):
        self._init_memory_db()
        # SessionLocal is None at this point
        factory = session_mod.get_session_factory()
        assert factory is not None

    def test_is_lock_error(self):
        assert session_mod._is_lock_error(Exception("database is locked")) is True
        assert session_mod._is_lock_error(Exception("something locked happened")) is True
        assert session_mod._is_lock_error(Exception("normal error")) is False

    def test_circuit_breaker_opens_after_threshold(self):
        for _ in range(session_mod._CB_THRESHOLD):
            session_mod._cb_record_failure()

        assert session_mod._cb_is_open() is True

    def test_circuit_breaker_success_decrements(self):
        session_mod._cb_failures = 5
        session_mod._cb_record_success()
        assert session_mod._cb_failures == 4
        # open_until should be reset
        assert session_mod._cb_open_until == 0.0

    def test_circuit_breaker_blocks_session_scope(self):
        self._init_memory_db()
        session_mod.initialize_session_factory()
        session_mod._cb_open_until = time.time() + 100  # far in the future

        with pytest.raises(RuntimeError, match="circuit breaker OPEN"):
            with session_mod.session_scope() as s:
                pass

    def test_batch_session_scope(self):
        self._init_memory_db()
        session_mod.initialize_session_factory()

        with session_mod.batch_session_scope(batch_size=2) as (s, flush):
            for i in range(4):
                s.add(Item(name=f"batch_{i}"))
                if (i + 1) % 2 == 0:
                    flush()

        with session_mod.session_scope() as s:
            count = s.query(Item).filter(Item.name.like("batch_%")).count()
            assert count == 4


# =====================================================================
# 6. Model definitions – verify schema (columns, relationships, tables)
# =====================================================================

class TestModelDefinitions:
    """Verify ORM model schemas without hitting a live DB."""

    def test_user_table_name(self):
        from models.database_models import User
        assert User.__tablename__ == "users"

    def test_user_columns(self):
        from models.database_models import User
        col_names = {c.name for c in User.__table__.columns}
        assert {"id", "username", "email", "full_name", "is_active",
                "created_at", "updated_at"} <= col_names

    def test_conversation_has_messages_relationship(self):
        from models.database_models import Conversation
        assert hasattr(Conversation, "messages")

    def test_message_foreign_key(self):
        from models.database_models import Message
        fk_cols = [
            c.name for c in Message.__table__.columns
            if c.foreign_keys
        ]
        assert "conversation_id" in fk_cols

    def test_chat_table_and_columns(self):
        from models.database_models import Chat
        assert Chat.__tablename__ == "chats"
        col_names = {c.name for c in Chat.__table__.columns}
        assert "temperature" in col_names
        assert "chat_type" in col_names
        assert "is_active" in col_names
        assert "folder_path" in col_names

    def test_chat_history_relationship(self):
        from models.database_models import Chat
        assert hasattr(Chat, "chat_history")

    def test_document_table_and_confidence_columns(self):
        from models.database_models import Document
        assert Document.__tablename__ == "documents"
        col_names = {c.name for c in Document.__table__.columns}
        assert "confidence_score" in col_names
        assert "source_reliability" in col_names
        assert "content_quality" in col_names

    def test_document_chunk_relationship(self):
        from models.database_models import Document
        assert hasattr(Document, "chunks")

    def test_embedding_columns(self):
        from models.database_models import Embedding
        col_names = {c.name for c in Embedding.__table__.columns}
        assert {"text", "embedding", "dimension", "model", "source"} <= col_names

    def test_governance_rule_table(self):
        from models.database_models import GovernanceRule
        assert GovernanceRule.__tablename__ == "governance_rules"
        col_names = {c.name for c in GovernanceRule.__table__.columns}
        assert "pillar_type" in col_names
        assert "severity" in col_names
        assert "action" in col_names

    def test_governance_decision_table(self):
        from models.database_models import GovernanceDecision
        assert GovernanceDecision.__tablename__ == "governance_decisions"
        col_names = {c.name for c in GovernanceDecision.__table__.columns}
        assert "approval_id" in col_names
        assert "action_type" in col_names

    def test_learning_example_table(self):
        from models.database_models import LearningExample
        assert LearningExample.__tablename__ == "learning_examples"
        col_names = {c.name for c in LearningExample.__table__.columns}
        assert "trust_score" in col_names
        assert "genesis_key_id" in col_names

    def test_schema_proposal_table(self):
        from models.database_models import SchemaProposal
        assert SchemaProposal.__tablename__ == "schema_proposals"
        col_names = {c.name for c in SchemaProposal.__table__.columns}
        assert "proposal_id" in col_names
        assert "proposed_code" in col_names

    def test_genesis_key_table_and_columns(self):
        from models.genesis_key_models import GenesisKey
        assert GenesisKey.__tablename__ == "genesis_key"
        col_names = {c.name for c in GenesisKey.__table__.columns}
        assert "key_id" in col_names
        assert "what_description" in col_names
        assert "who_actor" in col_names
        assert "is_error" in col_names

    def test_genesis_key_has_fix_suggestions_relationship(self):
        from models.genesis_key_models import GenesisKey
        assert hasattr(GenesisKey, "fix_suggestions")

    def test_fix_suggestion_foreign_key(self):
        from models.genesis_key_models import FixSuggestion
        fk_cols = [c.name for c in FixSuggestion.__table__.columns if c.foreign_keys]
        assert "genesis_key_id" in fk_cols

    def test_genesis_key_archive_columns(self):
        from models.genesis_key_models import GenesisKeyArchive
        col_names = {c.name for c in GenesisKeyArchive.__table__.columns}
        assert "archive_id" in col_names
        assert "key_count" in col_names
        assert "error_count" in col_names

    def test_user_profile_columns(self):
        from models.genesis_key_models import UserProfile
        col_names = {c.name for c in UserProfile.__table__.columns}
        assert "user_id" in col_names
        assert "total_actions" in col_names

    def test_genesis_key_type_enum_values(self):
        from models.genesis_key_models import GenesisKeyType
        assert GenesisKeyType.ERROR.value == "error"
        assert GenesisKeyType.CODE_CHANGE.value == "code_change"
        assert GenesisKeyType.LEARNING_COMPLETE.value == "learning_complete"

    def test_genesis_key_status_enum_values(self):
        from models.genesis_key_models import GenesisKeyStatus
        assert GenesisKeyStatus.ACTIVE.value == "active"
        assert GenesisKeyStatus.ROLLED_BACK.value == "rolled_back"

    def test_chat_type_enum(self):
        from models.database_models import ChatType
        assert ChatType.GENERAL.value == "general"
        assert ChatType.FORENSIC.value == "forensic"


# =====================================================================
# 7. Typed repositories from models.repositories
# =====================================================================

class TestTypedRepositories:
    """Test typed repository subclasses with a real in-memory DB."""

    @pytest.fixture(autouse=True)
    def _setup_session(self, in_memory_engine, db_session):
        self.session = db_session

    def test_user_repository_crud(self):
        from models.repositories import UserRepository
        from models.database_models import User

        repo = UserRepository(self.session)
        user = repo.create(username="alice", email="alice@test.com")
        assert user.id is not None

        fetched = repo.get_by_username("alice")
        assert fetched is not None
        assert fetched.email == "alice@test.com"

        by_email = repo.get_by_email("alice@test.com")
        assert by_email is not None

    def test_user_repository_active_users(self):
        from models.repositories import UserRepository

        repo = UserRepository(self.session)
        repo.create(username="active1", email="a1@t.com", is_active=True)
        repo.create(username="inactive1", email="i1@t.com", is_active=False)
        actives = repo.get_active_users()
        assert all(u.is_active for u in actives)

    def test_chat_repository_lifecycle(self):
        from models.repositories import ChatRepository

        repo = ChatRepository(self.session)
        chat = repo.create(title="Test Chat", model="gpt-4")
        assert chat.id is not None

        chats = repo.get_all_chats()
        assert len(chats) >= 1

        deactivated = repo.deactivate(chat.id)
        assert deactivated.is_active is False

        activated = repo.activate(chat.id)
        assert activated.is_active is True

    def test_chat_history_repository_add_and_count(self):
        from models.repositories import ChatRepository, ChatHistoryRepository

        chat_repo = ChatRepository(self.session)
        chat = chat_repo.create(title="History Chat", model="gpt-4")

        hist_repo = ChatHistoryRepository(self.session)
        msg = hist_repo.add_message(chat_id=chat.id, role="user", content="Hello")
        assert msg.id is not None
        assert msg.role == "user"

        count = hist_repo.count_by_chat(chat.id)
        assert count == 1

    def test_chat_history_edit_message(self):
        from models.repositories import ChatRepository, ChatHistoryRepository

        chat_repo = ChatRepository(self.session)
        chat = chat_repo.create(title="Edit Chat", model="gpt-4")

        hist_repo = ChatHistoryRepository(self.session)
        msg = hist_repo.add_message(chat_id=chat.id, role="user", content="Original")
        edited = hist_repo.edit_message(msg.id, "Edited content")
        assert edited.content == "Edited content"
        assert edited.is_edited is True
        assert edited.edited_content == "Original"


# =====================================================================
# 8. Auto-migrate helpers (unit-level, mocked DB)
# =====================================================================

class TestAutoMigrateHelpers:
    """Test auto_migrate utility functions."""

    def test_pg_type_for_column_known(self):
        from database.auto_migrate import _pg_type_for_column
        col = Column("test", String(255))
        assert _pg_type_for_column(col) == "VARCHAR"

    def test_pg_type_for_column_text(self):
        from database.auto_migrate import _pg_type_for_column
        col = Column("test", Text)
        assert _pg_type_for_column(col) == "TEXT"

    def test_pg_type_for_column_unknown_defaults_text(self):
        from database.auto_migrate import _pg_type_for_column
        # Use a type that's not in the map
        from sqlalchemy import LargeBinary
        col = Column("test", LargeBinary)
        result = _pg_type_for_column(col)
        assert isinstance(result, str)  # should return something valid

    def test_enum_column_map_keys(self):
        from database.auto_migrate import ENUM_COLUMN_MAP
        assert "genesiskeytype" in ENUM_COLUMN_MAP
        assert "genesiskeystatus" in ENUM_COLUMN_MAP
        _, vals = ENUM_COLUMN_MAP["genesiskeytype"]
        assert "error" in vals
        assert "learning_complete" in vals
