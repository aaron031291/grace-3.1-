import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from sqlalchemy.orm import Session
class QualityEnforcementLevel(str, Enum):
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    """Code quality enforcement levels."""
    BASIC = "basic"  # Static analysis only
    STANDARD = "standard"  # Static + LLM assessment
    ADVANCED = "advanced"  # + Transformation Library
    ENTERPRISE = "enterprise"  # + Grace Memory + OODA + Magma


class QualityIssueSeverity(str, Enum):
    """Quality issue severity levels."""
    CRITICAL = "critical"  # Security, correctness issues
    HIGH = "high"  # Performance, maintainability issues
    MEDIUM = "medium"  # Best practices, style issues
    LOW = "low"  # Minor improvements


@dataclass
class QualityIssue:
    """Code quality issue."""
    issue_id: str
    rule_id: str
    severity: QualityIssueSeverity
    category: str  # "security", "performance", "maintainability", etc.
    message: str
    file_path: str
    line_number: int
    code_snippet: str
    suggested_fix: str
    fix_confidence: float
    grace_memory_pattern: Optional[str] = None  # Pattern from Memory Mesh
    magma_layer: Optional[str] = None  # Surface, Mantle, or Core
    invariant_violations: List[str] = field(default_factory=list)  # Grace invariants


@dataclass
class QualityAnalysis:
    """Complete quality analysis result."""
    overall_score: float  # 0.0 - 1.0
    issues: List[QualityIssue]
    deterministic_fixes: List[Dict[str, Any]]  # From Transformation Library
    llm_suggestions: List[Dict[str, Any]]  # From Advanced Grace LLM
    grace_patterns_used: List[str]  # Patterns from Memory Mesh
    ooda_structure: Dict[str, Any]  # OODA reasoning steps
    resource_usage: Dict[str, Any]  # PC resource tracking


