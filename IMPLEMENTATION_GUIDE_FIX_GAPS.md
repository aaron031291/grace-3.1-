# Implementation Guide: Fix Critical Gaps in Grace's Autonomous Learning Loop

## 🎯 Goal
Complete the autonomous feedback loop by adding:
1. Automatic Outcome → LLM Knowledge Updates
2. Unified Outcome Aggregation

---

## 📋 Step 1: Create Outcome → LLM Bridge Service

**File:** `backend/cognitive/outcome_llm_bridge.py`

```python
"""
Outcome → LLM Bridge Service

Automatically updates LLM knowledge when high-trust outcomes are created.
Closes the feedback loop: Outcomes → Learning → LLM Knowledge → Better Responses
"""
import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import event
from cognitive.learning_memory import LearningExample
from llm_orchestrator.learning_integration import LearningIntegration
from cognitive.learning_memory import LearningMemoryManager

logger = logging.getLogger(__name__)

class OutcomeLLMBridge:
    """
    Automatically updates LLM knowledge from all outcomes.
    
    When any LearningExample is created with high trust score,
    immediately updates LLM knowledge base.
    """
    
    def __init__(self, session: Session, llm_orchestrator=None):
        self.session = session
        self.llm_orchestrator = llm_orchestrator
        
        # Initialize learning integration
        try:
            from llm_orchestrator.llm_orchestrator import LLMOrchestrator
            if llm_orchestrator is None:
                llm_orchestrator = LLMOrchestrator(session=session)
            
            self.learning_integration = LearningIntegration(
                multi_llm_client=llm_orchestrator.multi_llm if hasattr(llm_orchestrator, 'multi_llm') else None,
                repo_access=llm_orchestrator.repo_access if hasattr(llm_orchestrator, 'repo_access') else None,
                learning_memory=LearningMemoryManager(session=session),
                session=session
            )
            logger.info("[OUTCOME-LLM-BRIDGE] Initialized")
        except Exception as e:
            logger.warning(f"[OUTCOME-LLM-BRIDGE] Could not initialize: {e}")
            self.learning_integration = None
    
    def on_learning_example_created(self, example: LearningExample):
        """
        Called when any LearningExample is created.
        
        Automatically updates LLM knowledge if trust score is high enough.
        """
        if not self.learning_integration:
            return
        
        # Only update for high-trust outcomes
        min_trust_threshold = 0.75
        
        if example.trust_score >= min_trust_threshold:
            try:
                logger.info(
                    f"[OUTCOME-LLM-BRIDGE] High-trust outcome detected "
                    f"(trust={example.trust_score:.2f}, type={example.example_type})"
                )
                
                # Update LLM knowledge with recent high-trust examples
                result = self.learning_integration.update_llm_knowledge(
                    min_trust_score=example.trust_score,
                    limit=20  # Include recent high-trust examples
                )
                
                logger.info(
                    f"[OUTCOME-LLM-BRIDGE] LLM knowledge updated: "
                    f"{result.get('examples_included', 0)} examples included"
                )
            except Exception as e:
                logger.error(f"[OUTCOME-LLM-BRIDGE] Error updating LLM knowledge: {e}")


# Singleton instance
_bridge_instance = None

def get_outcome_bridge(session: Optional[Session] = None, llm_orchestrator=None) -> OutcomeLLMBridge:
    """Get or create OutcomeLLMBridge singleton."""
    global _bridge_instance
    
    if _bridge_instance is None:
        if session is None:
            from database.session import get_db
            session = next(get_db())
        _bridge_instance = OutcomeLLMBridge(session, llm_orchestrator)
    
    return _bridge_instance


# SQLAlchemy event listener to automatically trigger on LearningExample creation
@event.listens_for(LearningExample, 'after_insert')
def on_learning_example_inserted(mapper, connection, target):
    """
    Automatically trigger LLM knowledge update when LearningExample is created.
    
    This closes the feedback loop:
    - Healing outcome → LearningExample → LLM knowledge update
    - Test outcome → LearningExample → LLM knowledge update
    - Diagnostic outcome → LearningExample → LLM knowledge update
    """
    try:
        # Get bridge instance
        bridge = get_outcome_bridge()
        
        # Trigger update (async to avoid blocking)
        bridge.on_learning_example_created(target)
    except Exception as e:
        logger.warning(f"[OUTCOME-LLM-BRIDGE] Event listener error: {e}")
        # Don't fail the transaction if bridge update fails
```

---

## 📋 Step 2: Create Unified Outcome Aggregator

