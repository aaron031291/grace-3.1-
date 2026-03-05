"""
Ask Grace API — Unified system introspection endpoint.

Replaces the broken /api/world-model/chat with a fully wired endpoint
that aggregates data from:
  - SystemRegistry (auto-discovered components)
  - ComponentRegistry (runtime components)
  - Layer 1 Message Bus (communication stats)
  - Cognitive Event Bus (recent events)
  - Probe Agent (endpoint health)
  - Genesis Keys (provenance)
  - Live Console (model status)

Wired into both the Layer 1 message bus (via AskGraceConnector) and the
cognitive event bus (publishes ask_grace.* events).
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import traceback

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ask-grace", tags=["Ask Grace"])


class AskGraceQuery(BaseModel):
    query: str = Field(..., description="Natural language question about the system")
    include_system_state: bool = Field(True, description="Include full system context")
    scope: str = Field("all", description="Query scope: all, components, health, bus, genesis")


class AskGraceResponse(BaseModel):
    response: str
    intent: str
    sources_used: List[str] = []
    components_referenced: List[Dict[str, Any]] = []
    system_health: Optional[Dict[str, Any]] = None
    timestamp: str = ""


def _classify_intent(query: str) -> str:
    """Deterministic intent classification using pattern matching.

    Falls back to 'general' for anything that doesn't match a known pattern.
    This runs BEFORE the LLM so we can route the query efficiently.

    Order matters: more specific patterns are checked first to avoid
    generic keywords (like "show me") stealing matches from specific intents.
    """
    q = query.lower().strip()

    owner_keywords = ["who owns", "who maintains", "who built", "owned by", "maintainer"]
    if any(kw in q for kw in owner_keywords):
        return "ownership_query"

    genesis_keywords = ["genesis", "provenance", "audit trail"]
    if any(kw in q for kw in genesis_keywords):
        return "genesis_query"

    bus_keywords = ["message bus", "event bus", "subscriber", "publish", "layer 1", "communication bus", "on the bus", "the bus"]
    if any(kw in q for kw in bus_keywords):
        return "bus_query"

    probe_keywords = ["probe", "endpoint", "dormant"]
    if any(kw in q for kw in probe_keywords):
        return "probe_query"

    health_keywords = ["health", "status", "alive", "running", "broken", "down", "error", "degraded", "working"]
    if any(kw in q for kw in health_keywords):
        return "health_check"

    capability_keywords = ["can you", "capable", "ability", "feature", "what can"]
    if any(kw in q for kw in capability_keywords):
        return "capability_query"

    component_keywords = ["component", "module", "service", "registry", "list", "show me", "what is", "find"]
    if any(kw in q for kw in component_keywords):
        return "component_query"

    return "general"


async def _build_context_for_intent(intent: str, include_system_state: bool) -> Dict[str, Any]:
    """Build targeted context based on classified intent."""
    context: Dict[str, Any] = {"sources": []}

    try:
        from layer1.components.ask_grace_connector import get_ask_grace_connector
        connector = get_ask_grace_connector()

        if include_system_state or intent in ("health_check", "general"):
            full_ctx = await connector.gather_system_context()
            context.update(full_ctx)
            return context
    except Exception as e:
        logger.warning(f"[ASK-GRACE] Connector unavailable, building context manually: {e}")

    if intent in ("health_check", "general"):
        try:
            from cognitive.system_registry import get_system_registry
            sr = get_system_registry()
            context["system_health"] = sr.check_health()
            context["components"] = sr.get_all()
            context["sources"].append("system_registry")
        except Exception:
            pass

        try:
            from core.registry import get_component_registry
            cr = get_component_registry()
            context["component_health"] = cr.get_system_health()
            context["sources"].append("component_registry")
        except Exception:
            pass

    elif intent == "component_query":
        try:
            from cognitive.system_registry import get_system_registry
            sr = get_system_registry()
            context["components"] = sr.get_all()
            context["by_category"] = sr.get_by_category()
            context["sources"].append("system_registry")
        except Exception:
            pass

    elif intent == "bus_query":
        try:
            from layer1.message_bus import get_message_bus
            bus = get_message_bus()
            context["bus_stats"] = bus.get_stats()
            context["autonomous_actions"] = bus.get_autonomous_actions()
            context["sources"].append("message_bus")
        except Exception:
            pass

        try:
            from cognitive.event_bus import get_recent_events, get_subscriber_count
            context["recent_events"] = get_recent_events(30)
            context["event_subscribers"] = get_subscriber_count()
            context["sources"].append("cognitive_event_bus")
        except Exception:
            pass

    elif intent == "genesis_query":
        try:
            from database.session import get_session
            from models.genesis_key_models import GenesisKey
            session = next(get_session())
            recent_keys = session.query(GenesisKey).order_by(
                GenesisKey.created_at.desc()
            ).limit(20).all()
            context["recent_genesis_keys"] = [
                {
                    "key_id": k.key_id,
                    "type": k.key_type.value if k.key_type else "unknown",
                    "what": k.what_description[:150] if k.what_description else "",
                    "where": k.where_location or "",
                    "created": k.created_at.isoformat() if k.created_at else "",
                }
                for k in recent_keys
            ]
            context["sources"].append("genesis_keys_db")
            session.close()
        except Exception:
            pass

    elif intent == "probe_query":
        try:
            from api.probe_agent_api import _probe_results
            context["probe_results"] = _probe_results[-50:] if _probe_results else []
            context["sources"].append("probe_agent")
        except Exception:
            pass

    try:
        from api.live_console_api import live_status
        context["live_status"] = await live_status()
        context["sources"].append("live_console")
    except Exception:
        pass

    return context


def _build_deterministic_response(intent: str, query: str, context: Dict[str, Any]) -> Optional[str]:
    """Try to answer deterministically without an LLM call.

    Returns None if the question needs LLM reasoning.
    """
    if intent == "health_check":
        health = context.get("system_health") or context.get("system_registry", {}).get("health", {})
        if health:
            total = health.get("total", 0)
            green = health.get("green", 0)
            amber = health.get("amber", 0)
            red = health.get("red", 0)
            pct = health.get("health_pct", 0)

            broken = context.get("system_registry", {}).get("broken", [])
            degraded = context.get("system_registry", {}).get("degraded", [])

            lines = [f"System Health: {pct}% ({green} healthy, {amber} degraded, {red} broken out of {total} components)"]

            if broken:
                lines.append(f"\nBroken components ({len(broken)}):")
                for c in broken[:10]:
                    lines.append(f"  - {c.get('name', c.get('id', '?'))}: {c.get('description', '')}")

            if degraded:
                lines.append(f"\nDegraded components ({len(degraded)}):")
                for c in degraded[:10]:
                    lines.append(f"  - {c.get('name', c.get('id', '?'))}: {c.get('description', '')}")

            live = context.get("live_status", {})
            if live:
                lines.append(f"\nLive status: {live.get('summary', 'unknown')}")
                models = live.get("models", {})
                if models:
                    lines.append("Models:")
                    for name, info in models.items():
                        lines.append(f"  - {name}: {info.get('status', 'unknown')}")

            return "\n".join(lines)

    if intent == "bus_query":
        stats = context.get("bus_stats") or context.get("message_bus", {}).get("stats", {})
        if stats:
            lines = [
                f"Layer 1 Message Bus:",
                f"  Total messages: {stats.get('total_messages', 0)}",
                f"  Requests: {stats.get('requests', 0)}",
                f"  Events: {stats.get('events', 0)}",
                f"  Commands: {stats.get('commands', 0)}",
                f"  Autonomous actions triggered: {stats.get('autonomous_actions_triggered', 0)}",
                f"  Registered components: {stats.get('registered_components', 0)}",
                f"  Components: {', '.join(stats.get('components', []))}",
            ]

            actions = context.get("autonomous_actions") or context.get("message_bus", {}).get("autonomous_actions", [])
            if actions:
                lines.append(f"\nAutonomous Actions ({len(actions)}):")
                for a in actions[:15]:
                    status = "enabled" if a.get("enabled") else "disabled"
                    lines.append(f"  - [{status}] {a.get('description', '?')} (trigger: {a.get('trigger_event', '?')})")

            event_subs = context.get("event_subscribers", {})
            if event_subs:
                lines.append(f"\nCognitive Event Bus Subscribers ({len(event_subs)} topics):")
                for topic, count in sorted(event_subs.items()):
                    lines.append(f"  - {topic}: {count} handler(s)")

            return "\n".join(lines)

    if intent == "component_query":
        components = context.get("components", [])
        by_cat = context.get("by_category", {})

        if by_cat:
            lines = [f"Grace Components ({len(components)} total):"]
            for cat, comps in sorted(by_cat.items()):
                lines.append(f"\n  {cat.upper()} ({len(comps)}):")
                for c in comps[:8]:
                    status_icon = {"green": "[OK]", "amber": "[WARN]", "red": "[FAIL]", "unknown": "[?]"}.get(c.get("status", ""), "[?]")
                    lines.append(f"    {status_icon} {c.get('name', '?')}: {c.get('description', '')[:80]}")
                if len(comps) > 8:
                    lines.append(f"    ... and {len(comps) - 8} more")
            return "\n".join(lines)

        if components:
            lines = [f"Grace Components ({len(components)} total):"]
            for c in components[:20]:
                status_icon = {"green": "[OK]", "amber": "[WARN]", "red": "[FAIL]", "unknown": "[?]"}.get(c.get("status", ""), "[?]")
                lines.append(f"  {status_icon} {c.get('name', '?')} ({c.get('category', '?')}): {c.get('description', '')[:80]}")
            if len(components) > 20:
                lines.append(f"  ... and {len(components) - 20} more")
            return "\n".join(lines)

    if intent == "genesis_query":
        keys = context.get("recent_genesis_keys", [])
        if keys:
            lines = [f"Recent Genesis Keys ({len(keys)}):"]
            for k in keys:
                lines.append(f"  [{k.get('type', '?')}] {k.get('key_id', '?')}: {k.get('what', '?')}")
                if k.get("where"):
                    lines.append(f"    Location: {k['where']}")
            return "\n".join(lines)

    if intent == "probe_query":
        results = context.get("probe_results", [])
        if results:
            active = [r for r in results if r.get("status") == "ACTIVE"]
            dormant = [r for r in results if r.get("status") == "DORMANT"]
            broken = [r for r in results if r.get("status") == "BROKEN"]

            lines = [
                f"Probe Results ({len(results)} endpoints):",
                f"  Active: {len(active)}",
                f"  Dormant: {len(dormant)}",
                f"  Broken: {len(broken)}",
            ]

            if broken:
                lines.append("\nBroken endpoints:")
                for r in broken[:10]:
                    lines.append(f"  - {r.get('method', '?')} {r.get('path', '?')}: {r.get('error', '?')}")

            return "\n".join(lines)

    return None


async def _generate_llm_response(query: str, context: Dict[str, Any]) -> str:
    """Use the LLM orchestrator to generate a response when deterministic fails."""
    context_summary = _summarize_context(context)

    system_prompt = (
        "You are Grace's self-introspection engine. You answer questions about "
        "Grace's own components, health, architecture, and state. You have access "
        "to live system data provided as context. Be concise, accurate, and "
        "reference specific component names and statuses. If something is broken, "
        "say so directly. If you don't have enough data, say what's missing."
    )

    user_prompt = (
        f"System context:\n{context_summary}\n\n"
        f"User question: {query}\n\n"
        f"Answer based on the system context above. Be specific and actionable."
    )

    providers_to_try = ["qwen", None, "kimi", "opus"]

    for provider in providers_to_try:
        try:
            from llm_orchestrator.factory import get_llm_client
            client = get_llm_client(provider=provider)
            response = client.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=1500,
            )
            if response and isinstance(response, str) and len(response.strip()) > 10:
                return response
        except Exception as e:
            logger.debug(f"[ASK-GRACE] Provider {provider} failed: {e}")
            continue

    try:
        from cognitive.consensus_engine import run_consensus
        result = run_consensus(
            prompt=user_prompt,
            models=["qwen", "kimi", "opus"],
            context=system_prompt,
            source="ask_grace",
        )
        return result.final_output
    except Exception:
        pass

    return f"I gathered system data but couldn't generate a natural language response (LLM unavailable). Raw context sources: {', '.join(context.get('sources', context.get('sources_queried', ['none'])))}"


def _summarize_context(context: Dict[str, Any]) -> str:
    """Compress context into a text summary for the LLM prompt."""
    parts = []

    sr = context.get("system_registry", {})
    if sr and not sr.get("error"):
        health = sr.get("health", {})
        parts.append(
            f"System Registry: {health.get('total', '?')} components, "
            f"{health.get('green', '?')} healthy, {health.get('amber', '?')} degraded, "
            f"{health.get('red', '?')} broken ({health.get('health_pct', '?')}%)"
        )
        broken = sr.get("broken", [])
        if broken:
            names = [c.get("name", "?") for c in broken[:5]]
            parts.append(f"Broken: {', '.join(names)}")

    cr = context.get("component_registry", {})
    if cr and not cr.get("error"):
        ch = cr.get("health", {})
        parts.append(
            f"Component Registry: {ch.get('total_components', '?')} components, "
            f"health score {ch.get('health_score', '?')}, status: {ch.get('status', '?')}"
        )

    mb = context.get("message_bus", {})
    if mb:
        stats = mb.get("stats", {})
        parts.append(
            f"Message Bus: {stats.get('total_messages', 0)} messages, "
            f"{stats.get('registered_components', 0)} components, "
            f"{stats.get('autonomous_actions', 0)} auto-actions"
        )

    live = context.get("live_status", {})
    if live and not live.get("error"):
        parts.append(f"Live Status: {live.get('summary', 'unknown')}")
        models = live.get("models", {})
        for name, info in models.items():
            parts.append(f"  Model {name}: {info.get('status', 'unknown')}")

    eb = context.get("event_bus", {})
    if eb and not eb.get("error"):
        events = eb.get("recent_events", [])
        if events:
            parts.append(f"Recent events ({len(events)}): {', '.join(e.get('topic', '?') for e in events[:5])}")

    components = context.get("components", [])
    if components:
        cats = {}
        for c in components:
            cat = c.get("category", "other")
            cats[cat] = cats.get(cat, 0) + 1
        parts.append(f"Components by category: {', '.join(f'{k}={v}' for k, v in sorted(cats.items()))}")

    return "\n".join(parts) if parts else "No system context available."


@router.post("/query")
async def ask_grace(query: AskGraceQuery) -> Dict[str, Any]:
    """Main Ask Grace endpoint. Classifies intent, gathers context, responds."""
    start = datetime.utcnow()
    intent = _classify_intent(query.query)

    context = await _build_context_for_intent(intent, query.include_system_state)

    deterministic = _build_deterministic_response(intent, query.query, context)

    if deterministic:
        response_text = deterministic
        method = "deterministic"
    else:
        response_text = await _generate_llm_response(query.query, context)
        method = "llm"

    try:
        from layer1.components.ask_grace_connector import get_ask_grace_connector
        connector = get_ask_grace_connector()
        connector.record_query(query.query, response_text, intent)
        await connector.publish_query_event(intent=intent, query=query.query, result_count=1)
    except Exception:
        pass

    try:
        from cognitive.event_bus import publish_async
        publish_async("ask_grace.query_completed", {
            "query": query.query,
            "intent": intent,
            "method": method,
            "duration_ms": (datetime.utcnow() - start).total_seconds() * 1000,
        }, source="ask_grace")
    except Exception:
        pass

    sources_used = context.get("sources", context.get("sources_queried", []))

    components_referenced = []
    if intent == "component_query":
        components_referenced = context.get("components", [])[:10]

    health_info = None
    if intent == "health_check":
        health_info = (
            context.get("system_health")
            or context.get("system_registry", {}).get("health")
        )

    return {
        "response": response_text,
        "intent": intent,
        "method": method,
        "sources_used": sources_used,
        "components_referenced": components_referenced,
        "system_health": health_info,
        "timestamp": datetime.utcnow().isoformat(),
        "duration_ms": round((datetime.utcnow() - start).total_seconds() * 1000, 1),
    }


@router.post("/chat")
async def ask_grace_chat(query: AskGraceQuery) -> Dict[str, Any]:
    """Alias for /query — matches the frontend's expected /chat endpoint."""
    return await ask_grace(query)


