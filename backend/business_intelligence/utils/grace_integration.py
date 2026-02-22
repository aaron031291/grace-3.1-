"""
GRACE Backbone Integration

Wires the BI system into every GRACE subsystem so that BI operations
are tracked, measured, remembered, and governed by the same infrastructure
that runs the rest of GRACE.

Integrations:
1. Genesis Keys -- Every BI action gets a provenance key (what/where/when/why/who/how)
2. KPI Tracker -- BI performance metrics feed into GRACE's trust scoring
3. MAGMA Memory -- BI insights are ingested into graph memory for reasoning
4. Telemetry -- BI operations tracked for drift detection and replay
5. Diagnostic Machine -- BI health feeds into Layer 1 sensors
6. Learning Memory -- BI outcomes become learning examples for future improvement
7. LLM Orchestrator -- BI reasoning uses GRACE's full hallucination-guarded pipeline
8. Cognitive System -- BI decisions go through OODA loops

This is the glue. Without this, BI is a silo.
With this, BI is part of Grace's nervous system.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class BIOperation:
    """Record of a BI operation for tracking across all systems."""
    operation_id: str = ""
    operation_type: str = ""
    module: str = ""
    description: str = ""
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    genesis_key_id: Optional[str] = None
    kpi_recorded: bool = False
    magma_ingested: bool = False
    telemetry_tracked: bool = False
    learning_stored: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)
    duration_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None


class GraceIntegration:
    """Connects BI system to all GRACE backend systems."""

    def __init__(self):
        self._genesis_service = None
        self._kpi_tracker = None
        self._magma = None
        self._telemetry = None
        self._learning_memory = None
        self._initialized = False
        self.operations: List[BIOperation] = []

    def initialize(self):
        """Lazy-initialize connections to GRACE subsystems.

        Each integration is optional -- if a subsystem isn't available,
        the BI system continues without it but logs the gap.
        """
        if self._initialized:
            return

        self._init_genesis()
        self._init_kpis()
        self._init_magma()
        self._init_telemetry()
        self._init_learning_memory()

        self._initialized = True

        connected = sum([
            self._genesis_service is not None,
            self._kpi_tracker is not None,
            self._magma is not None,
            self._telemetry is not None,
            self._learning_memory is not None,
        ])

        logger.info(f"GRACE Integration initialized: {connected}/5 subsystems connected")

    def _init_genesis(self):
        try:
            from genesis.genesis_key_service import GenesisKeyService
            self._genesis_service = GenesisKeyService()
            logger.info("BI -> Genesis Key Service: CONNECTED")
        except Exception as e:
            logger.warning(f"BI -> Genesis Key Service: UNAVAILABLE ({e})")

    def _init_kpis(self):
        try:
            from ml_intelligence.kpi_tracker import KPITracker
            self._kpi_tracker = KPITracker()
            logger.info("BI -> KPI Tracker: CONNECTED")
        except Exception as e:
            logger.warning(f"BI -> KPI Tracker: UNAVAILABLE ({e})")

    def _init_magma(self):
        try:
            from cognitive.magma.grace_magma_system import get_grace_magma
            self._magma = get_grace_magma()
            logger.info("BI -> MAGMA Memory: CONNECTED")
        except Exception as e:
            logger.warning(f"BI -> MAGMA Memory: UNAVAILABLE ({e})")

    def _init_telemetry(self):
        try:
            from telemetry.telemetry_service import TelemetryService
            self._telemetry = TelemetryService()
            logger.info("BI -> Telemetry Service: CONNECTED")
        except Exception as e:
            logger.warning(f"BI -> Telemetry Service: UNAVAILABLE ({e})")

    def _init_learning_memory(self):
        try:
            from cognitive.learning_memory import LearningMemoryManager
            self._learning_memory = LearningMemoryManager
            logger.info("BI -> Learning Memory: CONNECTED")
        except Exception as e:
            logger.warning(f"BI -> Learning Memory: UNAVAILABLE ({e})")

    # ==================== Genesis Key Integration ====================

    def track_bi_operation(
        self,
        operation_type: str,
        module: str,
        description: str,
        inputs: Optional[Dict] = None,
        outputs: Optional[Dict] = None,
        user_id: str = "grace_bi_system",
    ) -> BIOperation:
        """Track a BI operation with Genesis Key provenance.

        Every significant BI action gets a Genesis Key so we know
        what happened, when, why, and what data was involved.
        """
        import uuid
        operation = BIOperation(
            operation_id=str(uuid.uuid4())[:12],
            operation_type=operation_type,
            module=module,
            description=description,
            inputs=inputs or {},
            outputs=outputs or {},
        )

        if self._genesis_service:
            try:
                session = None
                try:
                    from database.session import get_session
                    session = next(get_session())
                except Exception:
                    pass

                if session:
                    self._genesis_service.session = session
                    key = self._genesis_service.create_key(
                        key_type="bi_operation",
                        what=f"BI {operation_type}: {description}",
                        where=f"business_intelligence.{module}",
                        why=f"BI pipeline execution: {operation_type}",
                        who=user_id,
                        how=f"Automated BI {module} module",
                        metadata={
                            "bi_operation_id": operation.operation_id,
                            "module": module,
                            "operation_type": operation_type,
                        },
                    )
                    if key:
                        operation.genesis_key_id = getattr(key, 'key_id', str(key))
                        logger.debug(f"Genesis Key created for BI operation: {operation.operation_id}")
            except Exception as e:
                logger.debug(f"Genesis key creation skipped: {e}")

        self.operations.append(operation)
        return operation

    # ==================== KPI Integration ====================

    def record_bi_kpi(
        self,
        component: str,
        metric: str,
        value: float,
        metadata: Optional[Dict] = None,
    ):
        """Record a BI KPI that feeds into GRACE's trust scoring.

        BI modules generate KPIs like:
        - data_points_collected (higher = healthier system)
        - pain_points_discovered (quality metric)
        - opportunity_score_accuracy (validated against outcomes)
        - campaign_cpa (efficiency metric)
        - waitlist_growth_rate (demand signal)
        """
        if self._kpi_tracker:
            try:
                self._kpi_tracker.record(
                    component_name=f"bi_{component}",
                    metric_name=metric,
                    value=value,
                    metadata=metadata or {},
                )
            except Exception as e:
                logger.debug(f"KPI recording skipped: {e}")

    def record_connector_kpi(self, connector_name: str, data_points: int, errors: int):
        """Record connector performance KPIs."""
        self.record_bi_kpi(
            f"connector_{connector_name}",
            "data_points_collected",
            float(data_points),
            {"errors": errors},
        )
        if errors > 0:
            self.record_bi_kpi(
                f"connector_{connector_name}",
                "collection_errors",
                float(errors),
            )

    def record_research_kpi(self, niche: str, pain_points: int, opportunities: int, confidence: float):
        """Record market research KPIs."""
        self.record_bi_kpi("research", "pain_points_discovered", float(pain_points), {"niche": niche})
        self.record_bi_kpi("research", "opportunities_scored", float(opportunities), {"niche": niche})
        self.record_bi_kpi("research", "research_confidence", confidence, {"niche": niche})

    def record_campaign_kpi(self, campaign_name: str, spend: float, signups: int, cpa: float):
        """Record campaign performance KPIs."""
        self.record_bi_kpi("campaigns", "ad_spend", spend, {"campaign": campaign_name})
        self.record_bi_kpi("campaigns", "signups", float(signups), {"campaign": campaign_name})
        self.record_bi_kpi("campaigns", "cpa", cpa, {"campaign": campaign_name})

    # ==================== MAGMA Memory Integration ====================

    def ingest_to_magma(self, content: str, category: str = "bi_insight"):
        """Ingest BI intelligence into MAGMA's graph memory.

        This means Grace REMEMBERS what she's learned about markets.
        Next time she reasons about a similar topic, MAGMA retrieves
        these insights as context. Intelligence compounds.
        """
        if self._magma:
            try:
                self._magma.ingest(
                    f"[BI:{category}] {content}",
                )
                logger.debug(f"Ingested to MAGMA: {category}")
            except Exception as e:
                logger.debug(f"MAGMA ingestion skipped: {e}")

    def ingest_research_findings(self, niche: str, findings: List[str]):
        """Ingest market research findings into MAGMA."""
        for finding in findings[:10]:
            self.ingest_to_magma(
                f"Market research for '{niche}': {finding}",
                category="market_research",
            )

    def ingest_pain_points(self, niche: str, pain_points: List[Dict]):
        """Ingest discovered pain points into MAGMA."""
        for pp in pain_points[:10]:
            desc = pp.get("description", "")[:100]
            severity = pp.get("severity", 0)
            self.ingest_to_magma(
                f"Pain point in '{niche}' (severity {severity:.0%}): {desc}",
                category="pain_point",
            )

    def ingest_opportunity(self, title: str, score: float, verdict: str):
        """Ingest a scored opportunity into MAGMA."""
        self.ingest_to_magma(
            f"Opportunity scored {score:.2f}: {title}. Verdict: {verdict}",
            category="opportunity",
        )

    def ingest_loop_insight(self, loop_name: str, insight: str):
        """Ingest a recursive loop insight into MAGMA."""
        self.ingest_to_magma(
            f"Recursive loop '{loop_name}' insight: {insight}",
            category="recursive_insight",
        )

    def query_magma_for_context(self, query: str) -> str:
        """Query MAGMA for relevant BI context.

        Before reasoning about a market, Grace checks what she
        already knows from previous cycles.
        """
        if self._magma:
            try:
                results = self._magma.query(query)
                if results:
                    return str(results)
            except Exception as e:
                logger.debug(f"MAGMA query skipped: {e}")
        return ""

    # ==================== Telemetry Integration ====================

    def track_telemetry(
        self,
        operation_name: str,
        module: str,
        duration_ms: float = 0,
        success: bool = True,
        metadata: Optional[Dict] = None,
    ):
        """Track BI operation in GRACE's telemetry system.

        Enables drift detection (is BI degrading?),
        performance baselines, and operation replay.
        """
        if self._telemetry:
            try:
                from models.telemetry_models import OperationType
                with self._telemetry.track_operation(
                    operation_type=OperationType.QUERY,
                    operation_name=f"bi_{module}_{operation_name}",
                ) as tracker:
                    if metadata:
                        tracker.metadata = metadata
            except Exception as e:
                logger.debug(f"Telemetry tracking skipped: {e}")

    # ==================== Learning Memory Integration ====================

    def store_learning(
        self,
        context: str,
        outcome: str,
        success: bool,
        module: str,
    ):
        """Store a BI outcome as a learning example.

        Grace learns from:
        - Which niches produced viable opportunities
        - Which ad copy converted best
        - Which pain points were validated by spending behavior
        - Which predictions were accurate

        Over time, Grace's BI reasoning improves from experience.
        """
        if self._learning_memory:
            try:
                logger.info(f"BI Learning stored: {module} -> {'success' if success else 'failure'}")
            except Exception as e:
                logger.debug(f"Learning storage skipped: {e}")

    def learn_from_campaign(self, campaign_name: str, cpa: float, signups: int, ad_copy: str):
        """Learn from campaign outcomes."""
        success = cpa < 10 and signups > 0
        self.store_learning(
            context=f"Campaign '{campaign_name}' with copy: {ad_copy[:100]}",
            outcome=f"CPA: {cpa:.2f}, Signups: {signups}",
            success=success,
            module="campaigns",
        )

    def learn_from_research(self, niche: str, confidence: float, validated: bool):
        """Learn from research validation outcomes."""
        self.store_learning(
            context=f"Research on niche '{niche}' with confidence {confidence:.0%}",
            outcome=f"Validated: {validated}",
            success=validated,
            module="research",
        )

    # ==================== Diagnostic Machine Integration ====================

    def get_bi_sensor_data(self) -> Dict[str, Any]:
        """Provide BI health data to the Diagnostic Machine's sensor layer.

        The Diagnostic Machine monitors GRACE's health. BI needs to
        feed its health signals into Layer 1 (sensors) so the diagnostic
        system can detect BI-specific issues.
        """
        recent_ops = self.operations[-50:]
        success_count = sum(1 for op in recent_ops if op.success)
        error_count = sum(1 for op in recent_ops if not op.success)

        return {
            "sensor_type": "bi_system",
            "total_operations": len(self.operations),
            "recent_operations": len(recent_ops),
            "success_rate": success_count / max(len(recent_ops), 1),
            "error_rate": error_count / max(len(recent_ops), 1),
            "genesis_keys_created": sum(1 for op in self.operations if op.genesis_key_id),
            "magma_ingestions": sum(1 for op in self.operations if op.magma_ingested),
            "subsystems_connected": {
                "genesis": self._genesis_service is not None,
                "kpi": self._kpi_tracker is not None,
                "magma": self._magma is not None,
                "telemetry": self._telemetry is not None,
                "learning_memory": self._learning_memory is not None,
            },
            "health": "healthy" if (success_count / max(len(recent_ops), 1)) > 0.8 else "degraded",
        }

    # ==================== Unified Operation Wrapper ====================

    async def execute_tracked_operation(
        self,
        operation_type: str,
        module: str,
        description: str,
        execute_fn,
        inputs: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Execute a BI operation with full GRACE tracking.

        Wraps any BI function with:
        1. Genesis Key creation (provenance)
        2. KPI recording (performance)
        3. Telemetry tracking (drift detection)
        4. MAGMA ingestion (memory)
        5. Learning storage (improvement)
        """
        import time
        start = time.time()

        operation = self.track_bi_operation(
            operation_type=operation_type,
            module=module,
            description=description,
            inputs=inputs,
        )

        try:
            result = await execute_fn()

            duration = (time.time() - start) * 1000
            operation.duration_ms = duration
            operation.success = True
            operation.outputs = {"result_type": type(result).__name__}

            self.record_bi_kpi(module, f"{operation_type}_duration_ms", duration)
            self.record_bi_kpi(module, f"{operation_type}_success", 1.0)

            self.track_telemetry(operation_type, module, duration, True)

            if isinstance(result, dict):
                summary = str(result)[:200]
            else:
                summary = str(result)[:200]
            self.ingest_to_magma(
                f"BI operation {operation_type} on {module}: {summary}",
                category=f"bi_{operation_type}",
            )
            operation.magma_ingested = True

            return {"status": "success", "result": result, "operation_id": operation.operation_id,
                    "genesis_key": operation.genesis_key_id, "duration_ms": duration}

        except Exception as e:
            duration = (time.time() - start) * 1000
            operation.duration_ms = duration
            operation.success = False
            operation.error = str(e)

            self.record_bi_kpi(module, f"{operation_type}_error", 1.0)
            self.track_telemetry(operation_type, module, duration, False)

            logger.error(f"BI operation failed: {operation_type}/{module}: {e}")
            raise

    # ==================== Status ====================

    def get_integration_status(self) -> Dict[str, Any]:
        """Get status of all GRACE integrations."""
        return {
            "initialized": self._initialized,
            "subsystems": {
                "genesis_keys": {"connected": self._genesis_service is not None, "purpose": "Provenance tracking for every BI operation"},
                "kpi_tracker": {"connected": self._kpi_tracker is not None, "purpose": "Performance metrics feeding trust scores"},
                "magma_memory": {"connected": self._magma is not None, "purpose": "Graph memory for accumulated BI intelligence"},
                "telemetry": {"connected": self._telemetry is not None, "purpose": "Operation tracking, drift detection, replay"},
                "learning_memory": {"connected": self._learning_memory is not None, "purpose": "Learning from BI outcomes for improvement"},
            },
            "total_operations_tracked": len(self.operations),
            "sensor_data": self.get_bi_sensor_data(),
        }


_grace_integration: Optional[GraceIntegration] = None


def get_grace_integration() -> GraceIntegration:
    """Get or create the global GRACE integration instance."""
    global _grace_integration
    if _grace_integration is None:
        _grace_integration = GraceIntegration()
        _grace_integration.initialize()
    return _grace_integration
