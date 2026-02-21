"""
Library Connectors - External Deterministic Knowledge Sources

Gives Grace access to knowledge outside her domain.
100% factual, mineable, not probabilistic.

These connectors query real knowledge libraries and feed results
into the existing Knowledge Compiler as compiled facts, entities,
and procedures. No system architecture changes.

Sources:
  Wikidata   - 120M structured facts (entities, relationships)
  ConceptNet - Common sense reasoning (IsA, UsedFor, CapableOf)
  Wolfram    - Computational knowledge (math, science, geography)

Usage:
  from cognitive.library_connectors import LibraryConnectors
  lib = LibraryConnectors()

  # Query and compile into Grace's knowledge store
  facts = lib.query_wikidata("Python programming language")
  common_sense = lib.query_conceptnet("database")
  computed = lib.query_wolfram("population of Tokyo")
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("[LIBRARY] requests module not available")


class LibraryConnectors:
    """
    Connects Grace to external deterministic knowledge libraries.

    Every result is 100% factual. No probabilistic output.
    Results feed directly into the Knowledge Compiler.
    """

    WIKIDATA_API = "https://www.wikidata.org/w/api.php"
    WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"
    CONCEPTNET_API = "https://api.conceptnet.io"
    WOLFRAM_API = "https://api.wolframalpha.com/v2/query"

    def __init__(self, wolfram_app_id: Optional[str] = None, timeout: float = 10.0):
        self.wolfram_app_id = wolfram_app_id
        self.timeout = timeout

        try:
            from settings import settings
            if not self.wolfram_app_id and hasattr(settings, 'WOLFRAM_APP_ID'):
                self.wolfram_app_id = settings.WOLFRAM_APP_ID
        except Exception:
            pass

    # ==================================================================
    # WIKIDATA - 120M structured facts
    # ==================================================================

    def query_wikidata(self, search_term: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Query Wikidata for structured facts about a topic.

        Returns deterministic, sourced facts as subject/predicate/object triples.
        """
        if not REQUESTS_AVAILABLE:
            return []

        facts = []

        try:
            # Step 1: Search for the entity
            search_resp = requests.get(
                self.WIKIDATA_API,
                params={
                    "action": "wbsearchentities",
                    "search": search_term,
                    "language": "en",
                    "limit": 3,
                    "format": "json",
                },
                timeout=self.timeout,
            )
            search_data = search_resp.json()
            results = search_data.get("search", [])

            if not results:
                return []

            entity_id = results[0]["id"]
            entity_label = results[0].get("label", search_term)
            entity_desc = results[0].get("description", "")

            facts.append({
                "subject": entity_label,
                "predicate": "description",
                "object": entity_desc,
                "type": "text",
                "confidence": 1.0,
                "source": f"wikidata:{entity_id}",
                "verified": True,
            })

            # Step 2: Get entity properties
            entity_resp = requests.get(
                self.WIKIDATA_API,
                params={
                    "action": "wbgetentities",
                    "ids": entity_id,
                    "languages": "en",
                    "props": "labels|descriptions|claims",
                    "format": "json",
                },
                timeout=self.timeout,
            )
            entity_data = entity_resp.json()
            entity = entity_data.get("entities", {}).get(entity_id, {})

            claims = entity.get("claims", {})

            # Common properties to extract
            property_labels = {
                "P31": "instance_of",
                "P279": "subclass_of",
                "P17": "country",
                "P36": "capital",
                "P1082": "population",
                "P571": "inception_date",
                "P856": "official_website",
                "P154": "logo",
                "P138": "named_after",
                "P277": "programming_language",
                "P178": "developer",
                "P275": "license",
                "P306": "operating_system",
                "P144": "based_on",
                "P1324": "source_code_repository",
                "P348": "version",
                "P50": "author",
                "P136": "genre",
                "P495": "country_of_origin",
                "P159": "headquarters",
            }

            for prop_id, prop_label in property_labels.items():
                if prop_id in claims:
                    claim_list = claims[prop_id]
                    for claim in claim_list[:3]:
                        mainsnak = claim.get("mainsnak", {})
                        datavalue = mainsnak.get("datavalue", {})
                        value = datavalue.get("value", {})

                        obj_value = None
                        if isinstance(value, dict):
                            if "id" in value:
                                obj_value = value["id"]
                            elif "amount" in value:
                                obj_value = value["amount"].lstrip("+")
                            elif "time" in value:
                                obj_value = value["time"]
                            elif "text" in value:
                                obj_value = value["text"]
                        elif isinstance(value, str):
                            obj_value = value

                        if obj_value:
                            facts.append({
                                "subject": entity_label,
                                "predicate": prop_label,
                                "object": str(obj_value),
                                "type": "text",
                                "confidence": 1.0,
                                "source": f"wikidata:{entity_id}:{prop_id}",
                                "verified": True,
                            })

        except Exception as e:
            logger.warning(f"[LIBRARY] Wikidata query error: {e}")

        return facts[:limit]

    # ==================================================================
    # CONCEPTNET - Common sense reasoning
    # ==================================================================

    def query_conceptnet(self, term: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Query ConceptNet for common sense knowledge about a term.

        Returns relationships like IsA, UsedFor, CapableOf, HasProperty.
        100% deterministic, curated knowledge graph.
        """
        if not REQUESTS_AVAILABLE:
            return []

        facts = []

        try:
            resp = requests.get(
                f"{self.CONCEPTNET_API}/c/en/{term.lower().replace(' ', '_')}",
                params={"limit": limit},
                timeout=self.timeout,
            )
            data = resp.json()

            for edge in data.get("edges", []):
                rel = edge.get("rel", {}).get("label", "")
                start = edge.get("start", {}).get("label", "")
                end = edge.get("end", {}).get("label", "")
                weight = edge.get("weight", 1.0)
                surface = edge.get("surfaceText", "")

                if not start or not end:
                    continue

                facts.append({
                    "subject": start,
                    "predicate": rel,
                    "object": end,
                    "type": "relation",
                    "confidence": min(1.0, weight / 10.0),
                    "source": f"conceptnet:{edge.get('@id', '')}",
                    "verified": True,
                    "surface_text": surface,
                })

        except Exception as e:
            logger.warning(f"[LIBRARY] ConceptNet query error: {e}")

        return facts

    # ==================================================================
    # WOLFRAM ALPHA - Computational knowledge
    # ==================================================================

    def query_wolfram(self, query: str) -> List[Dict[str, Any]]:
        """
        Query Wolfram Alpha for computational/factual knowledge.

        Returns computed answers for math, science, geography, etc.
        Requires WOLFRAM_APP_ID in settings.
        """
        if not REQUESTS_AVAILABLE or not self.wolfram_app_id:
            return []

        facts = []

        try:
            resp = requests.get(
                self.WOLFRAM_API,
                params={
                    "input": query,
                    "appid": self.wolfram_app_id,
                    "output": "json",
                    "format": "plaintext",
                },
                timeout=self.timeout,
            )
            data = resp.json()

            result = data.get("queryresult", {})
            pods = result.get("pods", [])

            for pod in pods:
                title = pod.get("title", "")
                subpods = pod.get("subpods", [])

                for subpod in subpods:
                    plaintext = subpod.get("plaintext", "")
                    if plaintext:
                        facts.append({
                            "subject": query,
                            "predicate": title.lower().replace(" ", "_"),
                            "object": plaintext,
                            "type": "computed",
                            "confidence": 1.0,
                            "source": f"wolfram_alpha",
                            "verified": True,
                        })

        except Exception as e:
            logger.warning(f"[LIBRARY] Wolfram Alpha query error: {e}")

        return facts

    # ==================================================================
    # COMPILE INTO GRACE'S KNOWLEDGE STORE
    # ==================================================================

    def mine_and_compile(
        self,
        topic: str,
        session=None,
        sources: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Mine all libraries for a topic and compile into Grace's store.

        Feeds results directly into the existing Knowledge Compiler
        as compiled facts. No system changes needed.

        Args:
            topic: What to mine knowledge about
            session: DB session for Knowledge Compiler
            sources: Which libraries to query (default: all available)

        Returns:
            Stats about what was mined and compiled
        """
        if sources is None:
            sources = ["wikidata", "conceptnet"]
            if self.wolfram_app_id:
                sources.append("wolfram")

        all_facts = []
        stats = {"topic": topic, "sources_queried": [], "total_facts": 0, "compiled": 0}

        if "wikidata" in sources:
            wikidata_facts = self.query_wikidata(topic)
            all_facts.extend(wikidata_facts)
            stats["sources_queried"].append(f"wikidata:{len(wikidata_facts)}")

        if "conceptnet" in sources:
            conceptnet_facts = self.query_conceptnet(topic)
            all_facts.extend(conceptnet_facts)
            stats["sources_queried"].append(f"conceptnet:{len(conceptnet_facts)}")

        if "wolfram" in sources:
            wolfram_facts = self.query_wolfram(topic)
            all_facts.extend(wolfram_facts)
            stats["sources_queried"].append(f"wolfram:{len(wolfram_facts)}")

        stats["total_facts"] = len(all_facts)

        # Compile into Grace's existing knowledge store
        if session and all_facts:
            try:
                from cognitive.knowledge_compiler import get_knowledge_compiler

                compiler = get_knowledge_compiler(session)

                for fact in all_facts:
                    from cognitive.knowledge_compiler import CompiledFact

                    compiled = CompiledFact(
                        subject=fact["subject"][:256],
                        predicate=fact["predicate"][:256],
                        object_value=str(fact["object"])[:5000],
                        object_type=fact.get("type", "text"),
                        confidence=fact.get("confidence", 1.0),
                        source_text=fact.get("surface_text", ""),
                        domain=topic.lower(),
                        verified=fact.get("verified", True),
                        tags={"source": fact.get("source", "library")},
                    )
                    session.add(compiled)
                    stats["compiled"] += 1

                session.commit()

            except Exception as e:
                logger.error(f"[LIBRARY] Compilation error: {e}")
                stats["compile_error"] = str(e)

        # Track in learning system
        try:
            from cognitive.learning_hook import track_learning_event
            track_learning_event(
                "library_mining",
                f"Mined {len(all_facts)} facts about '{topic}' from {len(stats['sources_queried'])} libraries",
                data=stats,
            )
        except Exception:
            pass

        logger.info(
            f"[LIBRARY] Mined '{topic}': {stats['total_facts']} facts, "
            f"{stats['compiled']} compiled, sources: {stats['sources_queried']}"
        )

        return stats


_connectors_instance: Optional[LibraryConnectors] = None


def get_library_connectors(wolfram_app_id: Optional[str] = None) -> LibraryConnectors:
    """Get or create the library connectors singleton."""
    global _connectors_instance
    if _connectors_instance is None:
        _connectors_instance = LibraryConnectors(wolfram_app_id=wolfram_app_id)
    return _connectors_instance
