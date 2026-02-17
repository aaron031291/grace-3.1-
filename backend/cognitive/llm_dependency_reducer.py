"""
LLM Dependency Reducer

Measures, tracks, and actively works toward reducing Grace's dependency
on external LLMs. This is the strategic layer that coordinates:

1. Dependency Metrics: How much does Grace rely on LLMs?
2. Reduction Tracking: How is dependency changing over time?
3. Training Data Export: Package learned patterns for local model training
4. Autonomy Scoring: Which domains can Grace handle independently?
5. Cost Analysis: How much is being saved by autonomous handling?

The goal: Over time, Grace should need Kimi (and other LLMs) less and
less for common tasks, eventually reaching a state where LLMs are only
needed for truly novel or complex situations.
"""

import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc

from models.llm_tracking_models import (
    LLMInteraction,
    ReasoningPath,
    ExtractedPattern,
    CodingTaskRecord,
    LLMDependencyMetric,
    InteractionType,
    InteractionOutcome,
)

logger = logging.getLogger(__name__)


class LLMDependencyReducer:
    """
    Tracks and reduces Grace's dependency on external LLMs.

    This system provides:
    - Real-time dependency metrics
    - Historical trend analysis
    - Domain-level autonomy scores
    - Training data export for local model fine-tuning
    - Cost savings analysis
    - Recommendations for what to learn next
    """

    def __init__(self, session: Session):
        self.session = session
        logger.info("[DEPENDENCY-REDUCER] Initialized")

    def calculate_dependency_metrics(
        self,
        period_hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Calculate current LLM dependency metrics.

        Returns a comprehensive view of how much Grace depends on LLMs
        and where autonomous handling is possible.
        """
        period_end = datetime.now(timezone.utc)
        period_start = period_end - timedelta(hours=period_hours)

        interactions = self.session.query(LLMInteraction).filter(
            LLMInteraction.created_at >= period_start,
            LLMInteraction.created_at <= period_end,
        ).all()

        patterns = self.session.query(ExtractedPattern).filter(
            ExtractedPattern.can_replace_llm == True
        ).all()

        total_tasks = len(interactions)
        if total_tasks == 0:
            return {
                "period_hours": period_hours,
                "total_tasks": 0,
                "message": "No interactions in this period",
                "llm_dependency_ratio": 1.0,
                "autonomy_ratio": 0.0,
            }

        autonomous_patterns = {p.task_category: p for p in patterns}

        tasks_requiring_llm = 0
        tasks_autonomous = 0
        tasks_by_pattern = 0

        domain_breakdown = defaultdict(lambda: {
            "total": 0, "llm_required": 0, "autonomous": 0
        })
        type_breakdown = defaultdict(lambda: {
            "total": 0, "llm_required": 0, "autonomous": 0
        })

        total_tokens_in = 0
        total_tokens_out = 0
        total_duration = 0.0

        for interaction in interactions:
            itype = interaction.interaction_type.value
            type_breakdown[itype]["total"] += 1

            domain = self._infer_domain_from_interaction(interaction)
            domain_breakdown[domain]["total"] += 1

            total_tokens_in += interaction.token_count_input
            total_tokens_out += interaction.token_count_output
            total_duration += interaction.duration_ms

            if itype in autonomous_patterns:
                pattern = autonomous_patterns[itype]
                if pattern.confidence_score >= 0.85:
                    tasks_autonomous += 1
                    tasks_by_pattern += 1
                    domain_breakdown[domain]["autonomous"] += 1
                    type_breakdown[itype]["autonomous"] += 1
                    continue

            tasks_requiring_llm += 1
            domain_breakdown[domain]["llm_required"] += 1
            type_breakdown[itype]["llm_required"] += 1

        dependency_ratio = tasks_requiring_llm / total_tasks if total_tasks > 0 else 1.0
        autonomy_ratio = tasks_autonomous / total_tasks if total_tasks > 0 else 0.0

        est_cost_per_1k_tokens = 0.002
        total_tokens = total_tokens_in + total_tokens_out
        estimated_cost = (total_tokens / 1000) * est_cost_per_1k_tokens
        estimated_savings = (
            (tasks_by_pattern / total_tasks) * estimated_cost
            if total_tasks > 0 else 0
        )

        metric_id = f"DEP-{uuid.uuid4().hex[:12]}"
        metric = LLMDependencyMetric(
            metric_id=metric_id,
            period_start=period_start,
            period_end=period_end,
            total_tasks=total_tasks,
            tasks_requiring_llm=tasks_requiring_llm,
            tasks_handled_autonomously=tasks_autonomous,
            tasks_handled_by_pattern=tasks_by_pattern,
            llm_dependency_ratio=dependency_ratio,
            autonomy_ratio=autonomy_ratio,
            domain_breakdown=dict(domain_breakdown),
            task_type_breakdown=dict(type_breakdown),
            patterns_available=len(patterns),
            patterns_with_high_confidence=sum(
                1 for p in patterns if p.confidence_score >= 0.85
            ),
            estimated_llm_cost=estimated_cost,
            estimated_cost_saved=estimated_savings,
        )
        self.session.add(metric)
        self.session.flush()

        return {
            "metric_id": metric_id,
            "period_hours": period_hours,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "total_tasks": total_tasks,
            "tasks_requiring_llm": tasks_requiring_llm,
            "tasks_handled_autonomously": tasks_autonomous,
            "tasks_handled_by_pattern": tasks_by_pattern,
            "llm_dependency_ratio": round(dependency_ratio, 3),
            "autonomy_ratio": round(autonomy_ratio, 3),
            "domain_breakdown": dict(domain_breakdown),
            "task_type_breakdown": dict(type_breakdown),
            "patterns": {
                "available": len(patterns),
                "high_confidence": sum(
                    1 for p in patterns if p.confidence_score >= 0.85
                ),
            },
            "cost_analysis": {
                "estimated_llm_cost": round(estimated_cost, 4),
                "estimated_savings": round(estimated_savings, 4),
                "total_tokens": total_tokens,
            },
        }

    def get_dependency_trend(
        self,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        Get the dependency trend over time.

        Shows how LLM dependency is changing -- ideally decreasing.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        metrics = self.session.query(LLMDependencyMetric).filter(
            LLMDependencyMetric.period_start >= cutoff
        ).order_by(LLMDependencyMetric.period_start).all()

        if not metrics:
            return {
                "days": days,
                "data_points": 0,
                "message": "No dependency data available yet",
                "trend_direction": "unknown",
            }

        data_points = []
        for m in metrics:
            data_points.append({
                "period_start": m.period_start.isoformat(),
                "dependency_ratio": m.llm_dependency_ratio,
                "autonomy_ratio": m.autonomy_ratio,
                "total_tasks": m.total_tasks,
                "patterns_available": m.patterns_available,
            })

        if len(metrics) >= 2:
            first_ratio = metrics[0].llm_dependency_ratio
            last_ratio = metrics[-1].llm_dependency_ratio
            change = last_ratio - first_ratio

            if change < -0.05:
                trend_direction = "decreasing"
            elif change > 0.05:
                trend_direction = "increasing"
            else:
                trend_direction = "stable"

            trend_magnitude = abs(change)
        else:
            trend_direction = "insufficient_data"
            trend_magnitude = 0.0

        return {
            "days": days,
            "data_points": len(data_points),
            "trend_direction": trend_direction,
            "trend_magnitude": round(trend_magnitude, 3),
            "current_dependency": round(metrics[-1].llm_dependency_ratio, 3) if metrics else 1.0,
            "current_autonomy": round(metrics[-1].autonomy_ratio, 3) if metrics else 0.0,
            "timeline": data_points,
        }

    def get_domain_autonomy_scores(self) -> Dict[str, Any]:
        """
        Get autonomy scores per domain.

        Shows which domains Grace can handle independently and which
        still require LLM assistance.
        """
        patterns = self.session.query(ExtractedPattern).all()

        domain_scores = defaultdict(lambda: {
            "total_patterns": 0,
            "replaceable_patterns": 0,
            "avg_confidence": 0.0,
            "avg_success_rate": 0.0,
            "llm_calls_saved": 0,
            "autonomy_score": 0.0,
        })

        for pattern in patterns:
            domain = pattern.domain or "general"
            ds = domain_scores[domain]
            ds["total_patterns"] += 1
            if pattern.can_replace_llm:
                ds["replaceable_patterns"] += 1
            ds["avg_confidence"] += pattern.confidence_score
            ds["avg_success_rate"] += pattern.success_rate
            ds["llm_calls_saved"] += pattern.llm_calls_saved

        for domain, scores in domain_scores.items():
            total = scores["total_patterns"]
            if total > 0:
                scores["avg_confidence"] = round(scores["avg_confidence"] / total, 3)
                scores["avg_success_rate"] = round(scores["avg_success_rate"] / total, 3)
                scores["autonomy_score"] = round(
                    (scores["replaceable_patterns"] / total) * 0.5 +
                    scores["avg_confidence"] * 0.3 +
                    scores["avg_success_rate"] * 0.2,
                    3
                )

        sorted_domains = sorted(
            domain_scores.items(),
            key=lambda x: x[1]["autonomy_score"],
            reverse=True,
        )

        return {
            "domains": dict(sorted_domains),
            "most_autonomous": sorted_domains[0][0] if sorted_domains else None,
            "least_autonomous": sorted_domains[-1][0] if sorted_domains else None,
            "total_domains_tracked": len(sorted_domains),
        }

    def export_training_data(
        self,
        min_trust_score: float = 0.7,
        task_type: Optional[str] = None,
        limit: int = 1000,
        format_type: str = "instruction_tuning",
    ) -> Dict[str, Any]:
        """
        Export high-quality interaction data for training local models.

        This packages the best LLM interactions into training data
        that can be used to fine-tune a local model, further reducing
        LLM dependency.

        Args:
            min_trust_score: Minimum trust score for inclusion
            task_type: Optional task type filter
            limit: Maximum number of examples
            format_type: "instruction_tuning" or "chat" or "raw"

        Returns:
            Training dataset with examples
        """
        query = self.session.query(LLMInteraction).filter(
            LLMInteraction.trust_score >= min_trust_score,
            LLMInteraction.outcome == InteractionOutcome.SUCCESS,
            LLMInteraction.response != None,
        )

        if task_type:
            try:
                itype = InteractionType(task_type)
                query = query.filter(LLMInteraction.interaction_type == itype)
            except ValueError:
                pass

        query = query.order_by(
            desc(LLMInteraction.trust_score),
            desc(LLMInteraction.quality_score),
        )

        interactions = query.limit(limit).all()

        examples = []
        for interaction in interactions:
            if format_type == "instruction_tuning":
                example = {
                    "instruction": interaction.prompt,
                    "output": interaction.response,
                    "input": "",
                }
                if interaction.system_prompt:
                    example["system"] = interaction.system_prompt
            elif format_type == "chat":
                messages = []
                if interaction.system_prompt:
                    messages.append({
                        "role": "system",
                        "content": interaction.system_prompt,
                    })
                messages.append({
                    "role": "user",
                    "content": interaction.prompt,
                })
                messages.append({
                    "role": "assistant",
                    "content": interaction.response,
                })
                example = {"messages": messages}
            else:
                example = {
                    "prompt": interaction.prompt,
                    "response": interaction.response,
                    "system_prompt": interaction.system_prompt,
                    "model": interaction.model_used,
                    "type": interaction.interaction_type.value,
                    "trust_score": interaction.trust_score,
                    "confidence": interaction.confidence_score,
                }

            example["metadata"] = {
                "interaction_id": interaction.interaction_id,
                "model_used": interaction.model_used,
                "trust_score": interaction.trust_score,
                "interaction_type": interaction.interaction_type.value,
                "has_reasoning": bool(interaction.reasoning_chain),
            }

            examples.append(example)

        avg_trust = (
            sum(i.trust_score for i in interactions) / len(interactions)
            if interactions else 0
        )

        return {
            "format": format_type,
            "total_examples": len(examples),
            "min_trust_score": min_trust_score,
            "avg_trust_score": round(avg_trust, 3),
            "task_type_filter": task_type,
            "examples": examples,
            "export_timestamp": datetime.now(timezone.utc).isoformat(),
            "recommended_use": (
                "Use this data to fine-tune a local model. "
                "Higher trust score examples are more reliable. "
                "Examples with reasoning chains are particularly valuable."
            ),
        }

    def get_reduction_recommendations(self) -> Dict[str, Any]:
        """
        Get recommendations for how to further reduce LLM dependency.

        Analyzes current patterns and interaction data to suggest:
        - Which task types to focus on learning
        - Which patterns need more training data
        - What domains are closest to autonomous handling
        """
        patterns = self.session.query(ExtractedPattern).all()

        interactions_by_type = defaultdict(int)
        all_interactions = self.session.query(
            LLMInteraction.interaction_type,
            func.count(LLMInteraction.id)
        ).group_by(LLMInteraction.interaction_type).all()

        for itype, count in all_interactions:
            interactions_by_type[itype.value] = count

        pattern_coverage = defaultdict(lambda: {
            "has_pattern": False, "can_replace": False, "confidence": 0
        })
        for p in patterns:
            cat = p.task_category or "unknown"
            pattern_coverage[cat]["has_pattern"] = True
            if p.can_replace_llm:
                pattern_coverage[cat]["can_replace"] = True
            pattern_coverage[cat]["confidence"] = max(
                pattern_coverage[cat]["confidence"],
                p.confidence_score,
            )

        recommendations = []

        for itype, count in sorted(
            interactions_by_type.items(),
            key=lambda x: x[1],
            reverse=True,
        ):
            coverage = pattern_coverage.get(itype, {})
            if not coverage.get("has_pattern"):
                recommendations.append({
                    "priority": "high",
                    "task_type": itype,
                    "interaction_count": count,
                    "action": "extract_patterns",
                    "reason": (
                        f"High-frequency task type ({count} interactions) "
                        "with no extracted patterns. Extract patterns to enable "
                        "autonomous handling."
                    ),
                })
            elif not coverage.get("can_replace"):
                recommendations.append({
                    "priority": "medium",
                    "task_type": itype,
                    "interaction_count": count,
                    "current_confidence": coverage.get("confidence", 0),
                    "action": "improve_patterns",
                    "reason": (
                        f"Has patterns but confidence too low for autonomous handling "
                        f"(current: {coverage.get('confidence', 0):.2f}). "
                        "More training data needed."
                    ),
                })

        almost_autonomous = [
            p for p in patterns
            if not p.can_replace_llm
            and p.confidence_score >= 0.7
            and p.success_rate >= 0.8
        ]

        for pattern in almost_autonomous:
            recommendations.append({
                "priority": "low",
                "task_type": pattern.task_category,
                "pattern_name": pattern.pattern_name,
                "current_confidence": pattern.confidence_score,
                "current_success_rate": pattern.success_rate,
                "action": "validate_and_promote",
                "reason": (
                    f"Pattern '{pattern.pattern_name}' is close to autonomous "
                    f"(confidence={pattern.confidence_score:.2f}, "
                    f"success={pattern.success_rate:.2f}). "
                    "Needs validation to promote to autonomous."
                ),
            })

        priority_order = {"high": 0, "medium": 1, "low": 2}
        recommendations.sort(key=lambda r: priority_order.get(r["priority"], 99))

        return {
            "total_recommendations": len(recommendations),
            "high_priority": sum(1 for r in recommendations if r["priority"] == "high"),
            "medium_priority": sum(1 for r in recommendations if r["priority"] == "medium"),
            "low_priority": sum(1 for r in recommendations if r["priority"] == "low"),
            "recommendations": recommendations[:20],
        }

    def _infer_domain_from_interaction(
        self,
        interaction: LLMInteraction,
    ) -> str:
        """Infer domain from an interaction's metadata."""
        if interaction.context_used and isinstance(interaction.context_used, dict):
            domain = interaction.context_used.get("domain")
            if domain:
                return domain

        if interaction.files_referenced:
            files = interaction.files_referenced
            if isinstance(files, list) and files:
                ext = files[0].split(".")[-1] if "." in files[0] else ""
                ext_domain = {
                    "py": "python",
                    "js": "javascript",
                    "ts": "typescript",
                    "sql": "database",
                    "yaml": "devops",
                    "yml": "devops",
                    "sh": "devops",
                    "md": "documentation",
                }
                if ext in ext_domain:
                    return ext_domain[ext]

        return "general"


_reducer_instance: Optional[LLMDependencyReducer] = None


def get_llm_dependency_reducer(session: Session) -> LLMDependencyReducer:
    """Get or create the LLM dependency reducer singleton."""
    global _reducer_instance
    if _reducer_instance is None:
        _reducer_instance = LLMDependencyReducer(session)
    return _reducer_instance