class AdvancedCodeQualitySystem:
    """
    Advanced Code Quality System.
    
    Goes beyond current capabilities by:
    1. **Transformation Library** - Deterministic quality fixes
    2. **Advanced Grace-Aligned LLM** - Quality patterns from Memory Mesh
    3. **Magma Hierarchical Memory** - Quality principles (Surface→Mantle→Core)
    4. **OODA Structured Analysis** - Observe → Orient → Decide → Act
    5. **Resource-Aware Operations** - Smart for PC limitations
    6. **Collaborative Evolution** - Quality patterns learned from Grace
    """
    
    def __init__(
        self,
        session: Session,
        knowledge_base_path: Path,
        max_context_tokens: int = 4096,  # PC limitation
        enforcement_level: QualityEnforcementLevel = QualityEnforcementLevel.ENTERPRISE
    ):
        """Initialize Advanced Code Quality System."""
        self.session = session
        self.kb_path = knowledge_base_path
        self.max_context_tokens = max_context_tokens
        self.enforcement_level = enforcement_level
        
        # Import Grace systems
        try:
            from backend.transform.transformation_library import get_transformation_library
            from .advanced_grace_aligned_llm import get_advanced_grace_aligned_llm
            from cognitive.magma_memory_system import MagmaMemorySystem
            from backend.cognitive.ooda import OODALoop
            
            self.transform_library = get_transformation_library(session, knowledge_base_path)
            self.grace_aligned_llm = get_advanced_grace_aligned_llm(
                session=session,
                knowledge_base_path=knowledge_base_path,
                max_context_tokens=max_context_tokens
            )
            self.magma_system = MagmaMemorySystem(session, knowledge_base_path)
            self.ooda_loop = OODALoop()
            
            logger.info("[ADV-QUALITY] Initialized with Transformation Library + Grace LLM + Magma")
        except Exception as e:
            logger.warning(f"[ADV-QUALITY] Could not initialize all systems: {e}")
            self.transform_library = None
            self.grace_aligned_llm = None
            self.magma_system = None
            self.ooda_loop = None
        
        # Import base quality optimizer
        try:
            from .code_quality_optimizer import CodeQualityOptimizer
            self.base_quality_optimizer = CodeQualityOptimizer()
            logger.info("[ADV-QUALITY] Initialized base quality optimizer")
        except Exception as e:
            logger.warning(f"[ADV-QUALITY] Could not initialize base optimizer: {e}")
            self.base_quality_optimizer = None
        
        # Quality rule patterns (can be learned from Memory Mesh)
        self.quality_rules = self._initialize_quality_rules()
        
        logger.info(f"[ADV-QUALITY] Initialized with enforcement_level={enforcement_level.value}")
    
    # ==================== QUALITY ANALYSIS ====================
    
    def analyze_code_quality(
        self,
        code: str,
        file_path: str,
        language: str = "python",
        use_ooda: bool = True,
        use_magma: bool = True,
        use_transforms: bool = True
    ) -> QualityAnalysis:
        """
        Analyze code quality with full Grace cognitive architecture.
        
        Process:
        1. OBSERVE: Gather code and quality patterns from Memory Mesh
        2. ORIENT: Analyze with trust-weighted quality principles
        3. DECIDE: Apply quality rules and transformations
        4. ACT: Fix issues with deterministic transforms
        
        This makes quality analysis MORE capable than standalone tools.
        """
        issues = []
        deterministic_fixes = []
        llm_suggestions = []
        grace_patterns_used = []
        ooda_structure = {}
        
        # OODA: OBSERVE - Gather quality patterns from Memory Mesh
        if use_ooda and self.ooda_loop:
            try:
                self.ooda_loop.reset()
                self.ooda_loop.observe({
                    "code_length": len(code),
                    "file_path": file_path,
                    "language": language
                })
                ooda_structure["observe"] = {"code_analyzed": len(code), "language": language}
            except Exception as e:
                logger.warning(f"[ADV-QUALITY] OODA observe error: {e}")
        
        # Retrieve quality patterns from Magma hierarchical memory
        quality_patterns = {}
        if use_magma and self.magma_system:
            try:
                quality_query = f"{language} code quality patterns {file_path}"
                quality_patterns = self.magma_system.get_memories_by_layer(
                    layer="mantle",  # Patterns layer
                    query=quality_query,
                    limit=5
                )
                
                # Also get principles from Core layer
                core_principles = self.magma_system.get_memories_by_layer(
                    layer="core",
                    query=f"{language} quality principles",
                    limit=3
                )
                
                quality_patterns["mantle"] = quality_patterns
                quality_patterns["core"] = core_principles
                
                grace_patterns_used = [p.get("content", "")[:100] for p in (quality_patterns.get("mantle", []) + quality_patterns.get("core", []))]
                
                logger.info(f"[ADV-QUALITY] Retrieved {len(grace_patterns_used)} quality patterns from Magma")
            except Exception as e:
                logger.warning(f"[ADV-QUALITY] Magma retrieval error: {e}")
        
        # OODA: ORIENT - Analyze with quality principles
        if use_ooda and self.ooda_loop:
            try:
                self.ooda_loop.orient(
                    context={
                        "quality_patterns": len(grace_patterns_used),
                        "language": language,
                        "enforcement_level": self.enforcement_level.value
                    },
                    constraints={"max_tokens": self.max_context_tokens}
                )
                ooda_structure["orient"] = {
                    "patterns_used": len(grace_patterns_used),
                    "enforcement_level": self.enforcement_level.value
                }
            except Exception as e:
                logger.warning(f"[ADV-QUALITY] OODA orient error: {e}")
        
        # Step 1: Static analysis (base)
        static_issues = self._static_analysis(code, file_path, language)
        issues.extend(static_issues)
        
        # Step 2: Transformation Library analysis (deterministic)
        if use_transforms and self.transform_library:
            try:
                transform_issues, transforms_available = self._check_with_transforms(
                    code, file_path, language
                )
                issues.extend(transform_issues)
                deterministic_fixes.extend(transforms_available)
            except Exception as e:
                logger.warning(f"[ADV-QUALITY] Transform analysis error: {e}")
        
        # Step 3: Advanced Grace-Aligned LLM analysis (pattern-based)
        if self.grace_aligned_llm and self.enforcement_level in [
            QualityEnforcementLevel.ADVANCED, QualityEnforcementLevel.ENTERPRISE
        ]:
            try:
                llm_analysis = self._analyze_with_grace_llm(
                    code, file_path, language, quality_patterns
                )
                llm_suggestions = llm_analysis.get("suggestions", [])
                
                # Convert LLM suggestions to issues
                for suggestion in llm_suggestions:
                    issues.append(QualityIssue(
                        issue_id=f"llm_{suggestion.get('id', 'unknown')}",
                        rule_id=suggestion.get("rule", "llm_suggestion"),
                        severity=QualityIssueSeverity.MEDIUM,
                        category=suggestion.get("category", "maintainability"),
                        message=suggestion.get("message", ""),
                        file_path=file_path,
                        line_number=suggestion.get("line", 1),
                        code_snippet=suggestion.get("code", ""),
                        suggested_fix=suggestion.get("fix", ""),
                        fix_confidence=suggestion.get("confidence", 0.7),
                        grace_memory_pattern=suggestion.get("pattern", None)
                    ))
            except Exception as e:
                logger.warning(f"[ADV-QUALITY] Grace LLM analysis error: {e}")
        
        # OODA: DECIDE - Select quality fixes
        if use_ooda and self.ooda_loop:
            try:
                self.ooda_loop.decide({
                    "issues_found": len(issues),
                    "deterministic_fixes": len(deterministic_fixes),
                    "llm_suggestions": len(llm_suggestions),
                    "fix_strategy": "prioritize_deterministic"
                })
                ooda_structure["decide"] = {
                    "issues_count": len(issues),
                    "fixes_available": len(deterministic_fixes)
                }
            except Exception as e:
                logger.warning(f"[ADV-QUALITY] OODA decide error: {e}")
        
        # Calculate overall score
        overall_score = self._calculate_quality_score(issues)
        
        # Build result
        result = QualityAnalysis(
            overall_score=overall_score,
            issues=issues,
            deterministic_fixes=deterministic_fixes,
            llm_suggestions=llm_suggestions,
            grace_patterns_used=grace_patterns_used,
            ooda_structure=ooda_structure,
            resource_usage={
                "max_tokens": self.max_context_tokens,
                "patterns_retrieved": len(grace_patterns_used),
                "analysis_time_ms": 0.0  # Would track actual time
            }
        )
        
        logger.info(
            f"[ADV-QUALITY] Analysis complete: {len(issues)} issues, "
            f"{len(deterministic_fixes)} deterministic fixes, score={overall_score:.2f}"
        )
        
        return result
    
    # ==================== STATIC ANALYSIS ====================
    
    def _static_analysis(
        self,
        code: str,
        file_path: str,
        language: str
    ) -> List[QualityIssue]:
        """Perform static code analysis."""
        issues = []
        
        lines = code.split("\n")
        
        # Check for common issues
        for i, line in enumerate(lines, 1):
            # Missing logger (G012)
            if language == "python" and line.strip().startswith("class "):
                if "logger" not in code[:code.find(line) + len(line)]:
                    issues.append(QualityIssue(
                        issue_id=f"G012_{i}",
                        rule_id="G012",
                        severity=QualityIssueSeverity.LOW,
                        category="maintainability",
                        message="Class should have logger",
                        file_path=file_path,
                        line_number=i,
                        code_snippet=line,
                        suggested_fix="Add 'logger = logging.getLogger(__name__)' to class",
                        fix_confidence=0.9,
                        invariant_violations=["invariant_6"]  # Observability
                    ))
            
            # Long lines
            if len(line) > 120:
                issues.append(QualityIssue(
                    issue_id=f"long_line_{i}",
                    rule_id="line_length",
                    severity=QualityIssueSeverity.LOW,
                    category="readability",
                    message=f"Line too long ({len(line)} chars, max 120)",
                    file_path=file_path,
                        line_number=i,
                        code_snippet=line[:100] + "...",
                        suggested_fix="Split line or use shorter variable names",
                        fix_confidence=0.8
                ))
            
            # TODO comments
            if "TODO" in line.upper() and not line.strip().startswith("#"):
                issues.append(QualityIssue(
                    issue_id=f"todo_{i}",
                    rule_id="todo_comment",
                    severity=QualityIssueSeverity.MEDIUM,
                    category="completeness",
                    message="TODO comment found",
                    file_path=file_path,
                    line_number=i,
                    code_snippet=line,
                    suggested_fix="Resolve TODO or document why it remains",
                    fix_confidence=0.7
                ))
        
        return issues
    
    # ==================== TRANSFORMATION LIBRARY ====================
    
    def _check_with_transforms(
        self,
        code: str,
        file_path: str,
        language: str
    ) -> Tuple[List[QualityIssue], List[Dict[str, Any]]]:
        """Check code quality using Transformation Library."""
        issues = []
        transforms_available = []
        
        if not self.transform_library:
            return issues, transforms_available
        
        try:
            # Check for quality rules in Transformation Library
            for rule_id, rule in self.transform_library.rules.items():
                if "quality" in rule.description.lower() or "quality" in rule.rule_name.lower():
                    # Try to match rule pattern
                    try:
                        transformed_code, outcome = self.transform_library.apply_transform(
                            code=code,
                            rule=rule,
                            verify_proofs=True
                        )
                        
                        # If transform matches and improves code
                        if transformed_code != code:
                            transforms_available.append({
                                "rule_id": rule.rule_id,
                                "rule_name": rule.rule_name,
                                "description": rule.description,
                                "transformed_code": transformed_code,
                                "proofs_passed": all(
                                    p == "passed" for p in outcome.proof_results.values()
                                )
                            })
                            
                            # Create issue for the fix
                            issues.append(QualityIssue(
                                issue_id=f"transform_{rule.rule_id}",
                                rule_id=rule.rule_id,
                                severity=QualityIssueSeverity.MEDIUM,
                                category="code_quality",
                                message=f"Quality improvement available: {rule.description}",
                                file_path=file_path,
                                line_number=1,
                                code_snippet=code[:100],
                                suggested_fix=transformed_code,
                                fix_confidence=0.9 if all(
                                    p == "passed" for p in outcome.proof_results.values()
                                ) else 0.7
                            ))
                    except Exception as e:
                        logger.debug(f"[ADV-QUALITY] Transform check error for {rule_id}: {e}")
                        continue
        except Exception as e:
            logger.warning(f"[ADV-QUALITY] Transform analysis error: {e}")
        
        return issues, transforms_available
    
    # ==================== GRACE-ALIGNED LLM ANALYSIS ====================
    
    def _analyze_with_grace_llm(
        self,
        code: str,
        file_path: str,
        language: str,
        quality_patterns: Dict[str, List[Dict]]
    ) -> Dict[str, Any]:
        """Analyze code quality using Advanced Grace-Aligned LLM."""
        if not self.grace_aligned_llm:
            return {"suggestions": []}
        
        try:
            # Build quality analysis query
            query = f"Analyze {language} code quality for file {file_path}:\n\n```{language}\n{code}\n```"
            
            # Use quality patterns as context
            pattern_context = ""
            if quality_patterns:
                pattern_context = "\n\n=== QUALITY PATTERNS FROM GRACE MEMORY ===\n"
                for layer, patterns in quality_patterns.items():
                    pattern_context += f"\n[{layer.upper()}]:\n"
                    for p in patterns[:3]:
                        pattern_context += f"- {p.get('content', '')[:200]}...\n"
            
            query += pattern_context
            
            # Generate quality analysis with Grace-Aligned LLM
            result = self.grace_aligned_llm.generate_with_grace_cognition(
                query=query,
                enable_ooda_structure=True,
                enable_compression=True
            )
            
            # Parse suggestions from response
            suggestions = self._parse_quality_suggestions(
                result.get("response", ""),
                language
            )
            
            return {"suggestions": suggestions}
            
        except Exception as e:
            logger.warning(f"[ADV-QUALITY] Grace LLM analysis error: {e}")
            return {"suggestions": []}
    
    def _parse_quality_suggestions(
        self,
        response: str,
        language: str
    ) -> List[Dict[str, Any]]:
        """Parse quality suggestions from LLM response."""
        suggestions = []
        
        # Simple parsing (can be enhanced)
        lines = response.split("\n")
        current_suggestion = {}
        
        for line in lines:
            if "ISSUE:" in line.upper() or "PROBLEM:" in line.upper():
                if current_suggestion:
                    suggestions.append(current_suggestion)
                current_suggestion = {
                    "id": f"suggestion_{len(suggestions)}",
                    "message": line.split(":")[-1].strip(),
                    "category": "maintainability",
                    "confidence": 0.7
                }
            elif "FIX:" in line.upper() or "SUGGESTION:" in line.upper():
                if current_suggestion:
                    current_suggestion["fix"] = line.split(":")[-1].strip()
            elif "LINE:" in line.upper():
                try:
                    current_suggestion["line"] = int(line.split(":")[-1].strip())
                except:
                    pass
        
        if current_suggestion:
            suggestions.append(current_suggestion)
        
        return suggestions
    
    # ==================== QUALITY SCORING ====================
    
    def _calculate_quality_score(self, issues: List[QualityIssue]) -> float:
        """Calculate overall quality score from issues."""
        if not issues:
            return 1.0
        
        # Weight by severity
        severity_weights = {
            QualityIssueSeverity.CRITICAL: 0.4,
            QualityIssueSeverity.HIGH: 0.3,
            QualityIssueSeverity.MEDIUM: 0.2,
            QualityIssueSeverity.LOW: 0.1
        }
        
        total_weight = sum(severity_weights.get(issue.severity, 0.1) for issue in issues)
        
        # Score decreases with issues
        score = max(0.0, 1.0 - (total_weight / len(issues)) if issues else 1.0)
        
        return min(1.0, score)
    
    # ==================== QUALITY RULES ====================
    
    def _initialize_quality_rules(self) -> Dict[str, Dict[str, Any]]:
        """Initialize quality rules (can be learned from Memory Mesh)."""
        return {
            "G012": {
                "name": "Missing Logger",
                "severity": QualityIssueSeverity.LOW,
                "category": "maintainability",
                "invariant": "invariant_6"  # Observability
            },
            "line_length": {
                "name": "Long Lines",
                "severity": QualityIssueSeverity.LOW,
                "category": "readability"
            },
            "todo_comment": {
                "name": "TODO Comments",
                "severity": QualityIssueSeverity.MEDIUM,
                "category": "completeness"
            }
        }
    
    # ==================== APPLY FIXES ====================
    
    def apply_quality_fixes(
        self,
        code: str,
        analysis: QualityAnalysis,
        use_deterministic: bool = True,
        use_llm: bool = False
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Apply quality fixes to code.
        
        Prioritizes deterministic fixes from Transformation Library.
        """
        fixed_code = code
        fixes_applied = []
        
        # Apply deterministic fixes first
        if use_deterministic and analysis.deterministic_fixes:
            for fix in analysis.deterministic_fixes:
                try:
                    if fix.get("proofs_passed"):
                        fixed_code = fix.get("transformed_code", fixed_code)
                        fixes_applied.append({
                            "type": "deterministic",
                            "rule_id": fix.get("rule_id"),
                            "description": fix.get("description"),
                            "proofs_passed": True
                        })
                        logger.info(f"[ADV-QUALITY] Applied deterministic fix: {fix.get('rule_id')}")
                except Exception as e:
                    logger.warning(f"[ADV-QUALITY] Fix application error: {e}")
        
        # Apply LLM suggestions if enabled
        if use_llm and analysis.llm_suggestions:
            # Would use LLM to apply fixes
            pass
        
        return fixed_code, fixes_applied


def get_advanced_code_quality_system(
    session: Session,
    knowledge_base_path: Path,
    max_context_tokens: int = 4096,
    enforcement_level: QualityEnforcementLevel = QualityEnforcementLevel.ENTERPRISE
) -> AdvancedCodeQualitySystem:
    """Factory function to get Advanced Code Quality System."""
    return AdvancedCodeQualitySystem(
        session=session,
        knowledge_base_path=knowledge_base_path,
        max_context_tokens=max_context_tokens,
        enforcement_level=enforcement_level
    )
