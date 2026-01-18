"""
GRACE REASONING ENGINE

LLM reasons → Oracle/APIs/Web/Compute verify → Verified answer
"""

import re
import json
import logging
import requests
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ReasoningResult:
    question: str
    answer: Any
    confidence: float
    verified: bool
    reasoning: str
    verifications: List[Dict]
    
    def to_dict(self) -> Dict:
        return self.__dict__


class ReasoningEngine:
    """LLM + Oracle + APIs + Web + Compute verification."""
    
    def __init__(self, model: str = "mistral:7b"):
        self.model = model
        self.ollama_url = "http://localhost:11434"
        self._init_sources()
    
    def _init_sources(self):
        """Initialize all verification sources."""
        
        # Cognitive (math/compute)
        try:
            from cognitive_engine import CognitiveEngine
            self.cognitive = CognitiveEngine()
        except:
            self.cognitive = None
        
        # Oracle (knowledge base)
        try:
            from reasoning_knowledge import ReasoningKnowledgeBase
            self.oracle = ReasoningKnowledgeBase()
        except:
            self.oracle = None
        
        # LLM availability
        try:
            self.has_llm = requests.get(f"{self.ollama_url}/api/tags", timeout=2).ok
        except:
            self.has_llm = False
        
        logger.info(f"Sources: LLM={self.has_llm}, Cognitive={self.cognitive is not None}, Oracle={self.oracle is not None}")
    
    def reason(self, question: str) -> ReasoningResult:
        """
        Main entry: Ask LLM, verify with all sources.
        """
        
        verifications = []
        llm_answer = None
        llm_reasoning = ""
        
        # Step 1: Ask LLM (always try for reasoning)
        if self.has_llm:
            llm_answer, llm_reasoning = self._ask_llm(question)
            if llm_answer is not None:
                verifications.append({"source": "llm", "answer": llm_answer, "confidence": 0.6})
            elif llm_reasoning:
                # For text answers (not numeric), extract from reasoning
                llm_answer = llm_reasoning[:200]
                verifications.append({"source": "llm", "answer": llm_answer, "confidence": 0.5})
        
        # Step 2: Verify with Cognitive (compute)
        if self.cognitive:
            result = self.cognitive.solve(question)
            if result.get("solved"):
                verifications.append({
                    "source": "cognitive",
                    "answer": result["answer"],
                    "confidence": result["confidence"],
                    "method": result["method"]
                })
        
        # Step 3: Verify with Oracle
        if self.oracle:
            try:
                result = self.oracle.solve_by_retrieval(question)
                if result.get("solved"):
                    verifications.append({
                        "source": "oracle",
                        "answer": result["predicted_answer"],
                        "confidence": result["confidence"]
                    })
            except:
                pass
        
        # Step 4: Verify with APIs (Wikipedia for factual)
        if self._is_factual(question):
            api_result = self._check_wikipedia(question)
            if api_result:
                verifications.append(api_result)
        
        # Step 5: Determine best answer
        answer, confidence, verified = self._determine_answer(verifications)
        
        return ReasoningResult(
            question=question,
            answer=answer or llm_answer,
            confidence=confidence,
            verified=verified,
            reasoning=llm_reasoning,
            verifications=verifications
        )
    
    def _ask_llm(self, question: str) -> tuple:
        """Ask Ollama LLM."""
        
        try:
            resp = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": f"Solve step by step, give final answer:\n\n{question}",
                    "stream": False
                },
                timeout=60
            )
            
            if resp.ok:
                text = resp.json().get("response", "")
                answer = self._extract_answer(text)
                return answer, text
        except Exception as e:
            logger.warning(f"LLM error: {e}")
        
        return None, ""
    
    def _extract_answer(self, text: str) -> Any:
        """Extract answer from LLM response."""
        
        # Try common patterns for numeric
        patterns = [
            r'(?:answer|result)\s*(?:is|=|:)\s*(\d+\.?\d*)',
            r'=\s*(\d+\.?\d*)\s*$',
            r'(\d+\.?\d*)\s*(?:is the answer|total)',
        ]
        
        for p in patterns:
            m = re.search(p, text.lower())
            if m:
                try:
                    return float(m.group(1))
                except:
                    pass
        
        # Try text answer patterns (for factual questions)
        text_patterns = [
            r'(?:capital|answer|is)\s*(?:is|:)?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
            r'([A-Z][a-z]+)\s+is\s+the\s+capital',
        ]
        
        for p in text_patterns:
            m = re.search(p, text)
            if m:
                return m.group(1).strip()
        
        # Last number for numeric
        nums = re.findall(r'-?\d+\.?\d*', text)
        if nums:
            try:
                return float(nums[-1])
            except:
                pass
        
        return None
    
    def _is_factual(self, q: str) -> bool:
        """Check if factual question."""
        return bool(re.search(r'\b(who|what|when|where|capital|president)\b', q.lower()))
    
    def _check_wikipedia(self, question: str) -> Optional[Dict]:
        """Check Wikipedia API."""
        
        words = [w for w in question.split() if len(w) > 3 and w.lower() not in 
                 {'what', 'where', 'when', 'which', 'that', 'this', 'from', 'with'}]
        
        if not words:
            return None
        
        try:
            term = "_".join(words[:2])
            resp = requests.get(
                f"https://en.wikipedia.org/api/rest_v1/page/summary/{term}",
                timeout=5
            )
            if resp.ok:
                data = resp.json()
                return {
                    "source": "wikipedia",
                    "answer": data.get("extract", "")[:200],
                    "confidence": 0.8,
                    "url": data.get("content_urls", {}).get("desktop", {}).get("page")
                }
        except:
            pass
        
        return None
    
    def _determine_answer(self, verifications: List[Dict]) -> tuple:
        """Determine best answer from all sources."""
        
        if not verifications:
            return None, 0.0, False
        
        # Priority: cognitive > oracle > api > llm
        priority = {"cognitive": 4, "oracle": 3, "wikipedia": 2, "llm": 1}
        
        # Sort by priority then confidence
        sorted_v = sorted(
            verifications,
            key=lambda x: (priority.get(x["source"], 0), x.get("confidence", 0)),
            reverse=True
        )
        
        best = sorted_v[0]
        answer = best["answer"]
        confidence = best.get("confidence", 0.5)
        
        # Check if sources agree
        agreements = sum(1 for v in verifications if self._answers_match(v["answer"], answer))
        
        # Verified if cognitive confirms OR multiple sources agree
        verified = (best["source"] == "cognitive") or (agreements >= 2)
        
        # Boost confidence for agreement
        if agreements >= 2:
            confidence = min(1.0, confidence + 0.15)
        
        return answer, confidence, verified
    
    def _answers_match(self, a: Any, b: Any) -> bool:
        """Check if answers match."""
        try:
            return abs(float(a) - float(b)) < 0.01
        except:
            return str(a)[:50].lower() == str(b)[:50].lower()


# =============================================================================
# CONVENIENCE API
# =============================================================================

_engine = None

def get_engine() -> ReasoningEngine:
    global _engine
    if _engine is None:
        _engine = ReasoningEngine()
    return _engine


def reason(question: str) -> Dict:
    """Reason about a question with verification."""
    return get_engine().reason(question).to_dict()


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    engine = ReasoningEngine()
    
    tests = [
        "John has 5 apples. He buys 3 more. How many?",
        "What is 15% of 80?",
        "Solve for x: 2x + 5 = 15",
        "What is the capital of France?",
        "12 boxes with 8 items each. Total?",
    ]
    
    print("\n" + "="*60)
    print("GRACE REASONING ENGINE")
    print("="*60)
    
    for q in tests:
        result = engine.reason(q)
        v = "[OK]" if result.verified else "[?]"
        print(f"\n{v} Q: {q}")
        print(f"    A: {result.answer} (confidence: {result.confidence:.0%})")
        print(f"    Sources: {[s['source'] for s in result.verifications]}")
