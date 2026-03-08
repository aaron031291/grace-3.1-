"""
Example repositories demonstrating database operations.
These are templates - create specific repositories for your models.
"""

from sqlalchemy.orm import Session
from database.repository import BaseRepository
from models.database_models import User, Conversation, Message, Embedding, Chat, ChatHistory
from typing import List, Optional
from datetime import datetime


class UserRepository(BaseRepository[User]):
    """Repository for User model operations."""
    
    def __init__(self, session: Session):
        super().__init__(session, User)
    
    def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        return self.filter_first(username=username)
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.filter_first(email=email)
    
    def get_active_users(self) -> List[User]:
        """Get all active users."""
        return self.filter(is_active=True)


class ConversationRepository(BaseRepository[Conversation]):
    """Repository for Conversation model operations."""
    
    def __init__(self, session: Session):
        super().__init__(session, Conversation)
    
    def get_all_conversations(self, skip: int = 0, limit: int = 100) -> List[Conversation]:
        """Get all conversations with pagination."""
        return (
            self.session.query(Conversation)
            .order_by(Conversation.updated_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def search_by_title(self, search_term: str) -> List[Conversation]:
        """Search conversations by title."""
        return (
            self.session.query(Conversation)
            .filter(Conversation.title.ilike(f"%{search_term}%"))
            .order_by(Conversation.updated_at.desc())
            .all()
        )


class MessageRepository(BaseRepository[Message]):
    """Repository for Message model operations."""
    
    def __init__(self, session: Session):
        super().__init__(session, Message)
    
    def get_by_conversation(self, conversation_id: int, skip: int = 0, limit: int = 100) -> List[Message]:
        """Get messages for a conversation."""
        return (
            self.session.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def count_by_conversation(self, conversation_id: int) -> int:
        """Count messages in a conversation."""
        return self.session.query(Message).filter(Message.conversation_id == conversation_id).count()


class EmbeddingRepository(BaseRepository[Embedding]):
    """Repository for Embedding model operations."""
    
    def __init__(self, session: Session):
        super().__init__(session, Embedding)
    
    def get_by_source(self, source: str) -> List[Embedding]:
        """Get embeddings by source."""
        return self.filter(source=source)
    
    def get_by_model(self, model: str) -> List[Embedding]:
        """Get embeddings by model."""
        return self.filter(model=model)


class ChatRepository(BaseRepository[Chat]):
    """Repository for Chat model operations."""
    
    def __init__(self, session: Session):
        super().__init__(session, Chat)
    
    def get_all_chats(self, skip: int = 0, limit: int = 100) -> List[Chat]:
        """Get all chats with pagination."""
        return (
            self.session.query(Chat)
            .order_by(Chat.updated_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_active_chats(self, skip: int = 0, limit: int = 100) -> List[Chat]:
        """Get all active chats."""
        return (
            self.session.query(Chat)
            .filter(Chat.is_active == True)
            .order_by(Chat.updated_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def count_active(self) -> int:
        """Count total active chats."""
        return self.session.query(Chat).filter(Chat.is_active == True).count()
    
    def get_recent(self, days: int = 7) -> List[Chat]:
        """Get chats created in the last N days."""
        from datetime import timedelta
        start_date = datetime.utcnow() - timedelta(days=days)
        return (
            self.session.query(Chat)
            .filter(Chat.created_at >= start_date)
            .order_by(Chat.created_at.desc())
            .all()
        )
    
    def search_by_title(self, search_term: str) -> List[Chat]:
        """Search chats by title."""
        return (
            self.session.query(Chat)
            .filter(Chat.title.ilike(f"%{search_term}%"))
            .order_by(Chat.updated_at.desc())
            .all()
        )
    
    def deactivate(self, chat_id: int) -> Optional[Chat]:
        """Deactivate a chat."""
        return self.update(chat_id, is_active=False)
    
    def activate(self, chat_id: int) -> Optional[Chat]:
        """Activate a chat."""
        return self.update(chat_id, is_active=True)


class ChatHistoryRepository(BaseRepository[ChatHistory]):
    """Repository for ChatHistory model operations."""
    
    def __init__(self, session: Session):
        super().__init__(session, ChatHistory)
    
    def get_by_chat(self, chat_id: int, skip: int = 0, limit: int = 100) -> List[ChatHistory]:
        """Get chat history for a chat with pagination."""
        return (
            self.session.query(ChatHistory)
            .filter(ChatHistory.chat_id == chat_id)
            .order_by(ChatHistory.created_at.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_by_chat_reverse(self, chat_id: int, skip: int = 0, limit: int = 100) -> List[ChatHistory]:
        """Get chat history in reverse order (newest first)."""
        return (
            self.session.query(ChatHistory)
            .filter(ChatHistory.chat_id == chat_id)
            .order_by(ChatHistory.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def count_by_chat(self, chat_id: int) -> int:
        """Count messages in a chat."""
        return self.session.query(ChatHistory).filter(ChatHistory.chat_id == chat_id).count()
    
    def get_by_role(self, chat_id: int, role: str) -> List[ChatHistory]:
        """Get messages by role in a chat."""
        return (
            self.session.query(ChatHistory)
            .filter(ChatHistory.chat_id == chat_id, ChatHistory.role == role)
            .order_by(ChatHistory.created_at.asc())
            .all()
        )
    
    def count_tokens_in_chat(self, chat_id: int) -> int:
        """Count total tokens used in a chat."""
        result = (
            self.session.query(ChatHistory)
            .filter(ChatHistory.chat_id == chat_id, ChatHistory.tokens != None)
            .with_entities(ChatHistory.tokens)
            .all()
        )
        return sum([row[0] for row in result if row[0] is not None])
    
    def get_edited_messages(self, chat_id: int) -> List[ChatHistory]:
        """Get edited messages in a chat."""
        return (
            self.session.query(ChatHistory)
            .filter(ChatHistory.chat_id == chat_id, ChatHistory.is_edited == True)
            .order_by(ChatHistory.edited_at.desc())
            .all()
        )
    
    def add_message(
        self,
        chat_id: int,
        role: str,
        content: str,
        tokens: Optional[int] = None,
        token_ids: Optional[str] = None,
        completion_time: Optional[float] = None,
    ) -> ChatHistory:
        """Add a message to chat history."""
        message = self.create(
            chat_id=chat_id,
            role=role,
            content=content,
            tokens=tokens,
            token_ids=token_ids,
            completion_time=completion_time,
            is_edited=False,
        )
        # Refresh to ensure all fields are populated from DB
        self.session.refresh(message)
        return message
    
    def edit_message(
        self,
        message_id: int,
        new_content: str,
    ) -> Optional[ChatHistory]:
        """Edit a message in chat history."""
        message = self.get(message_id)
        if message:
            # Save original content
            self.update(
                message_id,
                edited_content=message.content,
                content=new_content,
                is_edited=True,
                edited_at=datetime.utcnow(),
            )
            return self.get(message_id)
        return None
