"""
Reasoning Knowledge Ingestion for Grace

Converts math/reasoning datasets into retrievable knowledge patterns.
Grace doesn't reason - it RETRIEVES similar solved problems and adapts solutions.

Strategy:
1. Embed problem descriptions → store in Qdrant
2. Store complete solutions as payloads
3. On query: find similar problems → return solution patterns

This is knowledge distillation via RETRIEVAL, not reasoning.
"""

import json
import logging
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import Grace's existing infrastructure
try:
    from embedding import get_embedding_model
    from vector_db.client import get_qdrant_client
    GRACE_AVAILABLE = True
except ImportError:
    GRACE_AVAILABLE = False
    logger.warning("Grace backend not available - running in standalone mode")


@dataclass
class ReasoningPattern:
    """A reasoning pattern extracted from LLM training data."""
    
    id: str
    problem_type: str  # math, reasoning, code, etc.
    problem_text: str
    solution_text: str
    solution_steps: List[str]  # Chain of thought steps
    final_answer: str
    source_dataset: str
    difficulty: str  # easy, medium, hard
    tags: List[str]
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "problem_type": self.problem_type,
            "problem_text": self.problem_text,
            "solution_text": self.solution_text,
            "solution_steps": self.solution_steps,
            "final_answer": self.final_answer,
            "source_dataset": self.source_dataset,
            "difficulty": self.difficulty,
            "tags": self.tags,
        }


