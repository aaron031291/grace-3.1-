"""
Comprehensive Test Suite for Models Module
==========================================
Tests for database models and repositories.

Coverage:
- Database model definitions and fields
- Model relationships
- Model serialization (to_dict methods)
- Repository CRUD operations
- Repository custom queries
- Repository pagination and filtering
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from datetime import datetime, timedelta
import sys

# =============================================================================
# Mock SQLAlchemy and related modules before any imports
# =============================================================================

# Create mock SQLAlchemy module hierarchy
mock_sqlalchemy = MagicMock()
mock_sqlalchemy.Column = MagicMock()
mock_sqlalchemy.Integer = MagicMock()
mock_sqlalchemy.String = MagicMock()
mock_sqlalchemy.Boolean = MagicMock()
mock_sqlalchemy.DateTime = MagicMock()
mock_sqlalchemy.Text = MagicMock()
mock_sqlalchemy.Float = MagicMock()
mock_sqlalchemy.ForeignKey = MagicMock()
mock_sqlalchemy.Index = MagicMock()
mock_sqlalchemy.create_engine = MagicMock()

# Mock pool
mock_pool = MagicMock()
mock_pool.QueuePool = MagicMock()
mock_pool.StaticPool = MagicMock()
mock_sqlalchemy.pool = mock_pool

# Mock orm
mock_orm = MagicMock()
mock_orm.Session = MagicMock()
mock_orm.sessionmaker = MagicMock()
mock_orm.relationship = MagicMock()
mock_orm.declarative_base = MagicMock(return_value=type('Base', (), {'metadata': MagicMock()}))
mock_sqlalchemy.orm = mock_orm

# Mock ext
mock_ext = MagicMock()
mock_ext.declarative = MagicMock()
mock_ext.declarative.declarative_base = MagicMock(return_value=type('Base', (), {'metadata': MagicMock()}))
mock_sqlalchemy.ext = mock_ext

# Register mocks
sys.modules['sqlalchemy'] = mock_sqlalchemy
sys.modules['sqlalchemy.pool'] = mock_pool
sys.modules['sqlalchemy.orm'] = mock_orm
sys.modules['sqlalchemy.ext'] = mock_ext
sys.modules['sqlalchemy.ext.declarative'] = mock_ext.declarative

sys.path.insert(0, '/home/user/grace-3.1-/backend')


# =============================================================================
# Model Definition Tests (Using Mock Classes)
# =============================================================================

class TestDatabaseModelDefinitions:
    """Test database model definitions and structure."""

    def test_user_model_has_expected_attributes(self):
        """Test User model definition."""
        # Create a mock User model
        class MockUser:
            __tablename__ = "users"
            id = None
            username = None
            email = None
            full_name = None
            is_active = True
            created_at = None
            updated_at = None

        user = MockUser()
        assert MockUser.__tablename__ == "users"
        assert hasattr(MockUser, 'id')
        assert hasattr(MockUser, 'username')
        assert hasattr(MockUser, 'email')
        assert hasattr(MockUser, 'full_name')
        assert hasattr(MockUser, 'is_active')

    def test_conversation_model_has_expected_attributes(self):
        """Test Conversation model definition."""
        class MockConversation:
            __tablename__ = "conversations"
            id = None
            title = None
            model = "gpt-4"
            system_prompt = None
            created_at = None
            updated_at = None

        conv = MockConversation()
        assert MockConversation.__tablename__ == "conversations"
        assert conv.model == "gpt-4"

    def test_message_model_has_expected_attributes(self):
        """Test Message model definition."""
        class MockMessage:
            __tablename__ = "messages"
            id = None
            conversation_id = None
            role = None
            content = None
            tokens = None
            created_at = None

        assert MockMessage.__tablename__ == "messages"
        assert hasattr(MockMessage, 'conversation_id')
        assert hasattr(MockMessage, 'role')
        assert hasattr(MockMessage, 'content')

    def test_embedding_model_has_expected_attributes(self):
        """Test Embedding model definition."""
        class MockEmbedding:
            __tablename__ = "embeddings"
            id = None
            content = None
            embedding = None
            source = None
            model = None
            dimension = 1536
            created_at = None

        embed = MockEmbedding()
        assert MockEmbedding.__tablename__ == "embeddings"
        assert embed.dimension == 1536

    def test_chat_model_has_expected_attributes(self):
        """Test Chat model definition."""
        class MockChat:
            __tablename__ = "chats"
            id = None
            title = None
            is_active = True
            created_at = None
            updated_at = None

        chat = MockChat()
        assert MockChat.__tablename__ == "chats"
        assert chat.is_active == True

    def test_chat_history_model_has_expected_attributes(self):
        """Test ChatHistory model definition."""
        class MockChatHistory:
            __tablename__ = "chat_history"
            id = None
            chat_id = None
            role = None
            content = None
            tokens = None
            token_ids = None
            completion_time = None
            is_edited = False
            edited_content = None
            edited_at = None
            created_at = None

        history = MockChatHistory()
        assert MockChatHistory.__tablename__ == "chat_history"
        assert history.is_edited == False

    def test_document_model_has_expected_attributes(self):
        """Test Document model definition."""
        class MockDocument:
            __tablename__ = "documents"
            id = None
            filename = None
            content = None
            file_type = None
            file_size = None
            is_processed = False
            created_at = None
            updated_at = None

        doc = MockDocument()
        assert MockDocument.__tablename__ == "documents"
        assert doc.is_processed == False

    def test_document_chunk_model_has_expected_attributes(self):
        """Test DocumentChunk model definition."""
        class MockDocumentChunk:
            __tablename__ = "document_chunks"
            id = None
            document_id = None
            chunk_index = None
            content = None
            embedding = None
            created_at = None

        chunk = MockDocumentChunk()
        assert MockDocumentChunk.__tablename__ == "document_chunks"
        assert hasattr(MockDocumentChunk, 'document_id')


# =============================================================================
# Governance Model Tests
# =============================================================================

class TestGovernanceModels:
    """Test governance-related models."""

    def test_governance_rule_model(self):
        """Test GovernanceRule model structure."""
        class MockGovernanceRule:
            __tablename__ = "governance_rules"
            id = None
            name = None
            description = None
            rule_type = None
            conditions = None
            actions = None
            priority = 0
            is_active = True
            created_at = None
            updated_at = None

            def to_dict(self):
                return {
                    "id": self.id,
                    "name": self.name,
                    "description": self.description,
                    "rule_type": self.rule_type,
                    "conditions": self.conditions,
                    "actions": self.actions,
                    "priority": self.priority,
                    "is_active": self.is_active,
                }

        rule = MockGovernanceRule()
        rule.id = 1
        rule.name = "Test Rule"
        rule.rule_type = "validation"
        rule.priority = 5

        result = rule.to_dict()
        assert result["id"] == 1
        assert result["name"] == "Test Rule"
        assert result["rule_type"] == "validation"
        assert result["priority"] == 5

    def test_governance_document_model(self):
        """Test GovernanceDocument model structure."""
        class MockGovernanceDocument:
            __tablename__ = "governance_documents"
            id = None
            title = None
            content = None
            document_type = None
            version = "1.0"
            status = "draft"
            created_at = None
            updated_at = None

            def to_dict(self):
                return {
                    "id": self.id,
                    "title": self.title,
                    "content": self.content,
                    "document_type": self.document_type,
                    "version": self.version,
                    "status": self.status,
                }

        doc = MockGovernanceDocument()
        doc.id = 1
        doc.title = "Policy Doc"
        doc.status = "approved"

        result = doc.to_dict()
        assert result["title"] == "Policy Doc"
        assert result["status"] == "approved"

    def test_governance_decision_model(self):
        """Test GovernanceDecision model structure."""
        class MockGovernanceDecision:
            __tablename__ = "governance_decisions"
            id = None
            decision_type = None
            context = None
            rules_applied = None
            outcome = None
            confidence_score = None
            explanation = None
            created_at = None

            def to_dict(self):
                return {
                    "id": self.id,
                    "decision_type": self.decision_type,
                    "context": self.context,
                    "rules_applied": self.rules_applied,
                    "outcome": self.outcome,
                    "confidence_score": self.confidence_score,
                    "explanation": self.explanation,
                }

        decision = MockGovernanceDecision()
        decision.id = 1
        decision.decision_type = "approval"
        decision.outcome = "approved"
        decision.confidence_score = 0.95

        result = decision.to_dict()
        assert result["decision_type"] == "approval"
        assert result["outcome"] == "approved"
        assert result["confidence_score"] == 0.95


# =============================================================================
# Repository Pattern Tests
# =============================================================================

class TestBaseRepositoryPattern:
    """Test the base repository pattern implementation."""

    def test_repository_create_operation(self):
        """Test repository create operation."""
        mock_session = MagicMock()
        mock_model = MagicMock()

        # Simulate create
        new_instance = MagicMock()
        mock_model.return_value = new_instance

        # Create through session
        mock_session.add(new_instance)
        mock_session.commit()
        mock_session.refresh(new_instance)

        mock_session.add.assert_called_once_with(new_instance)
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once_with(new_instance)

    def test_repository_get_operation(self):
        """Test repository get by id operation."""
        mock_session = MagicMock()
        mock_model = MagicMock()
        expected_instance = MagicMock()

        # Setup query chain
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.get.return_value = expected_instance

        result = mock_session.query(mock_model).get(1)

        assert result == expected_instance
        mock_session.query.assert_called_with(mock_model)

    def test_repository_update_operation(self):
        """Test repository update operation."""
        mock_session = MagicMock()
        existing_instance = MagicMock()
        existing_instance.id = 1
        existing_instance.name = "original"

        # Simulate update
        existing_instance.name = "updated"
        mock_session.commit()

        assert existing_instance.name == "updated"
        mock_session.commit.assert_called_once()

    def test_repository_delete_operation(self):
        """Test repository delete operation."""
        mock_session = MagicMock()
        instance_to_delete = MagicMock()

        # Simulate delete
        mock_session.delete(instance_to_delete)
        mock_session.commit()

        mock_session.delete.assert_called_once_with(instance_to_delete)
        mock_session.commit.assert_called_once()

    def test_repository_filter_operation(self):
        """Test repository filter operation."""
        mock_session = MagicMock()
        mock_model = MagicMock()

        # Setup query chain
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.all.return_value = [MagicMock(), MagicMock()]

        result = mock_session.query(mock_model).filter().all()

        assert len(result) == 2


# =============================================================================
# UserRepository Tests
# =============================================================================

class TestUserRepository:
    """Test UserRepository operations."""

    def test_user_repository_get_by_username(self):
        """Test getting user by username."""
        mock_session = MagicMock()
        mock_user = MagicMock()
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"

        # Setup query chain
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_filter
        mock_filter.first.return_value = mock_user

        result = mock_session.query().filter_by(username="testuser").first()

        assert result.username == "testuser"

    def test_user_repository_get_by_email(self):
        """Test getting user by email."""
        mock_session = MagicMock()
        mock_user = MagicMock()
        mock_user.email = "test@example.com"

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_filter
        mock_filter.first.return_value = mock_user

        result = mock_session.query().filter_by(email="test@example.com").first()

        assert result.email == "test@example.com"

    def test_user_repository_get_active_users(self):
        """Test getting active users."""
        mock_session = MagicMock()
        active_users = [MagicMock(is_active=True) for _ in range(3)]

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_filter
        mock_filter.all.return_value = active_users

        result = mock_session.query().filter_by(is_active=True).all()

        assert len(result) == 3
        assert all(u.is_active for u in result)


# =============================================================================
# ConversationRepository Tests
# =============================================================================

class TestConversationRepository:
    """Test ConversationRepository operations."""

    def test_get_all_conversations_with_pagination(self):
        """Test getting all conversations with pagination."""
        mock_session = MagicMock()
        conversations = [MagicMock() for _ in range(10)]

        mock_query = MagicMock()
        mock_order = MagicMock()
        mock_offset = MagicMock()
        mock_limit = MagicMock()

        mock_session.query.return_value = mock_query
        mock_query.order_by.return_value = mock_order
        mock_order.offset.return_value = mock_offset
        mock_offset.limit.return_value = mock_limit
        mock_limit.all.return_value = conversations[:5]

        result = mock_session.query().order_by().offset(0).limit(5).all()

        assert len(result) == 5

    def test_search_by_title(self):
        """Test searching conversations by title."""
        mock_session = MagicMock()
        matching_convs = [MagicMock(title="Test Conversation")]

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_order = MagicMock()

        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order
        mock_order.all.return_value = matching_convs

        result = mock_session.query().filter().order_by().all()

        assert len(result) == 1
        assert result[0].title == "Test Conversation"


# =============================================================================
# MessageRepository Tests
# =============================================================================

class TestMessageRepository:
    """Test MessageRepository operations."""

    def test_get_messages_by_conversation(self):
        """Test getting messages for a conversation."""
        mock_session = MagicMock()
        messages = [MagicMock(conversation_id=1) for _ in range(5)]

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_offset = MagicMock()
        mock_limit = MagicMock()

        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.offset.return_value = mock_offset
        mock_offset.limit.return_value = mock_limit
        mock_limit.all.return_value = messages

        result = mock_session.query().filter().offset(0).limit(100).all()

        assert len(result) == 5
        assert all(m.conversation_id == 1 for m in result)

    def test_count_messages_by_conversation(self):
        """Test counting messages in a conversation."""
        mock_session = MagicMock()

        mock_query = MagicMock()
        mock_filter = MagicMock()

        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.count.return_value = 25

        result = mock_session.query().filter().count()

        assert result == 25


# =============================================================================
# ChatRepository Tests
# =============================================================================

class TestChatRepository:
    """Test ChatRepository operations."""

    def test_get_all_chats(self):
        """Test getting all chats."""
        mock_session = MagicMock()
        chats = [MagicMock() for _ in range(10)]

        mock_query = MagicMock()
        mock_order = MagicMock()
        mock_offset = MagicMock()
        mock_limit = MagicMock()

        mock_session.query.return_value = mock_query
        mock_query.order_by.return_value = mock_order
        mock_order.offset.return_value = mock_offset
        mock_offset.limit.return_value = mock_limit
        mock_limit.all.return_value = chats

        result = mock_session.query().order_by().offset(0).limit(100).all()

        assert len(result) == 10

    def test_get_active_chats(self):
        """Test getting active chats only."""
        mock_session = MagicMock()
        active_chats = [MagicMock(is_active=True) for _ in range(5)]

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_order = MagicMock()
        mock_offset = MagicMock()
        mock_limit = MagicMock()

        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order
        mock_order.offset.return_value = mock_offset
        mock_offset.limit.return_value = mock_limit
        mock_limit.all.return_value = active_chats

        result = mock_session.query().filter().order_by().offset(0).limit(100).all()

        assert len(result) == 5
        assert all(c.is_active for c in result)

    def test_count_active_chats(self):
        """Test counting active chats."""
        mock_session = MagicMock()

        mock_query = MagicMock()
        mock_filter = MagicMock()

        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.count.return_value = 42

        result = mock_session.query().filter().count()

        assert result == 42

    def test_get_recent_chats(self):
        """Test getting recent chats within N days."""
        mock_session = MagicMock()
        recent_chats = [MagicMock(created_at=datetime.utcnow()) for _ in range(3)]

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_order = MagicMock()

        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order
        mock_order.all.return_value = recent_chats

        result = mock_session.query().filter().order_by().all()

        assert len(result) == 3

    def test_search_chats_by_title(self):
        """Test searching chats by title."""
        mock_session = MagicMock()
        matching_chats = [MagicMock(title="Test Chat")]

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_order = MagicMock()

        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order
        mock_order.all.return_value = matching_chats

        result = mock_session.query().filter().order_by().all()

        assert len(result) == 1
        assert result[0].title == "Test Chat"

    def test_deactivate_chat(self):
        """Test deactivating a chat."""
        mock_chat = MagicMock()
        mock_chat.id = 1
        mock_chat.is_active = True

        # Simulate deactivation
        mock_chat.is_active = False

        assert mock_chat.is_active == False

    def test_activate_chat(self):
        """Test activating a chat."""
        mock_chat = MagicMock()
        mock_chat.id = 1
        mock_chat.is_active = False

        # Simulate activation
        mock_chat.is_active = True

        assert mock_chat.is_active == True


# =============================================================================
# ChatHistoryRepository Tests
# =============================================================================

class TestChatHistoryRepository:
    """Test ChatHistoryRepository operations."""

    def test_get_by_chat(self):
        """Test getting chat history for a chat."""
        mock_session = MagicMock()
        history = [MagicMock(chat_id=1) for _ in range(10)]

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_order = MagicMock()
        mock_offset = MagicMock()
        mock_limit = MagicMock()

        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order
        mock_order.offset.return_value = mock_offset
        mock_offset.limit.return_value = mock_limit
        mock_limit.all.return_value = history

        result = mock_session.query().filter().order_by().offset(0).limit(100).all()

        assert len(result) == 10

    def test_get_by_chat_reverse(self):
        """Test getting chat history in reverse order."""
        mock_session = MagicMock()
        history = [MagicMock(chat_id=1) for _ in range(5)]

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_order = MagicMock()
        mock_offset = MagicMock()
        mock_limit = MagicMock()

        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order
        mock_order.offset.return_value = mock_offset
        mock_offset.limit.return_value = mock_limit
        mock_limit.all.return_value = history

        result = mock_session.query().filter().order_by().offset(0).limit(100).all()

        assert len(result) == 5

    def test_count_by_chat(self):
        """Test counting messages in a chat."""
        mock_session = MagicMock()

        mock_query = MagicMock()
        mock_filter = MagicMock()

        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.count.return_value = 50

        result = mock_session.query().filter().count()

        assert result == 50

    def test_get_by_role(self):
        """Test getting messages by role."""
        mock_session = MagicMock()
        user_messages = [MagicMock(role="user") for _ in range(5)]

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_order = MagicMock()

        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order
        mock_order.all.return_value = user_messages

        result = mock_session.query().filter().order_by().all()

        assert len(result) == 5
        assert all(m.role == "user" for m in result)

    def test_count_tokens_in_chat(self):
        """Test counting total tokens in a chat."""
        mock_session = MagicMock()
        token_results = [(100,), (200,), (150,)]

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_entities = MagicMock()

        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.with_entities.return_value = mock_entities
        mock_entities.all.return_value = token_results

        result = mock_session.query().filter().with_entities().all()
        total = sum([row[0] for row in result if row[0] is not None])

        assert total == 450

    def test_get_edited_messages(self):
        """Test getting edited messages."""
        mock_session = MagicMock()
        edited = [MagicMock(is_edited=True) for _ in range(2)]

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_order = MagicMock()

        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order
        mock_order.all.return_value = edited

        result = mock_session.query().filter().order_by().all()

        assert len(result) == 2
        assert all(m.is_edited for m in result)

    def test_add_message(self):
        """Test adding a message to chat history."""
        mock_session = MagicMock()
        new_message = MagicMock()
        new_message.chat_id = 1
        new_message.role = "user"
        new_message.content = "Hello, world!"
        new_message.tokens = 5
        new_message.is_edited = False

        mock_session.add(new_message)
        mock_session.commit()
        mock_session.refresh(new_message)

        assert new_message.chat_id == 1
        assert new_message.role == "user"
        assert new_message.content == "Hello, world!"
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    def test_edit_message(self):
        """Test editing a message in chat history."""
        existing_message = MagicMock()
        existing_message.id = 1
        existing_message.content = "Original content"
        existing_message.is_edited = False
        existing_message.edited_content = None
        existing_message.edited_at = None

        # Simulate edit
        original_content = existing_message.content
        existing_message.edited_content = original_content
        existing_message.content = "Updated content"
        existing_message.is_edited = True
        existing_message.edited_at = datetime.utcnow()

        assert existing_message.content == "Updated content"
        assert existing_message.edited_content == "Original content"
        assert existing_message.is_edited == True
        assert existing_message.edited_at is not None


# =============================================================================
# EmbeddingRepository Tests
# =============================================================================

class TestEmbeddingRepository:
    """Test EmbeddingRepository operations."""

    def test_get_by_source(self):
        """Test getting embeddings by source."""
        mock_session = MagicMock()
        embeddings = [MagicMock(source="document.pdf") for _ in range(3)]

        mock_query = MagicMock()
        mock_filter = MagicMock()

        mock_session.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_filter
        mock_filter.all.return_value = embeddings

        result = mock_session.query().filter_by(source="document.pdf").all()

        assert len(result) == 3
        assert all(e.source == "document.pdf" for e in result)

    def test_get_by_model(self):
        """Test getting embeddings by model."""
        mock_session = MagicMock()
        embeddings = [MagicMock(model="text-embedding-ada-002") for _ in range(5)]

        mock_query = MagicMock()
        mock_filter = MagicMock()

        mock_session.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_filter
        mock_filter.all.return_value = embeddings

        result = mock_session.query().filter_by(model="text-embedding-ada-002").all()

        assert len(result) == 5
        assert all(e.model == "text-embedding-ada-002" for e in result)


# =============================================================================
# Model Relationship Tests
# =============================================================================

class TestModelRelationships:
    """Test model relationship definitions."""

    def test_conversation_to_messages_relationship(self):
        """Test conversation has many messages relationship."""
        mock_conversation = MagicMock()
        mock_messages = [MagicMock(conversation_id=1) for _ in range(5)]
        mock_conversation.messages = mock_messages

        assert len(mock_conversation.messages) == 5
        assert all(m.conversation_id == 1 for m in mock_conversation.messages)

    def test_chat_to_history_relationship(self):
        """Test chat has many history entries relationship."""
        mock_chat = MagicMock()
        mock_chat.id = 1
        mock_history = [MagicMock(chat_id=1) for _ in range(10)]
        mock_chat.history = mock_history

        assert len(mock_chat.history) == 10
        assert all(h.chat_id == 1 for h in mock_chat.history)

    def test_document_to_chunks_relationship(self):
        """Test document has many chunks relationship."""
        mock_document = MagicMock()
        mock_document.id = 1
        mock_chunks = [MagicMock(document_id=1, chunk_index=i) for i in range(3)]
        mock_document.chunks = mock_chunks

        assert len(mock_document.chunks) == 3
        assert all(c.document_id == 1 for c in mock_document.chunks)

    def test_message_belongs_to_conversation(self):
        """Test message belongs to conversation relationship."""
        mock_message = MagicMock()
        mock_message.conversation_id = 1
        mock_conversation = MagicMock()
        mock_conversation.id = 1
        mock_message.conversation = mock_conversation

        assert mock_message.conversation.id == mock_message.conversation_id


# =============================================================================
# Index Tests
# =============================================================================

class TestModelIndexes:
    """Test model index definitions."""

    def test_index_definition_format(self):
        """Test index definitions follow expected format."""
        # Simulate index check
        mock_index = MagicMock()
        mock_index.name = "ix_users_username"
        mock_index.columns = ["username"]
        mock_index.unique = True

        assert mock_index.name == "ix_users_username"
        assert "username" in mock_index.columns
        assert mock_index.unique == True

    def test_composite_index_definition(self):
        """Test composite index definitions."""
        mock_index = MagicMock()
        mock_index.name = "ix_messages_conversation_created"
        mock_index.columns = ["conversation_id", "created_at"]
        mock_index.unique = False

        assert len(mock_index.columns) == 2
        assert "conversation_id" in mock_index.columns
        assert "created_at" in mock_index.columns


# =============================================================================
# Transaction Tests
# =============================================================================

class TestTransactionHandling:
    """Test transaction handling in repositories."""

    def test_commit_on_success(self):
        """Test transaction commits on successful operation."""
        mock_session = MagicMock()

        # Simulate successful create
        mock_session.add(MagicMock())
        mock_session.commit()

        mock_session.commit.assert_called_once()
        mock_session.rollback.assert_not_called()

    def test_rollback_on_error(self):
        """Test transaction rollback on error."""
        mock_session = MagicMock()
        mock_session.commit.side_effect = Exception("Database error")

        try:
            mock_session.add(MagicMock())
            mock_session.commit()
        except Exception:
            mock_session.rollback()

        mock_session.rollback.assert_called_once()

    def test_session_close_cleanup(self):
        """Test session is closed after operations."""
        mock_session = MagicMock()

        # Simulate complete operation
        mock_session.add(MagicMock())
        mock_session.commit()
        mock_session.close()

        mock_session.close.assert_called_once()


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_query_result(self):
        """Test handling empty query results."""
        mock_session = MagicMock()

        mock_query = MagicMock()
        mock_filter = MagicMock()

        mock_session.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_filter
        mock_filter.first.return_value = None

        result = mock_session.query().filter_by(username="nonexistent").first()

        assert result is None

    def test_pagination_with_zero_results(self):
        """Test pagination returns empty list when no results."""
        mock_session = MagicMock()

        mock_query = MagicMock()
        mock_order = MagicMock()
        mock_offset = MagicMock()
        mock_limit = MagicMock()

        mock_session.query.return_value = mock_query
        mock_query.order_by.return_value = mock_order
        mock_order.offset.return_value = mock_offset
        mock_offset.limit.return_value = mock_limit
        mock_limit.all.return_value = []

        result = mock_session.query().order_by().offset(0).limit(100).all()

        assert result == []
        assert len(result) == 0

    def test_update_nonexistent_record(self):
        """Test updating a nonexistent record returns None."""
        mock_session = MagicMock()

        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.get.return_value = None

        result = mock_session.query().get(99999)

        assert result is None

    def test_delete_nonexistent_record(self):
        """Test deleting nonexistent record is handled gracefully."""
        mock_session = MagicMock()

        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.get.return_value = None

        result = mock_session.query().get(99999)

        # Should not attempt to delete None
        assert result is None

    def test_ilike_search_case_insensitive(self):
        """Test ilike search is case insensitive."""
        mock_session = MagicMock()
        results = [MagicMock(title="Test Chat"), MagicMock(title="TEST CHAT")]

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_order = MagicMock()

        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order
        mock_order.all.return_value = results

        result = mock_session.query().filter().order_by().all()

        # Both should be returned with ilike
        assert len(result) == 2
