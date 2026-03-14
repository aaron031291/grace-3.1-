import pytest
from backend.genesis.code_analyzer import CodeAnalyzer, CodeIssue, get_code_analyzer

@pytest.fixture
def analyzer():
    return get_code_analyzer()

def test_analyze_python_syntax_error(analyzer):
    code = "def bad_func()\n    pass" # Missing colon
    issues = analyzer.analyze_python_code(code)
    
    assert len(issues) >= 1
    syntax_issues = [i for i in issues if i.issue_type == "syntax_error"]
    assert len(syntax_issues) == 1
    assert syntax_issues[0].severity == "critical"
    
def test_analyze_python_ast_issues(analyzer):
    code = """def bad_defaults(arg=[]):
    try:
        pass
    except:
        pass"""
        
    issues = analyzer.analyze_python_code(code)
    
    types = [i.issue_type for i in issues]
    assert "mutable_default" in types
    assert "bare_except" in types

def test_analyze_python_common_patterns(analyzer):
    code = """def do_something():
    print("hello")
    # TODO: fix this
    long_variable_name = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    """
    
    issues = analyzer.analyze_python_code(code)
    types = [i.issue_type for i in issues]
    
    assert "print_statement" in types
    assert "todo_comment" in types
    assert "line_too_long" in types

def test_analyze_javascript(analyzer):
    code = """
    function test() {
        console.log("here");
        var x = 1;
        if (x == 1) {
            return true;
        }
    }
    """
    
    issues = analyzer.analyze_javascript_code(code)
    types = [i.issue_type for i in issues]
    
    assert "console_log" in types
    assert "var_usage" in types
    assert "loose_equality" in types

def test_generate_fix_code(analyzer):
    code = "var x = 1;"
    issue = CodeIssue(
        issue_type="var_usage",
        severity="medium",
        line_number=1,
        column=0,
        message="",
        suggested_fix="const x = 1;",
        fix_confidence=1.0,
        context=""
    )
    
    fixed = analyzer.generate_fix_code(issue, code)
    assert fixed == "const x = 1;"

if __name__ == "__main__":
    pytest.main(['-v', __file__])
