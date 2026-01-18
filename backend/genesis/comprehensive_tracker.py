import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from models.genesis_key_models import GenesisKey, GenesisKeyType, GenesisKeyStatus, UserProfile
logger = logging.getLogger(__name__)

class ComprehensiveTracker:
    """
    Comprehensive tracker for all system inputs and actions.

    Creates Genesis Keys for:
    - User interactions
    - AI/agent actions
    - External API calls
    - File operations
    - Database changes
    - System events
    """

    def __init__(self, db_session: Session, user_id: Optional[str] = None, session_id: Optional[str] = None):
        """
        Initialize comprehensive tracker.

        Args:
            db_session: Database session
            user_id: User identifier (optional)
            session_id: Session identifier (optional)
        """
        self.db = db_session
        self.user_id = user_id or self._generate_user_id()
        self.session_id = session_id or str(uuid.uuid4())

    def _generate_user_id(self) -> str:
        """Generate a unique user ID."""
        return f"user_{uuid.uuid4().hex[:8]}"

    def _create_genesis_key(
        self,
        key_type: GenesisKeyType,
        what_description: str,
        where_location: Optional[str] = None,
        why_reason: Optional[str] = None,
        who_actor: Optional[str] = None,
        how_method: Optional[str] = None,
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
        context_data: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        parent_key_id: Optional[str] = None,
        **kwargs
    ) -> GenesisKey:
        """
        Create a Genesis Key with comprehensive metadata.

        Args:
            key_type: Type of Genesis Key
            what_description: What happened
            where_location: Where it happened
            why_reason: Why it happened
            who_actor: Who performed the action
            how_method: How it was done
            input_data: Input data (structured)
            output_data: Output data (structured)
            context_data: Additional context
            tags: Searchable tags
            parent_key_id: Parent key for chaining
            **kwargs: Additional fields

        Returns:
            Created GenesisKey instance
        """
        try:
            key = GenesisKey(
                key_id=str(uuid.uuid4()),
                parent_key_id=parent_key_id,
                key_type=key_type,
                status=GenesisKeyStatus.ACTIVE,
                user_id=self.user_id,
                session_id=self.session_id,
                what_description=what_description,
                where_location=where_location,
                when_timestamp=datetime.utcnow(),
                why_reason=why_reason,
                who_actor=who_actor or self.user_id,
                how_method=how_method,
                input_data=input_data,
                output_data=output_data,
                context_data=context_data,
                tags=tags,
                **kwargs
            )

            self.db.add(key)
            self.db.commit()

            logger.info(
                f"[GENESIS] Created {key_type.value} key: {key.key_id} - {what_description[:50]}"
            )

            return key

        except Exception as e:
            logger.error(f"[GENESIS] Failed to create key: {e}")
            self.db.rollback()
            raise

    # ==================== User Interactions ====================

    def track_user_input(
        self,
        message: str,
        message_type: str = "text",
        metadata: Optional[Dict[str, Any]] = None
    ) -> GenesisKey:
        """
        Track user input (messages, commands).

        Args:
            message: User message content
            message_type: Type of message (text, command, etc.)
            metadata: Additional metadata

        Returns:
            GenesisKey for user input
        """
        return self._create_genesis_key(
            key_type=GenesisKeyType.USER_INPUT,
            what_description=f"User input: {message[:100]}",
            why_reason="User interaction with system",
            how_method=f"Message type: {message_type}",
            input_data={
                "message": message,
                "message_type": message_type,
                "length": len(message)
            },
            context_data=metadata,
            tags=["user-input", message_type]
        )

    def track_user_upload(
        self,
        filename: str,
        file_path: str,
        file_size: int,
        file_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> GenesisKey:
        """
        Track user file upload.

        Args:
            filename: Name of uploaded file
            file_path: Path where file was saved
            file_size: Size of file in bytes
            file_type: MIME type or extension
            metadata: Additional metadata

        Returns:
            GenesisKey for file upload
        """
        return self._create_genesis_key(
            key_type=GenesisKeyType.USER_UPLOAD,
            what_description=f"User uploaded file: {filename}",
            where_location=file_path,
            why_reason="User file upload",
            how_method=f"Upload via API - {file_type}",
            input_data={
                "filename": filename,
                "file_path": file_path,
                "file_size": file_size,
                "file_type": file_type
            },
            context_data=metadata,
            tags=["upload", file_type, "user-action"]
        )

    # ==================== AI/Agent Interactions ====================

    def track_ai_response(
        self,
        prompt: str,
        response: str,
        model: str,
        tokens_used: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        parent_key_id: Optional[str] = None
    ) -> GenesisKey:
        """
        Track AI-generated response.

        Args:
            prompt: Input prompt to AI
            response: AI's response
            model: Model used (e.g., "claude-sonnet-4.5")
            tokens_used: Number of tokens consumed
            metadata: Additional metadata
            parent_key_id: Parent key (e.g., user input that triggered this)

        Returns:
            GenesisKey for AI response
        """
        return self._create_genesis_key(
            key_type=GenesisKeyType.AI_RESPONSE,
            what_description=f"AI response using {model}: {response[:100]}",
            why_reason="AI processing user request",
            who_actor=f"AI-{model}",
            how_method=f"Model: {model}, Tokens: {tokens_used}",
            input_data={
                "prompt": prompt,
                "prompt_length": len(prompt),
                "model": model
            },
            output_data={
                "response": response,
                "response_length": len(response),
                "tokens_used": tokens_used
            },
            context_data=metadata,
            tags=["ai-response", model],
            parent_key_id=parent_key_id
        )

    def track_ai_code_generation(
        self,
        file_path: str,
        code_generated: str,
        language: str,
        purpose: str,
        model: str,
        metadata: Optional[Dict[str, Any]] = None,
        parent_key_id: Optional[str] = None
    ) -> GenesisKey:
        """
        Track AI-generated code.

        Args:
            file_path: Path to file where code was generated
            code_generated: Generated code content
            language: Programming language
            purpose: Purpose of generated code
            model: AI model used
            metadata: Additional metadata
            parent_key_id: Parent key

        Returns:
            GenesisKey for code generation
        """
        return self._create_genesis_key(
            key_type=GenesisKeyType.AI_CODE_GENERATION,
            what_description=f"AI generated {language} code: {purpose}",
            where_location=file_path,
            why_reason=purpose,
            who_actor=f"AI-{model}",
            how_method=f"Code generation using {model}",
            file_path=file_path,
            code_after=code_generated,
            output_data={
                "language": language,
                "lines_generated": len(code_generated.split('\n')),
                "chars_generated": len(code_generated)
            },
            context_data=metadata,
            tags=["ai-code", language, "generated"],
            parent_key_id=parent_key_id
        )

    def track_coding_agent_action(
        self,
        action_type: str,
        action_description: str,
        files_affected: List[str],
        result: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> GenesisKey:
        """
        Track autonomous coding agent action.

        Args:
            action_type: Type of action (refactor, test, fix, etc.)
            action_description: Description of what agent did
            files_affected: List of files modified
            result: Result of action
            metadata: Additional metadata

        Returns:
            GenesisKey for agent action
        """
        return self._create_genesis_key(
            key_type=GenesisKeyType.CODING_AGENT_ACTION,
            what_description=f"Coding agent: {action_description}",
            where_location=", ".join(files_affected[:3]),
            why_reason="Autonomous agent action",
            who_actor="coding-agent",
            how_method=action_type,
            input_data={
                "action_type": action_type,
                "files_affected": files_affected
            },
            output_data=result,
            context_data=metadata,
            tags=["agent-action", action_type, "autonomous"]
        )

    # ==================== External Interactions ====================

    def track_external_api_call(
        self,
        api_name: str,
        endpoint: str,
        method: str,
        request_data: Optional[Dict[str, Any]] = None,
        response_data: Optional[Dict[str, Any]] = None,
        status_code: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> GenesisKey:
        """
        Track external API call.

        Args:
            api_name: Name of external API
            endpoint: API endpoint called
            method: HTTP method
            request_data: Request payload
            response_data: Response data
            status_code: HTTP status code
            metadata: Additional metadata

        Returns:
            GenesisKey for API call
        """
        return self._create_genesis_key(
            key_type=GenesisKeyType.EXTERNAL_API_CALL,
            what_description=f"External API call: {api_name} {method} {endpoint}",
            where_location=endpoint,
            why_reason=f"External API integration: {api_name}",
            how_method=f"{method} request to {api_name}",
            input_data={
                "api_name": api_name,
                "endpoint": endpoint,
                "method": method,
                "request": request_data
            },
            output_data={
                "response": response_data,
                "status_code": status_code
            },
            context_data=metadata,
            tags=["external-api", api_name, method]
        )

    def track_web_fetch(
        self,
        url: str,
        content: str,
        content_type: str,
        status_code: int,
        purpose: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> GenesisKey:
        """
        Track HTML/web content fetch.

        Args:
            url: URL fetched
            content: Fetched content
            content_type: Content type (text/html, etc.)
            status_code: HTTP status code
            purpose: Purpose of fetch
            metadata: Additional metadata

        Returns:
            GenesisKey for web fetch
        """
        return self._create_genesis_key(
            key_type=GenesisKeyType.WEB_FETCH,
            what_description=f"Web fetch: {url[:100]}",
            where_location=url,
            why_reason=purpose,
            how_method=f"HTTP GET - {content_type}",
            input_data={
                "url": url,
                "content_type": content_type
            },
            output_data={
                "content_length": len(content),
                "status_code": status_code,
                "content_preview": content[:500]
            },
            context_data=metadata,
            tags=["web-fetch", content_type]
        )

    # ==================== File Operations ====================

    def track_file_ingestion(
        self,
        filename: str,
        file_path: str,
        document_id: int,
        chunks_created: int,
        embeddings_created: int,
        metadata: Optional[Dict[str, Any]] = None,
        parent_key_id: Optional[str] = None
    ) -> GenesisKey:
        """
        Track file ingestion into knowledge base.

        Args:
            filename: Name of file
            file_path: Path to file
            document_id: Document ID created
            chunks_created: Number of chunks created
            embeddings_created: Number of embeddings created
            metadata: Additional metadata
            parent_key_id: Parent key (e.g., upload key)

        Returns:
            GenesisKey for ingestion
        """
        return self._create_genesis_key(
            key_type=GenesisKeyType.FILE_INGESTION,
            what_description=f"Ingested file: {filename} → document {document_id}",
            where_location=file_path,
            why_reason="File ingestion into knowledge base",
            how_method=f"Created {chunks_created} chunks, {embeddings_created} embeddings",
            file_path=file_path,
            output_data={
                "document_id": document_id,
                "chunks_created": chunks_created,
                "embeddings_created": embeddings_created
            },
            context_data=metadata,
            tags=["ingestion", "knowledge-base"],
            parent_key_id=parent_key_id
        )

    # ==================== Data Operations ====================

    def track_librarian_action(
        self,
        document_id: int,
        action_type: str,
        tags_assigned: List[str],
        relationships_detected: int,
        rules_matched: List[str],
        metadata: Optional[Dict[str, Any]] = None,
        parent_key_id: Optional[str] = None
    ) -> GenesisKey:
        """
        Track librarian auto-categorization.

        Args:
            document_id: Document processed
            action_type: Type of librarian action
            tags_assigned: Tags assigned to document
            relationships_detected: Number of relationships found
            rules_matched: Rules that matched
            metadata: Additional metadata
            parent_key_id: Parent key

        Returns:
            GenesisKey for librarian action
        """
        return self._create_genesis_key(
            key_type=GenesisKeyType.LIBRARIAN_ACTION,
            what_description=f"Librarian processed document {document_id}: {len(tags_assigned)} tags, {relationships_detected} relationships",
            why_reason="Automatic document categorization",
            who_actor="librarian-system",
            how_method=f"{action_type} using {len(rules_matched)} rules",
            output_data={
                "document_id": document_id,
                "tags_assigned": tags_assigned,
                "relationships_detected": relationships_detected,
                "rules_matched": rules_matched
            },
            context_data=metadata,
            tags=["librarian", "auto-categorization"],
            parent_key_id=parent_key_id
        )

    def track_database_change(
        self,
        table_name: str,
        operation: str,
        record_id: Optional[int] = None,
        data_before: Optional[Dict[str, Any]] = None,
        data_after: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> GenesisKey:
        """
        Track database change.

        Args:
            table_name: Database table
            operation: Operation (INSERT, UPDATE, DELETE)
            record_id: Record ID affected
            data_before: Data before change
            data_after: Data after change
            metadata: Additional metadata

        Returns:
            GenesisKey for database change
        """
        return self._create_genesis_key(
            key_type=GenesisKeyType.DATABASE_CHANGE,
            what_description=f"Database {operation} on {table_name}" + (f" (ID: {record_id})" if record_id else ""),
            where_location=table_name,
            why_reason="Database modification",
            how_method=f"{operation} operation",
            input_data=data_before,
            output_data=data_after,
            context_data=metadata,
            tags=["database", operation.lower(), table_name]
        )

    # ==================== System Operations ====================

    def track_system_event(
        self,
        event_type: str,
        event_description: str,
        severity: str = "info",
        metadata: Optional[Dict[str, Any]] = None
    ) -> GenesisKey:
        """
        Track system event.

        Args:
            event_type: Type of event
            event_description: Description of event
            severity: Severity level (info, warning, error)
            metadata: Additional metadata

        Returns:
            GenesisKey for system event
        """
        return self._create_genesis_key(
            key_type=GenesisKeyType.SYSTEM_EVENT,
            what_description=f"System event: {event_description}",
            why_reason=f"{severity.upper()} level system event",
            who_actor="system",
            how_method=event_type,
            context_data=metadata,
            tags=["system-event", severity, event_type]
        )

    # ==================== Utility Methods ====================

    def get_session_timeline(self) -> List[GenesisKey]:
        """
        Get complete timeline of actions for current session.

        Returns:
            List of GenesisKeys in chronological order
        """
        return self.db.query(GenesisKey).filter(
            GenesisKey.session_id == self.session_id
        ).order_by(GenesisKey.when_timestamp).all()

    def get_user_history(self, limit: int = 100) -> List[GenesisKey]:
        """
        Get user's action history.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of GenesisKeys for user
        """
        return self.db.query(GenesisKey).filter(
            GenesisKey.user_id == self.user_id
        ).order_by(GenesisKey.when_timestamp.desc()).limit(limit).all()

    def search_by_tags(self, tags: List[str]) -> List[GenesisKey]:
        """
        Search Genesis Keys by tags.

        Args:
            tags: List of tags to search for

        Returns:
            List of matching GenesisKeys
        """
        # This is a simple implementation - could be optimized with proper JSON querying
        all_keys = self.db.query(GenesisKey).filter(
            GenesisKey.tags.isnot(None)
        ).all()

        matching_keys = []
        for key in all_keys:
            if key.tags and any(tag in key.tags for tag in tags):
                matching_keys.append(key)

        return matching_keys
