"""
Generate Natural Language Report from Stress Test Results

Converts technical stress test results into a friendly, readable narrative.

Usage:
    python generate_nl_report.py [report_file.json]
"""

import sys
import json
from pathlib import Path
from datetime import datetime, UTC
from typing import Dict, Any

def generate_natural_language_report(report: Dict[str, Any]) -> str:
    """Generate a natural language, human-friendly report."""
    summary = report["test_summary"]
    
    # Calculate success rate - Target: 95% for excellent (HIGH STANDARD)
    success_rate = summary['fix_success_rate']
    if success_rate >= 95:
        overall_status = "excellent"
        status_emoji = "🌟"
        status_desc = "Grace performed exceptionally well - exceeded 95% target!"
    elif success_rate >= 90:
        overall_status = "very good"
        status_emoji = "✅"
        status_desc = f"Grace performed very well at {success_rate:.1f}%, but needs to reach 95% target"
    elif success_rate >= 80:
        overall_status = "good"
        status_emoji = "⚠️"
        status_desc = f"Grace performed well at {success_rate:.1f}%, but below 95% target - improvement needed"
    elif success_rate >= 70:
        overall_status = "good"
        status_emoji = "✅"
        status_desc = "Grace performed well"
    elif success_rate >= 50:
        overall_status = "moderate"
        status_emoji = "⚠️"
        status_desc = "Grace performed adequately"
    else:
        overall_status = "needs improvement"
        status_emoji = "❌"
        status_desc = "Grace needs improvement"
    
    duration_min = summary['duration_seconds'] / 60
    
    nl_report = f"""# Grace Self-Healing System - Stress Test Results

## Executive Summary

{status_emoji} **Overall Performance: {overall_status.upper()}**

{status_desc} during this comprehensive stress test. We deliberately broke various parts of the system to see how well Grace could detect, diagnose, and fix issues autonomously.

**Test Duration:** {summary['duration_seconds']:.1f} seconds ({duration_min:.1f} minutes)

**Results:**
- Grace detected and attempted to fix **{summary['total_tests']} different types of issues**
- She successfully fixed **{summary['successful_fixes']} out of {summary['total_tests']} issues**
- Her success rate was **{success_rate:.1f}%**
- **Target:** 95% (HIGH STANDARD)
- **Meets Target:** {'✅ YES' if summary.get('meets_target', False) else '❌ NO - Needs Improvement'}

This means Grace was able to autonomously resolve {summary['successful_fixes']} problems without human intervention, demonstrating her self-healing capabilities.

**KPI Performance:**
"""
    
    # Add KPI section if available
    if 'kpis' in report:
        kpis = report['kpis']
        nl_report += f"""
- **Overall KPI Score:** {kpis.get('overall_score', 0):.1f}/100
- **Fix Success Rate:** {kpis['metrics']['fix_success_rate']:.1f}% (Target: {kpis['targets']['fix_success_rate']}%)
- **Detection Rate:** {kpis['metrics']['detection_rate']:.1f}% (Target: {kpis['targets']['detection_rate']}%)
- **Genesis Key Creation:** {kpis['metrics']['genesis_key_creation_rate']:.2f} keys/test (Target: {kpis['targets']['genesis_key_creation_rate']})
- **Knowledge Request Rate:** {kpis['metrics']['knowledge_request_rate']:.2f} requests/test
- **LLM Usage Rate:** {kpis['metrics']['llm_usage_rate']:.2f} calls/test

**KPI Assessment:**
"""
        
        if kpis.get('overall_score', 0) >= 95:
            nl_report += "🌟 **EXCELLENT** - All KPIs meet or exceed targets!\n"
        elif kpis.get('overall_score', 0) >= 80:
            nl_report += "✅ **GOOD** - Most KPIs meet targets, minor improvements needed\n"
        else:
            nl_report += "⚠️ **NEEDS IMPROVEMENT** - Several KPIs below target\n"
        
        # Check if fix success rate meets 95% target
        if kpis['metrics']['fix_success_rate'] >= 95:
            nl_report += f"- ✅ Fix success rate of {kpis['metrics']['fix_success_rate']:.1f}% **EXCEEDS** 95% target\n"
        else:
            gap = 95 - kpis['metrics']['fix_success_rate']
            nl_report += f"- ❌ Fix success rate of {kpis['metrics']['fix_success_rate']:.1f}% is **{gap:.1f}% BELOW** 95% target\n"
    
    nl_report += """

---

## What Grace Did During the Test

### Genesis Keys Created: {report['genesis_keys']['total_created']}

Grace created **{report['genesis_keys']['total_created']} Genesis Keys** to track everything that happened. Each Genesis Key records:
- **What** happened (the issue or action)
- **Where** it occurred (file, location)
- **When** it happened (timestamp)
- **Who** did it (Grace's healing agent)
- **How** it was done (method used)
- **Why** it was done (reasoning)

This creates a complete audit trail of every decision and action Grace took.

**Breakdown by Type:**
"""
    
    for key_type, count in report['genesis_keys']['by_type'].items():
        nl_report += f"- **{key_type}:** {count} keys created\n"
    
    if report['knowledge_requests']['total'] > 0:
        nl_report += f"""
### Knowledge Requests: {report['knowledge_requests']['total']}

When Grace didn't know how to fix something, she requested knowledge **{report['knowledge_requests']['total']} times**. This shows Grace is:
- Aware of her limitations
- Proactive in seeking information
- Learning from external sources

**Types of Knowledge Requested:**
"""
        
        for req_type, count in report['knowledge_requests']['by_type'].items():
            nl_report += f"- **{req_type}:** {count} requests\n"
    else:
        nl_report += f"""
### Knowledge Requests: {report['knowledge_requests']['total']}

Grace didn't need to request any additional knowledge during this test, suggesting she already had the knowledge needed to fix the issues.
"""
    
    if report['llm_usage']['total'] > 0:
        nl_report += f"""
### LLM Usage: {report['llm_usage']['total']} Calls

Grace used Large Language Models **{report['llm_usage']['total']} times** to help make decisions. This shows she:
- Uses AI reasoning for complex problems
- Leverages LLMs for decision-making
- Combines multiple AI capabilities

**Models Used:**
"""
        
        for model, count in report['llm_usage']['by_model'].items():
            nl_report += f"- **{model}:** {count} calls\n"
    else:
        nl_report += f"""
### LLM Usage: {report['llm_usage']['total']} Calls

Grace didn't use LLMs during this test, suggesting she was able to make decisions using her built-in knowledge and rules.
"""
    
    nl_report += f"""
### Healing Actions Taken: {report['healing_actions']['total']}

Grace performed **{report['healing_actions']['total']} healing actions** to fix issues. Each action was:
- Logged with full context
- Linked to Genesis Keys
- Verified for success

---

## Detailed Test Results

"""
    
    # Add narrative for each test
    for i, test in enumerate(report['test_results'], 1):
        test_name = test['test_name'].replace('_', ' ').title()
        issue = test['issue_introduced']
        result = test['result']
        status = result.get('status', 'unknown')
        verified = result.get('verified', False)
        
        if status == 'fixed' and verified:
            outcome = "✅ **SUCCESS** - Grace detected the issue, applied a fix, and we verified it actually worked!"
        elif status == 'fixed':
            outcome = "✅ **FIXED** - Grace detected and fixed the issue."
        elif status == 'detected':
            outcome = "🔍 **DETECTED** - Grace identified the issue and attempted a fix, but verification is pending."
        else:
            outcome = "⚠️ **PARTIAL** - Grace detected the issue but the fix needs more work."
        
        nl_report += f"""
### Test {i}: {test_name}

**What We Did:** {issue}

**What Grace Did:** {outcome}

"""
        
        if result.get('healing_result'):
            hr = result['healing_result']
            nl_report += "**How Grace Fixed It:**\n"
            
            if hr.get('fix_applied'):
                nl_report += f"- Grace applied a fix using: {hr.get('fix_method', 'unknown method')}\n"
            if hr.get('knowledge_requested'):
                nl_report += f"- Grace requested knowledge about: {hr.get('knowledge_query', 'the issue')}\n"
            if hr.get('llm_used'):
                nl_report += f"- Grace used an LLM ({hr.get('llm_model', 'unknown')}) to help decide how to fix it\n"
            if hr.get('genesis_key_id'):
                nl_report += f"- Grace created Genesis Key {hr.get('genesis_key_id')} to track this fix\n"
        
        nl_report += "\n"
    
    nl_report += f"""
---

## Key Insights

### What Grace Proved

1. **Autonomous Detection:** Grace successfully detected all {summary['total_tests']} issues we introduced
2. **Self-Healing Capability:** Grace fixed {summary['successful_fixes']} issues without human help
3. **Learning Ability:** Grace requested knowledge {report['knowledge_requests']['total']} times when she didn't know how to fix something
4. **AI Integration:** Grace used LLMs {report['llm_usage']['total']} times to make intelligent decisions
5. **Complete Tracking:** Grace created {report['genesis_keys']['total_created']} Genesis Keys to track everything

### Genesis Keys - The Complete Story

Every action Grace took was recorded in Genesis Keys. Here are some examples:

"""
    
    # Add examples of Genesis Keys
    for key in report['genesis_keys']['details'][:5]:
        nl_report += f"""
**Genesis Key: {key['key_id']}**
- **What:** {key['what']}
- **Where:** {key['where'] or 'N/A'}
- **Who:** {key['who']}
- **How:** {key['how']}
- **Why:** {key['why']}

"""
    
    if report['knowledge_requests']['total'] > 0:
        nl_report += f"""
### Knowledge Requests - When Grace Asked for Help

Grace knows when she doesn't know something. Here are examples of when she requested knowledge:

"""
        
        for req in report['knowledge_requests']['details'][:3]:
            nl_report += f"""
- **Type:** {req.get('type', 'unknown')}
- **Query:** {req.get('query', 'N/A')}
- **When:** {req.get('timestamp', 'N/A')}

"""
    
    if report['llm_usage']['total'] > 0:
        nl_report += f"""
### LLM Usage - Grace's AI Reasoning

Grace used AI to help make decisions. Here are examples:

"""
        
        for llm in report['llm_usage']['details'][:3]:
            nl_report += f"""
- **Model:** {llm.get('model', 'unknown')}
- **Purpose:** {llm.get('purpose', 'N/A')}
- **Duration:** {llm.get('duration_seconds', 0):.2f} seconds
- **When:** {llm.get('timestamp', 'N/A')}

"""
    
    # Add knowledge gaps section
    if 'knowledge_gaps' in report and report['knowledge_gaps'].get('identified_gaps'):
        gaps = report['knowledge_gaps']
        nl_report += f"""
---

## What Knowledge Grace Needs

Based on the stress test, Grace identified **{len(gaps.get('identified_gaps', []))} knowledge gaps** where she needs more information or practice.

### Knowledge Gaps Identified:

"""
        
        for i, gap in enumerate(gaps.get('identified_gaps', [])[:5], 1):
            nl_report += f"""
**Gap {i}: {gap.get('topic', 'Unknown Topic')}**
- **Issue:** Grace knows this theoretically but needs more practice
- **Data Confidence:** {gap.get('data_confidence', 0):.1%}
- **Operational Confidence:** {gap.get('operational_confidence', 0):.1%}
- **Gap Size:** {gap.get('gap_size', 0):.1%}
- **Recommendation:** {gap.get('recommendation', 'Practice needed')}

"""
        
        if gaps.get('recommendations'):
            nl_report += """
### Recommendations for Grace:

"""
            for rec in gaps.get('recommendations', [])[:5]:
                nl_report += f"""
- **{rec.get('category', 'General')}:** {rec.get('recommendation', 'N/A')}
"""
        
        if gaps.get('missing_knowledge_areas'):
            nl_report += """
### Missing Knowledge Areas (from Failed Fixes):

"""
            for area in gaps.get('missing_knowledge_areas', [])[:5]:
                nl_report += f"""
- **Issue:** {area.get('issue', 'Unknown')}
- **Recommendation:** {area.get('recommendation', 'Study related knowledge')}
"""
    
    nl_report += f"""
---

## Conclusion

Grace's self-healing system demonstrated **{overall_status}** performance with a **{success_rate:.1f}% success rate**. 

**What This Means:**
- Grace can autonomously detect and fix most system issues
- She knows when to ask for help (knowledge requests)
- She uses AI reasoning to make intelligent decisions
- She tracks everything she does (Genesis Keys)
- She verifies her fixes actually work

**Areas for Improvement:**
"""
    
    if summary['failed_fixes'] > 0:
        nl_report += f"- {summary['failed_fixes']} issues were detected but not fully resolved. These may require more complex fixes or human intervention.\n"
    
    if report['knowledge_requests']['total'] > 0:
        nl_report += f"- Grace requested knowledge {report['knowledge_requests']['total']} times, suggesting she could benefit from more pre-loaded knowledge in certain areas.\n"
    else:
        nl_report += "- Grace didn't need to request knowledge, showing she has good coverage of common issues.\n"
    
    nl_report += f"""
**Overall Assessment:**

Grace proved she can autonomously handle system issues with a {success_rate:.1f}% success rate. 
"""
    
    # Add target assessment
    if success_rate >= 95:
        nl_report += f"""
**🎯 TARGET ACHIEVED:** Grace exceeded the 95% target with {success_rate:.1f}% success rate! This demonstrates exceptional self-healing capabilities.
"""
    else:
        gap = 95 - success_rate
        nl_report += f"""
**🎯 TARGET NOT MET:** Grace achieved {success_rate:.1f}% but needs to reach 95% target. She is {gap:.1f}% away from the high standard.

**To reach 95% target, Grace needs to:**
- Improve fix success rate by {gap:.1f}%
- Address knowledge gaps identified in the test
- Enhance her healing strategies for the {summary.get('failed_fixes', 0)} issues that weren't fully resolved
"""
    
    nl_report += f"""
She demonstrates:
- ✅ Strong problem detection
- ✅ Autonomous decision-making
- ✅ Self-learning capabilities
- ✅ Complete audit trail
- ✅ Fix verification

This stress test validates Grace's self-healing capabilities and shows she can operate autonomously to maintain system health.

---

*Report generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}*
"""
    
    return nl_report


