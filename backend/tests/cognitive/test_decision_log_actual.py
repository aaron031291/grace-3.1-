import pytest
from datetime import datetime, timezone
import tempfile
import json
import os
from pathlib import Path
from backend.cognitive.decision_log import DecisionLogger

class MockAmbiguityLedger:
    def to_dict(self):
        return {"ambiguities": 0}

class MockDecisionContext:
    def __init__(self, d_id):
        self.decision_id = d_id
        self.problem_statement = "Fix something"
        self.goal = "It works"
        self.success_criteria = "Tests pass"
        self.parent_decision_id = None
        self.created_at = datetime.now(timezone.utc)
        self.ambiguity_ledger = MockAmbiguityLedger()
        self.impact_scope = "system"
        self.is_reversible = True
        self.complexity_score = 0.5
        self.benefit_score = 0.8

def test_decision_logger_logic():
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = DecisionLogger(log_dir=tmpdir)
        ctx = MockDecisionContext("dec-1")
        
        # Test start
        logger.log_decision_start(ctx)
        
        # Test alternatives
        logger.log_alternatives("dec-1", [{"name": "A"}, {"name": "B"}], {"name": "A"})
        
        # Test complete
        logger.log_decision_complete(ctx, "Done")
        
        # Check in-memory logs
        logs = logger.get_decision_log("dec-1")
        assert len(logs) == 3
        assert logs[0]["event"] == "decision_start"
        assert logs[1]["event"] == "alternatives_considered"
        assert logs[2]["event"] == "decision_complete"
        
        # Also check generating report
        report = logger.generate_decision_report("dec-1")
        assert "Decision Report: dec-1" in report
        assert "DECISION_START" in report
        
        # Check files
        date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        daily_log = Path(tmpdir) / f"decisions_{date_str}.jsonl"
        dec_log = Path(tmpdir) / "dec-1.jsonl"
        
        assert daily_log.exists()
        assert dec_log.exists()
        
        # Verify JSON
        with open(dec_log, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 3
            entry = json.loads(lines[0])
            assert entry["decision_id"] == "dec-1"

if __name__ == "__main__":
    pytest.main(['-v', __file__])
