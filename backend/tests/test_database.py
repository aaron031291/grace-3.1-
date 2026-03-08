"""
Database module tests.
"""

import pytest
from sqlalchemy.orm import Session
from pathlib import Path
import tempfile
import os

from database.config import DatabaseConfig, DatabaseType
from database.connection import DatabaseConnection
from database import session as db_session
from database.migration import create_tables, drop_tables, table_exists, get_all_tables
from models.database_models import User, Conversation, Message, Chat, ChatHistory
from models.repositories import UserRepository, ConversationRepository, ChatRepository, ChatHistoryRepository


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_grace.db")
        yield db_path


@pytest.fixture
def test_config(temp_db):
    """Create a test database configuration."""
    return DatabaseConfig(
        db_type=DatabaseType.SQLITE,
        database_path=temp_db,
        echo=False,
    )


@pytest.fixture
def initialized_db(test_config):
    """Initialize database for testing."""
    DatabaseConnection.initialize(test_config)
    db_session.initialize_session_factory()
    create_tables()
    yield
    drop_tables()
    DatabaseConnection.close()


class TestDatabaseConfig:
    """Test database configuration."""
    
    def test_sqlite_connection_string(self):
        """Test SQLite connection string generation."""
        config = DatabaseConfig(
            db_type=DatabaseType.SQLITE,
            database_path="./test.db"
        )
        assert config.get_connection_string().startswith("sqlite:///")
    
    def test_postgresql_connection_string(self):
        """Test PostgreSQL connection string generation."""
        config = DatabaseConfig(
            db_type=DatabaseType.POSTGRESQL,
            host="localhost",
            port=5432,
            username="user",
            password="pass",
            database="testdb"
        )
        assert config.get_connection_string() == "postgresql+psycopg2://user:pass@localhost:5432/testdb"
    
    def test_mysql_connection_string(self):
        """Test MySQL connection string generation."""
        config = DatabaseConfig(
            db_type=DatabaseType.MYSQL,
            host="localhost",
            port=3306,
            username="user",
            password="pass",
            database="testdb"
        )
        assert config.get_connection_string() == "mysql+pymysql://user:pass@localhost:3306/testdb"


class TestDatabaseConnection:
    """Test database connection."""
    
    def test_initialize_connection(self, test_config):
        """Test database connection initialization."""
        db = DatabaseConnection.initialize(test_config)
        assert db is not None
        assert DatabaseConnection.get_engine() is not None
        DatabaseConnection.close()
    
    def test_singleton_pattern(self, test_config):
        """Test database connection is singleton."""
        db1 = DatabaseConnection.initialize(test_config)
        db2 = DatabaseConnection()
        assert db1 is db2
        DatabaseConnection.close()
    
    def test_health_check(self, initialized_db):
        """Test database health check."""
        assert DatabaseConnection.health_check() is True


class TestDatabaseModels:
    """Test database models."""
    
    def test_create_user(self, initialized_db):
        """Test creating a user."""
        session = db_session.SessionLocal()
        user = User(
            username="testuser",
            email="test@example.com",
            full_name="Test User"
        )
        session.add(user)
        session.commit()
        
        # Verify creation
        created_user = session.query(User).filter_by(username="testuser").first()
        assert created_user is not None
        assert created_user.email == "test@example.com"
        assert created_user.is_active is True
        session.close()
    
    def test_user_timestamps(self, initialized_db):
        """Test user creation timestamps."""
        from datetime import timedelta
        session = db_session.SessionLocal()
        user = User(username="test", email="test@example.com")
        session.add(user)
        session.commit()

        assert user.created_at is not None
        assert user.updated_at is not None
        # Timestamps may differ by a few microseconds, allow 1 second tolerance
        assert abs((user.created_at - user.updated_at).total_seconds()) < 1
        session.close()
    
    def test_conversation_relationship(self, initialized_db):
        """Test conversation relationship."""
        session = db_session.SessionLocal()
        
        # Create conversation
        conversation = Conversation(
            title="Test Chat",
            model="mistral:7b"
        )
        session.add(conversation)
        session.commit()
        
        # Verify conversation exists
        conv = session.query(Conversation).filter_by(id=conversation.id).first()
        assert conv is not None
        assert conv.title == "Test Chat"
        
        session.close()