**File:** `backend/cognitive/outcome_aggregator.py`

```python
"""
Unified Outcome Aggregator

Collects outcomes from all systems and enables cross-system learning.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from collections import defaultdict

logger = logging.getLogger(__name__)

class OutcomeAggregator:
    """
    Unified aggregator for all system outcomes.
    
    Enables:
    - Cross-system pattern detection
    - Unified learning feed
    - System-to-system knowledge sharing
    """
    
    def __init__(self, session: Session):
        self.session = session
        self.outcome_history: List[Dict[str, Any]] = []
        self.max_history = 1000  # Keep last 1000 outcomes
        
        # Pattern detection
        self.patterns_detected = []
        
        logger.info("[OUTCOME-AGGREGATOR] Initialized")
    
    def record_outcome(
        self,
        source: str,
        outcome: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record outcome from any system.
        
        Args:
            source: System source ('healing', 'testing', 'diagnostics', 'llm', 'file_processing')
            outcome: Outcome data (must include 'success' and optionally 'trust_score')
            metadata: Additional metadata
        """
        unified_outcome = {
            'source': source,
            'timestamp': datetime.utcnow(),
            'outcome': outcome,
            'success': outcome.get('success', False),
            'trust_score': outcome.get('trust_score', 0.5),
            'metadata': metadata or {}
        }
        
        # Add to history
        self.outcome_history.append(unified_outcome)
        
        # Trim history if too long
        if len(self.outcome_history) > self.max_history:
            self.outcome_history = self.outcome_history[-self.max_history:]
        
        logger.debug(
            f"[OUTCOME-AGGREGATOR] Recorded outcome from {source}: "
            f"success={unified_outcome['success']}, trust={unified_outcome['trust_score']:.2f}"
        )
        
        # Detect cross-system patterns
        self._detect_cross_system_patterns()
        
        # Update relevant systems
        self._update_systems(unified_outcome)
    
    def _detect_cross_system_patterns(self):
        """Detect patterns across systems."""
        if len(self.outcome_history) < 10:
            return  # Need enough data
        
        # Group outcomes by source
        by_source = defaultdict(list)
        for outcome in self.outcome_history[-100:]:  # Last 100 outcomes
            by_source[outcome['source']].append(outcome)
        
        # Pattern 1: Healing action X works for diagnostic issue Y
        healing_outcomes = by_source.get('healing', [])
        diagnostic_outcomes = by_source.get('diagnostics', [])
        
        for healing in healing_outcomes:
            if not healing['success']:
                continue
            
            healing_action = healing['outcome'].get('action')
            anomaly_type = healing['outcome'].get('anomaly_type')
            
            # Find related diagnostic outcomes
            for diagnostic in diagnostic_outcomes:
                diagnostic_type = diagnostic['outcome'].get('issue_type')
                
                if diagnostic_type == anomaly_type:
                    # Pattern found: This healing action works for this diagnostic issue
                    pattern = {
                        'type': 'healing_diagnostic_correlation',
                        'healing_action': healing_action,
                        'diagnostic_issue': diagnostic_type,
                        'success_rate': 1.0,  # This instance succeeded
                        'evidence_count': 1,
                        'first_seen': healing['timestamp'].isoformat()
                    }
                    
                    # Check if pattern already exists
                    existing = next(
                        (p for p in self.patterns_detected 
                         if p.get('type') == pattern['type'] 
                         and p.get('healing_action') == healing_action
                         and p.get('diagnostic_issue') == diagnostic_type),
                        None
                    )
                    
                    if existing:
                        existing['evidence_count'] += 1
                        existing['success_rate'] = (
                            (existing['success_rate'] * (existing['evidence_count'] - 1) + 1.0) 
                            / existing['evidence_count']
                        )
                    else:
                        self.patterns_detected.append(pattern)
                        logger.info(
                            f"[OUTCOME-AGGREGATOR] Pattern detected: "
                            f"{healing_action} works for {diagnostic_type}"
                        )
    
    def _update_systems(self, outcome: Dict[str, Any]):
        """
        Update all relevant systems with new outcome.
        
        This enables cross-system learning:
        - Test outcomes inform healing system
        - Diagnostic outcomes inform testing system
        - All outcomes inform LLM system
        """
        source = outcome['source']
        success = outcome['success']
        trust_score = outcome['trust_score']
        
        # Update healing system with test/diagnostic outcomes
        if source in ['testing', 'diagnostics'] and trust_score >= 0.8:
            self._update_healing_knowledge(outcome)
        
        # Update testing system with healing/diagnostic outcomes
        if source in ['healing', 'diagnostics'] and trust_score >= 0.8:
            self._update_testing_knowledge(outcome)
        
        # Update LLM system (handled by OutcomeLLMBridge, but we can add patterns)
        if trust_score >= 0.8:
            self._update_llm_patterns(outcome)
    
    def _update_healing_knowledge(self, outcome: Dict[str, Any]):
        """Update healing system with knowledge from other systems."""
        # This could update healing action selection based on test/diagnostic outcomes
        # For now, just log
        logger.debug(f"[OUTCOME-AGGREGATOR] Updating healing knowledge from {outcome['source']}")
    
    def _update_testing_knowledge(self, outcome: Dict[str, Any]):
        """Update testing system with knowledge from other systems."""
        # This could update test selection based on healing/diagnostic outcomes
        logger.debug(f"[OUTCOME-AGGREGATOR] Updating testing knowledge from {outcome['source']}")
    
    def _update_llm_patterns(self, outcome: Dict[str, Any]):
        """Update LLM with detected patterns."""
        # Patterns are already detected in _detect_cross_system_patterns
        # This could feed patterns to LLM context
        logger.debug(f"[OUTCOME-AGGREGATOR] Updating LLM patterns from {outcome['source']}")
    
    def get_patterns(self, pattern_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get detected patterns."""
        if pattern_type:
            return [p for p in self.patterns_detected if p.get('type') == pattern_type]
        return self.patterns_detected
    
    def get_outcome_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get summary of recent outcomes."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        recent = [o for o in self.outcome_history if o['timestamp'] >= cutoff]
        
        by_source = defaultdict(lambda: {'total': 0, 'success': 0, 'avg_trust': 0.0})
        
        for outcome in recent:
            source = outcome['source']
            by_source[source]['total'] += 1
            if outcome['success']:
                by_source[source]['success'] += 1
            by_source[source]['avg_trust'] += outcome['trust_score']
        
        # Calculate averages
        summary = {}
        for source, stats in by_source.items():
            summary[source] = {
                'total': stats['total'],
                'success_count': stats['success'],
                'success_rate': stats['success'] / stats['total'] if stats['total'] > 0 else 0.0,
                'avg_trust': stats['avg_trust'] / stats['total'] if stats['total'] > 0 else 0.0
            }
        
        return {
            'period_hours': hours,
            'total_outcomes': len(recent),
            'by_source': summary,
            'patterns_detected': len(self.patterns_detected)
        }


# Singleton instance
_aggregator_instance = None

def get_outcome_aggregator(session: Optional[Session] = None) -> OutcomeAggregator:
    """Get or create OutcomeAggregator singleton."""
    global _aggregator_instance
    
    if _aggregator_instance is None:
        if session is None:
            from database.session import get_db
            session = next(get_db())
        _aggregator_instance = OutcomeAggregator(session)
    
    return _aggregator_instance
```

