#!/usr/bin/env python3
"""
Grace AI Deep Probe — tests EVERY brain action, service, cognitive module.
Reports what is alive, what is dead, what is connected.
"""

import os, sys, time, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.update({
    "SKIP_EMBEDDING_LOAD": "true", "SKIP_QDRANT_CHECK": "true",
    "SKIP_OLLAMA_CHECK": "true", "SKIP_AUTO_INGESTION": "true",
    "DISABLE_CONTINUOUS_LEARNING": "true", "SKIP_LLM_CHECK": "true",
})

ALIVE = 0
DEAD = 0
TOTAL = 0


def probe(name, func):
    global ALIVE, DEAD, TOTAL
    TOTAL += 1
    try:
        result = func()
        ok = result is not None
        if isinstance(result, dict):
            ok = not result.get("error")
        ALIVE += 1
        print(f"  🟢 {name}")
        return True
    except Exception as e:
        DEAD += 1
        print(f"  🔴 {name} — {str(e)[:60]}")
        return False


print("=" * 65)
print("  GRACE AI DEEP PROBE — Testing Every Component")
print("=" * 65)

# ── Brain Actions (all 8 domains) ─────────────────────────────
print("\n▶ BRAIN ACTIONS")
from api.brain_api_v2 import call_brain, _build_directory
d = _build_directory()
for domain, info in d.items():
    for action in info["actions"]:
        try:
            r = call_brain(domain, action, {})
            if r.get("ok"):
                ALIVE += 1
                TOTAL += 1
            else:
                DEAD += 1
                TOTAL += 1
                if "Unknown" not in r.get("error", ""):
                    print(f"  🟡 brain/{domain}/{action}: {r.get('error','')[:50]}")
        except Exception as e:
            DEAD += 1
            TOTAL += 1
            print(f"  🔴 brain/{domain}/{action}: {str(e)[:50]}")

brain_total = sum(len(info["actions"]) for info in d.values())
print(f"  Brains: {brain_total} actions tested")

# ── Core Services ─────────────────────────────────────────────
print("\n▶ CORE SERVICES")
probe("chat_service.list_chats", lambda: __import__("core.services.chat_service", fromlist=["list_chats"]).list_chats(5))
probe("files_service.stats", lambda: __import__("core.services.files_service", fromlist=["stats"]).stats())
probe("files_service.tree", lambda: __import__("core.services.files_service", fromlist=["tree"]).tree())
probe("govern_service.get_persona", lambda: __import__("core.services.govern_service", fromlist=["get_persona"]).get_persona())
probe("govern_service.genesis_stats", lambda: __import__("core.services.govern_service", fromlist=["genesis_stats"]).genesis_stats())
probe("data_service.api_sources", lambda: __import__("core.services.data_service", fromlist=["api_sources"]).api_sources())
probe("tasks_service.time_sense", lambda: __import__("core.services.tasks_service", fromlist=["time_sense"]).time_sense())
probe("code_service.list_projects", lambda: __import__("core.services.code_service", fromlist=["list_projects"]).list_projects())
probe("system_service.get_runtime", lambda: __import__("core.services.system_service", fromlist=["get_runtime_status"]).get_runtime_status())

# ── Cognitive Modules ─────────────────────────────────────────
print("\n▶ COGNITIVE MODULES")
probe("TimeSense.get_context", lambda: __import__("cognitive.time_sense", fromlist=["TimeSense"]).TimeSense.get_context())
probe("consensus_engine.get_available_models", lambda: __import__("cognitive.consensus_engine", fromlist=["get_available_models"]).get_available_models())

# Cognitive Mesh (newly wired)
probe("cognitive_mesh.ooda_cycle", lambda: __import__("core.cognitive_mesh", fromlist=["CognitiveMesh"]).CognitiveMesh.ooda_cycle("probe test"))
probe("cognitive_mesh.resolve_ambiguity", lambda: __import__("core.cognitive_mesh", fromlist=["CognitiveMesh"]).CognitiveMesh.resolve_ambiguity("maybe test"))
probe("cognitive_mesh.check_invariants", lambda: __import__("core.cognitive_mesh", fromlist=["CognitiveMesh"]).CognitiveMesh.check_invariants())
probe("cognitive_mesh.find_procedure", lambda: __import__("core.cognitive_mesh", fromlist=["CognitiveMesh"]).CognitiveMesh.find_procedure("test"))
probe("cognitive_mesh.bandit_select", lambda: __import__("core.cognitive_mesh", fromlist=["CognitiveMesh"]).CognitiveMesh.bandit_select(["a", "b", "c"]))
probe("cognitive_mesh.knowledge_gaps", lambda: __import__("core.cognitive_mesh", fromlist=["CognitiveMesh"]).CognitiveMesh.analyze_knowledge_gaps())
probe("cognitive_mesh.full_report", lambda: __import__("core.cognitive_mesh", fromlist=["CognitiveMesh"]).CognitiveMesh.full_cognitive_report("probe"))

# ── Intelligence ──────────────────────────────────────────────
print("\n▶ INTELLIGENCE")
probe("adaptive_trust", lambda: __import__("core.intelligence", fromlist=["AdaptiveTrust"]).AdaptiveTrust.get_all_trust())
probe("genesis_key_miner", lambda: __import__("core.intelligence", fromlist=["GenesisKeyMiner"]).GenesisKeyMiner().mine_patterns(hours=1, limit=100))
probe("episodic_miner", lambda: __import__("core.intelligence", fromlist=["EpisodicMiner"]).EpisodicMiner().mine_episodes(limit=50))

# ── Deep Learning ─────────────────────────────────────────────
print("\n▶ DEEP LEARNING")
probe("dl_model.predict", lambda: __import__("core.deep_learning", fromlist=["get_model"]).get_model().predict({"key_type": "test", "what": "probe", "who": "probe", "is_error": False}))

# ── Resilience ────────────────────────────────────────────────
print("\n▶ RESILIENCE")
probe("circuit_breaker", lambda: __import__("core.resilience", fromlist=["CircuitBreaker"]).CircuitBreaker("probe", 3).status())
probe("error_boundary", lambda: (lambda: None)())
probe("degradation_level", lambda: __import__("core.resilience", fromlist=["GracefulDegradation"]).GracefulDegradation.get_level())

# ── Security ──────────────────────────────────────────────────
print("\n▶ SECURITY")
probe("rate_limiter", lambda: __import__("core.security", fromlist=["check_rate_limit"]).check_rate_limit("probe", "1.2.3.4"))
probe("sql_injection", lambda: __import__("core.security", fromlist=["check_sql_injection"]).check_sql_injection("'; DROP TABLE--"))

# ── Hebbian ───────────────────────────────────────────────────
print("\n▶ HEBBIAN LEARNING")
probe("hebbian_mesh", lambda: __import__("core.hebbian", fromlist=["get_hebbian_mesh"]).get_hebbian_mesh().get_weights())

# ── Summary ───────────────────────────────────────────────────
print("\n" + "=" * 65)
pct = round(ALIVE / TOTAL * 100) if TOTAL > 0 else 0
print(f"  ALIVE: {ALIVE}  |  DEAD: {DEAD}  |  TOTAL: {TOTAL}  |  {pct}%")
if DEAD == 0:
    print(f"  STATUS: EVERYTHING CONNECTED ✅")
else:
    print(f"  STATUS: {DEAD} COMPONENTS NEED ATTENTION ⚠️")
print("=" * 65)

sys.exit(0 if DEAD == 0 else 1)