class TestBaseRepository:
    """Test base repository functionality."""
    
    def test_create_user(self, initialized_db):
        """Test repository create operation."""
        session = db_session.SessionLocal()
        repo = UserRepository(session)
        
        user = repo.create(
            username="testuser",
            email="test@example.com",
            full_name="Test User"
        )
        
        assert user.id is not None
        assert user.username == "testuser"
        session.close()
    
    def test_get_user(self, initialized_db):
        """Test repository get operation."""
        session = db_session.SessionLocal()
        repo = UserRepository(session)
        
        # Create user
        user = repo.create(username="test", email="test@example.com")
        user_id = user.id
        
        # Get user
        retrieved_user = repo.get(user_id)
        assert retrieved_user is not None
        assert retrieved_user.username == "test"
        
        session.close()
    
    def test_update_user(self, initialized_db):
        """Test repository update operation."""
        session = db_session.SessionLocal()
        repo = UserRepository(session)
        
        # Create and update user
        user = repo.create(username="test", email="test@example.com")
        user_id = user.id
        
        updated_user = repo.update(user_id, full_name="Updated Name")
        assert updated_user.full_name == "Updated Name"
        
        session.close()
    
    def test_delete_user(self, initialized_db):
        """Test repository delete operation."""
        session = db_session.SessionLocal()
        repo = UserRepository(session)
        
        # Create and delete user
        user = repo.create(username="test", email="test@example.com")
        user_id = user.id
        
        deleted = repo.delete(user_id)
        assert deleted is True
        
        # Verify deletion
        retrieved_user = repo.get(user_id)
        assert retrieved_user is None
        
        session.close()
    
    def test_get_all(self, initialized_db):
        """Test repository get_all operation."""
        session = db_session.SessionLocal()
        repo = UserRepository(session)
        
        # Create multiple users
        repo.create(username="user1", email="user1@example.com")
        repo.create(username="user2", email="user2@example.com")
        repo.create(username="user3", email="user3@example.com")
        
        users = repo.get_all()
        assert len(users) == 3
        
        session.close()
    
    def test_filter(self, initialized_db):
        """Test repository filter operation."""
        session = db_session.SessionLocal()
        repo = UserRepository(session)
        
        # Create users
        repo.create(username="active1", email="user1@example.com", is_active=True)
        repo.create(username="inactive", email="user2@example.com", is_active=False)
        repo.create(username="active2", email="user3@example.com", is_active=True)
        
        active_users = repo.filter(is_active=True)
        assert len(active_users) == 2
        
        session.close()
    
    def test_count(self, initialized_db):
        """Test repository count operation."""
        session = db_session.SessionLocal()
        repo = UserRepository(session)
        
        repo.create(username="user1", email="user1@example.com")
        repo.create(username="user2", email="user2@example.com")
        
        count = repo.count()
        assert count == 2
        
        session.close()
    
    def test_exists(self, initialized_db):
        """Test repository exists operation."""
        session = db_session.SessionLocal()
        repo = UserRepository(session)
        
        repo.create(username="testuser", email="test@example.com")
        
        assert repo.exists(username="testuser") is True
        assert repo.exists(username="notexist") is False
        
        session.close()
    
    def test_bulk_create(self, initialized_db):
        """Test repository bulk create."""
        session = db_session.SessionLocal()
        repo = UserRepository(session)
        
        users = [
            User(username="user1", email="user1@example.com"),
            User(username="user2", email="user2@example.com"),
            User(username="user3", email="user3@example.com"),
        ]
        
        created = repo.bulk_create(users)
        assert len(created) == 3
        
        total = repo.count()
        assert total == 3
        
        session.close()
    
    def test_bulk_delete(self, initialized_db):
        """Test repository bulk delete."""
        session = db_session.SessionLocal()
        repo = UserRepository(session)
        
        user1 = repo.create(username="user1", email="user1@example.com")
        user2 = repo.create(username="user2", email="user2@example.com")
        user3 = repo.create(username="user3", email="user3@example.com")
        
        deleted_count = repo.bulk_delete([user1.id, user2.id])
        assert deleted_count == 2
        
        remaining = repo.count()
        assert remaining == 1
        
        session.close()


class TestCustomRepositories:
    """Test custom repository implementations."""
    
    def test_get_by_username(self, initialized_db):
        """Test custom get_by_username method."""
        session = db_session.SessionLocal()
        repo = UserRepository(session)
        
        repo.create(username="testuser", email="test@example.com")
        
        user = repo.get_by_username("testuser")
        assert user is not None
        assert user.email == "test@example.com"
        
        session.close()
    
    def test_get_active_users(self, initialized_db):
        """Test custom get_active_users method."""
        session = db_session.SessionLocal()
        repo = UserRepository(session)
        
        repo.create(username="active1", email="user1@example.com", is_active=True)
        repo.create(username="inactive", email="user2@example.com", is_active=False)
        repo.create(username="active2", email="user3@example.com", is_active=True)
        
        active_users = repo.get_active_users()
        assert len(active_users) == 2
        
        session.close()
    
    def test_get_all_conversations(self, initialized_db):
        """Test getting all conversations."""
        session = db_session.SessionLocal()
        conv_repo = ConversationRepository(session)
        
        # Create conversations
        conv_repo.create(title="Chat 1")
        conv_repo.create(title="Chat 2")
        
        # Get conversations
        conversations = conv_repo.get_all_conversations()
        assert len(conversations) == 2
        
        session.close()