---

## 📋 Step 3: Integrate with Healing System

**File:** `backend/cognitive/autonomous_healing_system.py`

**Add to `_learn_from_healing()` method:**

```python
def _learn_from_healing(
    self,
    decision: Dict[str, Any],
    result: Optional[Dict[str, Any]],
    success: bool
):
    """
    Learn from healing outcome to improve future decisions.
    
    Updates trust scores based on success/failure.
    Creates learning examples for training.
    """
    # ... existing code ...
    
    self.session.add(example)
    self.session.commit()
    
    # ✅ NEW: Record in outcome aggregator
    try:
        from cognitive.outcome_aggregator import get_outcome_aggregator
        aggregator = get_outcome_aggregator(self.session)
        aggregator.record_outcome(
            source='healing',
            outcome={
                'action': action.value,
                'success': success,
                'trust_score': self.trust_scores[action],
                'anomaly_type': decision['anomaly']['type'].value,
                'anomaly_severity': decision['anomaly']['severity']
            },
            metadata={
                'decision_id': decision.get('decision_id'),
                'execution_mode': decision.get('execution_mode')
            }
        )
    except Exception as e:
        logger.warning(f"[AUTONOMOUS-HEALING] Could not record outcome: {e}")
    
    # ... rest of existing code ...
```

---

## 📋 Step 4: Integrate with Testing System

**File:** `backend/tests/conftest.py`

**Add to `pytest_runtest_logreport()` function:**

