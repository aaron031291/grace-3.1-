import os

# 1. hallucination_guard.py
file1 = r"c:\Users\aaron\Desktop\grace-3.1--Aaron-new2\backend\llm_orchestrator\hallucination_guard.py"
with open(file1, "r", encoding="utf-8") as f:
    c1 = f.read()

c1 = c1.replace(
    "from confidence_scorer.confidence_scorer import ConfidenceScorer\nfrom confidence_scorer.contradiction_detector import SemanticContradictionDetector",
    ""
)
c1 = c1.replace("confidence_scorer: Optional[ConfidenceScorer] = None", "confidence_scorer: Optional[Any] = None")
c1 = c1.replace("contradiction_detector: Optional[SemanticContradictionDetector] = None", "contradiction_detector: Optional[Any] = None")
c1 = c1.replace("self.contradiction_detector = contradiction_detector or SemanticContradictionDetector()", "self.contradiction_detector = contradiction_detector")

with open(file1, "w", encoding="utf-8") as f:
    f.write(c1)

# 2. llm_orchestrator.py
file2 = r"c:\Users\aaron\Desktop\grace-3.1--Aaron-new2\backend\llm_orchestrator\llm_orchestrator.py"
with open(file2, "r", encoding="utf-8") as f:
    c2 = f.read()

c2 = c2.replace("from confidence_scorer.confidence_scorer import ConfidenceScorer\n", "")
c2 = c2.replace(
    "            if hasattr(self, 'confidence_scorer') and hasattr(self.confidence_scorer, 'calculate_confidence_score'):\n",
    "            if False:\n"
)
c2 = c2.replace("self.confidence_scorer = ConfidenceScorer()", "self.confidence_scorer = None")

with open(file2, "w", encoding="utf-8") as f:
    f.write(c2)

# 3. ingestion/service.py
file3 = r"c:\Users\aaron\Desktop\grace-3.1--Aaron-new2\backend\ingestion\service.py"
with open(file3, "r", encoding="utf-8") as f:
    c3 = f.read()

c3 = c3.replace("from confidence_scorer import ConfidenceScorer\n", "")
c3 = c3.replace("self.confidence_scorer = ConfidenceScorer()", "self.confidence_scorer = None")

with open(file3, "w", encoding="utf-8") as f:
    f.write(c3)

print("Imports fixed.")
