"""
RuleBasedCategorizer - Pattern Matching for Automatic Categorization

Executes pattern-matching rules to automatically categorize and tag documents
based on file extensions, names, paths, MIME types, and content.
"""

from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging
import re

from models.librarian_models import LibrarianRule
from models.database_models import Document
from librarian.utils import (
    match_pattern,
    extract_file_extension,
    normalize_tag_name
)

logger = logging.getLogger(__name__)


class RuleBasedCategorizer:
    """
    Pattern-based automatic categorization engine.

    Executes rules in priority order (higher priority first) to automatically
    assign tags, set categories, or trigger other actions based on file patterns.

    Supports multiple pattern types:
    - extension: Match file extension (e.g., r"\\.pdf$")
    - filename: Match filename (e.g., r"^README")
    - path: Match file path (e.g., r"ai research")
    - mime_type: Match MIME type (e.g., r"^application/pdf")
    - content: Match text content (expensive, opt-in)

    Features:
    - Priority-based execution
    - Rule caching for performance
    - Statistics tracking (match counts)
    - Multiple actions per rule
    - Case-sensitive/insensitive matching

    Example:
        >>> categorizer = RuleBasedCategorizer(db_session)
        >>> matches = categorizer.categorize_document(document_id=123)
        >>> print(f"Matched {len(matches)} rules")
    """

    def __init__(self, db_session: Session, cache_ttl: int = 60):
        """
        Initialize RuleBasedCategorizer.

        Args:
            db_session: SQLAlchemy database session
            cache_ttl: Cache time-to-live in seconds (default: 60)
        """
        self.db = db_session
        self.cache_ttl = cache_ttl
        self._rules_cache: Optional[List[LibrarianRule]] = None
        self._cache_time: Optional[datetime] = None

    def _get_rules(self, force_refresh: bool = False) -> List[LibrarianRule]:
        """
        Get enabled rules with caching.

        Args:
            force_refresh: Force cache refresh

        Returns:
            List[LibrarianRule]: List of enabled rules sorted by priority
        """
        now = datetime.utcnow()

        # Check if cache is valid
        if (not force_refresh and
            self._rules_cache is not None and
            self._cache_time is not None and
            (now - self._cache_time).total_seconds() < self.cache_ttl):
            return self._rules_cache

        # Fetch rules from database
        rules = self.db.query(LibrarianRule).filter(
            LibrarianRule.enabled == True
        ).order_by(
            LibrarianRule.priority.desc(),
            LibrarianRule.created_at.asc()
        ).all()

        # Update cache
        self._rules_cache = rules
        self._cache_time = now

        logger.debug(f"Loaded {len(rules)} rules from database")
        return rules

    def categorize_document(
        self,
        document_id: int,
        check_content: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Categorize a document by matching it against all enabled rules.

        Args:
            document_id: Document ID to categorize
            check_content: Whether to match against content (expensive)

        Returns:
            List[Dict]: List of matched rules with their actions

        Example:
            >>> matches = categorizer.categorize_document(123)
            >>> for match in matches:
            ...     print(f"Rule: {match['rule_name']}")
            ...     print(f"Action: {match['action_type']}")
            ...     print(f"Params: {match['action_params']}")
        """
        # Get document
        document = self.db.query(Document).filter(
            Document.id == document_id
        ).first()

        if not document:
            logger.warning(f"Document {document_id} not found")
            return []

        # Get rules
        rules = self._get_rules()

        matched_rules = []

        for rule in rules:
            try:
                # Check if rule matches document
                if self._rule_matches_document(rule, document, check_content):
                    matched_rules.append({
                        "rule_id": rule.id,
                        "rule_name": rule.name,
                        "action_type": rule.action_type,
                        "action_params": rule.action_params,
                        "priority": rule.priority
                    })

                    # Update rule statistics
                    rule.matches_count += 1
                    rule.last_matched_at = datetime.utcnow()
                    rule.updated_at = datetime.utcnow()

                    logger.info(f"Document {document_id} matched rule: {rule.name}")

            except Exception as e:
                logger.error(f"Error evaluating rule {rule.id} ({rule.name}): {e}")
                continue

        # Commit statistics updates
        if matched_rules:
            self.db.commit()

        logger.info(f"Document {document_id} matched {len(matched_rules)} rules")
        return matched_rules

    def _rule_matches_document(
        self,
        rule: LibrarianRule,
        document: Document,
        check_content: bool = False
    ) -> bool:
        """
        Check if a rule matches a document.

        Args:
            rule: Rule to evaluate
            document: Document to check
            check_content: Whether to check content

        Returns:
            bool: True if rule matches, False otherwise
        """
        pattern_type = rule.pattern_type
        pattern_value = rule.pattern_value
        case_sensitive = rule.case_sensitive

        # Match based on pattern type
        if pattern_type == "extension":
            return self._match_extension(document, pattern_value, case_sensitive)

        elif pattern_type == "filename":
            return self._match_filename(document, pattern_value, case_sensitive)

        elif pattern_type == "path":
            return self._match_path(document, pattern_value, case_sensitive)

        elif pattern_type == "mime_type":
            return self._match_mime_type(document, pattern_value, case_sensitive)

        elif pattern_type == "content":
            if check_content:
                return self._match_content(document, pattern_value, case_sensitive)
            else:
                logger.debug(f"Skipping content match for rule {rule.id} (check_content=False)")
                return False

        else:
            logger.warning(f"Unknown pattern type: {pattern_type}")
            return False

    def _match_extension(
        self,
        document: Document,
        pattern: str,
        case_sensitive: bool
    ) -> bool:
        """Match against file extension."""
        if not document.filename:
            return False

        extension = extract_file_extension(document.filename)
        if not extension:
            return False

        # Match pattern against extension
        return match_pattern(f".{extension}", pattern, case_sensitive)

    def _match_filename(
        self,
        document: Document,
        pattern: str,
        case_sensitive: bool
    ) -> bool:
        """Match against filename."""
        if not document.filename:
            return False

        return match_pattern(document.filename, pattern, case_sensitive)

    def _match_path(
        self,
        document: Document,
        pattern: str,
        case_sensitive: bool
    ) -> bool:
        """Match against file path."""
        if not document.file_path:
            return False

        return match_pattern(document.file_path, pattern, case_sensitive)

    def _match_mime_type(
        self,
        document: Document,
        pattern: str,
        case_sensitive: bool
    ) -> bool:
        """Match against MIME type."""
        if not document.mime_type:
            return False

        return match_pattern(document.mime_type, pattern, case_sensitive)

    def _match_content(
        self,
        document: Document,
        pattern: str,
        case_sensitive: bool
    ) -> bool:
        """
        Match against document content.

        This is expensive as it requires loading chunks from database.
        Only use when necessary.
        """
        if not document.chunks:
            return False

        # Check first few chunks only (performance)
        max_chunks_to_check = 5

        for i, chunk in enumerate(document.chunks[:max_chunks_to_check]):
            if match_pattern(chunk.text_content, pattern, case_sensitive):
                return True

        return False

    def test_rule_against_documents(
        self,
        rule_id: int,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Test a rule against documents to see what would match.

        Useful for previewing rule effects before enabling.

        Args:
            rule_id: Rule ID to test
            limit: Maximum number of documents to test

        Returns:
            Dict: Test results including matched documents

        Example:
            >>> results = categorizer.test_rule_against_documents(rule_id=5)
            >>> print(f"Would match {results['match_count']} documents")
            >>> for doc in results['matched_documents'][:10]:
            ...     print(f"  - {doc['filename']}")
        """
        # Get rule
        rule = self.db.query(LibrarianRule).filter(
            LibrarianRule.id == rule_id
        ).first()

        if not rule:
            raise ValueError(f"Rule {rule_id} not found")

        # Get documents
        documents = self.db.query(Document).limit(limit).all()

        matched_documents = []
        for document in documents:
            try:
                if self._rule_matches_document(rule, document, check_content=False):
                    matched_documents.append({
                        "id": document.id,
                        "filename": document.filename,
                        "file_path": document.file_path
                    })
            except Exception as e:
                logger.error(f"Error testing rule {rule_id} against document {document.id}: {e}")
                continue

        return {
            "rule_id": rule.id,
            "rule_name": rule.name,
            "pattern_type": rule.pattern_type,
            "pattern_value": rule.pattern_value,
            "documents_tested": len(documents),
            "match_count": len(matched_documents),
            "matched_documents": matched_documents
        }

    def create_rule(
        self,
        name: str,
        pattern_type: str,
        pattern_value: str,
        action_type: str,
        action_params: Dict[str, Any],
        priority: int = 0,
        case_sensitive: bool = False,
        description: Optional[str] = None,
        enabled: bool = True
    ) -> LibrarianRule:
        """
        Create a new categorization rule.

        Args:
            name: Rule name
            pattern_type: Type of pattern (extension, filename, path, mime_type, content)
            pattern_value: Regex pattern to match
            action_type: Action to take (assign_tag, set_category, move_to_folder)
            action_params: Parameters for action (e.g., {"tag_names": ["ai"]})
            priority: Priority (higher runs first)
            case_sensitive: Whether pattern is case-sensitive
            description: Optional description
            enabled: Whether rule is enabled

        Returns:
            LibrarianRule: Created rule

        Raises:
            ValueError: If parameters are invalid

        Example:
            >>> rule = categorizer.create_rule(
            ...     name="PDF Documents",
            ...     pattern_type="extension",
            ...     pattern_value=r"\\.pdf$",
            ...     action_type="assign_tag",
            ...     action_params={"tag_names": ["document", "pdf"]},
            ...     priority=10
            ... )
        """
        # Validate pattern type
        valid_pattern_types = ["extension", "filename", "path", "mime_type", "content"]
        if pattern_type not in valid_pattern_types:
            raise ValueError(f"Invalid pattern_type. Must be one of: {valid_pattern_types}")

        # Validate action type
        valid_action_types = ["assign_tag", "set_category", "move_to_folder"]
        if action_type not in valid_action_types:
            raise ValueError(f"Invalid action_type. Must be one of: {valid_action_types}")

        # Validate regex pattern
        try:
            re.compile(pattern_value)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")

        # Create rule
        rule = LibrarianRule(
            name=name,
            description=description,
            enabled=enabled,
            priority=priority,
            pattern_type=pattern_type,
            pattern_value=pattern_value,
            case_sensitive=case_sensitive,
            action_type=action_type,
            action_params=action_params,
            matches_count=0
        )

        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)

        # Invalidate cache
        self._rules_cache = None

        logger.info(f"Created rule: {name} (ID: {rule.id})")
        return rule

    def update_rule(
        self,
        rule_id: int,
        **kwargs
    ) -> LibrarianRule:
        """
        Update an existing rule.

        Args:
            rule_id: Rule ID to update
            **kwargs: Fields to update

        Returns:
            LibrarianRule: Updated rule

        Example:
            >>> rule = categorizer.update_rule(
            ...     rule_id=5,
            ...     priority=20,
            ...     enabled=False
            ... )
        """
        rule = self.db.query(LibrarianRule).filter(
            LibrarianRule.id == rule_id
        ).first()

        if not rule:
            raise ValueError(f"Rule {rule_id} not found")

        # Update fields
        for key, value in kwargs.items():
            if hasattr(rule, key):
                setattr(rule, key, value)

        rule.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(rule)

        # Invalidate cache
        self._rules_cache = None

        logger.info(f"Updated rule: {rule.name} (ID: {rule.id})")
        return rule

    def delete_rule(self, rule_id: int) -> bool:
        """
        Delete a rule.

        Args:
            rule_id: Rule ID to delete

        Returns:
            bool: True if deleted, False if not found

        Example:
            >>> categorizer.delete_rule(5)
        """
        rule = self.db.query(LibrarianRule).filter(
            LibrarianRule.id == rule_id
        ).first()

        if not rule:
            logger.warning(f"Rule {rule_id} not found")
            return False

        self.db.delete(rule)
        self.db.commit()

        # Invalidate cache
        self._rules_cache = None

        logger.info(f"Deleted rule: {rule.name} (ID: {rule_id})")
        return True

    def get_rule_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about rule usage.

        Returns:
            Dict: Statistics including total rules, most matched, by type, etc.

        Example:
            >>> stats = categorizer.get_rule_statistics()
            >>> print(f"Total rules: {stats['total_rules']}")
            >>> print(f"Most matched: {stats['most_matched'][0]['name']}")
        """
        from sqlalchemy import func

        total_rules = self.db.query(func.count(LibrarianRule.id)).scalar()
        enabled_rules = self.db.query(func.count(LibrarianRule.id)).filter(
            LibrarianRule.enabled == True
        ).scalar()

        # Most matched rules
        most_matched = self.db.query(LibrarianRule).order_by(
            LibrarianRule.matches_count.desc()
        ).limit(10).all()

        # Rules by pattern type
        by_pattern_type = self.db.query(
            LibrarianRule.pattern_type,
            func.count(LibrarianRule.id)
        ).group_by(LibrarianRule.pattern_type).all()

        # Rules by action type
        by_action_type = self.db.query(
            LibrarianRule.action_type,
            func.count(LibrarianRule.id)
        ).group_by(LibrarianRule.action_type).all()

        return {
            "total_rules": total_rules,
            "enabled_rules": enabled_rules,
            "disabled_rules": total_rules - enabled_rules,
            "most_matched": [
                {
                    "id": rule.id,
                    "name": rule.name,
                    "matches_count": rule.matches_count,
                    "pattern_type": rule.pattern_type
                }
                for rule in most_matched
            ],
            "by_pattern_type": {
                pattern_type: count for pattern_type, count in by_pattern_type
            },
            "by_action_type": {
                action_type: count for action_type, count in by_action_type
            }
        }

    def list_rules(
        self,
        enabled_only: bool = False,
        pattern_type: Optional[str] = None,
        action_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List rules with optional filtering.

        Args:
            enabled_only: Only return enabled rules
            pattern_type: Filter by pattern type
            action_type: Filter by action type

        Returns:
            List[Dict]: List of rules

        Example:
            >>> # Get all enabled extension rules
            >>> rules = categorizer.list_rules(
            ...     enabled_only=True,
            ...     pattern_type="extension"
            ... )
        """
        query = self.db.query(LibrarianRule)

        if enabled_only:
            query = query.filter(LibrarianRule.enabled == True)

        if pattern_type:
            query = query.filter(LibrarianRule.pattern_type == pattern_type)

        if action_type:
            query = query.filter(LibrarianRule.action_type == action_type)

        query = query.order_by(
            LibrarianRule.priority.desc(),
            LibrarianRule.created_at.asc()
        )

        rules = query.all()

        return [
            {
                "id": rule.id,
                "name": rule.name,
                "description": rule.description,
                "enabled": rule.enabled,
                "priority": rule.priority,
                "pattern_type": rule.pattern_type,
                "pattern_value": rule.pattern_value,
                "case_sensitive": rule.case_sensitive,
                "action_type": rule.action_type,
                "action_params": rule.action_params,
                "matches_count": rule.matches_count,
                "last_matched_at": rule.last_matched_at.isoformat() if rule.last_matched_at else None,
                "created_at": rule.created_at.isoformat() if rule.created_at else None
            }
            for rule in rules
        ]