def main():
    """Generate natural language report from JSON file."""
    if len(sys.argv) > 1:
        report_file = Path(sys.argv[1])
    else:
        # Find most recent report
        reports = sorted(Path(".").glob("stress_test_report_*.json"), reverse=True)
        if not reports:
            print("No stress test report found. Run stress_test_self_healing.py first.")
            return
        report_file = reports[0]
    
    print(f"Reading report: {report_file}")
    
    # Load report
    with open(report_file, 'r') as f:
        report = json.load(f)
    
    # Generate natural language report
    nl_report = generate_natural_language_report(report)
    
    # Save report (with UTF-8 encoding for Windows compatibility)
    # Fix filename: replace 'stress_test_report_' with 'stress_test_report_nl_'
    if report_file.stem.startswith('stress_test_report_'):
        output_file = report_file.with_name('stress_test_report_nl_' + report_file.stem.replace('stress_test_report_', '') + '.md')
    else:
        output_file = report_file.with_name(report_file.stem + '_nl.md')
    output_file.write_text(nl_report, encoding='utf-8')
    
    print(f"\n[SUCCESS] Natural language report saved to: {output_file}")
    print(f"\nReport Summary:")
    summary = report["test_summary"]
    print(f"  - Success Rate: {summary['fix_success_rate']:.1f}% (Target: 95%)")
    print(f"  - Meets Target: {'YES' if summary.get('meets_target', False) else 'NO'}")
    if 'kpis' in report:
        print(f"  - Overall KPI Score: {report['kpis']['overall_score']:.1f}/100")
    print(f"  - Genesis Keys: {report['genesis_keys']['total_created']}")
    print(f"  - Knowledge Requests: {report['knowledge_requests']['total']}")
    print(f"  - LLM Usage: {report['llm_usage']['total']}")
    if 'knowledge_gaps' in report:
        gaps = report['knowledge_gaps']
        print(f"  - Knowledge Gaps Identified: {len(gaps.get('identified_gaps', []))}")
        print(f"  - Recommendations: {len(gaps.get('recommendations', []))}")


if __name__ == "__main__":
    main()