@router.get("/health")
async def ask_grace_health() -> Dict[str, Any]:
    """Quick aggregated health from all registries."""
    result: Dict[str, Any] = {"status": "operational", "registries": {}}

    try:
        from cognitive.system_registry import get_system_registry
        sr = get_system_registry()
        result["registries"]["system"] = sr.check_health()
    except Exception as e:
        result["registries"]["system"] = {"error": str(e)}

    try:
        from core.registry import get_component_registry
        cr = get_component_registry()
        result["registries"]["component"] = cr.get_system_health()
    except Exception as e:
        result["registries"]["component"] = {"error": str(e)}

    try:
        from layer1.message_bus import get_message_bus
        bus = get_message_bus()
        result["message_bus"] = bus.get_stats()
    except Exception as e:
        result["message_bus"] = {"error": str(e)}

    try:
        from cognitive.event_bus import get_subscriber_count
        result["event_bus"] = {"subscriber_topics": len(get_subscriber_count())}
    except Exception:
        pass

    has_errors = any(
        isinstance(v, dict) and v.get("error")
        for v in result["registries"].values()
    )
    result["status"] = "degraded" if has_errors else "operational"

    return result


@router.get("/components")
async def list_components(
    category: Optional[str] = None,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    """List all components from all registries, with optional filters."""
    try:
        from layer1.components.ask_grace_connector import get_ask_grace_connector
        connector = get_ask_grace_connector()
        components = connector._get_all_components()
    except Exception:
        components = []
        try:
            from cognitive.system_registry import get_system_registry
            sr = get_system_registry()
            components = sr.get_all()
        except Exception:
            pass

    if category:
        components = [c for c in components if c.get("category") == category]
    if status:
        components = [c for c in components if c.get("status") == status]

    return {
        "components": components,
        "total": len(components),
        "filters": {"category": category, "status": status},
    }


@router.get("/bus-status")
async def bus_status() -> Dict[str, Any]:
    """Detailed status of all communication buses."""
    result: Dict[str, Any] = {}

    try:
        from layer1.message_bus import get_message_bus
        bus = get_message_bus()
        result["layer1_message_bus"] = bus.get_stats()
        result["layer1_message_bus"]["autonomous_actions"] = bus.get_autonomous_actions()
    except Exception as e:
        result["layer1_message_bus"] = {"error": str(e)}

    try:
        from cognitive.event_bus import get_recent_events, get_subscriber_count
        result["cognitive_event_bus"] = {
            "subscriber_topics": get_subscriber_count(),
            "recent_events": get_recent_events(20),
        }
    except Exception as e:
        result["cognitive_event_bus"] = {"error": str(e)}

    try:
        from grace_os.kernel.event_system import EventSystem
        result["grace_os_event_system"] = {"available": True}
    except Exception:
        result["grace_os_event_system"] = {"available": False}

    return result


@router.get("/recent-queries")
async def recent_queries(limit: int = 20) -> Dict[str, Any]:
    """Return recent Ask Grace queries for analytics."""
    try:
        from layer1.components.ask_grace_connector import get_ask_grace_connector
        connector = get_ask_grace_connector()
        return {"queries": connector.get_recent_queries(limit)}
    except Exception:
        return {"queries": []}