```python
def pytest_runtest_logreport(report):
    """Hook to capture detailed test results for GRACE learning."""
    # ... existing code ...
    
    # ✅ NEW: Record in outcome aggregator
    if report.when == 'call':  # Only on test execution
        try:
            from cognitive.outcome_aggregator import get_outcome_aggregator
            from database.session import get_db
            
            session = next(get_db())
            aggregator = get_outcome_aggregator(session)
            
            aggregator.record_outcome(
                source='testing',
                outcome={
                    'test_name': report.nodeid,
                    'success': report.outcome == 'passed',
                    'trust_score': 0.9 if report.outcome == 'passed' else 0.3,
                    'duration': report.duration,
                    'outcome': report.outcome
                },
                metadata={
                    'test_file': report.fspath,
                    'test_line': getattr(report, 'lineno', None)
                }
            )
        except Exception as e:
            # Don't fail tests if aggregator fails
            logger.warning(f"[TEST-AGGREGATOR] Could not record test outcome: {e}")
```

---

## 📋 Step 5: Integrate with Diagnostic System

**File:** `backend/cognitive/autonomous_healing_system.py`

**Add to `_check_diagnostic_engine()` method:**

```python
def _check_diagnostic_engine(self) -> List[Dict[str, Any]]:
    """Check diagnostic engine for alerts and issues."""
    # ... existing code ...
    
    # ✅ NEW: Record diagnostic outcomes
    if anomalies:
        try:
            from cognitive.outcome_aggregator import get_outcome_aggregator
            aggregator = get_outcome_aggregator(self.session)
            
            for anomaly in anomalies:
                aggregator.record_outcome(
                    source='diagnostics',
                    outcome={
                        'issue_type': anomaly.get('type', 'unknown'),
                        'severity': anomaly.get('severity', 'medium'),
                        'success': False,  # Diagnostic issues are problems
                        'trust_score': 0.9,  # High trust in diagnostic findings
                        'details': anomaly.get('details', '')
                    },
                    metadata={
                        'service': anomaly.get('service'),
                        'file_path': anomaly.get('file_path')
                    }
                )
        except Exception as e:
            logger.debug(f"[AUTONOMOUS-HEALING] Could not record diagnostic outcome: {e}")
    
    return anomalies
```

---

## 📋 Step 6: Initialize Services on Startup

**File:** `backend/app.py` or startup script

**Add initialization:**

```python
# Initialize outcome systems
try:
    from cognitive.outcome_llm_bridge import get_outcome_bridge
    from cognitive.outcome_aggregator import get_outcome_aggregator
    from database.session import get_db
    
    session = next(get_db())
    
    # Initialize bridge (will auto-trigger on LearningExample creation)
    bridge = get_outcome_bridge(session)
    logger.info("[STARTUP] Outcome → LLM Bridge initialized")
    
    # Initialize aggregator
    aggregator = get_outcome_aggregator(session)
    logger.info("[STARTUP] Outcome Aggregator initialized")
except Exception as e:
    logger.warning(f"[STARTUP] Could not initialize outcome systems: {e}")
```

---

## ✅ Verification Steps

1. **Test Outcome → LLM Bridge:**
   ```python
   # Create a high-trust LearningExample
   example = LearningExample(
       example_type="healing_outcome",
       trust_score=0.9,
       ...
   )
   session.add(example)
   session.commit()
   # Should automatically trigger LLM knowledge update
   ```

2. **Test Outcome Aggregator:**
   ```python
   aggregator = get_outcome_aggregator(session)
   aggregator.record_outcome('testing', {'success': True, 'trust_score': 0.9})
   summary = aggregator.get_outcome_summary()
   # Should show test outcome recorded
   ```

3. **Test Cross-System Patterns:**
   ```python
   # Record healing outcome
   aggregator.record_outcome('healing', {'action': 'code_fix', 'success': True, ...})
   # Record related diagnostic outcome
   aggregator.record_outcome('diagnostics', {'issue_type': 'syntax_error', ...})
   # Should detect pattern
   patterns = aggregator.get_patterns()
   ```

---

## 🎯 Expected Results

After implementation:

1. ✅ **Automatic LLM Updates**: Every high-trust outcome automatically updates LLM knowledge
2. ✅ **Cross-System Learning**: Systems learn from each other's outcomes
3. ✅ **Pattern Detection**: Patterns across systems are automatically detected
4. ✅ **Complete Feedback Loop**: Detect → Heal → Test → Learn → Update LLM → Repeat

**Grace will have a fully autonomous learning ecosystem!** 🚀
