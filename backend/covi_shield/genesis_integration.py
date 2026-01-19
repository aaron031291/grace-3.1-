"""
COVI-SHIELD Genesis Integration

Integrates COVI-SHIELD with the GRACE Genesis Key system.
Triggered on EVERY Genesis Key creation for comprehensive protection.

Integration Points:
- Genesis Key creation hook
- Autonomous trigger pipeline
- Knowledge Base integration
- Memory Mesh learning
"""

import logging
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from pathlib import Path
from datetime import datetime

try:
    from sqlalchemy.orm import Session
except ImportError:
    Session = None

from .orchestrator import (
    COVIShieldOrchestrator,
    get_covi_shield,
    VerificationLevel
)
from .models import (
    AnalysisReport,
    VerificationResult,
    RiskLevel
)

logger = logging.getLogger(__name__)


# ============================================================================
# GENESIS KEY TYPES TO ANALYZE
# ============================================================================

# Genesis Key types that should trigger COVI-SHIELD analysis
ANALYZABLE_KEY_TYPES = {
    "code_change",
    "ai_code_generation",
    "coding_agent_action",
    "file_operation",
    "file_ingestion",
    "api_request",
    "external_api_call",
    "database_change",
    "configuration",
    "error",
    "fix"
}

# Types that require full verification
FULL_VERIFICATION_TYPES = {
    "code_change",
    "ai_code_generation",
    "coding_agent_action",
    "fix"
}

# Types that only need quick check
QUICK_CHECK_TYPES = {
    "file_operation",
    "file_ingestion",
    "api_request",
    "configuration"
}


# ============================================================================
# GENESIS INTEGRATION
# ============================================================================

