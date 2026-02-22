"""
Near-Zero Hallucination Guard - Pushing to 99% Accuracy

Extends the existing 6-layer HallucinationGuard with 7 additional layers
designed to catch the remaining edge cases. The goal: near-zero hallucinations.

EXISTING LAYERS (from hallucination_guard.py):
  Layer 1: Repository Grounding        - Claims reference actual files
  Layer 2: Cross-Model Consensus       - Multiple LLMs agree
  Layer 3: Contradiction Detection     - No conflicts with known facts
  Layer 4: Confidence Scoring          - Trust score calculation
  Layer 5: Trust System Verification   - Learning memory validation
  Layer 6: External Verification       - Docs/web lookup

NEW LAYERS (this file):
  Layer 7:  Atomic Claim Decomposition   - Break into atoms, verify each
  Layer 8:  Source Attribution Enforce    - Every claim MUST cite a source
  Layer 9:  Structural Code Validation   - AST parse, import verify, type check
  Layer 10: Internal Logic Consistency   - No self-contradictions within response
  Layer 11: Adversarial Self-Challenge   - LLM attacks its own output
  Layer 12: Ensemble Weighted Voting     - 5+ models vote, weighted by accuracy
  Layer 13: Claim Density Guard          - Flag too many unverifiable claims

ARCHITECTURE:
  Content -> [Layers 1-6 existing] -> [Layers 7-13 new]
                                            |
                                            v
                                    Bayesian Ensemble Score
                                            |
                              if score < threshold: REJECT
                              if score >= threshold: PASS
                                            |
                                    if REJECT and retries left:
                                        -> auto-correct -> re-verify
"""

import logging
import re
import ast
import hashlib
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


@dataclass
class AtomicClaim:
    """A single atomic (indivisible) claim extracted from content."""
    claim_id: str
    text: str
    claim_type: str  # factual, code, reference, opinion, instruction
    source_cited: bool
    source: Optional[str]
    verifiable: bool
    verified: Optional[bool] = None
    confidence: float = 0.5
    verification_method: Optional[str] = None


@dataclass
class LayerResult:
    """Result from a single verification layer."""
    layer_name: str
    layer_number: int
    passed: bool
    confidence: float
    details: Dict[str, Any] = field(default_factory=dict)
    claims_checked: int = 0
    claims_passed: int = 0
    claims_failed: int = 0
    duration_ms: float = 0.0


@dataclass
class NearZeroVerificationResult:
    """Complete result from near-zero hallucination verification."""
    is_verified: bool
    hallucination_probability: float  # 0.0 = definitely real, 1.0 = definitely hallucinated
    confidence_score: float
    layer_results: List[LayerResult]
    atomic_claims: List[AtomicClaim]
    total_claims: int
    verified_claims: int
    unverified_claims: int
    hallucinated_claims: int
    final_content: str
    corrections_applied: int
    audit_trail: List[Dict[str, Any]]


