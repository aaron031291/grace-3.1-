#!/usr/bin/env python3
"""
Diagnose MBPP Performance Regression Using Genesis Keys

Analyzes Genesis Keys to understand what changed between 50% pass rate
and current 4.6% (or 0%) pass rate.
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def analyze_results_file(results_file: Path) -> Dict[str, Any]:
    """Analyze MBPP results file."""
    with open(results_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    results = data.get('results', {})
    individual_results = results.get('results', [])
    
    # Analyze errors
    error_types = {}
    function_name_errors = 0
    generation_methods = {}
    
    for result in individual_results:
        # Count generation methods
        method = result.get('generation_method', 'unknown')
        generation_methods[method] = generation_methods.get(method, 0) + 1
        
        # Analyze errors
        error = result.get('error', '')
        if error:
            # Check for NameError (function name issues)
            if 'NameError' in error:
                function_name_errors += 1
                # Extract function name from error
                import re
                match = re.search(r"name '(\w+)' is not defined", error)
                if match:
                    func_name = match.group(1)
                    error_types[f"NameError: {func_name}"] = error_types.get(f"NameError: {func_name}", 0) + 1
            
            # Check for other error types
            for err_type in ['TypeError', 'ValueError', 'SyntaxError', 'AttributeError', 'IndexError', 'KeyError']:
                if err_type in error:
                    error_types[err_type] = error_types.get(err_type, 0) + 1
    
    return {
        'total': results.get('total', 0),
        'passed': results.get('passed', 0),
        'failed': results.get('failed', 0),
        'pass_rate': results.get('pass_rate', 0),
        'timestamp': data.get('timestamp', ''),
        'error_types': error_types,
        'function_name_errors': function_name_errors,
        'generation_methods': generation_methods,
        'sample_errors': [r.get('error', '')[:200] for r in individual_results[:5] if r.get('error')]
    }


def query_genesis_keys_for_mbpp_changes(session, days_back: int = 7) -> List[Dict[str, Any]]:
    """Query Genesis Keys for MBPP-related changes."""
    try:
        from backend.models.genesis_key_models import GenesisKey, GenesisKeyType
        from sqlalchemy import and_
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        # Find Genesis Keys related to MBPP, benchmarking, or code generation
        keys = session.query(GenesisKey).filter(
            and_(
                GenesisKey.when_timestamp >= cutoff_date,
                or_(
                    GenesisKey.what_description.ilike('%mbpp%'),
                    GenesisKey.what_description.ilike('%benchmark%'),
                    GenesisKey.file_path.ilike('%mbpp%'),
                    GenesisKey.file_path.ilike('%benchmark%'),
                    GenesisKey.error_message.ilike('%NameError%'),
                    GenesisKey.error_message.ilike('%function%')
                )
            )
        ).order_by(GenesisKey.when_timestamp.desc()).limit(100).all()
        
        return [
            {
                'key_id': key.key_id,
                'what': key.what_description,
                'where': key.where_location,
                'when': key.when_timestamp.isoformat(),
                'file_path': key.file_path,
                'error_type': key.error_type,
                'error_message': key.error_message,
                'code_before': key.code_before[:200] if key.code_before else None,
                'code_after': key.code_after[:200] if key.code_after else None
            }
            for key in keys
        ]
    except Exception as e:
        logger.error(f"Error querying Genesis Keys: {e}")
        return []


def analyze_code_changes(genesis_keys: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze code changes from Genesis Keys."""
    changes_by_file = {}
    error_patterns = {}
    
    for key in genesis_keys:
        file_path = key.get('file_path', 'unknown')
        if file_path not in changes_by_file:
            changes_by_file[file_path] = {
                'changes': 0,
                'errors': 0,
                'recent_changes': []
            }
        
        changes_by_file[file_path]['changes'] += 1
        
        if key.get('error_type'):
            changes_by_file[file_path]['errors'] += 1
            error_type = key.get('error_type', 'Unknown')
            error_patterns[error_type] = error_patterns.get(error_type, 0) + 1
        
        changes_by_file[file_path]['recent_changes'].append({
            'when': key.get('when'),
            'what': key.get('what', '')[:100],
            'error': key.get('error_message', '')[:100] if key.get('error_message') else None
        })
    
    return {
        'changes_by_file': changes_by_file,
        'error_patterns': error_patterns,
        'total_changes': len(genesis_keys)
    }