class TestMigration:
    """Test migration utilities."""
    
    def test_table_exists(self, initialized_db):
        """Test table_exists function."""
        assert table_exists("users") is True
        assert table_exists("nonexistent") is False
    
    def test_get_all_tables(self, initialized_db):
        """Test get_all_tables function."""
        tables = get_all_tables()
        assert "users" in tables
        assert "conversations" in tables
        assert "messages" in tables
        assert "chats" in tables
        assert "chat_history" in tables


class TestChatModel:
    """Test Chat model."""
    
    def test_create_chat(self, initialized_db):
        """Test creating a chat."""
        session = db_session.SessionLocal()
        
        # Create chat
        chat = Chat(
            title="Test Chat",
            model="mistral:7b",
            temperature=0.7
        )
        session.add(chat)
        session.commit()
        
        # Verify
        created_chat = session.query(Chat).filter_by(id=chat.id).first()
        assert created_chat is not None
        assert created_chat.title == "Test Chat"
        assert created_chat.is_active is True
        session.close()
    
    def test_multiple_chats(self, initialized_db):
        """Test creating multiple chats."""
        session = db_session.SessionLocal()
        chat_repo = ChatRepository(session)
        
        # Create multiple chats
        chat1 = chat_repo.create(title="Chat 1")
        chat2 = chat_repo.create(title="Chat 2")
        
        # Verify they were created
        assert chat1.id is not None
        assert chat2.id is not None
        assert chat1.is_active is True
        assert chat2.is_active is True
        session.close()


class TestChatHistoryModel:
    """Test ChatHistory model."""
    
    def test_create_chat_history(self, initialized_db):
        """Test creating chat history."""
        session = db_session.SessionLocal()
        
        # Create chat
        chat = Chat(title="Test Chat")
        session.add(chat)
        session.commit()
        
        # Create history
        history = ChatHistory(
            chat_id=chat.id,
            role="user",
            content="Hello AI",
            tokens=3
        )
        session.add(history)
        session.commit()
        
        # Verify
        created_history = session.query(ChatHistory).filter_by(id=history.id).first()
        assert created_history is not None
        assert created_history.role == "user"
        assert created_history.is_edited is False
        session.close()


class TestChatRepository:
    """Test ChatRepository operations."""
    
    def test_get_all_chats(self, initialized_db):
        """Test getting all chats."""
        session = db_session.SessionLocal()
        chat_repo = ChatRepository(session)
        
        # Create chats
        chat_repo.create(title="Chat 1")
        chat_repo.create(title="Chat 2")
        chat_repo.create(title="Chat 3")
        
        # Get chats
        chats = chat_repo.get_all_chats()
        assert len(chats) == 3
        session.close()
    
    def test_get_active_chats(self, initialized_db):
        """Test getting active chats."""
        session = db_session.SessionLocal()
        chat_repo = ChatRepository(session)
        
        # Create chats
        chat1 = chat_repo.create(title="Chat 1", is_active=True)
        chat2 = chat_repo.create(title="Chat 2", is_active=False)
        chat3 = chat_repo.create(title="Chat 3", is_active=True)
        
        # Get active chats
        active_chats = chat_repo.get_active_chats()
        assert len(active_chats) == 2
        session.close()
    
    def test_deactivate_chat(self, initialized_db):
        """Test deactivating a chat."""
        session = db_session.SessionLocal()
        chat_repo = ChatRepository(session)
        
        # Create chat
        chat = chat_repo.create(title="Chat 1", is_active=True)
        
        # Deactivate
        deactivated = chat_repo.deactivate(chat.id)
        assert deactivated.is_active is False
        session.close()
    
    def test_search_by_title(self, initialized_db):
        """Test searching chats by title."""
        session = db_session.SessionLocal()
        chat_repo = ChatRepository(session)
        
        # Create chats with searchable titles
        chat_repo.create(title="Python Help")
        chat_repo.create(title="JavaScript Question")
        chat_repo.create(title="Python Performance")
        
        # Search
        results = chat_repo.search_by_title("Python")
        assert len(results) == 2
        session.close()