class ReasoningKnowledgeBase:
    """
    Stores reasoning patterns for retrieval-based problem solving.
    
    Instead of reasoning, Grace:
    1. Finds similar problems it has seen before
    2. Returns the solution pattern
    3. Adapts the pattern to the new problem
    """
    
    COLLECTION_NAME = "reasoning_patterns"
    
    def __init__(self, data_dir: str = "./data/oracle_knowledge"):
        self.data_dir = Path(data_dir)
        self.patterns: List[ReasoningPattern] = []
        
        if GRACE_AVAILABLE:
            self.embedding_model = get_embedding_model()
            self.qdrant = get_qdrant_client()
            self._ensure_collection()
        else:
            self.embedding_model = None
            self.qdrant = None
    
    def _ensure_collection(self):
        """Ensure Qdrant collection exists."""
        from qdrant_client.models import Distance, VectorParams
        
        collections = self.qdrant.get_collections().collections
        exists = any(c.name == self.COLLECTION_NAME for c in collections)
        
        if not exists:
            vector_size = self.embedding_model.get_embedding_dimension()
            self.qdrant.create_collection(
                collection_name=self.COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE,
                ),
            )
            logger.info(f"Created collection: {self.COLLECTION_NAME}")
    
    def _generate_id(self, text: str) -> str:
        """Generate unique ID from text."""
        return hashlib.md5(text.encode()).hexdigest()[:16]
    
    def extract_gsm8k_pattern(self, problem: Dict) -> ReasoningPattern:
        """Extract pattern from GSM8K format."""
        
        question = problem.get("question", "")
        answer = problem.get("answer", "")
        
        # GSM8K has step-by-step reasoning ending with #### answer
        steps = []
        final_answer = ""
        
        if "####" in answer:
            reasoning, final = answer.rsplit("####", 1)
            steps = [s.strip() for s in reasoning.split("\n") if s.strip()]
            final_answer = final.strip()
        else:
            steps = [answer]
            # Try to extract number
            numbers = re.findall(r'-?\d+\.?\d*', answer)
            final_answer = numbers[-1] if numbers else answer
        
        return ReasoningPattern(
            id=self._generate_id(question),
            problem_type="math",
            problem_text=question,
            solution_text=answer,
            solution_steps=steps,
            final_answer=final_answer,
            source_dataset="gsm8k",
            difficulty="grade_school",
            tags=["arithmetic", "word_problem"],
        )
    
    def extract_math_pattern(self, problem: Dict) -> ReasoningPattern:
        """Extract pattern from MATH dataset format."""
        
        question = problem.get("problem", "")
        solution = problem.get("solution", "")
        level = problem.get("level", "unknown")
        problem_type = problem.get("type", "algebra")
        
        # Extract boxed answer if present
        final_answer = ""
        match = re.search(r'\\boxed\{([^}]+)\}', solution)
        if match:
            final_answer = match.group(1)
        else:
            numbers = re.findall(r'-?\d+\.?\d*', solution)
            final_answer = numbers[-1] if numbers else ""
        
        # Split into steps
        steps = [s.strip() for s in solution.split("\n") if s.strip()]
        
        return ReasoningPattern(
            id=self._generate_id(question),
            problem_type="math",
            problem_text=question,
            solution_text=solution,
            solution_steps=steps,
            final_answer=final_answer,
            source_dataset="math",
            difficulty=level,
            tags=[problem_type, "competition"],
        )
    
    def extract_arc_pattern(self, problem: Dict) -> ReasoningPattern:
        """Extract pattern from ARC (science reasoning) format."""
        
        question = problem.get("question", "")
        choices = problem.get("choices", {})
        answer_key = problem.get("answerKey", "")
        
        # Format choices
        choice_text = choices.get("text", [])
        choice_labels = choices.get("label", [])
        
        formatted_choices = "\n".join(
            f"{label}. {text}" 
            for label, text in zip(choice_labels, choice_text)
        )
        
        # Find correct answer text
        correct_text = ""
        for label, text in zip(choice_labels, choice_text):
            if label == answer_key:
                correct_text = text
                break
        
        solution = f"The answer is {answer_key}: {correct_text}"
        
        return ReasoningPattern(
            id=self._generate_id(question),
            problem_type="reasoning",
            problem_text=f"{question}\n\n{formatted_choices}",
            solution_text=solution,
            solution_steps=[f"Evaluate each option", f"Select {answer_key}"],
            final_answer=answer_key,
            source_dataset="arc",
            difficulty="grade_school",
            tags=["science", "multiple_choice"],
        )
    
    def extract_code_pattern(self, problem: Dict) -> ReasoningPattern:
        """Extract pattern from HumanEval/code format."""
        
        prompt = problem.get("prompt", "")
        canonical = problem.get("canonical_solution", "")
        task_id = problem.get("task_id", "")
        
        return ReasoningPattern(
            id=self._generate_id(prompt),
            problem_type="code",
            problem_text=prompt,
            solution_text=canonical,
            solution_steps=[canonical],  # Code is the solution
            final_answer=canonical,
            source_dataset="humaneval",
            difficulty="medium",
            tags=["python", "function", task_id.split("/")[0] if "/" in task_id else "general"],
        )
    
    def extract_cot_pattern(self, example: Dict) -> ReasoningPattern:
        """Extract pattern from Chain-of-Thought data."""
        
        # COT datasets vary in format
        question = example.get("question", example.get("input", example.get("prompt", "")))
        answer = example.get("answer", example.get("output", example.get("response", "")))
        rationale = example.get("rationale", example.get("chain_of_thought", ""))
        
        if rationale:
            steps = [s.strip() for s in rationale.split("\n") if s.strip()]
        else:
            steps = [answer]
        
        return ReasoningPattern(
            id=self._generate_id(question),
            problem_type="reasoning",
            problem_text=question,
            solution_text=answer,
            solution_steps=steps,
            final_answer=answer.split()[-1] if answer else "",
            source_dataset="cot_collection",
            difficulty="mixed",
            tags=["chain_of_thought"],
        )
    
    def ingest_dataset(self, dataset_name: str, max_samples: int = 10000) -> int:
        """
        Ingest a dataset into the knowledge base.
        
        Args:
            dataset_name: Name of dataset (gsm8k, math, arc, humaneval, etc.)
            max_samples: Maximum samples to ingest
            
        Returns:
            Number of patterns ingested
        """
        
        # Find dataset file
        dataset_path = None
        for category in ["math", "reasoning", "code", "chain_of_thought"]:
            path = self.data_dir / category / dataset_name / "train.json"
            if path.exists():
                dataset_path = path
                break
            path = self.data_dir / category / dataset_name / "test.json"
            if path.exists():
                dataset_path = path
                break
        
        # Try benchmarks directory
        if dataset_path is None:
            path = self.data_dir / "benchmarks" / f"{dataset_name}_benchmark.json"
            if path.exists():
                dataset_path = path
        
        if dataset_path is None:
            logger.error(f"Dataset not found: {dataset_name}")
            logger.error(f"Run: python scripts/download_reasoning_datasets.py --benchmarks")
            return 0
        
        logger.info(f"Loading dataset from: {dataset_path}")
        
        with open(dataset_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Handle benchmark format
        if "problems" in data:
            problems = data["problems"]
        else:
            problems = data
        
        # Select extractor based on dataset
        extractors = {
            "gsm8k": self.extract_gsm8k_pattern,
            "math": self.extract_math_pattern,
            "arc": self.extract_arc_pattern,
            "humaneval": self.extract_code_pattern,
            "mbpp": self.extract_code_pattern,
            "cot_collection": self.extract_cot_pattern,
            "metamath": self.extract_gsm8k_pattern,  # Similar format
            "orca_math": self.extract_gsm8k_pattern,
        }
        
        extractor = extractors.get(dataset_name, self.extract_cot_pattern)
        
        # Extract patterns
        patterns = []
        for i, problem in enumerate(problems[:max_samples]):
            try:
                pattern = extractor(problem)
                patterns.append(pattern)
            except Exception as e:
                logger.warning(f"Failed to extract pattern {i}: {e}")
        
        logger.info(f"Extracted {len(patterns)} patterns from {dataset_name}")
        
        # Store in vector database
        if GRACE_AVAILABLE and patterns:
            self._store_patterns(patterns)
        
        self.patterns.extend(patterns)
        return len(patterns)
    
    def _store_patterns(self, patterns: List[ReasoningPattern], batch_size: int = 100):
        """Store patterns in Qdrant."""
        from qdrant_client.models import PointStruct
        
        logger.info(f"Embedding and storing {len(patterns)} patterns...")
        
        for i in range(0, len(patterns), batch_size):
            batch = patterns[i:i + batch_size]
            
            # Embed problem texts
            texts = [p.problem_text for p in batch]
            embeddings = self.embedding_model.embed_text(texts, convert_to_numpy=True)
            
            # Create points
            points = []
            for j, (pattern, embedding) in enumerate(zip(batch, embeddings)):
                point = PointStruct(
                    id=hash(pattern.id) % (2**63),  # Convert to int
                    vector=embedding.tolist(),
                    payload=pattern.to_dict(),
                )
                points.append(point)
            
            # Upsert to Qdrant
            self.qdrant.upsert(
                collection_name=self.COLLECTION_NAME,
                points=points,
            )
            
            logger.info(f"  Stored batch {i//batch_size + 1}/{(len(patterns)-1)//batch_size + 1}")
        
        logger.info(f"✓ Stored {len(patterns)} patterns in Qdrant")
    
    def find_similar_problems(
        self, 
        query: str, 
        top_k: int = 5,
        problem_type: Optional[str] = None,
    ) -> List[Tuple[ReasoningPattern, float]]:
        """
        Find similar problems to a query.
        
        This is how Grace "reasons" - by finding similar solved problems.
        
        Args:
            query: The problem to solve
            top_k: Number of similar problems to retrieve
            problem_type: Filter by type (math, reasoning, code)
            
        Returns:
            List of (pattern, similarity_score) tuples
        """
        
        if not GRACE_AVAILABLE:
            logger.warning("Grace not available - using in-memory patterns")
            return self._find_similar_local(query, top_k, problem_type)
        
        # Embed query
        query_embedding = self.embedding_model.embed_text(query, convert_to_numpy=True)
        
        # Build filter
        search_filter = None
        if problem_type:
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            search_filter = Filter(
                must=[
                    FieldCondition(
                        key="problem_type",
                        match=MatchValue(value=problem_type),
                    )
                ]
            )
        
        # Search
        results = self.qdrant.search(
            collection_name=self.COLLECTION_NAME,
            query_vector=query_embedding.tolist(),
            limit=top_k,
            query_filter=search_filter,
        )
        
        # Convert to patterns
        patterns = []
        for result in results:
            payload = result.payload
            pattern = ReasoningPattern(
                id=payload["id"],
                problem_type=payload["problem_type"],
                problem_text=payload["problem_text"],
                solution_text=payload["solution_text"],
                solution_steps=payload["solution_steps"],
                final_answer=payload["final_answer"],
                source_dataset=payload["source_dataset"],
                difficulty=payload["difficulty"],
                tags=payload["tags"],
            )
            patterns.append((pattern, result.score))
        
        return patterns
    
    def _find_similar_local(
        self, 
        query: str, 
        top_k: int, 
        problem_type: Optional[str],
    ) -> List[Tuple[ReasoningPattern, float]]:
        """Fallback: find similar using simple text matching."""
        
        query_words = set(query.lower().split())
        
        scores = []
        for pattern in self.patterns:
            if problem_type and pattern.problem_type != problem_type:
                continue
            
            pattern_words = set(pattern.problem_text.lower().split())
            overlap = len(query_words & pattern_words)
            score = overlap / max(len(query_words), 1)
            scores.append((pattern, score))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]
    
    def solve_by_retrieval(self, problem: str, problem_type: str = None) -> Dict[str, Any]:
        """
        Solve a problem using retrieval-based reasoning.
        
        This is Grace's approach: find similar solved problems and adapt.
        
        Args:
            problem: The problem to solve
            problem_type: Optional type hint (math, reasoning, code)
            
        Returns:
            Dict with solution, similar problems, and confidence
        """
        
        similar = self.find_similar_problems(problem, top_k=3, problem_type=problem_type)
        
        if not similar:
            return {
                "solved": False,
                "message": "No similar problems found in knowledge base",
                "suggestion": "Run: python scripts/download_reasoning_datasets.py --benchmarks",
            }
        
        best_match, confidence = similar[0]
        
        return {
            "solved": True,
            "confidence": confidence,
            "solution_pattern": best_match.solution_text,
            "solution_steps": best_match.solution_steps,
            "predicted_answer": best_match.final_answer,
            "similar_problems": [
                {
                    "problem": p.problem_text[:200] + "...",
                    "answer": p.final_answer,
                    "similarity": s,
                    "source": p.source_dataset,
                }
                for p, s in similar
            ],
            "note": "Solution adapted from similar problem in knowledge base",
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        
        stats = {
            "in_memory_patterns": len(self.patterns),
            "grace_available": GRACE_AVAILABLE,
        }
        
        if GRACE_AVAILABLE:
            try:
                info = self.qdrant.get_collection(self.COLLECTION_NAME)
                stats["qdrant_vectors"] = info.points_count
                stats["qdrant_indexed"] = info.indexed_vectors_count
            except:
                stats["qdrant_vectors"] = 0
        
        return stats


def ingest_all_datasets(max_per_dataset: int = 5000):
    """Ingest all downloaded datasets into knowledge base."""
    
    kb = ReasoningKnowledgeBase()
    
    datasets = ["gsm8k", "math", "arc", "humaneval"]
    
    total = 0
    for dataset in datasets:
        try:
            count = kb.ingest_dataset(dataset, max_samples=max_per_dataset)
            total += count
            logger.info(f"✓ {dataset}: {count} patterns")
        except Exception as e:
            logger.warning(f"✗ {dataset}: {e}")
    
    logger.info(f"\nTotal patterns ingested: {total}")
    return kb


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Reasoning knowledge ingestion")
    parser.add_argument("--ingest", type=str, help="Ingest specific dataset")
    parser.add_argument("--ingest-all", action="store_true", help="Ingest all datasets")
    parser.add_argument("--max", type=int, default=5000, help="Max patterns per dataset")
    parser.add_argument("--query", type=str, help="Test query")
    parser.add_argument("--stats", action="store_true", help="Show stats")
    
    args = parser.parse_args()
    
    kb = ReasoningKnowledgeBase()
    
    if args.ingest:
        count = kb.ingest_dataset(args.ingest, max_samples=args.max)
        print(f"Ingested {count} patterns from {args.ingest}")
    
    elif args.ingest_all:
        ingest_all_datasets(args.max)
    
    elif args.query:
        result = kb.solve_by_retrieval(args.query)
        print(json.dumps(result, indent=2))
    
    elif args.stats:
        stats = kb.get_stats()
        print(json.dumps(stats, indent=2))
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