def main():
    """Main diagnostic function."""
    print("="*80)
    print("MBPP PERFORMANCE REGRESSION DIAGNOSIS")
    print("="*80)
    
    # Analyze current results
    results_file = Path("full_mbpp_results_parallel.json")
    if not results_file.exists():
        print(f"\n✗ Results file not found: {results_file}")
        return
    
    print(f"\n[1] Analyzing Results File: {results_file}")
    current_results = analyze_results_file(results_file)
    
    print(f"\n  Current Performance:")
    print(f"    Total: {current_results['total']}")
    print(f"    Passed: {current_results['passed']}")
    print(f"    Failed: {current_results['failed']}")
    print(f"    Pass Rate: {current_results['pass_rate']*100:.2f}%")
    print(f"    Timestamp: {current_results['timestamp']}")
    
    print(f"\n  Error Analysis:")
    print(f"    Function Name Errors: {current_results['function_name_errors']}")
    print(f"    Error Types:")
    for err_type, count in sorted(current_results['error_types'].items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"      {err_type}: {count}")
    
    print(f"\n  Generation Methods:")
    for method, count in current_results['generation_methods'].items():
        print(f"    {method}: {count}")
    
    # Query Genesis Keys
    print(f"\n[2] Querying Genesis Keys for Recent Changes...")
    try:
        from backend.database.session import initialize_session_factory
        session_factory = initialize_session_factory()
        session = session_factory()
        
        genesis_keys = query_genesis_keys_for_mbpp_changes(session, days_back=7)
        print(f"    Found {len(genesis_keys)} relevant Genesis Keys")
        
        if genesis_keys:
            changes_analysis = analyze_code_changes(genesis_keys)
            
            print(f"\n  Code Changes Analysis:")
            print(f"    Total changes tracked: {changes_analysis['total_changes']}")
            print(f"    Files modified:")
            for file_path, info in sorted(changes_analysis['changes_by_file'].items(), 
                                         key=lambda x: x[1]['changes'], reverse=True)[:10]:
                print(f"      {file_path}: {info['changes']} changes, {info['errors']} errors")
            
            print(f"\n  Error Patterns in Changes:")
            for err_type, count in sorted(changes_analysis['error_patterns'].items(), 
                                         key=lambda x: x[1], reverse=True):
                print(f"      {err_type}: {count}")
        else:
            print("    No relevant Genesis Keys found")
        
        session.close()
    except Exception as e:
        logger.error(f"Error accessing Genesis Keys: {e}")
        import traceback
        traceback.print_exc()
    
    # Root cause analysis
    print(f"\n[3] Root Cause Analysis:")
    print(f"\n  Key Issues Identified:")
    
    issues = []
    
    # Issue 1: Function name errors
    if current_results['function_name_errors'] > 0:
        issues.append({
            'severity': 'CRITICAL',
            'issue': 'Function Name Mismatch',
            'count': current_results['function_name_errors'],
            'description': 'Generated code uses wrong function names (e.g., solve_task instead of expected name)',
            'impact': f'Causes {current_results["function_name_errors"]} NameError failures'
        })
    
    # Issue 2: Low pass rate
    if current_results['pass_rate'] < 0.1:
        issues.append({
            'severity': 'CRITICAL',
            'issue': 'Extremely Low Pass Rate',
            'count': current_results['pass_rate'] * 100,
            'description': f'Pass rate dropped to {current_results["pass_rate"]*100:.1f}%',
            'impact': 'System is not generating correct code'
        })
    
    # Issue 3: Generation method distribution
    template_count = current_results['generation_methods'].get('template', 0) + \
                    current_results['generation_methods'].get('template_fallback', 0)
    llm_count = current_results['generation_methods'].get('llm', 0) + \
                current_results['generation_methods'].get('template_llm_collaboration', 0)
    
    if llm_count > 0 and template_count == 0:
        issues.append({
            'severity': 'HIGH',
            'issue': 'Templates Not Being Used',
            'count': llm_count,
            'description': 'All code generated by LLM, templates not matching',
            'impact': 'Missing template-based solutions that might work better'
        })
    
    for issue in issues:
        print(f"\n    [{issue['severity']}] {issue['issue']}")
        print(f"      Count: {issue['count']}")
        print(f"      Description: {issue['description']}")
        print(f"      Impact: {issue['impact']}")
    
    # Recommendations
    print(f"\n[4] Recommendations:")
    print(f"\n  1. Fix Function Name Extraction:")
    print(f"     - Ensure function names are extracted from test cases")
    print(f"     - Pass function name explicitly to LLM prompts")
    print(f"     - Post-process code to fix function names")
    
    print(f"\n  2. Verify Template Matching:")
    print(f"     - Check if templates are being loaded correctly")
    print(f"     - Verify template matching logic")
    print(f"     - Ensure template-LLM collaboration is working")
    
    print(f"\n  3. Check Recent Code Changes:")
    print(f"     - Review Genesis Keys for recent modifications")
    print(f"     - Check if fixes broke existing functionality")
    print(f"     - Verify parallel integration is using correct code paths")
    
    print(f"\n  4. Test Individual Components:")
    print(f"     - Test function name extraction separately")
    print(f"     - Test template matching on known problems")
    print(f"     - Test LLM generation with explicit function names")
    
    print("\n" + "="*80)


if __name__ == "__main__":
    main()
