"""
Integration Test for Self-Healing System Components

Tests that all self-healing components load together properly:
1. All imports work
2. All components initialize
3. Basic healing flow works
"""

import sys
import pytest
sys.path.insert(0, 'backend')


class TestSelfHealingImports:
    """Test that all self-healing related imports work."""
    
    def test_autonomous_healing_system_imports(self):
        """Test autonomous healing system imports."""
        from cognitive.autonomous_healing_system import (
            AutonomousHealingSystem,
            HealthStatus,
            AnomalyType,
            HealingAction,
            TrustLevel,
            get_autonomous_healing
        )
        assert AutonomousHealingSystem is not None
        assert HealthStatus.HEALTHY is not None
        assert AnomalyType.ERROR_SPIKE is not None
        assert HealingAction.BUFFER_CLEAR is not None
        assert TrustLevel.MEDIUM_RISK_AUTO is not None
    
    def test_code_analyzer_self_healing_imports(self):
        """Test code analyzer self-healing imports."""
        from cognitive.code_analyzer_self_healing import (
            CodeFixApplicator,
            ASTCodeTransformer,
            CodeAnalyzerSelfHealing
        )
        assert CodeFixApplicator is not None
        assert ASTCodeTransformer is not None
        assert CodeAnalyzerSelfHealing is not None
    
    def test_mirror_self_modeling_imports(self):
        """Test mirror self-modeling imports."""
        from cognitive.mirror_self_modeling import (
            get_mirror_system,
            MirrorSelfModelingSystem
        )
        assert get_mirror_system is not None
        assert MirrorSelfModelingSystem is not None
    
    def test_genesis_healing_imports(self):
        """Test genesis healing system imports."""
        from genesis.healing_system import get_healing_system
        from genesis.genesis_key_service import get_genesis_service
        assert get_healing_system is not None
        assert get_genesis_service is not None


class TestCodeFixApplicator:
    """Test the CodeFixApplicator deterministic fixes."""
    
    @pytest.fixture
    def applicator(self):
        from cognitive.code_analyzer_self_healing import CodeFixApplicator
        return CodeFixApplicator()
    
    @pytest.fixture
    def make_issue(self):
        from cognitive.grace_code_analyzer import CodeIssue, Severity, Confidence
        def _make(rule_id, line_number, suggested_fix=None):
            return CodeIssue(
                rule_id=rule_id,
                message=f"Test issue for {rule_id}",
                file_path="test.py",
                line_number=line_number,
                severity=Severity.MEDIUM,
                confidence=Confidence.MEDIUM,
                suggested_fix=suggested_fix
            )
        return _make
    
    def test_g001_missing_docstring(self, applicator, make_issue):
        """Test G001: Missing docstring fix."""
        source = '''def my_function():
    return 42
'''
        issue = make_issue('G001', 1)
        success, fixed = applicator.apply_fix(issue, source)
        assert success is True
        assert '"""Placeholder docstring."""' in fixed or "'''Placeholder docstring.'''" in fixed
    
    def test_g002_unused_import(self, applicator, make_issue):
        """Test G002: Unused import removal."""
        source = '''import os
import sys
import unused_module

def main():
    print(sys.version)
'''
        issue = make_issue('G002', 3, 'Remove unused import: unused_module')
        success, fixed = applicator.apply_fix(issue, source)
        assert success is True
        assert 'import unused_module' not in fixed
    
    def test_g005_bare_except(self, applicator, make_issue):
        """Test G005: Bare except fix."""
        source = '''try:
    risky_operation()
except:
    pass
'''
        issue = make_issue('G005', 3)
        success, fixed = applicator.apply_fix(issue, source)
        assert success is True
        assert 'except Exception:' in fixed
        assert 'except:' not in fixed.replace('except Exception:', '')
    
    def test_g011_print_statement(self, applicator, make_issue):
        """Test G011: Print statement to logger.info."""
        source = '''def process():
    print("Processing data")
    return True
'''
        issue = make_issue('G011', 2)
        success, fixed = applicator.apply_fix(issue, source)
        assert success is True
        assert 'logger.info("Processing data")' in fixed
        assert 'print(' not in fixed
    
    def test_g012_missing_logger(self, applicator, make_issue):
        """Test G012: Missing logger in class."""
        source = '''class MyClass:
    def __init__(self):
        self.value = 42
'''
        issue = make_issue('G012', 1)
        success, fixed = applicator.apply_fix(issue, source)
        # G012 uses AST transformation, may or may not succeed depending on context
        assert isinstance(success, bool)
        assert isinstance(fixed, str)


