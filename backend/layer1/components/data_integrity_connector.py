import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
from layer1.message_bus import Layer1MessageBus, Message, ComponentType, MessageType, get_message_bus
from layer1.autonomous_actions import AutonomousAction
class DataIntegrityConnector:
    logger = logging.getLogger(__name__)
    """
    Connector for Data Integrity Verification.
    
    Integrates integrity verifier with Layer 1 message bus for:
    - Autonomous integrity checks
    - Post-ingestion verification
    - Trust score calculation
    - Integrity report generation
    - Neuro-symbolic trust integration
    """

    def __init__(
        self,
        ai_research_path: str,
        database_path: str,
        message_bus: Optional[Layer1MessageBus] = None,
        enable_trust_scoring: bool = False,
    ):
        """
        Initialize data integrity connector.

        Args:
            ai_research_path: Path to ai_research directory
            database_path: Path to database
            message_bus: Layer 1 message bus instance
            enable_trust_scoring: Whether to calculate trust scores
        """
        self.ai_research_path = Path(ai_research_path)
        self.database_path = Path(database_path)
        self.message_bus = message_bus or get_message_bus()
        self.enable_trust_scoring = enable_trust_scoring
        self.verifier = None
        self.enabled = True
        self._last_report = None  # Cache last integrity report

        # Register with message bus
        self.message_bus.register_component(
            ComponentType.KNOWLEDGE_BASE,
            self
        )
        logger.info("[DATA-INTEGRITY-CONNECTOR] Registered with message bus")
        
        self._register_request_handlers()
        self._register_autonomous_actions()
        self._subscribe_to_events()

    def _initialize_verifier(self):
        """Lazy initialization of integrity verifier."""
        if self.verifier is not None:
            return

        try:
            from scripts.verify_data_integrity import DataIntegrityVerifier
            
            self.verifier = DataIntegrityVerifier(
                str(self.ai_research_path),
                str(self.database_path),
            )
            
            logger.info("[DATA-INTEGRITY-CONNECTOR] Verifier initialized")
            
        except Exception as e:
            logger.error(f"[DATA-INTEGRITY-CONNECTOR] Failed to initialize: {e}")
            raise

    def _register_request_handlers(self):
        """Register request handlers with message bus."""
        self.message_bus.register_handler(
            MessageType.REQUEST,
            "knowledge_base.verify_integrity",
            self._handle_verify_integrity,
        )
        self.message_bus.register_handler(
            MessageType.REQUEST,
            "knowledge_base.get_integrity_report",
            self._handle_get_report,
        )

    def _register_autonomous_actions(self):
        """Register autonomous actions."""
        # Periodic integrity checks
        self.message_bus.register_autonomous_action(
            AutonomousAction(
                trigger_topic="system.periodic_check",
                action_type="knowledge_base.periodic_verify",
                handler=self._on_periodic_check,
                priority=2,
            )
        )

        # Trust score updates after verification
        if self.enable_trust_scoring:
            self.message_bus.register_autonomous_action(
                AutonomousAction(
                    trigger_topic="knowledge_base.integrity_verified",
                    action_type="knowledge_base.update_trust_scores",
                    handler=self._on_update_trust_scores,
                    priority=4,
                )
            )

    def _subscribe_to_events(self):
        """Subscribe to relevant events."""
        self.message_bus.subscribe(
            "knowledge_base.*",
            self._on_knowledge_base_event,
        )

    async def _handle_verify_integrity(self, message: Message) -> Dict[str, Any]:
        """Handle verify integrity request."""
        if not self.enabled:
            return {"success": False, "error": "Connector disabled"}

        category = message.payload.get("category")  # Optional filter
        detailed = message.payload.get("detailed", False)

        try:
            self._initialize_verifier()

            # Publish start event
            await self.message_bus.publish(
                topic="knowledge_base.verification_started",
                payload={
                    "category": category,
                    "detailed": detailed,
                    "timestamp": datetime.utcnow().isoformat(),
                },
                from_component=ComponentType.KNOWLEDGE_BASE,
            )

            # Run verification
            if category:
                # Verify specific category
                report = self.verifier.verify_category(category, detailed=detailed)
            else:
                # Verify all
                report = self.verifier.verify_all(detailed=detailed)

            # Publish completion event
            await self.message_bus.publish(
                topic="knowledge_base.integrity_verified",
                payload={
                    "report": report.summary if hasattr(report, 'summary') else report,
                    "all_checks_passed": self._check_all_passed(report),
                    "timestamp": datetime.utcnow().isoformat(),
                },
                from_component=ComponentType.KNOWLEDGE_BASE,
            )

            # Cache the report
            self._last_report = {
                "report": report.summary if hasattr(report, 'summary') else report,
                "all_checks_passed": self._check_all_passed(report),
                "timestamp": datetime.utcnow().isoformat(),
            }

            return {
                "success": True,
                "report": self._last_report["report"],
                "all_checks_passed": self._last_report["all_checks_passed"],
            }

        except Exception as e:
            logger.error(f"[DATA-INTEGRITY-CONNECTOR] Verification failed: {e}")
            return {"success": False, "error": str(e)}

    async def _handle_get_report(self, message: Message) -> Dict[str, Any]:
        """Handle get integrity report request."""
        if self._last_report is None:
            return {
                "success": True,
                "message": "No report available. Run verify_integrity first.",
                "report": None,
            }

        return {
            "success": True,
            "report": self._last_report["report"],
            "all_checks_passed": self._last_report["all_checks_passed"],
            "timestamp": self._last_report["timestamp"],
        }

    async def _on_periodic_check(self, message: Message):
        """Autonomous action: Periodic integrity check."""
        if not self.enabled:
            return

        logger.info("[DATA-INTEGRITY-CONNECTOR] 🤖 Running periodic integrity check")

        try:
            await self._handle_verify_integrity(
                Message(
                    type=MessageType.REQUEST,
                    topic="knowledge_base.verify_integrity",
                    payload={"detailed": False},
                )
            )
        except Exception as e:
            logger.error(f"[DATA-INTEGRITY-CONNECTOR] Periodic check failed: {e}")

    async def _on_update_trust_scores(self, message: Message):
        """Autonomous action: Update trust scores after verification."""
        if not self.enable_trust_scoring:
            return

        logger.info("[DATA-INTEGRITY-CONNECTOR] 🤖 Updating trust scores based on integrity")

        try:
            # Get verification report
            report = message.payload.get("report", {})
            
            # Calculate trust scores based on integrity
            # High integrity = high trust
            if report.get("all_checks_passed", False):
                trust_score = 0.9  # High trust for verified data
            else:
                trust_score = 0.5  # Medium trust if issues found

            # Publish trust score update
            await self.message_bus.publish(
                topic="knowledge_base.trust_scores_updated",
                payload={
                    "trust_score": trust_score,
                    "source": "integrity_verification",
                    "timestamp": datetime.utcnow().isoformat(),
                },
                from_component=ComponentType.KNOWLEDGE_BASE,
            )

        except Exception as e:
            logger.error(f"[DATA-INTEGRITY-CONNECTOR] Trust score update failed: {e}")

    async def _on_knowledge_base_event(self, message: Message):
        """Handle knowledge base events."""
        logger.debug(f"[DATA-INTEGRITY-CONNECTOR] Event: {message.topic}")

    def _check_all_passed(self, report: Any) -> bool:
        """Check if all integrity checks passed."""
        if hasattr(report, 'verification_checks'):
            checks = report.verification_checks
            if isinstance(checks, dict):
                return all(checks.values())
        if isinstance(report, dict):
            checks = report.get('verification_checks', {})
            if isinstance(checks, dict):
                return all(checks.values())
        return False


def create_data_integrity_connector(
    ai_research_path: str,
    database_path: str,
    message_bus: Optional[Layer1MessageBus] = None,
    enable_trust_scoring: bool = False,
) -> DataIntegrityConnector:
    """
    Factory function to create data integrity connector.

    Args:
        ai_research_path: Path to ai_research directory
        database_path: Path to database
        message_bus: Layer 1 message bus instance
        enable_trust_scoring: Whether to calculate trust scores

    Returns:
        DataIntegrityConnector instance
    """
    return DataIntegrityConnector(
        ai_research_path=ai_research_path,
        database_path=database_path,
        message_bus=message_bus,
        enable_trust_scoring=enable_trust_scoring,
    )
