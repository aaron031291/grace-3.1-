import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, UTC
from pathlib import Path
from enum import Enum
from sqlalchemy.orm import Session
from models.genesis_key_models import GenesisKey, GenesisKeyType
class HelpPriority(Enum):
    logger = logging.getLogger(__name__)
    """Priority levels for help requests."""
    CRITICAL = "critical"  # System failing, immediate help needed
    HIGH = "high"  # Important issue, help needed soon
    MEDIUM = "medium"  # Issue that needs attention
    LOW = "low"  # Question or clarification needed


class HelpRequestType(Enum):
    """Types of help requests Grace can make."""
    DEBUGGING = "debugging"  # Need help debugging an issue
    STABILIZATION = "stabilization"  # Need help stabilizing the system
    CODE_REVIEW = "code_review"  # Need code reviewed or fixed
    ARCHITECTURE = "architecture"  # Need architectural guidance
    PERFORMANCE = "performance"  # Need performance optimization help
    ERROR_RESOLUTION = "error_resolution"  # Need help resolving errors
    LEARNING = "learning"  # Need help understanding something
    GENERAL = "general"  # General help request


class AutonomousHelpRequester:
    """
    Allows Grace to autonomously request help from the AI assistant.
    
    Grace uses this when:
    - She encounters errors she cannot fix
    - She needs code reviewed or fixed
    - She needs help stabilizing the system
    - She needs debugging assistance
    - She encounters issues beyond her autonomous capabilities
    """

    def __init__(self, session: Session, help_log_path: Optional[Path] = None):
        self.session = session
        self.help_log_path = help_log_path or Path("logs/grace_help_requests.jsonl")
        
        # Ensure log directory exists
        self.help_log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Statistics
        self.total_requests = 0
        self.requests_by_type = {}
        self.requests_by_priority = {}
        
        logger.info("[AUTONOMOUS-HELP] Help requester initialized")

    def request_help(
        self,
        request_type: HelpRequestType,
        priority: HelpPriority,
        issue_description: str,
        context: Optional[Dict[str, Any]] = None,
        error_details: Optional[Dict[str, Any]] = None,
        affected_files: Optional[List[str]] = None,
        attempted_solutions: Optional[List[str]] = None,
        genesis_key_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a help request that Grace can use to communicate with the AI assistant.
        
        Args:
            request_type: Type of help needed
            priority: Priority level
            issue_description: Description of the issue
            context: Additional context about the issue
            error_details: Error information if applicable
            affected_files: List of files affected by the issue
            attempted_solutions: Solutions Grace has already tried
            genesis_key_id: Related Genesis Key ID for tracking
            
        Returns:
            Dict with help request information
        """
        self.total_requests += 1
        
        # Update statistics
        self.requests_by_type[request_type.value] = self.requests_by_type.get(request_type.value, 0) + 1
        self.requests_by_priority[priority.value] = self.requests_by_priority.get(priority.value, 0) + 1
        
        # Create help request
        help_request = {
            "request_id": f"HR-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{self.total_requests:04d}",
            "timestamp": datetime.now(UTC).isoformat(),
            "request_type": request_type.value,
            "priority": priority.value,
            "issue_description": issue_description,
            "context": context or {},
            "error_details": error_details or {},
            "affected_files": affected_files or [],
            "attempted_solutions": attempted_solutions or [],
            "genesis_key_id": genesis_key_id,
            "status": "pending",
            "source": "grace_autonomous"
        }
        
        # Log the help request
        self._log_help_request(help_request)
        
        # Create Genesis Key for tracking
        genesis_key = self._create_help_request_genesis_key(help_request)
        
        # Format help request for AI assistant
        formatted_request = self._format_help_request(help_request)
        
        logger.info(
            f"[AUTONOMOUS-HELP] Help request created: {help_request['request_id']} "
            f"(type={request_type.value}, priority={priority.value})"
        )
        
        # Print formatted request to console (this is how Grace communicates with me)
        print("\n" + "="*80)
        print("[HELP REQUEST] GRACE HELP REQUEST")
        print("="*80)
        print(formatted_request)
        print("="*80 + "\n")
        
        return {
            "help_request": help_request,
            "genesis_key_id": genesis_key.key_id if genesis_key else None,
            "formatted_request": formatted_request
        }

    def _format_help_request(self, help_request: Dict[str, Any]) -> str:
        """Format help request for display to AI assistant."""
        lines = [
            f"Request ID: {help_request['request_id']}",
            f"Type: {help_request['request_type'].upper()}",
            f"Priority: {help_request['priority'].upper()}",
            f"Timestamp: {help_request['timestamp']}",
            "",
            "ISSUE DESCRIPTION:",
            help_request['issue_description'],
            ""
        ]
        
        if help_request.get('error_details'):
            lines.extend([
                "ERROR DETAILS:",
                json.dumps(help_request['error_details'], indent=2),
                ""
            ])
        
        if help_request.get('affected_files'):
            lines.extend([
                "AFFECTED FILES:",
                "\n".join(f"  - {f}" for f in help_request['affected_files']),
                ""
            ])
        
        if help_request.get('attempted_solutions'):
            lines.extend([
                "ATTEMPTED SOLUTIONS:",
                "\n".join(f"  - {s}" for s in help_request['attempted_solutions']),
                ""
            ])
        
        if help_request.get('context'):
            # Convert exceptions and other non-serializable objects to strings
            context_serializable = self._make_json_serializable(help_request['context'])
            lines.extend([
                "ADDITIONAL CONTEXT:",
                json.dumps(context_serializable, indent=2),
                ""
            ])
        
        if help_request.get('genesis_key_id'):
            lines.append(f"Related Genesis Key: {help_request['genesis_key_id']}")
        
        return "\n".join(lines)

    def _log_help_request(self, help_request: Dict[str, Any]):
        """Log help request to file."""
        try:
            with open(self.help_log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(help_request) + '\n')
        except Exception as e:
            logger.error(f"[AUTONOMOUS-HELP] Failed to log help request: {e}")

    def _make_json_serializable(self, obj: Any) -> Any:
        """Convert non-JSON-serializable objects to strings."""
        if isinstance(obj, Exception):
            return {
                "type": type(obj).__name__,
                "message": str(obj),
                "args": [str(arg) for arg in obj.args] if obj.args else []
            }
        elif isinstance(obj, dict):
            return {k: self._make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._make_json_serializable(item) for item in obj]
        elif isinstance(obj, (datetime,)):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return str(obj)
        else:
            try:
                json.dumps(obj)
                return obj
            except (TypeError, ValueError):
                return str(obj)
    
    def _create_help_request_genesis_key(self, help_request: Dict[str, Any]) -> Optional[GenesisKey]:
        """Create a Genesis Key to track the help request."""
        try:
            from genesis.genesis_key_service import get_genesis_service
            genesis_service = get_genesis_service(self.session)
            
            genesis_key = genesis_service.create_key(
                key_type=GenesisKeyType.SYSTEM_EVENT,
                what_description=f"Help request: {help_request['issue_description'][:200]}",
                who_actor="grace_autonomous",
                why_reason=f"Grace requested help for {help_request['request_type'].value} issue",
                how_method="autonomous_help_requester",
                context_data={
                    "help_request_id": help_request['request_id'],
                    "request_type": help_request['request_type'].value if hasattr(help_request['request_type'], 'value') else str(help_request['request_type']),
                    "priority": help_request['priority'].value if hasattr(help_request['priority'], 'value') else str(help_request['priority']),
                    "status": help_request['status'].value if hasattr(help_request['status'], 'value') else str(help_request['status'])
                },
                session=self.session
            )
            
            # Set metadata_ai after creation if needed
            if help_request.get('context'):
                genesis_key.metadata_ai = self._make_json_serializable(help_request.get('context', {}))
            
            self.session.add(genesis_key)
            self.session.commit()
            
            return genesis_key
            
        except Exception as e:
            logger.error(f"[AUTONOMOUS-HELP] Failed to create Genesis Key: {e}")
            return None

    def request_debugging_help(
        self,
        issue: str,
        error: Optional[Exception] = None,
        affected_files: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
        priority: HelpPriority = HelpPriority.HIGH
    ) -> Dict[str, Any]:
        """Convenience method for requesting debugging help."""
        error_details = {}
        if error:
            error_details = {
                "type": type(error).__name__,
                "message": str(error),
                "traceback": None  # Could include traceback if needed
            }
        
        return self.request_help(
            request_type=HelpRequestType.DEBUGGING,
            priority=priority,
            issue_description=issue,
            context=context,
            error_details=error_details,
            affected_files=affected_files
        )

    def request_stabilization_help(
        self,
        issue: str,
        system_status: Optional[Dict[str, Any]] = None,
        affected_components: Optional[List[str]] = None,
        priority: HelpPriority = HelpPriority.CRITICAL
    ) -> Dict[str, Any]:
        """Convenience method for requesting system stabilization help."""
        return self.request_help(
            request_type=HelpRequestType.STABILIZATION,
            priority=priority,
            issue_description=issue,
            context={"system_status": system_status or {}},
            affected_files=affected_components or []
        )
    
    def request_knowledge(
        self,
        topic: str,
        knowledge_type: str = "debugging",
        context: Optional[Dict[str, Any]] = None,
        priority: HelpPriority = HelpPriority.MEDIUM
    ) -> Dict[str, Any]:
        """
        Request specific knowledge from AI assistant.
        
        Grace uses this when she needs to learn about:
        - How to debug specific issues
        - How to fix certain problems
        - Best practices for specific technologies
        - Solutions to common problems
        """
        # Search AI research knowledge base first
        ai_knowledge = self._search_ai_research_knowledge(topic, context)
        
        # Create knowledge request
        knowledge_request = self.request_help(
            request_type=HelpRequestType.LEARNING,
            priority=priority,
            issue_description=(
                f"Grace needs knowledge about: {topic}\n\n"
                f"Knowledge type: {knowledge_type}\n\n"
                f"Please provide:\n"
                f"1. Comprehensive explanation of {topic}\n"
                f"2. Common issues and solutions\n"
                f"3. Best practices\n"
                f"4. Code examples if applicable\n"
                f"5. Debugging techniques\n"
                f"6. Prevention strategies"
            ),
            context={
                "topic": topic,
                "knowledge_type": knowledge_type,
                "ai_research_results": ai_knowledge,
                **(context or {})
            }
        )
        
        return {
            **knowledge_request,
            "ai_research_results": ai_knowledge
        }
    
    def _search_ai_research_knowledge(
        self,
        topic: str,
        context: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Search AI research knowledge base for relevant information."""
        try:
            from llm_orchestrator.repo_access import RepositoryAccessLayer
            
            repo_access = RepositoryAccessLayer(session=self.session)
            
            # Search repositories (will use RAG if available, otherwise file search)
            results = repo_access.search_repositories(
                query=topic,
                limit=5
            )
            
            return results.get("results", [])[:3]  # Top 3 results
            
        except Exception as e:
            logger.error(f"[AUTONOMOUS-HELP] Failed to search AI research: {e}")
            return []

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about help requests."""
        return {
            "total_requests": self.total_requests,
            "requests_by_type": self.requests_by_type,
            "requests_by_priority": self.requests_by_priority
        }


# ======================================================================
# Global Instance
# ======================================================================

_help_requester: Optional[AutonomousHelpRequester] = None


def get_help_requester(session: Optional[Session] = None) -> AutonomousHelpRequester:
    """Get or create global help requester instance."""
    global _help_requester
    
    if _help_requester is None:
        if session is None:
            from database.session import initialize_session_factory
            session_factory = initialize_session_factory()
            session = session_factory()
        
        _help_requester = AutonomousHelpRequester(session=session)
    
    return _help_requester
