import logging
import ast
import re
import subprocess
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from collections import defaultdict
from sqlalchemy.orm import Session
from cognitive.transformation_library.outcome_ledger import OutcomeLedger, TransformationOutcome
from cognitive.magma_memory_system import MagmaLayer, MagmaMemorySystem
from cognitive.memory_mesh_integration import MemoryMeshIntegration

logger = logging.getLogger(__name__)
class TransformationPatternMiner:
    logger = logging.getLogger(__name__)
    """
    Pattern miner that discovers new rules from successful transforms.
    
    Features:
    1. Clusters successful diffs from Outcome Ledger
    2. Detects recurring manual edits (not yet automated)
    3. Proposes new rules or refinements
    4. Generates "why this rule exists" documentation
    """

    def __init__(
        self,
        session: Session,
        outcome_ledger: OutcomeLedger,
        magma_memory: Optional[MagmaMemorySystem] = None,
        memory_mesh: Optional[MemoryMeshIntegration] = None
    ):
        """
        Initialize Pattern Miner.
        
        Args:
            session: Database session
            outcome_ledger: Outcome ledger
            magma_memory: Magma memory system (optional)
            memory_mesh: Memory mesh integration (optional)
        """
        self.session = session
        self.outcome_ledger = outcome_ledger
        self.magma_memory = magma_memory
        self.memory_mesh = memory_mesh
        
        logger.info("[PATTERN-MINER] Initialized")

    def mine_patterns(self) -> Dict[str, Any]:
        """
        Mine patterns from successful transforms.
        
        Returns:
            Dictionary with discovered patterns and proposals
        """
        logger.info("[PATTERN-MINER] Starting pattern mining")
        
        results = {
            "clusters": [],
            "manual_edits": [],
            "rule_proposals": [],
            "rule_refinements": [],
            "statistics": {}
        }
        
        try:
            # 1. Get successful transforms from Outcome Ledger (Mantle/Core layers)
            successful_transforms = self.outcome_ledger.get_by_layer(
                layers=[MagmaLayer.MANTLE, MagmaLayer.CORE],
                min_crystallized=0.7,
                limit=1000
            )
            
            logger.info(f"[PATTERN-MINER] Found {len(successful_transforms)} successful transforms")
            
            if not successful_transforms:
                logger.info("[PATTERN-MINER] No successful transforms to mine")
                return results
            
            # 2. Cluster by AST pattern signature
            clusters = self._cluster_transforms(successful_transforms)
            results["clusters"] = clusters
            
            logger.info(f"[PATTERN-MINER] Discovered {len(clusters)} clusters")
            
            # 3. Detect recurring manual edits (compare with manual code changes)
            manual_edits = self._detect_manual_patterns()
            results["manual_edits"] = manual_edits
            
            logger.info(f"[PATTERN-MINER] Found {len(manual_edits)} manual edit patterns")
            
            # 4. Generate rule proposals from clusters and manual edits
            rule_proposals = self._generate_rule_proposals(clusters, manual_edits)
            results["rule_proposals"] = rule_proposals
            
            logger.info(f"[PATTERN-MINER] Generated {len(rule_proposals)} rule proposals")
            
            # 5. Generate rule refinements from clusters
            rule_refinements = self._generate_rule_refinements(clusters)
            results["rule_refinements"] = rule_refinements
            
            logger.info(f"[PATTERN-MINER] Generated {len(rule_refinements)} rule refinements")
            
            # 6. Store proposals in learning memory
            self._store_proposals_in_memory(rule_proposals, rule_refinements)
            
            # Statistics
            results["statistics"] = {
                "successful_transforms": len(successful_transforms),
                "clusters_discovered": len(clusters),
                "manual_edits_found": len(manual_edits),
                "rule_proposals_generated": len(rule_proposals),
                "rule_refinements_generated": len(rule_refinements)
            }
            
            logger.info("[PATTERN-MINER] Pattern mining complete")
        
        except Exception as e:
            logger.error(f"[PATTERN-MINER] Error during pattern mining: {e}")
            results["error"] = str(e)
        
        return results

    def _cluster_transforms(
        self,
        transforms: List[TransformationOutcome]
    ) -> List[Dict[str, Any]]:
        """Cluster transforms by AST pattern signature."""
        # Group by pattern signature
        clusters = defaultdict(list)
        
        for transform in transforms:
            signature = transform.ast_pattern_signature
            clusters[signature].append(transform)
        
        # Convert to cluster list
        cluster_list = []
        
        for signature, transform_list in clusters.items():
            if len(transform_list) >= 2:  # At least 2 similar transforms
                cluster_list.append({
                    "pattern_signature": signature,
                    "count": len(transform_list),
                    "rule_ids": list(set(t.rule_id for t in transform_list)),
                    "avg_crystallized": sum(t.crystallized for t in transform_list) / len(transform_list),
                    "transforms": [t.id for t in transform_list[:5]]  # First 5
                })
        
        # Sort by count (most frequent first)
        cluster_list.sort(key=lambda c: c["count"], reverse=True)
        
        return cluster_list

    def _detect_manual_patterns(self) -> List[Dict[str, Any]]:
        """
        Detect recurring manual edits not yet automated.
        
        Analyzes git history to find patterns in manual code changes
        that could be automated as transformation rules.
        """
        manual_edits = []
        
        try:
            git_diffs = self._get_recent_git_diffs(limit=100)
            
            if not git_diffs:
                logger.debug("[PATTERN-MINER] No git diffs found")
                return manual_edits
            
            pattern_counts = defaultdict(list)
            
            for diff_info in git_diffs:
                patterns = self._extract_patterns_from_diff(diff_info)
                for pattern in patterns:
                    pattern_counts[pattern["signature"]].append({
                        "commit": diff_info.get("commit", "unknown"),
                        "file": diff_info.get("file", "unknown"),
                        "pattern": pattern
                    })
            
            for signature, occurrences in pattern_counts.items():
                if len(occurrences) >= 2:
                    manual_edits.append({
                        "pattern_signature": signature,
                        "frequency": len(occurrences),
                        "pattern": occurrences[0]["pattern"].get("details", {}),
                        "rewrite": self._infer_rewrite_from_occurrences(occurrences),
                        "examples": [
                            {"commit": o["commit"], "file": o["file"]}
                            for o in occurrences[:5]
                        ]
                    })
            
            manual_edits.sort(key=lambda x: x["frequency"], reverse=True)
            
        except Exception as e:
            logger.warning(f"[PATTERN-MINER] Error detecting manual patterns: {e}")
        
        return manual_edits

    def _get_recent_git_diffs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent git diffs from repository history."""
        diffs = []
        
        try:
            result = subprocess.run(
                ["git", "log", f"-{limit}", "--oneline", "--format=%H"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return diffs
            
            commits = result.stdout.strip().split("\n")[:limit]
            
            for commit in commits:
                if not commit:
                    continue
                    
                diff_result = subprocess.run(
                    ["git", "show", commit, "--format=", "--unified=3"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if diff_result.returncode == 0 and diff_result.stdout:
                    parsed = self._parse_git_diff(diff_result.stdout, commit)
                    diffs.extend(parsed)
                    
        except subprocess.TimeoutExpired:
            logger.warning("[PATTERN-MINER] Git command timed out")
        except FileNotFoundError:
            logger.debug("[PATTERN-MINER] Git not available")
        except Exception as e:
            logger.warning(f"[PATTERN-MINER] Error getting git diffs: {e}")
        
        return diffs

    def _parse_git_diff(self, diff_output: str, commit: str) -> List[Dict[str, Any]]:
        """Parse git diff output to extract file changes."""
        parsed_diffs = []
        current_file = None
        added_lines = []
        removed_lines = []
        context_lines = []
        
        for line in diff_output.split("\n"):
            if line.startswith("diff --git"):
                if current_file and (added_lines or removed_lines):
                    parsed_diffs.append({
                        "commit": commit,
                        "file": current_file,
                        "added": added_lines.copy(),
                        "removed": removed_lines.copy(),
                        "context": context_lines.copy()
                    })
                match = re.search(r"b/(.+)$", line)
                current_file = match.group(1) if match else None
                added_lines = []
                removed_lines = []
                context_lines = []
            elif line.startswith("+") and not line.startswith("+++"):
                added_lines.append(line[1:])
            elif line.startswith("-") and not line.startswith("---"):
                removed_lines.append(line[1:])
            elif line.startswith(" "):
                context_lines.append(line[1:])
        
        if current_file and (added_lines or removed_lines):
            parsed_diffs.append({
                "commit": commit,
                "file": current_file,
                "added": added_lines,
                "removed": removed_lines,
                "context": context_lines
            })
        
        return parsed_diffs

    def _extract_patterns_from_diff(self, diff_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract code patterns from a diff."""
        patterns = []
        file_path = diff_info.get("file", "")
        added = diff_info.get("added", [])
        removed = diff_info.get("removed", [])
        
        if not file_path.endswith(".py"):
            return patterns
        
        added_code = "\n".join(added)
        removed_code = "\n".join(removed)
        
        if self._detect_error_handling_added(added, removed):
            patterns.append({
                "signature": "add_error_handling",
                "details": {
                    "type": "ast",
                    "match": "bare_statement",
                    "language": "python"
                }
            })
        
        if self._detect_logging_added(added, removed):
            patterns.append({
                "signature": "add_logging",
                "details": {
                    "type": "ast",
                    "match": "function_without_logging",
                    "language": "python"
                }
            })
        
        if self._detect_type_hints_added(added, removed):
            patterns.append({
                "signature": "add_type_hints",
                "details": {
                    "type": "ast",
                    "match": "function_without_types",
                    "language": "python"
                }
            })
        
        if self._detect_docstring_added(added, removed):
            patterns.append({
                "signature": "add_docstring",
                "details": {
                    "type": "ast",
                    "match": "function_without_docstring",
                    "language": "python"
                }
            })
        
        if self._detect_variable_rename(added, removed):
            patterns.append({
                "signature": "rename_variable",
                "details": {
                    "type": "text",
                    "match": "variable_rename_pattern",
                    "language": "python"
                }
            })
        
        if self._detect_async_conversion(added, removed):
            patterns.append({
                "signature": "convert_to_async",
                "details": {
                    "type": "ast",
                    "match": "sync_function",
                    "language": "python"
                }
            })
        
        return patterns

    def _detect_error_handling_added(self, added: List[str], removed: List[str]) -> bool:
        """Detect if error handling was added."""
        added_text = " ".join(added)
        removed_text = " ".join(removed)
        
        has_try_added = "try:" in added_text and "try:" not in removed_text
        has_except_added = "except" in added_text and "except" not in removed_text
        
        return has_try_added or has_except_added

    def _detect_logging_added(self, added: List[str], removed: List[str]) -> bool:
        """Detect if logging was added."""
        added_text = " ".join(added)
        removed_text = " ".join(removed)
        
        logging_patterns = ["logger.", "logging.", "log."]
        return any(p in added_text and p not in removed_text for p in logging_patterns)

    def _detect_type_hints_added(self, added: List[str], removed: List[str]) -> bool:
        """Detect if type hints were added."""
        type_hint_pattern = re.compile(r":\s*\w+(\[[\w\[\],\s]+\])?\s*(=|,|\))")
        return_type_pattern = re.compile(r"\)\s*->\s*\w+")
        
        added_text = " ".join(added)
        removed_text = " ".join(removed)
        
        added_hints = bool(type_hint_pattern.search(added_text) or return_type_pattern.search(added_text))
        removed_hints = bool(type_hint_pattern.search(removed_text) or return_type_pattern.search(removed_text))
        
        return added_hints and not removed_hints

    def _detect_docstring_added(self, added: List[str], removed: List[str]) -> bool:
        """Detect if docstrings were added."""
        added_text = " ".join(added)
        removed_text = " ".join(removed)
        
        return '"""' in added_text and '"""' not in removed_text

    def _detect_variable_rename(self, added: List[str], removed: List[str]) -> bool:
        """Detect if a variable was renamed."""
        if not added or not removed:
            return False
        
        for add_line, rem_line in zip(added, removed):
            if add_line.strip() and rem_line.strip():
                add_words = set(re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', add_line))
                rem_words = set(re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', rem_line))
                
                only_in_add = add_words - rem_words
                only_in_rem = rem_words - add_words
                
                if len(only_in_add) == 1 and len(only_in_rem) == 1:
                    return True
        
        return False

    def _detect_async_conversion(self, added: List[str], removed: List[str]) -> bool:
        """Detect if sync functions were converted to async."""
        added_text = " ".join(added)
        removed_text = " ".join(removed)
        
        has_async_added = "async def" in added_text and "async def" not in removed_text
        has_await_added = "await " in added_text and "await " not in removed_text
        
        return has_async_added or has_await_added

    def _infer_rewrite_from_occurrences(self, occurrences: List[Dict]) -> Dict[str, Any]:
        """Infer rewrite template from pattern occurrences."""
        if not occurrences:
            return {}
        
        first = occurrences[0].get("pattern", {}).get("details", {})
        signature = occurrences[0].get("pattern", {}).get("signature", "")
        
        rewrite_templates = {
            "add_error_handling": {
                "template": "try:\n    {original}\nexcept Exception as e:\n    logger.error(f'Error: {e}')\n    raise",
                "preserve": ["original_logic"]
            },
            "add_logging": {
                "template": "logger.info('Entering {function_name}')\n{original}\nlogger.info('Exiting {function_name}')",
                "preserve": ["function_name", "original_logic"]
            },
            "add_type_hints": {
                "template": "def {function_name}({typed_params}) -> {return_type}:",
                "preserve": ["function_name", "params"]
            },
            "add_docstring": {
                "template": 'def {function_name}({params}):\n    """{description}"""\n    {body}',
                "preserve": ["function_name", "params", "body"]
            },
            "rename_variable": {
                "template": "{new_name}",
                "preserve": ["old_name"]
            },
            "convert_to_async": {
                "template": "async def {function_name}({params}):\n    {async_body}",
                "preserve": ["function_name", "params"]
            }
        }
        
        return rewrite_templates.get(signature, {"template": "TODO: Extract from examples", "preserve": []})

    def _generate_rule_proposals(
        self,
        clusters: List[Dict[str, Any]],
        manual_edits: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate new rule proposals from clusters and manual edits."""
        proposals = []
        
        # Generate proposals from clusters with high frequency but no existing rule
        for cluster in clusters:
            if cluster["count"] >= 5:  # High frequency
                # Check if there's already a rule for this pattern
                # For now, propose a new rule
                proposal = {
                    "pattern_signature": cluster["pattern_signature"],
                    "frequency": cluster["count"],
                    "confidence": min(1.0, cluster["count"] / 10.0),  # Scale confidence
                    "proposed_rule": {
                        "id": f"auto_discovered_{cluster['pattern_signature'][:8]}",
                        "version": "1.0",
                        "pattern": {
                            "type": "ast",
                            "match": "TODO: Extract from cluster",
                            "language": "python"
                        },
                        "rewrite": {
                            "template": "TODO: Extract from diffs",
                            "preserve": []
                        },
                        "constraints": {
                            "pre": [],
                            "post": []
                        },
                        "proof_required": [],
                        "side_effects": [],
                        "description": f"Auto-discovered rule from {cluster['count']} successful transforms"
                    },
                    "why_exists": self._generate_why_documentation(cluster)
                }
                proposals.append(proposal)
        
        # Generate proposals from manual edits
        for edit in manual_edits:
            proposal = {
                "pattern_signature": edit.get("pattern_signature", "unknown"),
                "frequency": edit.get("frequency", 1),
                "confidence": 0.6,  # Manual edits are less certain
                "proposed_rule": {
                    "id": f"manual_edit_{edit.get('pattern_signature', 'unknown')[:8]}",
                    "version": "1.0",
                    "pattern": edit.get("pattern", {}),
                    "rewrite": edit.get("rewrite", {}),
                    "constraints": {"pre": [], "post": []},
                    "proof_required": [],
                    "side_effects": [],
                    "description": f"Rule proposed from {edit.get('frequency', 1)} manual edits"
                },
                "why_exists": f"Recurring manual edit pattern detected {edit.get('frequency', 1)} times"
            }
            proposals.append(proposal)
        
        # Sort by confidence
        proposals.sort(key=lambda p: p["confidence"], reverse=True)
        
        return proposals

    def _generate_rule_refinements(
        self,
        clusters: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate refinements for existing rules based on pattern analysis."""
        refinements = []
        
        rule_variations = defaultdict(list)
        for cluster in clusters:
            for rule_id in cluster.get("rule_ids", []):
                if rule_id:
                    rule_variations[rule_id].append(cluster)
        
        for rule_id, related_clusters in rule_variations.items():
            if len(related_clusters) >= 2:
                signatures = [c.get("pattern_signature", "") for c in related_clusters]
                unique_signatures = set(signatures)
                
                if len(unique_signatures) > 1:
                    refinements.append({
                        "rule_id": rule_id,
                        "type": "pattern_variation",
                        "description": f"Rule has {len(unique_signatures)} pattern variations",
                        "variations": list(unique_signatures)[:5],
                        "proposal": {
                            "action": "generalize_pattern",
                            "reason": "Multiple similar patterns could be handled by a single generalized rule"
                        }
                    })
            
            total_transforms = sum(c.get("count", 0) for c in related_clusters)
            avg_crystallized = sum(c.get("avg_crystallized", 0) for c in related_clusters) / len(related_clusters)
            
            if avg_crystallized < 0.8 and total_transforms >= 5:
                refinements.append({
                    "rule_id": rule_id,
                    "type": "low_crystallization",
                    "description": f"Rule has low crystallization ({avg_crystallized:.2f})",
                    "transforms_count": total_transforms,
                    "proposal": {
                        "action": "improve_constraints",
                        "reason": "Low crystallization suggests rule may need tighter constraints"
                    }
                })
        
        code_patterns = self._extract_code_patterns_from_codebase()
        for pattern in code_patterns:
            if pattern.get("frequency", 0) >= 3:
                refinements.append({
                    "rule_id": None,
                    "type": "code_pattern",
                    "pattern_name": pattern.get("name"),
                    "description": f"Found {pattern.get('frequency', 0)} occurrences of {pattern.get('name')} pattern",
                    "examples": pattern.get("examples", [])[:3],
                    "proposal": {
                        "action": "create_pattern_rule",
                        "reason": f"Common {pattern.get('name')} pattern could benefit from standardization"
                    }
                })
        
        refinements.sort(key=lambda r: r.get("transforms_count", r.get("frequency", 0)), reverse=True)
        
        return refinements

    def _extract_code_patterns_from_codebase(self) -> List[Dict[str, Any]]:
        """Extract common code patterns from Python files using AST analysis."""
        patterns = []
        pattern_counts = {
            "exception_handling": {"count": 0, "examples": []},
            "list_comprehension": {"count": 0, "examples": []},
            "generator_expression": {"count": 0, "examples": []},
            "decorator_usage": {"count": 0, "examples": []},
            "async_function": {"count": 0, "examples": []},
            "context_manager": {"count": 0, "examples": []},
            "singleton_pattern": {"count": 0, "examples": []},
            "factory_pattern": {"count": 0, "examples": []},
            "property_decorator": {"count": 0, "examples": []},
            "dataclass_usage": {"count": 0, "examples": []}
        }
        
        try:
            result = subprocess.run(
                ["git", "ls-files", "*.py"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return patterns
            
            py_files = result.stdout.strip().split("\n")[:50]
            
            for file_path in py_files:
                if not file_path:
                    continue
                try:
                    file_patterns = self._analyze_file_patterns(file_path)
                    for pattern_name, occurrences in file_patterns.items():
                        if pattern_name in pattern_counts:
                            pattern_counts[pattern_name]["count"] += occurrences["count"]
                            pattern_counts[pattern_name]["examples"].extend(
                                occurrences.get("examples", [])[:2]
                            )
                except Exception:
                    continue
            
            for name, data in pattern_counts.items():
                if data["count"] > 0:
                    patterns.append({
                        "name": name,
                        "frequency": data["count"],
                        "examples": data["examples"][:5]
                    })
            
        except Exception as e:
            logger.warning(f"[PATTERN-MINER] Error extracting code patterns: {e}")
        
        return patterns

    def _analyze_file_patterns(self, file_path: str) -> Dict[str, Dict[str, Any]]:
        """Analyze a single Python file for patterns using AST."""
        patterns = {
            "exception_handling": {"count": 0, "examples": []},
            "list_comprehension": {"count": 0, "examples": []},
            "generator_expression": {"count": 0, "examples": []},
            "decorator_usage": {"count": 0, "examples": []},
            "async_function": {"count": 0, "examples": []},
            "context_manager": {"count": 0, "examples": []},
            "singleton_pattern": {"count": 0, "examples": []},
            "factory_pattern": {"count": 0, "examples": []},
            "property_decorator": {"count": 0, "examples": []},
            "dataclass_usage": {"count": 0, "examples": []}
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                source = f.read()
            
            tree = ast.parse(source)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Try):
                    patterns["exception_handling"]["count"] += 1
                    patterns["exception_handling"]["examples"].append({
                        "file": file_path,
                        "line": node.lineno
                    })
                
                elif isinstance(node, ast.ListComp):
                    patterns["list_comprehension"]["count"] += 1
                    patterns["list_comprehension"]["examples"].append({
                        "file": file_path,
                        "line": node.lineno
                    })
                
                elif isinstance(node, ast.GeneratorExp):
                    patterns["generator_expression"]["count"] += 1
                    patterns["generator_expression"]["examples"].append({
                        "file": file_path,
                        "line": node.lineno
                    })
                
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.decorator_list:
                        patterns["decorator_usage"]["count"] += 1
                        patterns["decorator_usage"]["examples"].append({
                            "file": file_path,
                            "line": node.lineno,
                            "name": node.name
                        })
                        
                        for decorator in node.decorator_list:
                            dec_name = ""
                            if isinstance(decorator, ast.Name):
                                dec_name = decorator.id
                            elif isinstance(decorator, ast.Attribute):
                                dec_name = decorator.attr
                            
                            if dec_name == "property":
                                patterns["property_decorator"]["count"] += 1
                                patterns["property_decorator"]["examples"].append({
                                    "file": file_path,
                                    "line": node.lineno,
                                    "name": node.name
                                })
                    
                    if isinstance(node, ast.AsyncFunctionDef):
                        patterns["async_function"]["count"] += 1
                        patterns["async_function"]["examples"].append({
                            "file": file_path,
                            "line": node.lineno,
                            "name": node.name
                        })
                
                elif isinstance(node, ast.With):
                    patterns["context_manager"]["count"] += 1
                    patterns["context_manager"]["examples"].append({
                        "file": file_path,
                        "line": node.lineno
                    })
                
                elif isinstance(node, ast.ClassDef):
                    for decorator in node.decorator_list:
                        dec_name = ""
                        if isinstance(decorator, ast.Name):
                            dec_name = decorator.id
                        elif isinstance(decorator, ast.Attribute):
                            dec_name = decorator.attr
                        
                        if dec_name == "dataclass":
                            patterns["dataclass_usage"]["count"] += 1
                            patterns["dataclass_usage"]["examples"].append({
                                "file": file_path,
                                "line": node.lineno,
                                "name": node.name
                            })
                    
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            if item.name == "__new__" or item.name == "create":
                                patterns["factory_pattern"]["count"] += 1
                                patterns["factory_pattern"]["examples"].append({
                                    "file": file_path,
                                    "line": item.lineno,
                                    "class": node.name
                                })
                    
                    has_instance = False
                    has_new = False
                    for item in node.body:
                        if isinstance(item, ast.Assign):
                            for target in item.targets:
                                if isinstance(target, ast.Name) and target.id == "_instance":
                                    has_instance = True
                        elif isinstance(item, ast.FunctionDef) and item.name == "__new__":
                            has_new = True
                    
                    if has_instance and has_new:
                        patterns["singleton_pattern"]["count"] += 1
                        patterns["singleton_pattern"]["examples"].append({
                            "file": file_path,
                            "line": node.lineno,
                            "class": node.name
                        })
                        
        except SyntaxError:
            pass
        except Exception as e:
            logger.debug(f"[PATTERN-MINER] Error analyzing {file_path}: {e}")
        
        return patterns

    def _generate_why_documentation(self, cluster: Dict[str, Any]) -> str:
        """Generate 'why this rule exists' documentation."""
        rule_ids = cluster.get("rule_ids", [])
        count = cluster.get("count", 0)
        avg_crystallized = cluster.get("avg_crystallized", 0.0)
        
        doc = f"""
This rule was discovered through pattern mining from {count} successful transformations.

Pattern Signature: {cluster.get('pattern_signature', 'unknown')[:16]}...
Rules Involved: {', '.join(rule_ids) if rule_ids else 'Auto-discovered'}
Average Crystallization: {avg_crystallized:.2f}

This pattern appears frequently in successful transforms, indicating it's a common
and valuable transformation that should be automated.
        """.strip()
        
        return doc

    def _store_proposals_in_memory(
        self,
        rule_proposals: List[Dict[str, Any]],
        rule_refinements: List[Dict[str, Any]]
    ):
        """Store proposals in learning memory for review."""
        if not self.memory_mesh:
            return
        
        try:
            # Store rule proposals
            for proposal in rule_proposals:
                self.memory_mesh.ingest_learning_experience(
                    experience_type="rule_proposal",
                    context={
                        "pattern": proposal.get("pattern_signature"),
                        "frequency": proposal.get("frequency", 0),
                        "confidence": proposal.get("confidence", 0.0)
                    },
                    action_taken={
                        "proposed_rule": proposal.get("proposed_rule", {}),
                        "why_exists": proposal.get("why_exists", "")
                    },
                    outcome={
                        "quality_score": proposal.get("confidence", 0.0),
                        "status": "proposed"
                    },
                    source="pattern_miner",
                    genesis_key_id=None
                )
            
            logger.info(
                f"[PATTERN-MINER] Stored {len(rule_proposals)} proposals in memory mesh"
            )
        
        except Exception as e:
            logger.warning(f"[PATTERN-MINER] Error storing proposals in memory: {e}")
