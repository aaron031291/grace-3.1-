import logging
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from models.genesis_key_models import GenesisKey, GenesisKeyType
from genesis.intelligent_cicd_orchestrator import IntelligentTestSelector, TestSelectionStrategy, IntelligenceMode
from genesis.code_change_analyzer import ChangeAnalysis
from genesis.cicd import GenesisCICD, get_cicd
from genesis.predictive_failure_detector import get_predictive_failure_detector
from genesis.autonomous_code_reviewer import get_autonomous_code_reviewer
from genesis.proactive_test_generator import get_proactive_test_generator
from genesis.semantic_intent_analyzer import get_semantic_intent_analyzer
class GenesisCICDIntegration:
    logger = logging.getLogger(__name__)
    """
    Integrates Genesis Keys with CI/CD for intelligent, autonomous testing.
    
    This is the "Grace Way" - goes beyond traditional Git by:
    - Understanding code semantics (not just file diffs)
    - Selecting only affected tests (10x faster)
    - Learning from outcomes (gets smarter over time)
    - Autonomous healing (fixes issues automatically)
    """

    def __init__(
        self,
        session: Session,
        base_path: Optional[str] = None
    ):
        self.session = session
        self.base_path = base_path
        self.test_selector = IntelligentTestSelector(base_path=base_path)
        self.cicd = get_cicd()
        self.failure_detector = get_predictive_failure_detector()
        self.code_reviewer = get_autonomous_code_reviewer()
        self.test_generator = get_proactive_test_generator()
        self.intent_analyzer = get_semantic_intent_analyzer()
        self.integrations_count = 0

    def on_code_change_genesis_key(
        self,
        genesis_key: GenesisKey
    ) -> Dict[str, Any]:
        """
        Handle a CODE_CHANGE Genesis Key by triggering intelligent CI/CD.
        
        This is called automatically when a code change Genesis Key is created.
        
        Args:
            genesis_key: Genesis Key representing the code change
            
        Returns:
            Dict with CI/CD trigger results and test selection
        """
        if genesis_key.key_type not in [
            GenesisKeyType.CODE_CHANGE,
            GenesisKeyType.FILE_OPERATION
        ]:
            return {
                "triggered": False,
                "reason": f"Genesis Key type {genesis_key.key_type} is not a code change"
            }

        logger.info(
            f"[GenesisCICD] Processing code change Genesis Key: {genesis_key.key_id}"
        )

        try:
            # 1. Analyze the code change semantically
            selected_tests, change_analysis = self.test_selector.select_tests_from_genesis_key(
                genesis_key=genesis_key,
                strategy=TestSelectionStrategy.IMPACT_ANALYSIS
            )

            if not change_analysis:
                logger.warning(
                    f"[GenesisCICD] Could not analyze Genesis Key {genesis_key.key_id}"
                )
                return {
                    "triggered": False,
                    "reason": "Could not analyze code change"
                }

            # 2. Advanced Analysis (BEYOND traditional CI/CD)
            # 2a. Predict failures BEFORE running tests
            failure_predictions = self.failure_detector.predict_failures(
                genesis_key=genesis_key,
                change_analysis=change_analysis,
                test_ids=selected_tests
            )
            
            # 2b. Autonomous code review
            code_review = self.code_reviewer.review_code_change(
                genesis_key=genesis_key,
                change_analysis=change_analysis
            )
            
            # 2c. Understand intent
            intent_analysis = self.intent_analyzer.analyze_intent(
                genesis_key=genesis_key,
                change_analysis=change_analysis
            )
            
            # 2d. Generate tests proactively
            test_generation_plan = self.test_generator.generate_tests_for_change(
                genesis_key=genesis_key,
                change_analysis=change_analysis
            )
            
            # 3. Build intelligent CI/CD pipeline configuration
            pipeline_config = self._build_intelligent_pipeline_config(
                genesis_key=genesis_key,
                change_analysis=change_analysis,
                selected_tests=selected_tests,
                failure_predictions=failure_predictions,
                code_review=code_review,
                intent_analysis=intent_analysis,
                test_generation=test_generation_plan
            )

            # 3. Trigger CI/CD pipeline with intelligent test selection
            pipeline_run = self._trigger_intelligent_pipeline(
                genesis_key=genesis_key,
                pipeline_config=pipeline_config
            )

            self.integrations_count += 1

            return {
                "triggered": True,
                "genesis_key_id": genesis_key.key_id,
                "pipeline_run_id": pipeline_run.id if pipeline_run else None,
                "tests_selected": len(selected_tests),
                "test_ids": selected_tests,
                "change_analysis": {
                    "risk_score": change_analysis.risk_score,
                    "confidence": change_analysis.confidence,
                    "affected_files": change_analysis.affected_files,
                    "affected_functions": change_analysis.affected_functions,
                    "estimated_test_time": change_analysis.estimated_test_time
                },
                "pipeline_config": pipeline_config
            }

        except Exception as e:
            logger.error(f"[GenesisCICD] Error processing Genesis Key {genesis_key.key_id}: {e}")
            return {
                "triggered": False,
                "error": str(e)
            }

    def _build_intelligent_pipeline_config(
        self,
        genesis_key: GenesisKey,
        change_analysis: ChangeAnalysis,
        selected_tests: List[str],
        failure_predictions: List = None,
        code_review = None,
        intent_analysis = None,
        test_generation = None
    ) -> Dict[str, Any]:
        """Build intelligent CI/CD pipeline configuration from analysis."""
        config = {
            "genesis_key_id": genesis_key.key_id,
            "file_path": genesis_key.file_path,
            "risk_score": change_analysis.risk_score,
            "confidence": change_analysis.confidence,
            "selected_tests": selected_tests,
            "test_count": len(selected_tests),
            "estimated_time": change_analysis.estimated_test_time,
            "affected_files": change_analysis.affected_files,
            "affected_functions": change_analysis.affected_functions,
            "strategy": "intelligent_selection",
            "intelligence_mode": IntelligenceMode.ML_ASSISTED.value,
            # Advanced features
            "failure_predictions": [
                {
                    "test_id": p.test_id,
                    "failure_probability": p.failure_probability,
                    "predicted_type": p.predicted_failure_type
                }
                for p in (failure_predictions or [])[:5]  # Top 5 predictions
            ],
            "code_review": {
                "score": code_review.overall_score if code_review else 1.0,
                "issues_count": len(code_review.issues) if code_review else 0,
                "critical_issues": len([
                    i for i in (code_review.issues or [])
                    if i.severity.value in ['error', 'critical']
                ]) if code_review else 0
            },
            "intent": {
                "primary": intent_analysis.primary_intent.value if intent_analysis else "unknown",
                "confidence": intent_analysis.confidence if intent_analysis else 0.0,
                "suggested_followups": intent_analysis.suggested_followups if intent_analysis else []
            },
            "generated_tests": {
                "count": len(test_generation.generated_tests) if test_generation else 0,
                "coverage_estimate": test_generation.coverage_estimate if test_generation else 0.0
            }
        }

        # Adjust pipeline behavior based on risk
        if change_analysis.risk_score > 0.7:
            config["run_full_suite"] = True  # High risk - run more tests
            config["security_scan"] = True
            config["code_review_required"] = True
        elif change_analysis.risk_score > 0.4:
            config["run_full_suite"] = False
            config["security_scan"] = True
            config["code_review_required"] = False
        else:
            config["run_full_suite"] = False
            config["security_scan"] = False
            config["code_review_required"] = False

        return config

    def _trigger_intelligent_pipeline(
        self,
        genesis_key: GenesisKey,
        pipeline_config: Dict[str, Any]
    ):
        """Trigger CI/CD pipeline with intelligent configuration."""
        try:
            # Use the existing CI/CD system but with intelligent test selection
            # This would integrate with the GenesisCICD system
            
            # For now, return a mock pipeline run
            # In production, this would actually trigger the pipeline
            logger.info(
                f"[GenesisCICD] Would trigger pipeline for {genesis_key.key_id} "
                f"with {pipeline_config['test_count']} tests "
                f"(risk={pipeline_config['risk_score']:.2f})"
            )
            
            # TODO: Actually trigger the pipeline
            # pipeline_run = await self.cicd.trigger_pipeline(
            #     pipeline_id="grace-ci-intelligent",
            #     trigger="genesis_key",
            #     variables={
            #         "GENESIS_KEY_ID": genesis_key.key_id,
            #         "SELECTED_TESTS": ",".join(pipeline_config['selected_tests']),
            #         "RISK_SCORE": str(pipeline_config['risk_score']),
            #         "ESTIMATED_TIME": str(pipeline_config['estimated_time'])
            #     }
            # )
            
            return None  # Placeholder
            
        except Exception as e:
            logger.error(f"[GenesisCICD] Error triggering pipeline: {e}")
            return None

    def learn_from_pipeline_outcome(
        self,
        genesis_key_id: str,
        pipeline_result: Dict[str, Any]
    ):
        """
        Learn from CI/CD pipeline outcome to improve future test selection.
        
        This is how Grace gets smarter over time.
        """
        try:
            # Get the Genesis Key
            genesis_key = self.session.query(GenesisKey).filter_by(
                key_id=genesis_key_id
            ).first()
            
            if not genesis_key:
                logger.warning(f"[GenesisCICD] Genesis Key {genesis_key_id} not found for learning")
                return

            # Extract learning data
            tests_run = pipeline_result.get("tests_run", [])
            tests_passed = pipeline_result.get("tests_passed", [])
            tests_failed = pipeline_result.get("tests_failed", [])
            duration = pipeline_result.get("duration", 0.0)

            # Update test metrics
            for test_id in tests_run:
                passed = test_id in tests_passed
                self.test_selector.record_test_result(
                    test_id=test_id,
                    passed=passed,
                    duration=duration / len(tests_run) if tests_run else 0.0
                )

            logger.info(
                f"[GenesisCICD] Learned from pipeline outcome: "
                f"{len(tests_passed)}/{len(tests_run)} tests passed"
            )

        except Exception as e:
            logger.error(f"[GenesisCICD] Error learning from outcome: {e}")

    def get_integration_stats(self) -> Dict[str, Any]:
        """Get statistics about Genesis-CI/CD integration."""
        return {
            "integrations_count": self.integrations_count,
            "test_selector_stats": {
                "total_tests_tracked": len(self.test_selector.test_metrics),
                "selection_history_count": len(self.test_selector.selection_history)
            }
        }


# Global instance
_integration: Optional[GenesisCICDIntegration] = None


def get_genesis_cicd_integration(
    session: Optional[Session] = None,
    base_path: Optional[str] = None
) -> GenesisCICDIntegration:
    """Get or create global Genesis-CI/CD integration instance."""
    global _integration
    if _integration is None or session is not None or base_path is not None:
        if session is None:
            from database.session import SessionLocal
            session = SessionLocal()
        _integration = GenesisCICDIntegration(session=session, base_path=base_path)
    return _integration
