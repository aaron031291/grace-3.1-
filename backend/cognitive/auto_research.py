"""
Auto-Research Engine — Proactive knowledge expansion for domain folders.

When a user creates a new domain folder, Grace:
1. Reads the folder name and subfolder names
2. Reasons about what topics this domain covers
3. Offers to auto-ingest knowledge around those topics
4. Searches: web, APIs, knowledge base, Kimi reasoning
5. Pulls data into the folder automatically
6. Versions each research cycle (Research v1, v2, v3...)
7. Uses reverse KNN to predict what the user will need NEXT
8. Stays 5-7 steps ahead of the user's current knowledge
9. Kimi deepens and broadens the context each cycle
10. Librarian organises everything, genesis tracks it all

Connected to: Librarian, Ingestion, Kimi, Opus, Magma, Trust Engine,
Knowledge Cycle, Genesis Keys, TimeSense, Cognitive Partner
"""

import logging
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
from cognitive.event_bus import publish

logger = logging.getLogger(__name__)


def _get_kb():
    try:
        from settings import settings
        return Path(settings.KNOWLEDGE_BASE_PATH)
    except Exception:
        return Path("knowledge_base")


class AutoResearchEngine:
    """
    Proactive research engine that pre-empts user knowledge needs.
    """

    def __init__(self):
        self._research_history: List[Dict] = []

    def analyse_folder(self, folder_path: str) -> Dict[str, Any]:
        """
        Analyse a folder to understand what domain it represents.
        Read folder name, subfolders, existing files.
        Reason about what topics this covers.
        """
        kb = _get_kb()
        folder = kb / folder_path
        
        if not folder.exists():
            folder.mkdir(parents=True, exist_ok=True)

        # Read structure
        folder_name = folder.name
        subfolders = [d.name for d in folder.iterdir() if d.is_dir() and not d.name.startswith('.')]
        files = [f.name for f in folder.iterdir() if f.is_file() and not f.name.startswith('.')]

        # Existing content preview
        content_preview = ""
        for f in folder.iterdir():
            if f.is_file() and f.suffix in ('.txt', '.md', '.py', '.json'):
                try:
                    content_preview += f.read_text(errors="ignore")[:500] + "\n"
                except Exception:
                    pass

        analysis = {
            "folder_path": folder_path,
            "folder_name": folder_name,
            "subfolders": subfolders,
            "files": files,
            "file_count": len(files),
            "content_preview": content_preview[:1000],
        }

        # Ask Kimi to reason about the domain
        topics = self._reason_about_domain(folder_name, subfolders, files, content_preview)
        analysis["topics"] = topics
        analysis["suggested_research"] = topics.get("research_queries", [])

        # Genesis track
        try:
            from api._genesis_tracker import track
            track(key_type="system", what=f"Auto-research: analysed folder {folder_path}",
                  where=folder_path, output_data={"topics": len(topics.get("research_queries", []))},
                  tags=["auto_research", "analyse"])
        except Exception:
            pass
            
        publish("research.folder_analysed", data=analysis, source="auto_research")

        return analysis

    def _reason_about_domain(self, folder_name: str, subfolders: List[str], 
                              files: List[str], content: str) -> Dict:
        """Use Kimi to reason about what this domain folder needs."""
        try:
            from llm_orchestrator.kimi_enhanced import get_kimi_enhanced
            kimi = get_kimi_enhanced()
            
            response = kimi._call(
                f"A user created a knowledge folder called '{folder_name}'.\n"
                f"Subfolders: {subfolders}\n"
                f"Files: {files}\n"
                f"Content preview:\n{content[:500]}\n\n"
                f"Based on the folder name and structure, determine:\n"
                f"1. What domain/topic does this folder cover?\n"
                f"2. List 10 specific topics the user likely needs to learn about\n"
                f"3. List 5 search queries to find relevant content\n"
                f"4. What subfolders should be created for organisation?\n"
                f"5. What related domains should we also research?\n"
                f"Respond as JSON with keys: domain, topics, research_queries, suggested_subfolders, related_domains",
                system="You are a research strategist. Predict what knowledge a user needs based on their folder structure.",
                temperature=0.3, max_tokens=2000,
            )

            if response:
                try:
                    import json
                    return json.loads(response.strip().strip('```json').strip('```'))
                except Exception:
                    return {"domain": folder_name, "research_queries": [folder_name],
                            "topics": [folder_name], "raw": response[:500]}
        except Exception:
            pass

        return {"domain": folder_name, "research_queries": [folder_name], "topics": [folder_name]}

    def run_research_cycle(self, folder_path: str, depth: int = 1, 
                           max_queries: int = 10) -> Dict[str, Any]:
        """
        Run a full research cycle for a domain folder.
        Searches, ingests, versions, and expands.
        """
        start = time.time()
        kb = _get_kb()
        folder = kb / folder_path

        # Get or create analysis
        analysis = self.analyse_folder(folder_path)
        queries = analysis.get("suggested_research", [folder_path])[:max_queries]
        
        publish("research.cycle_started", data={"folder": folder_path, "queries_count": len(queries)}, source="auto_research")

        # Determine version
        existing_research = [d.name for d in folder.iterdir() if d.is_dir() and d.name.startswith("research_")]
        version = len(existing_research) + 1
        research_dir = folder / f"research_v{version}"
        research_dir.mkdir(parents=True, exist_ok=True)

        result = {
            "folder": folder_path,
            "version": f"v{version}",
            "research_dir": str(research_dir.relative_to(kb)),
            "queries": queries,
            "results": [],
            "files_created": 0,
        }

        for query in queries:
            # Search knowledge base first
            kb_results = self._search_knowledge_base(query)
            
            # Search via Kimi for deeper context
            kimi_results = self._search_kimi(query, analysis.get("topics", {}).get("domain", folder_path))

            # Combine and save
            content = ""
            if kb_results:
                content += f"## From Knowledge Base\n\n{kb_results}\n\n"
            if kimi_results:
                content += f"## Research\n\n{kimi_results}\n\n"

            if content:
                filename = query.lower().replace(" ", "_")[:40] + ".md"
                filepath = research_dir / filename
                filepath.write_text(content, encoding="utf-8")
                result["files_created"] += 1
                result["results"].append({"query": query, "file": filename, "length": len(content)})

                # Ingest into Magma
                try:
                    from cognitive.magma_bridge import ingest
                    ingest(content[:2000], source=f"auto_research_{folder_path}")
                except Exception:
                    pass

        # Reverse KNN — predict what user needs NEXT
        next_topics = self._predict_next_topics(analysis, result)
        result["predicted_next"] = next_topics

        # Store suggested subfolders
        for subfolder in analysis.get("topics", {}).get("suggested_subfolders", []):
            sf_path = folder / subfolder.lower().replace(" ", "_")
            if not sf_path.exists():
                sf_path.mkdir(parents=True, exist_ok=True)
                result.setdefault("subfolders_created", []).append(subfolder)

        result["duration_ms"] = round((time.time() - start) * 1000, 1)

        # Genesis track
        try:
            from api._genesis_tracker import track
            track(key_type="system",
                  what=f"Auto-research v{version}: {folder_path} ({result['files_created']} files)",
                  where=folder_path,
                  output_data={"version": version, "files": result["files_created"], 
                              "queries": len(queries), "predicted_next": len(next_topics)},
                  tags=["auto_research", "cycle", f"v{version}"])
        except Exception:
            pass

        # Store in Magma as procedure
        try:
            from cognitive.magma_bridge import store_procedure
            store_procedure(f"Research: {folder_path} v{version}",
                          f"Researched {len(queries)} topics, created {result['files_created']} files",
                          steps=queries[:5])
        except Exception:
            pass

        self._research_history.append(result)
        publish("research.cycle_completed", data=result, source="auto_research")
        return result

    def _search_knowledge_base(self, query: str) -> str:
        """Search existing knowledge base for relevant content."""
        try:
            from retrieval.retriever import DocumentRetriever
            from embedding.embedder import get_embedding_model
            from vector_db.client import get_qdrant_client
            retriever = DocumentRetriever(embedding_model=get_embedding_model(), qdrant_client=get_qdrant_client())
            chunks = retriever.retrieve(query=query, limit=3, score_threshold=0.4)
            if chunks:
                return "\n\n".join(c.get("text", "")[:500] for c in chunks)
        except Exception:
            pass
        return ""

    def _search_kimi(self, query: str, domain: str) -> str:
        """Use Kimi to research a topic in depth."""
        try:
            from llm_orchestrator.kimi_enhanced import get_kimi_enhanced
            kimi = get_kimi_enhanced()
            return kimi._call(
                f"Research this topic in depth for the domain '{domain}':\n\n{query}\n\n"
                f"Provide: key facts, practical applications, common patterns, "
                f"code examples if relevant, and connections to related concepts.",
                system="You are a research assistant building a knowledge base. Be comprehensive and practical.",
                temperature=0.3, max_tokens=2000,
            ) or ""
        except Exception:
            return ""

    def _predict_next_topics(self, analysis: Dict, results: Dict) -> List[str]:
        """Reverse KNN — predict what the user will need next."""
        try:
            from llm_orchestrator.kimi_enhanced import get_kimi_enhanced
            kimi = get_kimi_enhanced()

            current_topics = [r["query"] for r in results.get("results", [])]
            domain = analysis.get("topics", {}).get("domain", "")

            response = kimi._call(
                f"Domain: {domain}\n"
                f"Topics already researched: {current_topics}\n\n"
                f"Predict the next 5-7 topics the user will need but hasn't thought of yet.\n"
                f"Think several steps ahead — what would a domain expert research next?\n"
                f"List just the topic names, one per line.",
                system="You are predicting future knowledge needs. Think 5-7 steps ahead.",
                temperature=0.4, max_tokens=500,
            )

            if response:
                return [line.strip().lstrip("0123456789.-) ") for line in response.split("\n") 
                        if line.strip() and len(line.strip()) > 5][:7]
        except Exception:
            pass
        return []

    def get_history(self) -> List[Dict]:
        return self._research_history[-20:]


_engine = None

def get_auto_research() -> AutoResearchEngine:
    global _engine
    if _engine is None:
        _engine = AutoResearchEngine()
    return _engine
