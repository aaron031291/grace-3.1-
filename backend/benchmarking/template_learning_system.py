"""
Template Learning System - Proactive Template Discovery

Automatically learns new templates from MBPP evaluation failures by:
1. Analyzing failed problems to identify patterns
2. Extracting common code patterns from test cases
3. Generating new template candidates
4. Validating templates against similar problems
"""

import json
import re
from typing import Dict, Any, List, Optional, Tuple
from collections import Counter, defaultdict
from pathlib import Path
from dataclasses import dataclass
import ast
import difflib
import numpy as np


@dataclass
class FailurePattern:
    """Pattern extracted from failed problems."""
    problem_text: str
    test_cases: List[str]
    error_type: str
    error_message: str
    function_name: str
    keywords: List[str]
    test_patterns: List[str]
    frequency: int = 1


class TemplateLearningSystem:
    """Learn new templates from evaluation failures."""
    
    def __init__(self, results_file: str = "full_mbpp_results.json", use_embedding_clustering: bool = True):
        self.results_file = Path(results_file)
        self.failure_patterns: List[FailurePattern] = []
        self.template_candidates: List[Dict[str, Any]] = []
        self.use_embedding_clustering = use_embedding_clustering
        self._embedder = None
        # REVERSED KNN: Use embeddings for better failure clustering without storing them
    
    @property
    def embedder(self):
        """Lazy load embedder for semantic similarity."""
        if self._embedder is None and self.use_embedding_clustering:
            try:
                from backend.embedding import get_embedding_model
                self._embedder = get_embedding_model()
            except Exception as e:
                print(f"[TEMPLATE-LEARNING] Embedder not available, using keyword clustering: {e}")
                self.use_embedding_clustering = False
        return self._embedder
        
    def analyze_failures(self) -> List[FailurePattern]:
        """Analyze failed problems to extract patterns."""
        if not self.results_file.exists():
            print(f"[TEMPLATE-LEARNING] Results file not found: {self.results_file}")
            return []
        
        with open(self.results_file) as f:
            data = json.load(f)
        
        results = data.get("results", {}).get("results", [])
        failures = [r for r in results if not r.get("passed", False)]
        
        print(f"[TEMPLATE-LEARNING] Analyzing {len(failures)} failures...")
        
        patterns = []
        pattern_groups = defaultdict(list)
        
        for failure in failures:
            problem_text = failure.get("problem_text", "")
            test_cases = failure.get("test_cases", [])
            error = failure.get("error", "")
            function_name = self._extract_function_name(test_cases)
            
            # Extract keywords from problem text
            keywords = self._extract_keywords(problem_text)
            
            # Extract test patterns
            test_patterns = self._extract_test_patterns(test_cases)
            
            # REVERSED KNN: Use embedding-based clustering if available
        if self.use_embedding_clustering and self.embedder:
            # Cluster failures using embeddings (computed on-demand)
            pattern_groups = self._cluster_failures_with_embeddings(failures)
        else:
            # Fallback to keyword-based grouping
            for failure in failures:
                problem_text = failure.get("problem_text", "")
                test_cases = failure.get("test_cases", [])
                error = failure.get("error", "")
                function_name = self._extract_function_name(test_cases)
                keywords = self._extract_keywords(problem_text)
                test_patterns = self._extract_test_patterns(test_cases)
                pattern_key = self._create_pattern_key(keywords, test_patterns)
                pattern_groups[pattern_key].append({
                    "problem_text": problem_text,
                    "test_cases": test_cases,
                    "error": error,
                    "function_name": function_name,
                    "keywords": keywords,
                    "test_patterns": test_patterns
                })
        
        # Create patterns from groups
        for pattern_key, group in pattern_groups.items():
            if len(group) >= 1:  # Lower threshold - even single failures can be patterns
                representative = group[0]
                pattern = FailurePattern(
                    problem_text=representative["problem_text"],
                    test_cases=representative["test_cases"],
                    error_type=self._classify_error(representative["error"]),
                    error_message=representative["error"],
                    function_name=representative["function_name"],
                    keywords=list(set(kw for item in group for kw in item["keywords"])),
                    test_patterns=list(set(tp for item in group for tp in item["test_patterns"])),
                    frequency=len(group)
                )
                patterns.append(pattern)
        
        self.failure_patterns = patterns
        print(f"[TEMPLATE-LEARNING] Identified {len(patterns)} failure patterns")
        return patterns
    
    def _cluster_failures_with_embeddings(self, failures: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        REVERSED KNN: Cluster failures using embeddings computed on-demand.
        
        Instead of storing failure embeddings, we:
        1. Generate embeddings for all failures on-the-fly
        2. Cluster by similarity
        3. Group similar failures together
        
        Returns grouped failures dictionary.
        """
        if not self.embedder:
            return defaultdict(list)
        
        print(f"[TEMPLATE-LEARNING] Using embedding-based clustering for {len(failures)} failures...")
        
        # Build failure texts (on-demand, no storage)
        failure_texts = []
        failure_data = []
        
        for failure in failures:
            problem_text = failure.get("problem_text", "")
            test_cases = failure.get("test_cases", [])
            test_text = " ".join(test_cases) if test_cases else ""
            
            # Combine problem and test cases for embedding
            failure_text = f"{problem_text} {test_text}"
            failure_texts.append(failure_text)
            
            # Store metadata
            function_name = self._extract_function_name(test_cases)
            keywords = self._extract_keywords(problem_text)
            test_patterns = self._extract_test_patterns(test_cases)
            
            failure_data.append({
                "problem_text": problem_text,
                "test_cases": test_cases,
                "error": failure.get("error", ""),
                "function_name": function_name,
                "keywords": keywords,
                "test_patterns": test_patterns
            })
        
        # Generate embeddings for all failures (batch for efficiency)
        try:
            failure_embeddings = self.embedder.embed_text(
                failure_texts,
                convert_to_numpy=True,
                batch_size=min(16, len(failure_texts))
            )
            
            # Cluster by cosine similarity
            from sklearn.metrics.pairwise import cosine_similarity
            similarity_matrix = cosine_similarity(failure_embeddings)
            
            # Group failures by similarity threshold
            pattern_groups = defaultdict(list)
            used_indices = set()
            cluster_id = 0
            
            for i in range(len(failures)):
                if i in used_indices:
                    continue
                
                # Find all similar failures
                similar_indices = [i]
                for j in range(i + 1, len(failures)):
                    if j not in used_indices and similarity_matrix[i][j] > 0.7:  # 70% similarity threshold
                        similar_indices.append(j)
                        used_indices.add(j)
                
                # Create cluster key
                cluster_key = f"cluster_{cluster_id}"
                cluster_id += 1
                
                # Add all similar failures to this cluster
                for idx in similar_indices:
                    pattern_groups[cluster_key].append(failure_data[idx])
                    used_indices.add(idx)
            
            print(f"[TEMPLATE-LEARNING] Created {len(pattern_groups)} failure clusters using embeddings")
            return pattern_groups
            
        except Exception as e:
            print(f"[TEMPLATE-LEARNING] Embedding clustering failed, using keyword clustering: {e}")
            # Fallback to keyword-based clustering
            pattern_groups = defaultdict(list)
            for i, failure in enumerate(failures):
                problem_text = failure.get("problem_text", "")
                test_cases = failure.get("test_cases", [])
                function_name = self._extract_function_name(test_cases)
                keywords = self._extract_keywords(problem_text)
                test_patterns = self._extract_test_patterns(test_cases)
                pattern_key = self._create_pattern_key(keywords, test_patterns)
                pattern_groups[pattern_key].append({
                    "problem_text": problem_text,
                    "test_cases": test_cases,
                    "error": failure.get("error", ""),
                    "function_name": function_name,
                    "keywords": keywords,
                    "test_patterns": test_patterns
                })
            return pattern_groups
    
    def generate_template_candidates(self) -> List[Dict[str, Any]]:
        """Generate template candidates from failure patterns using REVERSED KNN."""
        if not self.failure_patterns:
            self.analyze_failures()
        
        candidates = []
        
        # REVERSED KNN: Use embedding similarity to find best template matches for failures
        if self.use_embedding_clustering and self.embedder:
            embedding_candidates = self._generate_candidates_with_embeddings()
            candidates.extend(embedding_candidates)
            print(f"[TEMPLATE-LEARNING] Generated {len(embedding_candidates)} candidates using reversed KNN")
        
        # Also generate candidates from keyword-based patterns
        for pattern in self.failure_patterns:
            # Lower threshold - even single failures can be useful if they have good keywords
            if pattern.frequency < 1 or not pattern.keywords:
                continue
            
            # Try to infer code from test cases
            inferred_code = self._infer_code_from_tests(pattern)
            
            if inferred_code:
                candidate = {
                    "name": self._generate_template_name(pattern),
                    "pattern_keywords": pattern.keywords[:10],  # Top 10 keywords
                    "pattern_regex": self._generate_regex(pattern),
                    "template_code": inferred_code,
                    "description": f"Auto-learned from {pattern.frequency} similar failure(s)",
                    "examples": pattern.test_patterns[:3] if pattern.test_patterns else [],
                    "confidence": min(0.9, 0.3 + (pattern.frequency / 20.0)),  # Higher frequency = higher confidence
                    "source": "proactive_learning",
                    "frequency": pattern.frequency
                }
                candidates.append(candidate)
        
        self.template_candidates = candidates
        print(f"[TEMPLATE-LEARNING] Generated {len(candidates)} template candidates")
        return candidates
    
    def _generate_candidates_with_embeddings(self) -> List[Dict[str, Any]]:
        """
        REVERSED KNN: Generate template candidates by finding similar failures
        and matching them to existing templates or creating new ones.
        """
        if not self.embedder or not self.failure_patterns:
            return []
        
        print(f"[TEMPLATE-LEARNING] Generating candidates using reversed KNN...")
        
        # Load existing templates to compare against
        try:
            from backend.benchmarking.mbpp_templates import TEMPLATES
            existing_templates = TEMPLATES
        except:
            existing_templates = []
        
        candidates = []
        
        # For each failure pattern, find similar existing templates
        for pattern in self.failure_patterns:
            # Build query text from failure
            query_text = f"{pattern.problem_text} {' '.join(pattern.test_cases)}"
            
            # Generate query embedding (on-the-fly)
            try:
                query_embedding = self.embedder.embed_text(query_text, convert_to_numpy=True)
                if len(query_embedding.shape) == 1:
                    query_embedding = query_embedding.reshape(1, -1)
            except:
                continue
            
            # Build template texts for comparison (on-demand)
            template_texts = []
            for template in existing_templates:
                template_text = f"{template.name} {template.description} {' '.join(template.pattern_keywords)}"
                template_texts.append(template_text)
            
            # Find best matching existing template
            best_match_idx = None
            best_similarity = 0.0
            
            if template_texts:
                try:
                    template_embeddings = self.embedder.embed_text(
                        template_texts,
                        convert_to_numpy=True,
                        batch_size=min(16, len(template_texts))
                    )
                    
                    from sklearn.metrics.pairwise import cosine_similarity
                    similarities = cosine_similarity(query_embedding, template_embeddings)[0]
                    best_match_idx = np.argmax(similarities)
                    best_similarity = float(similarities[best_match_idx])
                except:
                    pass
            
            # If no good match found (similarity < 0.6), create new template candidate
            if best_similarity < 0.6:
                template_code = self._infer_code_from_tests(pattern)
                if template_code:
                    # Generate regex pattern from keywords
                    regex_pattern = "|".join(pattern.keywords[:5]) if pattern.keywords else ""
                    
                    candidate = {
                        "name": f"auto_{pattern.function_name}_{pattern.frequency}",
                        "pattern_keywords": pattern.keywords[:15],
                        "pattern_regex": regex_pattern,
                        "template_code": template_code,
                        "description": f"Auto-learned from {pattern.frequency} similar failure(s)",
                        "examples": pattern.test_patterns[:3],
                        "confidence": min(0.9, 0.3 + (pattern.frequency / 20.0)),
                        "source": "reversed_knn_embedding",
                        "frequency": pattern.frequency
                    }
                    candidates.append(candidate)
                    print(f"[TEMPLATE-LEARNING] Generated candidate: {candidate['name']} (confidence: {candidate['confidence']:.1%})")
            else:
                # Found similar template - could improve it or note the match
                matched_template = existing_templates[best_match_idx]
                print(f"[TEMPLATE-LEARNING] Failure pattern matches existing template '{matched_template.name}' (similarity: {best_similarity:.2f})")
        
        return candidates
    
    def _extract_function_name(self, test_cases: List[str]) -> str:
        """Extract function name from test cases."""
        for test in test_cases:
            match = re.search(r'(\w+)\s*\(', test)
            if match:
                return match.group(1)
        return "unknown_function"
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from problem text (ENHANCED)."""
        # Expanded programming keywords with priority weighting
        high_priority_keywords = [
            "find", "count", "sum", "sort", "filter", "remove", "check", "get",
            "maximum", "minimum", "largest", "smallest", "first", "last",
            "duplicate", "unique", "reverse", "palindrome", "prime", "even", "odd",
            "frequency", "occurrence", "convert", "transform"
        ]
        
        medium_priority_keywords = [
            "list", "string", "number", "array", "tuple", "dictionary", "set",
            "divide", "multiply", "add", "subtract", "power", "factorial",
            "fibonacci", "gcd", "lcm", "merge", "split", "join", "combine"
        ]
        
        text_lower = text.lower()
        found_keywords = []
        
        # Add high priority keywords first
        found_keywords.extend([kw for kw in high_priority_keywords if kw in text_lower])
        
        # Add medium priority keywords
        found_keywords.extend([kw for kw in medium_priority_keywords if kw in text_lower])
        
        # Extract meaningful words (nouns, verbs, adjectives)
        words = re.findall(r'\b\w+\b', text_lower)
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been", 
                     "have", "has", "had", "do", "does", "did", "will", "would",
                     "should", "could", "can", "may", "might", "to", "from", "of",
                     "in", "on", "at", "for", "with", "by", "as", "if", "and", "or",
                     "function", "python", "write", "given", "should", "name"}
        meaningful_words = [w for w in words if w not in stop_words and len(w) > 2]
        
        # Count frequency and prioritize longer, more specific words
        word_freq = Counter(meaningful_words)
        # Weight by length and frequency
        scored_words = [(word, count * (1 + len(word) * 0.1)) 
                       for word, count in word_freq.items()]
        scored_words.sort(key=lambda x: x[1], reverse=True)
        top_words = [word for word, score in scored_words[:8]]
        
        # Combine and deduplicate, preserving order (high priority first)
        all_keywords = found_keywords + top_words
        seen = set()
        result = []
        for kw in all_keywords:
            if kw not in seen:
                seen.add(kw)
                result.append(kw)
        
        return result[:15]  # Limit to top 15 keywords
    
    def _extract_test_patterns(self, test_cases: List[str]) -> List[str]:
        """Extract patterns from test cases."""
        patterns = []
        for test in test_cases:
            # Extract function call pattern
            func_match = re.search(r'(\w+)\s*\(([^)]*)\)', test)
            if func_match:
                func_name = func_match.group(1)
                args = func_match.group(2)
                # Count arguments
                arg_count = len([a for a in args.split(',') if a.strip()])
                patterns.append(f"{func_name}({arg_count}_args)")
            
            # Extract assertion patterns
            if "assert" in test.lower():
                patterns.append("assertion_test")
            if "==" in test:
                patterns.append("equality_check")
            if "in" in test.lower():
                patterns.append("membership_check")
        
        return list(set(patterns))
    
    def _create_pattern_key(self, keywords: List[str], test_patterns: List[str]) -> str:
        """Create a key to group similar patterns."""
        # Use top 3 keywords + test pattern signature
        key_parts = sorted(keywords[:3]) + sorted(test_patterns[:2])
        return "_".join(key_parts)
    
    def _classify_error(self, error: str) -> str:
        """Classify error type."""
        error_lower = error.lower()
        if "assertion" in error_lower or "assert" in error_lower:
            return "assertion_error"
        elif "nameerror" in error_lower:
            return "name_error"
        elif "typeerror" in error_lower:
            return "type_error"
        elif "syntaxerror" in error_lower:
            return "syntax_error"
        elif "indentation" in error_lower:
            return "indentation_error"
        else:
            return "unknown_error"
    
    def _infer_code_from_tests(self, pattern: FailurePattern) -> Optional[str]:
        """Try to infer code structure from test cases."""
        # Extract function signature
        func_name = pattern.function_name
        if func_name == "unknown_function":
            # Try to infer from problem text
            func_match = re.search(r'function.*?(\w+)', pattern.problem_text, re.IGNORECASE)
            if func_match:
                func_name = func_match.group(1)
            else:
                # Use keywords to create function name
                if pattern.keywords:
                    func_name = pattern.keywords[0] + "_" + pattern.keywords[1] if len(pattern.keywords) > 1 else pattern.keywords[0]
                else:
                    func_name = "solve_task"
        
        # Analyze test cases to infer parameters
        params = self._infer_parameters(pattern.test_cases)
        if not params:
            # Default parameters based on keywords
            if any(kw in pattern.keywords for kw in ["list", "array"]):
                params = ["lst"]
            elif any(kw in pattern.keywords for kw in ["string", "str"]):
                params = ["s"]
            elif any(kw in pattern.keywords for kw in ["number", "num", "n"]):
                params = ["n"]
            else:
                params = ["*args"]
        
        param_str = ", ".join(params) if params else "lst"
        
        # Generate basic template structure with hints
        keywords_str = ', '.join(pattern.keywords[:5]) if pattern.keywords else "unknown"
        
        # Try to generate a basic implementation based on keywords
        implementation = self._generate_basic_implementation(pattern.keywords, params)
        
        template = f"""def {func_name}({param_str}):
    \"\"\"{pattern.problem_text[:80]}...\"\"\"
    # Auto-learned template from {pattern.frequency} similar failures
    # Keywords: {keywords_str}
{implementation}
"""
        return template
    
    def _generate_basic_implementation(self, keywords: List[str], params: List[str]) -> str:
        """Generate basic implementation hints based on keywords."""
        keywords_lower = [kw.lower() for kw in keywords]
        param = params[0] if params else "lst"
        
        # Pattern-based implementations
        if "sum" in keywords_lower:
            return f"    return sum({param})"
        elif "count" in keywords_lower:
            return f"    return len({param})"
        elif "max" in keywords_lower or "maximum" in keywords_lower:
            return f"    return max({param}) if {param} else None"
        elif "min" in keywords_lower or "minimum" in keywords_lower:
            return f"    return min({param}) if {param} else None"
        elif "reverse" in keywords_lower:
            return f"    return {param}[::-1]"
        elif "sort" in keywords_lower:
            return f"    return sorted({param})"
        elif "unique" in keywords_lower or "duplicate" in keywords_lower:
            return f"    return list(set({param}))"
        elif "filter" in keywords_lower:
            return f"    return [x for x in {param} if x]"
        elif "find" in keywords_lower:
            return f"    # Find operation - implement based on test cases\n    pass"
        elif "check" in keywords_lower:
            return f"    # Check operation - implement based on test cases\n    return True"
        else:
            return f"    # Implement based on keywords: {', '.join(keywords[:3])}\n    pass"
    
    def _infer_parameters(self, test_cases: List[str]) -> List[str]:
        """Infer function parameters from test cases."""
        params = set()
        for test in test_cases:
            # Extract arguments from function calls
            match = re.search(r'\w+\s*\(([^)]*)\)', test)
            if match:
                args = match.group(1)
                # Simple heuristic: if it's a list/array, use 'lst', if string use 's', etc.
                if '[' in args or 'list' in args.lower():
                    params.add('lst')
                elif '"' in args or "'" in args or 'str' in args.lower():
                    params.add('s')
                elif re.search(r'\d+', args):
                    params.add('n')
                else:
                    # Extract variable names
                    var_matches = re.findall(r'\b([a-z_][a-z0-9_]*)\b', args.lower())
                    params.update(var_matches[:2])
        
        return list(params)[:5]  # Limit to 5 parameters
    
    def _infer_return_type(self, test_cases: List[str]) -> str:
        """Infer return type from test cases."""
        for test in test_cases:
            if "assert" in test.lower():
                # Check what's being asserted
                if "==" in test:
                    return "value"
                elif "in" in test.lower():
                    return "bool"
                elif "len" in test.lower():
                    return "int"
        return "any"
    
    def _generate_template_name(self, pattern: FailurePattern) -> str:
        """Generate a template name from pattern."""
        # Use top keywords to create name
        keywords = pattern.keywords[:3]
        if keywords:
            name = "_".join(kw.lower() for kw in keywords[:2])
            return f"auto_{name}"
        return f"auto_{pattern.function_name}"
    
    def _generate_regex(self, pattern: FailurePattern) -> str:
        """Generate regex pattern from keywords."""
        keywords = pattern.keywords[:5]
        if not keywords:
            return ""
        
        # Create regex that matches any of the keywords
        regex_parts = [f"{kw}.*" for kw in keywords[:3]]
        return "|".join(regex_parts)
    
    def suggest_templates(self, min_confidence: float = 0.3) -> List[Dict[str, Any]]:
        """Get template suggestions sorted by confidence."""
        if not self.template_candidates:
            self.generate_template_candidates()
        
        suggestions = [
            tc for tc in self.template_candidates 
            if tc.get("confidence", 0) >= min_confidence
        ]
        
        # Sort by confidence (highest first)
        suggestions.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        
        return suggestions
    
    def export_templates(self, output_file: str = "learned_templates.json"):
        """Export learned templates to JSON."""
        suggestions = self.suggest_templates()
        
        with open(output_file, 'w') as f:
            json.dump({
                "timestamp": str(Path().cwd()),
                "templates": suggestions,
                "total_patterns": len(self.failure_patterns),
                "total_candidates": len(self.template_candidates)
            }, f, indent=2)
        
        print(f"[TEMPLATE-LEARNING] Exported {len(suggestions)} templates to {output_file}")
        return output_file


def analyze_and_learn_templates(results_file: str = "full_mbpp_results.json"):
    """Main function to analyze failures and learn templates."""
    learner = TemplateLearningSystem(results_file)
    
    print("="*70)
    print("PROACTIVE TEMPLATE LEARNING")
    print("="*70)
    
    # Analyze failures
    patterns = learner.analyze_failures()
    
    # Generate candidates
    candidates = learner.generate_template_candidates()
    
    # Get suggestions
    suggestions = learner.suggest_templates(min_confidence=0.2)
    
    print("\n" + "="*70)
    print("TOP TEMPLATE SUGGESTIONS")
    print("="*70)
    for i, template in enumerate(suggestions[:10], 1):
        print(f"\n{i}. {template['name']}")
        print(f"   Keywords: {', '.join(template['pattern_keywords'][:5])}")
        print(f"   Confidence: {template['confidence']:.2%}")
        print(f"   Frequency: {template.get('frequency', 'N/A')}")
    
    # Export
    output_file = learner.export_templates()
    
    return learner, suggestions


if __name__ == "__main__":
    analyze_and_learn_templates()