class TestChatHistoryRepository:
    """Test ChatHistoryRepository operations."""
    
    def test_add_message(self, initialized_db):
        """Test adding a message to chat history."""
        session = db_session.SessionLocal()
        chat_repo = ChatRepository(session)
        history_repo = ChatHistoryRepository(session)
        
        # Create chat
        chat = chat_repo.create(title="Chat 1")
        
        # Add message
        message = history_repo.add_message(
            chat_id=chat.id,
            role="user",
            content="Hello",
            tokens=1
        )
        
        assert message.id is not None
        assert message.role == "user"
        session.close()
    
    def test_get_by_chat(self, initialized_db):
        """Test getting messages from a chat."""
        session = db_session.SessionLocal()
        chat_repo = ChatRepository(session)
        history_repo = ChatHistoryRepository(session)
        
        # Create chat
        chat = chat_repo.create(title="Chat 1")
        
        # Add messages
        history_repo.add_message(chat_id=chat.id, role="user", content="Hi")
        history_repo.add_message(chat_id=chat.id, role="assistant", content="Hello!")
        history_repo.add_message(chat_id=chat.id, role="user", content="How are you?")
        
        # Get messages
        messages = history_repo.get_by_chat(chat.id)
        assert len(messages) == 3
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"
        session.close()
    
    def test_get_by_role(self, initialized_db):
        """Test getting messages by role."""
        session = db_session.SessionLocal()
        chat_repo = ChatRepository(session)
        history_repo = ChatHistoryRepository(session)
        
        # Create chat
        chat = chat_repo.create(title="Chat 1")
        
        # Add messages
        history_repo.add_message(chat_id=chat.id, role="user", content="Hi")
        history_repo.add_message(chat_id=chat.id, role="assistant", content="Hello!")
        history_repo.add_message(chat_id=chat.id, role="user", content="How are you?")
        
        # Get user messages
        user_messages = history_repo.get_by_role(chat.id, "user")
        assert len(user_messages) == 2
        
        # Get assistant messages
        assistant_messages = history_repo.get_by_role(chat.id, "assistant")
        assert len(assistant_messages) == 1
        session.close()
    
    def test_edit_message(self, initialized_db):
        """Test editing a message."""
        session = db_session.SessionLocal()
        chat_repo = ChatRepository(session)
        history_repo = ChatHistoryRepository(session)
        
        # Create chat
        chat = chat_repo.create(title="Chat 1")
        
        # Add message
        message = history_repo.add_message(chat_id=chat.id, role="user", content="Original")
        
        # Edit message
        edited = history_repo.edit_message(message.id, "Modified")
        assert edited.content == "Modified"
        assert edited.is_edited is True
        assert edited.edited_content == "Original"
        session.close()
    
    def test_count_tokens(self, initialized_db):
        """Test counting tokens in a chat."""
        session = db_session.SessionLocal()
        chat_repo = ChatRepository(session)
        history_repo = ChatHistoryRepository(session)
        
        # Create chat
        chat = chat_repo.create(title="Chat 1")
        
        # Add messages with tokens
        history_repo.add_message(chat_id=chat.id, role="user", content="Hi", tokens=2)
        history_repo.add_message(chat_id=chat.id, role="assistant", content="Hello!", tokens=3)
        history_repo.add_message(chat_id=chat.id, role="user", content="How?", tokens=1)
        
        # Count tokens
        total_tokens = history_repo.count_tokens_in_chat(chat.id)
        assert total_tokens == 6
        session.close()
    
    def test_get_edited_messages(self, initialized_db):
        """Test getting edited messages."""
        session = db_session.SessionLocal()
        chat_repo = ChatRepository(session)
        history_repo = ChatHistoryRepository(session)
        
        # Create chat
        chat = chat_repo.create(title="Chat 1")
        
        # Add and edit messages
        msg1 = history_repo.add_message(chat_id=chat.id, role="user", content="Original 1")
        msg2 = history_repo.add_message(chat_id=chat.id, role="user", content="Original 2")
        msg3 = history_repo.add_message(chat_id=chat.id, role="user", content="Original 3")
        
        # Edit some messages
        history_repo.edit_message(msg1.id, "Modified 1")
        history_repo.edit_message(msg3.id, "Modified 3")
        
        # Get edited messages
        edited = history_repo.get_edited_messages(chat.id)
        assert len(edited) == 2
        session.close()