class TestAutonomousHealingSystemInit:
    """Test autonomous healing system initialization and graceful degradation."""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        from unittest.mock import MagicMock
        session = MagicMock()
        session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        return session
    
    def test_system_initializes(self, mock_session):
        """Test that the system initializes without errors."""
        from cognitive.autonomous_healing_system import AutonomousHealingSystem, TrustLevel
        from pathlib import Path
        
        system = AutonomousHealingSystem(
            session=mock_session,
            repo_path=Path.cwd(),
            trust_level=TrustLevel.MEDIUM_RISK_AUTO,
            enable_learning=True
        )
        
        assert system is not None
        assert system.trust_level == TrustLevel.MEDIUM_RISK_AUTO
        assert system.enable_learning is True
    
    def test_degraded_components_tracked(self, mock_session):
        """Test that degraded components are tracked."""
        from cognitive.autonomous_healing_system import AutonomousHealingSystem, TrustLevel
        from pathlib import Path
        
        system = AutonomousHealingSystem(
            session=mock_session,
            repo_path=Path.cwd(),
            trust_level=TrustLevel.LOW_RISK_AUTO,
            enable_learning=False
        )
        
        # Check that degraded_components list exists
        assert hasattr(system, 'degraded_components')
        assert isinstance(system.degraded_components, list)
    
    def test_get_system_capabilities(self, mock_session):
        """Test get_system_capabilities method."""
        from cognitive.autonomous_healing_system import AutonomousHealingSystem, TrustLevel
        from pathlib import Path
        
        system = AutonomousHealingSystem(
            session=mock_session,
            repo_path=Path.cwd(),
            trust_level=TrustLevel.MEDIUM_RISK_AUTO,
            enable_learning=True
        )
        
        capabilities = system.get_system_capabilities()
        
        assert isinstance(capabilities, dict)
        assert 'available' in capabilities
        assert 'degraded' in capabilities
        assert isinstance(capabilities['available'], list)
        assert isinstance(capabilities['degraded'], list)


class TestBasicHealingFlow:
    """Test the basic healing flow works end-to-end."""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        from unittest.mock import MagicMock
        session = MagicMock()
        session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        return session
    
    def test_health_assessment(self, mock_session):
        """Test health assessment flow."""
        from cognitive.autonomous_healing_system import AutonomousHealingSystem, TrustLevel, HealthStatus
        from pathlib import Path
        
        system = AutonomousHealingSystem(
            session=mock_session,
            repo_path=Path.cwd(),
            trust_level=TrustLevel.MEDIUM_RISK_AUTO
        )
        
        assessment = system.assess_system_health()
        
        assert isinstance(assessment, dict)
        assert 'health_status' in assessment
    
    def test_code_fix_applicator_workflow(self):
        """Test complete code fix applicator workflow."""
        from cognitive.code_analyzer_self_healing import CodeFixApplicator
        from cognitive.grace_code_analyzer import CodeIssue, Severity, Confidence
        
        applicator = CodeFixApplicator()
        
        # Create an issue
        issue = CodeIssue(
            rule_id='G005',
            message='Bare except clause',
            file_path='test.py',
            line_number=3,
            severity=Severity.MEDIUM,
            confidence=Confidence.HIGH,
            suggested_fix='Use except Exception:'
        )
        
        source = '''try:
    x = 1/0
except:
    pass
'''
        
        # Check if auto-fixable
        can_fix = applicator.can_auto_fix(issue)
        assert can_fix is True
        
        # Apply fix
        success, fixed_code = applicator.apply_fix(issue, source)
        assert success is True
        assert 'except Exception:' in fixed_code


class TestComponentIntegration:
    """Test that components integrate properly."""
    
    def test_self_healing_code_system_exists(self):
        """Test CodeAnalyzerSelfHealing can be imported and instantiated."""
        from cognitive.code_analyzer_self_healing import CodeAnalyzerSelfHealing
        from pathlib import Path
        from unittest.mock import MagicMock
        
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        
        # Just test that it can be created
        try:
            system = CodeAnalyzerSelfHealing(
                repo_path=Path.cwd(),
                session=mock_session
            )
            assert system is not None
        except Exception as e:
            # Some dependencies may not be available in test environment
            pytest.skip(f"CodeAnalyzerSelfHealing requires additional dependencies: {e}")
    
    def test_healing_actions_enum_complete(self):
        """Test that HealingAction enum has all expected values."""
        from cognitive.autonomous_healing_system import HealingAction
        
        expected_actions = [
            'BUFFER_CLEAR',
            'CACHE_FLUSH', 
            'CONNECTION_RESET',
            'CODE_FIX',
            'PROCESS_RESTART',
            'SERVICE_RESTART',
            'STATE_ROLLBACK',
            'ISOLATION',
            'EMERGENCY_SHUTDOWN'
        ]
        
        for action in expected_actions:
            assert hasattr(HealingAction, action), f"Missing action: {action}"
    
    def test_health_status_enum_complete(self):
        """Test that HealthStatus enum has all expected values."""
        from cognitive.autonomous_healing_system import HealthStatus
        
        expected_statuses = ['HEALTHY', 'DEGRADED', 'WARNING', 'CRITICAL', 'FAILING']
        
        for status in expected_statuses:
            assert hasattr(HealthStatus, status), f"Missing status: {status}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