class COVIShieldGenesisIntegration:
    """
    Integrates COVI-SHIELD with Genesis Key system.

    Called on every Genesis Key creation to:
    1. Analyze code changes for bugs/vulnerabilities
    2. Auto-repair detected issues
    3. Issue verification certificates
    4. Feed learning outcomes to Memory Mesh
    """

    def __init__(
        self,
        session: Optional[Session] = None,
        knowledge_base_path: Optional[Path] = None,
        auto_repair: bool = True,
        learning_enabled: bool = True
    ):
        self.session = session
        self.knowledge_base_path = knowledge_base_path or Path("knowledge_base")
        self.auto_repair = auto_repair
        self.learning_enabled = learning_enabled

        # Get COVI-SHIELD instance
        self.shield = get_covi_shield(
            knowledge_base_path=knowledge_base_path,
            auto_repair=auto_repair,
            learning_enabled=learning_enabled
        )

        # Statistics
        self.stats = {
            "genesis_keys_processed": 0,
            "code_analyzed": 0,
            "issues_detected": 0,
            "issues_fixed": 0,
            "certificates_issued": 0
        }

        logger.info("[COVI-SHIELD Genesis] Integration initialized - Active on all Genesis Keys")

    def on_genesis_key_created(
        self,
        genesis_key: Any  # GenesisKey model
    ) -> Dict[str, Any]:
        """
        Main hook - called when ANY Genesis Key is created.

        This is the primary integration point with GRACE.

        Args:
            genesis_key: The newly created Genesis Key

        Returns:
            Dict with analysis results and actions taken
        """
        self.stats["genesis_keys_processed"] += 1

        key_type = genesis_key.key_type.value if hasattr(genesis_key.key_type, 'value') else str(genesis_key.key_type)

        logger.info(
            f"[COVI-SHIELD Genesis] Processing Genesis Key: {genesis_key.key_id} "
            f"(type={key_type})"
        )

        result = {
            "genesis_key_id": genesis_key.key_id,
            "key_type": key_type,
            "analyzed": False,
            "actions": []
        }

        # Check if this key type should be analyzed
        if key_type.lower() not in ANALYZABLE_KEY_TYPES:
            logger.debug(f"[COVI-SHIELD Genesis] Skipping non-analyzable key type: {key_type}")
            return result

        # Extract code from Genesis Key
        code = self._extract_code(genesis_key)

        if not code:
            logger.debug(f"[COVI-SHIELD Genesis] No code to analyze for key: {genesis_key.key_id}")
            return result

        # Determine verification level
        verification_level = self._determine_verification_level(key_type, genesis_key)

        # Run COVI-SHIELD analysis
        report = self.shield.analyze(
            code=code,
            language="python",  # Could be extended based on file extension
            file_path=genesis_key.file_path,
            verification_level=verification_level,
            genesis_key_id=genesis_key.key_id,
            auto_repair=self.auto_repair
        )

        self.stats["code_analyzed"] += 1
        self.stats["issues_detected"] += report.total_issues
        self.stats["issues_fixed"] += report.total_fixed

        if report.certificate:
            self.stats["certificates_issued"] += 1

        result["analyzed"] = True
        result["report"] = report.to_dict()
        result["risk_level"] = report.overall_risk.value
        result["issues_found"] = report.total_issues
        result["issues_fixed"] = report.total_fixed

        # Record actions taken
        if report.total_issues > 0:
            result["actions"].append({
                "action": "issues_detected",
                "count": report.total_issues,
                "severity": report.overall_risk.value
            })

        if report.total_fixed > 0:
            result["actions"].append({
                "action": "issues_auto_repaired",
                "count": report.total_fixed
            })

        if report.certificate:
            result["actions"].append({
                "action": "certificate_issued",
                "certificate_id": report.certificate.certificate_id,
                "status": report.certificate.status.value
            })

        # Handle high-risk issues
        if report.overall_risk == RiskLevel.CRITICAL:
            result["actions"].append({
                "action": "critical_alert",
                "message": "Critical security or stability issues detected",
                "requires_attention": True
            })
            self._handle_critical_finding(genesis_key, report)

        # Integrate with existing GRACE systems
        self._integrate_with_grace(genesis_key, report)

        logger.info(
            f"[COVI-SHIELD Genesis] Analysis complete for {genesis_key.key_id}: "
            f"issues={report.total_issues}, fixed={report.total_fixed}, "
            f"risk={report.overall_risk.value}"
        )

        return result

    def _extract_code(self, genesis_key: Any) -> Optional[str]:
        """Extract analyzable code from Genesis Key."""
        # Try various sources
        code = None

        # Check code_after (for changes)
        if hasattr(genesis_key, 'code_after') and genesis_key.code_after:
            code = genesis_key.code_after

        # Check code_before (for verification)
        elif hasattr(genesis_key, 'code_before') and genesis_key.code_before:
            code = genesis_key.code_before

        # Check input_data
        elif hasattr(genesis_key, 'input_data') and genesis_key.input_data:
            input_data = genesis_key.input_data
            if isinstance(input_data, dict):
                code = input_data.get('code') or input_data.get('content')

        # Check output_data
        elif hasattr(genesis_key, 'output_data') and genesis_key.output_data:
            output_data = genesis_key.output_data
            if isinstance(output_data, dict):
                code = output_data.get('code') or output_data.get('generated_code')

        # Check context_data
        elif hasattr(genesis_key, 'context_data') and genesis_key.context_data:
            context_data = genesis_key.context_data
            if isinstance(context_data, dict):
                code = context_data.get('code')

        # If file_path is provided, try to read the file
        if not code and hasattr(genesis_key, 'file_path') and genesis_key.file_path:
            code = self._read_file(genesis_key.file_path)

        return code

    def _read_file(self, file_path: str) -> Optional[str]:
        """Read code from file if it exists."""
        try:
            path = Path(file_path)
            if path.exists() and path.suffix in ('.py', '.js', '.ts', '.java', '.c', '.cpp', '.go'):
                return path.read_text()
        except Exception as e:
            logger.warning(f"[COVI-SHIELD Genesis] Failed to read file {file_path}: {e}")
        return None

    def _determine_verification_level(
        self,
        key_type: str,
        genesis_key: Any
    ) -> VerificationLevel:
        """Determine appropriate verification level."""
        key_type_lower = key_type.lower()

        # Full verification for code changes
        if key_type_lower in FULL_VERIFICATION_TYPES:
            return VerificationLevel.REPAIR

        # Quick check for less critical types
        if key_type_lower in QUICK_CHECK_TYPES:
            return VerificationLevel.QUICK

        # Check metadata for hints
        if hasattr(genesis_key, 'metadata') and genesis_key.metadata:
            metadata = genesis_key.metadata if isinstance(genesis_key.metadata, dict) else {}

            # High stakes -> full verification
            if metadata.get('high_stakes') or metadata.get('production'):
                return VerificationLevel.FULL

            # Low confidence -> standard verification
            if metadata.get('confidence_score', 1.0) < 0.7:
                return VerificationLevel.STANDARD

        return VerificationLevel.STANDARD

    def _handle_critical_finding(
        self,
        genesis_key: Any,
        report: AnalysisReport
    ) -> None:
        """Handle critical security or stability findings."""
        logger.warning(
            f"[COVI-SHIELD Genesis] CRITICAL FINDING for {genesis_key.key_id}"
        )

        # Could trigger alerts, notifications, etc.
        # Integration with diagnostic machine alerts
        try:
            from diagnostic_machine.notifications import NotificationManager

            notifier = NotificationManager()
            notifier.send_alert(
                title="COVI-SHIELD Critical Alert",
                message=f"Critical issues detected in Genesis Key {genesis_key.key_id}",
                priority="critical",
                data=report.to_dict()
            )
        except Exception as e:
            logger.warning(f"[COVI-SHIELD Genesis] Failed to send alert: {e}")

    def _integrate_with_grace(
        self,
        genesis_key: Any,
        report: AnalysisReport
    ) -> None:
        """Integrate findings with other GRACE systems."""
        # Integrate with diagnostic machine
        try:
            from diagnostic_machine.cognitive_integration import DiagnosticCognitiveIntegration

            cognitive = DiagnosticCognitiveIntegration(session=self.session)

            # Log as diagnostic insight
            cognitive.log_insight(
                insight_type="covi_shield_analysis",
                data={
                    "genesis_key_id": genesis_key.key_id,
                    "issues_found": report.total_issues,
                    "issues_fixed": report.total_fixed,
                    "risk_level": report.overall_risk.value,
                    "certificate_id": report.certificate.certificate_id if report.certificate else None
                }
            )
        except Exception as e:
            logger.debug(f"[COVI-SHIELD Genesis] Diagnostic integration skipped: {e}")

        # Integrate with Memory Mesh
        if self.learning_enabled:
            try:
                from cognitive.memory_mesh_integration import MemoryMeshIntegration

                memory_mesh = MemoryMeshIntegration(
                    session=self.session,
                    knowledge_base_path=self.knowledge_base_path
                )

                memory_mesh.ingest_learning_experience(
                    experience_type="covi_shield_verification",
                    context={
                        "genesis_key_id": genesis_key.key_id,
                        "key_type": genesis_key.key_type.value if hasattr(genesis_key.key_type, 'value') else str(genesis_key.key_type),
                        "file_path": genesis_key.file_path
                    },
                    action_taken={
                        "verification_level": "full",
                        "auto_repair": self.auto_repair
                    },
                    outcome={
                        "issues_found": report.total_issues,
                        "issues_fixed": report.total_fixed,
                        "risk_level": report.overall_risk.value,
                        "success": report.overall_risk != RiskLevel.CRITICAL
                    },
                    source="covi_shield",
                    genesis_key_id=genesis_key.key_id
                )
            except Exception as e:
                logger.debug(f"[COVI-SHIELD Genesis] Memory Mesh integration skipped: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get integration status."""
        shield_status = self.shield.get_status()

        return {
            "integration_active": True,
            "stats": self.stats,
            "shield_status": shield_status.to_dict(),
            "auto_repair_enabled": self.auto_repair,
            "learning_enabled": self.learning_enabled
        }


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

_genesis_integration: Optional[COVIShieldGenesisIntegration] = None


def get_covi_shield_genesis_integration(
    session: Optional[Session] = None,
    knowledge_base_path: Optional[Path] = None,
    auto_repair: bool = True,
    learning_enabled: bool = True
) -> COVIShieldGenesisIntegration:
    """Get or create global COVI-SHIELD Genesis integration instance."""
    global _genesis_integration

    if _genesis_integration is None:
        _genesis_integration = COVIShieldGenesisIntegration(
            session=session,
            knowledge_base_path=knowledge_base_path,
            auto_repair=auto_repair,
            learning_enabled=learning_enabled
        )

    return _genesis_integration