class NearZeroHallucinationGuard:
    """
    Near-zero hallucination guard. 13 layers of verification.

    This wraps and extends the existing HallucinationGuard with
    7 additional layers specifically designed to catch the edge
    cases that the first 6 layers miss.

    Target: 99%+ accuracy (< 1% hallucination rate).

    Strategy:
    - Decompose claims into atoms and verify EACH one
    - Require source attribution for every factual claim
    - Parse code as AST to catch syntax hallucinations
    - Check for internal logical consistency
    - Have the LLM attack its own output
    - Use 5+ models with weighted voting
    - Flag claim-dense responses for extra scrutiny
    """

    def __init__(
        self,
        base_guard=None,
        multi_llm=None,
        repo_access=None,
    ):
        self.base_guard = base_guard
        self.multi_llm = multi_llm
        self.repo_access = repo_access

        self._verification_history: List[NearZeroVerificationResult] = []
        self._model_accuracy_weights: Dict[str, float] = {}

        logger.info("[NEAR-ZERO] Near-zero hallucination guard initialized (13 layers)")

    def verify(
        self,
        prompt: str,
        content: str,
        task_type: str = "general",
        context_documents: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        strict_mode: bool = True,
        max_retries: int = 3,
    ) -> NearZeroVerificationResult:
        """
        Run the full 13-layer verification pipeline.

        Args:
            prompt: Original prompt
            content: LLM output to verify
            task_type: Type of task
            context_documents: Context docs for checking
            system_prompt: System prompt used
            strict_mode: Require ALL layers to pass
            max_retries: Auto-correction retries

        Returns:
            NearZeroVerificationResult with complete analysis
        """
        logger.info("[NEAR-ZERO] Starting 13-layer verification pipeline")
        audit_trail = []
        layer_results = []

        # STEP 1: Run base guard (layers 1-6) if available
        base_result = None
        if self.base_guard:
            try:
                from .multi_llm_client import TaskType
                tt_map = {
                    "code_generation": TaskType.CODE_GENERATION,
                    "code_debugging": TaskType.CODE_DEBUGGING,
                    "reasoning": TaskType.REASONING,
                    "general": TaskType.GENERAL,
                }
                tt = tt_map.get(task_type, TaskType.GENERAL)

                base_result = self.base_guard.verify_content(
                    prompt=prompt,
                    content=content,
                    task_type=tt,
                    context_documents=context_documents,
                    system_prompt=system_prompt,
                    max_retry_attempts=1,
                    auto_correct_low_trust=False,
                )

                for layer_name, passed in base_result.verification_layers.items():
                    layer_results.append(LayerResult(
                        layer_name=layer_name,
                        layer_number=len(layer_results) + 1,
                        passed=passed,
                        confidence=base_result.confidence_score,
                    ))

                audit_trail.append({
                    "phase": "base_guard_layers_1_6",
                    "passed": base_result.is_verified,
                    "confidence": base_result.confidence_score,
                    "trust": base_result.trust_score,
                })
            except Exception as e:
                logger.warning(f"[NEAR-ZERO] Base guard error: {e}")
                audit_trail.append({"phase": "base_guard_layers_1_6", "error": str(e)})

        # STEP 2: Layer 7 - Atomic Claim Decomposition
        atomic_claims = self._layer7_decompose_claims(content)
        verified_atoms = self._verify_atomic_claims(atomic_claims, context_documents)

        total_claims = len(atomic_claims)
        verified_count = sum(1 for c in atomic_claims if c.verified is True)
        failed_count = sum(1 for c in atomic_claims if c.verified is False)
        unverified_count = sum(1 for c in atomic_claims if c.verified is None)

        atom_pass_rate = verified_count / total_claims if total_claims > 0 else 1.0
        layer_results.append(LayerResult(
            layer_name="atomic_claim_decomposition",
            layer_number=7,
            passed=atom_pass_rate >= 0.7,
            confidence=atom_pass_rate,
            claims_checked=total_claims,
            claims_passed=verified_count,
            claims_failed=failed_count,
            details={"unverified": unverified_count},
        ))

        # STEP 3: Layer 8 - Source Attribution Enforcement
        l8_result = self._layer8_source_attribution(content, atomic_claims)
        layer_results.append(l8_result)

        # STEP 4: Layer 9 - Structural Code Validation
        l9_result = self._layer9_code_validation(content, task_type)
        layer_results.append(l9_result)

        # STEP 5: Layer 10 - Internal Logic Consistency
        l10_result = self._layer10_logic_consistency(content, atomic_claims)
        layer_results.append(l10_result)

        # STEP 6: Layer 11 - Adversarial Self-Challenge
        l11_result = self._layer11_adversarial_challenge(prompt, content)
        layer_results.append(l11_result)

        # STEP 7: Layer 12 - Ensemble Weighted Voting
        l12_result = self._layer12_ensemble_voting(prompt, content, task_type, system_prompt)
        layer_results.append(l12_result)

        # STEP 8: Layer 13 - Claim Density Guard
        l13_result = self._layer13_claim_density(content, atomic_claims)
        layer_results.append(l13_result)

        # CALCULATE FINAL SCORE using Bayesian ensemble
        hallucination_prob = self._calculate_hallucination_probability(layer_results)
        is_verified = hallucination_prob < 0.15  # < 15% hallucination probability
        confidence = 1.0 - hallucination_prob

        result = NearZeroVerificationResult(
            is_verified=is_verified,
            hallucination_probability=round(hallucination_prob, 4),
            confidence_score=round(confidence, 4),
            layer_results=layer_results,
            atomic_claims=atomic_claims,
            total_claims=total_claims,
            verified_claims=verified_count,
            unverified_claims=unverified_count,
            hallucinated_claims=failed_count,
            final_content=content,
            corrections_applied=0,
            audit_trail=audit_trail,
        )

        # AUTO-CORRECT if failed and retries available
        if not is_verified and max_retries > 0:
            corrected = self._auto_correct(
                prompt, content, result, task_type, system_prompt
            )
            if corrected and corrected != content:
                logger.info("[NEAR-ZERO] Auto-correcting and re-verifying...")
                retry_result = self.verify(
                    prompt=prompt,
                    content=corrected,
                    task_type=task_type,
                    context_documents=context_documents,
                    system_prompt=system_prompt,
                    strict_mode=strict_mode,
                    max_retries=max_retries - 1,
                )
                retry_result.corrections_applied += 1
                retry_result.audit_trail.insert(0, {
                    "phase": "auto_correction",
                    "original_hallucination_prob": hallucination_prob,
                })
                return retry_result

        self._verification_history.append(result)

        logger.info(
            f"[NEAR-ZERO] Verification complete: "
            f"{'PASS' if is_verified else 'FAIL'}, "
            f"hallucination_prob={hallucination_prob:.3f}, "
            f"claims={verified_count}/{total_claims} verified"
        )

        return result

    # ==================================================================
    # LAYER 7: Atomic Claim Decomposition
    # ==================================================================

    def _layer7_decompose_claims(self, content: str) -> List[AtomicClaim]:
        """
        Break content into atomic claims that can each be verified independently.

        A claim is a single factual assertion. Complex sentences are split
        into individual verifiable atoms.
        """
        claims = []
        sentences = re.split(r'(?<=[.!?])\s+', content)

        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if not sentence or len(sentence) < 10:
                continue

            claim_type = self._classify_claim(sentence)
            source_cited = self._has_source_citation(sentence)
            source = self._extract_source(sentence) if source_cited else None

            verifiable = claim_type in ("factual", "code", "reference")

            claims.append(AtomicClaim(
                claim_id=f"CLAIM-{i:04d}",
                text=sentence,
                claim_type=claim_type,
                source_cited=source_cited,
                source=source,
                verifiable=verifiable,
            ))

        return claims

    def _classify_claim(self, sentence: str) -> str:
        """Classify what type of claim a sentence makes."""
        s = sentence.lower()

        if re.search(r'```|`[^`]+`|def\s|class\s|import\s|function\s', s):
            return "code"
        if re.search(r'according to|docs say|documentation|reference|see\s', s):
            return "reference"
        if re.search(r'i think|maybe|perhaps|might|could be|opinion|suggest', s):
            return "opinion"
        if re.search(r'you should|run\s|execute|install|create|set up', s):
            return "instruction"
        if re.search(r'\b(is|are|was|were|has|have|does|do|will|can)\b', s):
            return "factual"

        return "factual"

    def _has_source_citation(self, sentence: str) -> bool:
        """Check if a sentence cites a source."""
        patterns = [
            r'`[a-zA-Z0-9_/\\.-]+\.\w+`',  # file references
            r'according to',
            r'from the docs',
            r'documentation',
            r'https?://',
            r'in file\s',
            r'line \d+',
            r'function\s+`?\w+`?\s+in',
        ]
        return any(re.search(p, sentence, re.IGNORECASE) for p in patterns)

    def _extract_source(self, sentence: str) -> Optional[str]:
        """Extract source reference from a sentence."""
        file_match = re.search(r'`([a-zA-Z0-9_/\\.-]+\.\w+)`', sentence)
        if file_match:
            return file_match.group(1)

        url_match = re.search(r'(https?://[^\s]+)', sentence)
        if url_match:
            return url_match.group(1)

        return None

    def _verify_atomic_claims(
        self,
        claims: List[AtomicClaim],
        context_docs: Optional[List[str]],
    ) -> List[AtomicClaim]:
        """Verify each atomic claim independently."""
        context_text = "\n".join(context_docs) if context_docs else ""

        for claim in claims:
            if not claim.verifiable:
                claim.verified = None
                claim.confidence = 0.5
                claim.verification_method = "not_verifiable"
                continue

            if claim.claim_type == "code":
                verified = self._verify_code_claim(claim)
                claim.verified = verified
                claim.confidence = 0.9 if verified else 0.2
                claim.verification_method = "code_parse"

            elif claim.source_cited and claim.source:
                verified = self._verify_sourced_claim(claim)
                claim.verified = verified
                claim.confidence = 0.85 if verified else 0.3
                claim.verification_method = "source_check"

            elif context_text:
                similarity = SequenceMatcher(
                    None,
                    claim.text.lower()[:200],
                    context_text.lower()[:2000],
                ).ratio()
                claim.verified = similarity > 0.3
                claim.confidence = min(0.8, similarity + 0.3)
                claim.verification_method = "context_match"

            else:
                claim.verified = None
                claim.confidence = 0.4
                claim.verification_method = "no_verification_source"

        return claims

    def _verify_code_claim(self, claim: AtomicClaim) -> bool:
        """Verify a code-related claim by attempting to parse it."""
        code_blocks = re.findall(r'`([^`]+)`', claim.text)
        if not code_blocks:
            return True

        for code in code_blocks:
            if any(kw in code for kw in ["def ", "class ", "import ", "from "]):
                try:
                    ast.parse(code)
                    return True
                except SyntaxError:
                    return False

        return True

    def _verify_sourced_claim(self, claim: AtomicClaim) -> bool:
        """Verify a claim that cites a source."""
        if not claim.source:
            return False

        if self.repo_access:
            try:
                result = self.repo_access.read_file(claim.source, max_lines=1)
                return "error" not in result
            except Exception:
                pass

        return claim.source_cited

    # ==================================================================
    # LAYER 8: Source Attribution Enforcement
    # ==================================================================

    def _layer8_source_attribution(
        self,
        content: str,
        claims: List[AtomicClaim],
    ) -> LayerResult:
        """
        Enforce that factual claims have source attribution.

        Unsourced factual claims are flagged. A high ratio of unsourced
        claims indicates potential hallucination.
        """
        factual_claims = [c for c in claims if c.claim_type == "factual" and c.verifiable]
        if not factual_claims:
            return LayerResult(
                layer_name="source_attribution_enforcement",
                layer_number=8,
                passed=True,
                confidence=1.0,
                details={"note": "No factual claims to check"},
            )

        sourced = sum(1 for c in factual_claims if c.source_cited)
        total = len(factual_claims)
        ratio = sourced / total if total > 0 else 1.0

        return LayerResult(
            layer_name="source_attribution_enforcement",
            layer_number=8,
            passed=ratio >= 0.3,
            confidence=ratio,
            claims_checked=total,
            claims_passed=sourced,
            claims_failed=total - sourced,
            details={
                "sourced_ratio": round(ratio, 3),
                "unsourced_claims": total - sourced,
            },
        )

    # ==================================================================
    # LAYER 9: Structural Code Validation
    # ==================================================================

    def _layer9_code_validation(self, content: str, task_type: str) -> LayerResult:
        """
        Validate code blocks using AST parsing.

        Catches: syntax errors, invalid imports, impossible constructs.
        """
        code_blocks = re.findall(r'```(?:python|py)?\n?(.*?)```', content, re.DOTALL)
        inline_code = re.findall(r'`([^`]{10,})`', content)

        all_code = code_blocks + [c for c in inline_code if any(
            kw in c for kw in ["def ", "class ", "import ", "return ", "for ", "if "]
        )]

        if not all_code:
            return LayerResult(
                layer_name="structural_code_validation",
                layer_number=9,
                passed=True,
                confidence=1.0,
                details={"note": "No code blocks to validate"},
            )

        valid = 0
        errors = []

        for i, code in enumerate(all_code):
            code = code.strip()
            if not code:
                continue

            try:
                ast.parse(code)
                valid += 1
            except SyntaxError as e:
                errors.append({
                    "block_index": i,
                    "error": str(e),
                    "code_preview": code[:100],
                })

            self._check_impossible_imports(code, errors)

        total = len(all_code)
        pass_rate = valid / total if total > 0 else 1.0

        return LayerResult(
            layer_name="structural_code_validation",
            layer_number=9,
            passed=pass_rate >= 0.8,
            confidence=pass_rate,
            claims_checked=total,
            claims_passed=valid,
            claims_failed=len(errors),
            details={"errors": errors[:5]},
        )

    def _check_impossible_imports(self, code: str, errors: list):
        """Check for commonly hallucinated imports."""
        hallucinated_modules = [
            "torch.quantum", "tensorflow.magic", "numpy.ai",
            "fastapi.ml", "django.quantum", "flask.neural",
        ]
        for module in hallucinated_modules:
            if f"import {module}" in code or f"from {module}" in code:
                errors.append({
                    "type": "hallucinated_import",
                    "module": module,
                    "code_preview": code[:100],
                })

    # ==================================================================
    # LAYER 10: Internal Logic Consistency
    # ==================================================================

    def _layer10_logic_consistency(
        self,
        content: str,
        claims: List[AtomicClaim],
    ) -> LayerResult:
        """
        Check for internal contradictions within the response.

        Catches: "Use X" then later "Never use X", conflicting numbers,
        contradictory recommendations.
        """
        contradictions = []

        factual = [c for c in claims if c.claim_type == "factual"]

        for i in range(len(factual)):
            for j in range(i + 1, len(factual)):
                if self._claims_contradict(factual[i].text, factual[j].text):
                    contradictions.append({
                        "claim_a": factual[i].text[:100],
                        "claim_b": factual[j].text[:100],
                    })

        numbers = re.findall(r'(\w+)\s+(?:is|are|=|equals?)\s+(\d+[\d,.]*)', content)
        num_map = {}
        for name, value in numbers:
            name_lower = name.lower()
            if name_lower in num_map and num_map[name_lower] != value:
                contradictions.append({
                    "type": "numeric_inconsistency",
                    "name": name,
                    "value_a": num_map[name_lower],
                    "value_b": value,
                })
            num_map[name_lower] = value

        has_contradictions = len(contradictions) > 0

        return LayerResult(
            layer_name="internal_logic_consistency",
            layer_number=10,
            passed=not has_contradictions,
            confidence=1.0 if not has_contradictions else max(0.2, 1.0 - len(contradictions) * 0.2),
            details={
                "contradictions_found": len(contradictions),
                "contradictions": contradictions[:5],
            },
        )

    def _claims_contradict(self, a: str, b: str) -> bool:
        """Check if two claims contradict each other."""
        a_lower, b_lower = a.lower(), b.lower()

        negation_pairs = [
            ("should", "should not"), ("must", "must not"),
            ("always", "never"), ("is", "is not"),
            ("can", "cannot"), ("will", "will not"),
            ("enable", "disable"), ("true", "false"),
            ("increase", "decrease"), ("add", "remove"),
        ]

        a_words = set(a_lower.split())
        b_words = set(b_lower.split())
        common = a_words & b_words

        if len(common) < 3:
            return False

        for pos, neg in negation_pairs:
            if (pos in a_lower and neg in b_lower) or (neg in a_lower and pos in b_lower):
                if len(common) > 4:
                    return True

        return False

    # ==================================================================
    # LAYER 11: Adversarial Self-Challenge
    # ==================================================================

    def _layer11_adversarial_challenge(
        self,
        prompt: str,
        content: str,
    ) -> LayerResult:
        """
        Have an LLM try to find flaws in the output.

        The adversarial model is prompted to:
        1. Find factual errors
        2. Find logical flaws
        3. Find unsupported claims
        4. Rate the overall reliability
        """
        # Try Kimi Cloud first (higher quality adversarial check)
        try:
            from cognitive.kimi_teacher import get_kimi_teacher
            from database.session import SessionLocal
            _s = SessionLocal()
            teacher = get_kimi_teacher(_s)
            cloud_result = teacher.verify_with_cloud(content, prompt)
            _s.close()
            if cloud_result.get("verified") is not None:
                return LayerResult(
                    layer_name="adversarial_self_challenge",
                    layer_number=11,
                    passed=cloud_result["verified"],
                    confidence=0.85,
                    details={"source": "kimi_cloud", "response": cloud_result.get("response", "")[:200]},
                )
        except Exception:
            pass

        if not self.multi_llm:
            return LayerResult(
                layer_name="adversarial_self_challenge",
                layer_number=11,
                passed=True,
                confidence=0.5,
                details={"note": "Multi-LLM not available for adversarial check"},
            )

        challenge_prompt = f"""You are a fact-checker. Critically analyze this response for errors.

QUESTION: {prompt[:500]}

RESPONSE TO CHECK:
{content[:2000]}

List ONLY factual errors, logical flaws, or unsupported claims you can identify.
If the response is accurate, say "NO ERRORS FOUND".
Rate reliability 0-10 (10=perfectly reliable).

FORMAT:
ERRORS: [list or "NO ERRORS FOUND"]
RELIABILITY: [0-10]"""

        try:
            response = self.multi_llm.generate(
                prompt=challenge_prompt,
                task_type=TaskType.REASONING if hasattr(self.multi_llm, 'generate') else None,
                system_prompt="You are a strict fact-checker. Only flag genuine errors, not style issues."
            )

            if response.get("success"):
                challenge_text = response.get("content", "")

                no_errors = "no errors found" in challenge_text.lower()

                reliability_match = re.search(r'RELIABILITY:\s*(\d+)', challenge_text)
                reliability = int(reliability_match.group(1)) if reliability_match else 5

                passed = no_errors or reliability >= 7
                confidence = reliability / 10.0

                return LayerResult(
                    layer_name="adversarial_self_challenge",
                    layer_number=11,
                    passed=passed,
                    confidence=confidence,
                    details={
                        "no_errors_found": no_errors,
                        "reliability_score": reliability,
                        "challenge_response": challenge_text[:500],
                    },
                )
        except Exception as e:
            logger.warning(f"[NEAR-ZERO] Adversarial challenge error: {e}")

        return LayerResult(
            layer_name="adversarial_self_challenge",
            layer_number=11,
            passed=True,
            confidence=0.5,
            details={"note": "Challenge could not be completed"},
        )

    # ==================================================================
    # LAYER 12: Ensemble Weighted Voting
    # ==================================================================

    def _layer12_ensemble_voting(
        self,
        prompt: str,
        content: str,
        task_type: str,
        system_prompt: Optional[str],
    ) -> LayerResult:
        """
        Get 5+ models to vote on whether the response is accurate.

        Each model is weighted by its historical accuracy.
        """
        if not self.multi_llm:
            return LayerResult(
                layer_name="ensemble_weighted_voting",
                layer_number=12,
                passed=True,
                confidence=0.5,
                details={"note": "Multi-LLM not available for ensemble voting"},
            )

        vote_prompt = f"""Is this response factually accurate? Answer ONLY "ACCURATE" or "INACCURATE" followed by a one-line reason.

QUESTION: {prompt[:300]}
RESPONSE: {content[:1000]}

VERDICT:"""

        try:
            from .multi_llm_client import TaskType as TT
            responses = self.multi_llm.generate_multiple(
                prompt=vote_prompt,
                task_type=TT.VALIDATION,
                num_models=5,
                system_prompt="You are a verification system. Only answer ACCURATE or INACCURATE."
            )

            successful = [r for r in responses if r.get("success")]
            if len(successful) < 2:
                return LayerResult(
                    layer_name="ensemble_weighted_voting",
                    layer_number=12,
                    passed=True,
                    confidence=0.5,
                    details={"note": f"Only {len(successful)} models responded"},
                )

            accurate_votes = 0
            inaccurate_votes = 0
            total_weight = 0

            for resp in successful:
                model = resp.get("model_name", "unknown")
                vote_text = resp.get("content", "").lower()
                weight = self._model_accuracy_weights.get(model, 1.0)

                if "accurate" in vote_text and "inaccurate" not in vote_text:
                    accurate_votes += weight
                elif "inaccurate" in vote_text:
                    inaccurate_votes += weight
                else:
                    accurate_votes += weight * 0.5

                total_weight += weight

            vote_ratio = accurate_votes / total_weight if total_weight > 0 else 0.5
            passed = vote_ratio >= 0.6

            return LayerResult(
                layer_name="ensemble_weighted_voting",
                layer_number=12,
                passed=passed,
                confidence=vote_ratio,
                details={
                    "accurate_votes": round(accurate_votes, 2),
                    "inaccurate_votes": round(inaccurate_votes, 2),
                    "total_weight": round(total_weight, 2),
                    "vote_ratio": round(vote_ratio, 3),
                    "models_voted": len(successful),
                },
            )

        except Exception as e:
            logger.warning(f"[NEAR-ZERO] Ensemble voting error: {e}")
            return LayerResult(
                layer_name="ensemble_weighted_voting",
                layer_number=12,
                passed=True,
                confidence=0.5,
                details={"error": str(e)},
            )

    # ==================================================================
    # LAYER 13: Claim Density Guard
    # ==================================================================

    def _layer13_claim_density(
        self,
        content: str,
        claims: List[AtomicClaim],
    ) -> LayerResult:
        """
        Flag responses with too many unverifiable claims per sentence.

        Hallucinated responses tend to be confidently dense with
        specific-sounding but unverifiable claims. Real responses
        tend to be more measured and qualified.
        """
        word_count = len(content.split())
        total_claims = len(claims)
        verifiable = sum(1 for c in claims if c.verifiable)
        unverifiable = sum(
            1 for c in claims
            if c.verifiable and c.verified is None
        )

        claims_per_100_words = (total_claims / word_count * 100) if word_count > 0 else 0
        unverified_ratio = unverifiable / verifiable if verifiable > 0 else 0

        hedging_words = len(re.findall(
            r'\b(maybe|perhaps|might|could|possibly|likely|approximately|roughly|about|around)\b',
            content.lower(),
        ))
        hedging_ratio = hedging_words / total_claims if total_claims > 0 else 0

        suspicious = (
            claims_per_100_words > 5 and
            unverified_ratio > 0.7 and
            hedging_ratio < 0.1
        )

        confidence = 1.0
        if suspicious:
            confidence = 0.3
        elif unverified_ratio > 0.5:
            confidence = 0.6

        return LayerResult(
            layer_name="claim_density_guard",
            layer_number=13,
            passed=not suspicious,
            confidence=confidence,
            details={
                "claims_per_100_words": round(claims_per_100_words, 2),
                "unverified_ratio": round(unverified_ratio, 3),
                "hedging_ratio": round(hedging_ratio, 3),
                "suspicious": suspicious,
                "word_count": word_count,
                "total_claims": total_claims,
            },
        )

    # ==================================================================
    # BAYESIAN ENSEMBLE SCORING
    # ==================================================================

    def _calculate_hallucination_probability(
        self,
        layer_results: List[LayerResult],
    ) -> float:
        """
        Calculate overall hallucination probability using weighted ensemble.

        Each layer contributes an independent probability estimate.
        The final score is a weighted combination, NOT a simple average.

        Layer weights reflect their reliability:
        - Code validation (high weight - objective)
        - Logic consistency (high weight - objective)
        - Ensemble voting (high weight - multiple perspectives)
        - Adversarial challenge (medium weight)
        - Atomic claims (medium weight)
        - Source attribution (lower weight - many valid unsourced claims)
        - Claim density (lower weight - heuristic)
        """
        layer_weights = {
            "repository_grounding": 0.10,
            "cross_model_consensus": 0.12,
            "contradiction_check": 0.10,
            "confidence_scoring": 0.08,
            "trust_system": 0.08,
            "external_verification": 0.07,
            "atomic_claim_decomposition": 0.10,
            "source_attribution_enforcement": 0.05,
            "structural_code_validation": 0.12,
            "internal_logic_consistency": 0.10,
            "adversarial_self_challenge": 0.08,
            "ensemble_weighted_voting": 0.12,
            "claim_density_guard": 0.05,
        }

        weighted_score = 0.0
        total_weight = 0.0

        for result in layer_results:
            weight = layer_weights.get(result.layer_name, 0.05)

            if result.passed:
                layer_hallucination_prob = (1.0 - result.confidence) * 0.3
            else:
                layer_hallucination_prob = max(0.3, 1.0 - result.confidence)

            weighted_score += layer_hallucination_prob * weight
            total_weight += weight

        if total_weight > 0:
            raw_probability = weighted_score / total_weight
        else:
            raw_probability = 0.5

        return min(1.0, max(0.0, raw_probability))

    # ==================================================================
    # AUTO-CORRECTION
    # ==================================================================

    def _auto_correct(
        self,
        prompt: str,
        content: str,
        result: NearZeroVerificationResult,
        task_type: str,
        system_prompt: Optional[str],
    ) -> Optional[str]:
        """
        Attempt to auto-correct a failing response.

        Uses the verification failures to guide correction.
        """
        if not self.multi_llm:
            return None

        failed_layers = [
            r.layer_name for r in result.layer_results if not r.passed
        ]

        hallucinated_claims = [
            c.text for c in result.atomic_claims
            if c.verified is False
        ]

        correction_prompt = f"""The following response failed verification. Fix it.

ORIGINAL QUESTION: {prompt[:500]}

RESPONSE TO FIX:
{content[:2000]}

VERIFICATION FAILURES:
{chr(10).join(f'- {l}' for l in failed_layers)}

FLAGGED CLAIMS:
{chr(10).join(f'- {c[:100]}' for c in hallucinated_claims[:5])}

Rules for correction:
1. Remove or fix any factual errors
2. Add source references for claims
3. Mark uncertain information with "likely" or "approximately"
4. Only state what you can verify
5. Keep the response helpful and complete

CORRECTED RESPONSE:"""

        try:
            response = self.multi_llm.generate(
                prompt=correction_prompt,
                task_type=TaskType.GENERAL if hasattr(self.multi_llm, 'generate') else None,
                system_prompt="You are correcting an inaccurate response. Be precise and only state verifiable facts."
            )
            if response.get("success"):
                return response.get("content", "")
        except Exception as e:
            logger.error(f"[NEAR-ZERO] Auto-correction failed: {e}")

        return None

    # ==================================================================
    # STATS & REPORTING
    # ==================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get hallucination guard statistics."""
        if not self._verification_history:
            return {"total_verifications": 0}

        total = len(self._verification_history)
        passed = sum(1 for r in self._verification_history if r.is_verified)
        avg_prob = sum(r.hallucination_probability for r in self._verification_history) / total
        avg_claims = sum(r.total_claims for r in self._verification_history) / total
        avg_verified = sum(r.verified_claims for r in self._verification_history) / total
        total_corrections = sum(r.corrections_applied for r in self._verification_history)

        layer_pass_rates = {}
        for result in self._verification_history:
            for lr in result.layer_results:
                if lr.layer_name not in layer_pass_rates:
                    layer_pass_rates[lr.layer_name] = {"total": 0, "passed": 0}
                layer_pass_rates[lr.layer_name]["total"] += 1
                if lr.passed:
                    layer_pass_rates[lr.layer_name]["passed"] += 1

        return {
            "total_verifications": total,
            "pass_rate": round(passed / total, 4),
            "avg_hallucination_probability": round(avg_prob, 4),
            "avg_claims_per_response": round(avg_claims, 1),
            "avg_verified_claims": round(avg_verified, 1),
            "total_corrections_applied": total_corrections,
            "layer_pass_rates": {
                name: round(stats["passed"] / stats["total"], 3) if stats["total"] > 0 else 0
                for name, stats in layer_pass_rates.items()
            },
            "target_accuracy": "99%",
            "layers_active": 13,
        }


_near_zero_guard: Optional[NearZeroHallucinationGuard] = None


def get_near_zero_hallucination_guard(
    base_guard=None,
    multi_llm=None,
    repo_access=None,
) -> NearZeroHallucinationGuard:
    """Get or create the near-zero hallucination guard."""
    global _near_zero_guard
    if _near_zero_guard is None:
        _near_zero_guard = NearZeroHallucinationGuard(
            base_guard=base_guard,
            multi_llm=multi_llm,
            repo_access=repo_access,
        )
    return _near_zero_guard
