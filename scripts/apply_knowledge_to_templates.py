#!/usr/bin/env python3
"""
Apply Knowledge-Driven Enhancements to Templates

Uses successful patterns, research best practices, and learning memory
to automatically improve templates.
"""

import json
import sys
from pathlib import Path
import re

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

def load_recommendations():
    """Load template enhancement recommendations."""
    rec_file = project_root / "template_enhancement_recommendations.json"
    
    if not rec_file.exists():
        print(f"ERROR: {rec_file} not found. Run enhance_templates_from_knowledge.py first.")
        return None
    
    with open(rec_file) as f:
        return json.load(f)

def analyze_template_gaps():
    """Analyze gaps in current templates vs successful patterns."""
    from backend.benchmarking.mbpp_templates import TEMPLATES
    
    recs = load_recommendations()
    if not recs:
        return
    
    successful_patterns = recs["successful_patterns"]
    recommendations = recs["recommendations"]
    
    # Get current template keywords
    current_keywords = set()
    for template in TEMPLATES:
        current_keywords.update(template.pattern_keywords)
    
    # Get successful keywords
    successful_keywords = set()
    for rec in recommendations:
        successful_keywords.add(rec["keyword"])
    
    # Find gaps
    missing_keywords = successful_keywords - current_keywords
    
    print("="*80)
    print("TEMPLATE GAP ANALYSIS")
    print("="*80)
    print(f"\nCurrent templates cover: {len(current_keywords)} keywords")
    print(f"Successful patterns use: {len(successful_keywords)} keywords")
    print(f"Missing keywords: {len(missing_keywords)}")
    
    if missing_keywords:
        print("\nMissing keywords (high priority):")
        for kw in sorted(missing_keywords):
            # Find success count
            rec = next((r for r in recommendations if r["keyword"] == kw), None)
            if rec:
                print(f"  {kw}: {rec['success_count']} successful examples")
    
    return missing_keywords

def create_enhanced_templates():
    """Create enhanced templates based on knowledge."""
    recs = load_recommendations()
    if not recs:
        return []
    
    recommendations = recs["recommendations"]
    successful_patterns = recs["successful_patterns"]
    
    enhanced_templates = []
    
    # Group successful patterns by keyword
    keyword_patterns = {}
    for pattern in successful_patterns:
        for kw in pattern["keywords"]:
            if kw not in keyword_patterns:
                keyword_patterns[kw] = []
            keyword_patterns[kw].append(pattern)
    
    # Create templates for high-success keywords
    for rec in recommendations:
        keyword = rec["keyword"]
        success_count = rec["success_count"]
        
        if success_count >= 3:  # At least 3 successful examples
            patterns = keyword_patterns.get(keyword, [])
            
            # Find most common code pattern
            if patterns:
                # Get best example (most complete code)
                best_pattern = max(patterns, key=lambda p: len(p["code"]))
                
                # Extract function signature
                func_match = re.search(r'def\s+(\w+)\s*\(([^)]*)\)', best_pattern["code"])
                if func_match:
                    func_name_placeholder = "{function_name}"
                    params = func_match.group(2)
                    
                    # Create template code based on successful pattern
                    template_code = best_pattern["code"]
                    
                    # Replace function name with placeholder
                    template_code = re.sub(
                        r'def\s+\w+\s*\(',
                        f'def {func_name_placeholder}(',
                        template_code
                    )
                    
                    enhanced_templates.append({
                        "name": f"knowledge_{keyword}",
                        "pattern_keywords": [keyword] + list(rec["common_code_patterns"].keys())[:5],
                        "pattern_regex": f"{keyword}.*",
                        "template_code": template_code,
                        "description": f"Knowledge-driven template from {success_count} successful examples",
                        "examples": [best_pattern["problem_text"][:100]],
                        "source": "knowledge_driven",
                        "success_count": success_count
                    })
    
    return enhanced_templates

def main():
    """Main function."""
    print("="*80)
    print("APPLYING KNOWLEDGE TO TEMPLATES")
    print("="*80)
    
    # 1. Analyze gaps
    print("\n[1] Analyzing template gaps...")
    missing_keywords = analyze_template_gaps()
    
    # 2. Create enhanced templates
    print("\n[2] Creating enhanced templates from knowledge...")
    enhanced = create_enhanced_templates()
    print(f"   Generated {len(enhanced)} enhanced templates")
    
    # 3. Show top enhancements
    print("\n[3] Top enhanced templates:")
    enhanced.sort(key=lambda x: x["success_count"], reverse=True)
    for i, template in enumerate(enhanced[:10], 1):
        print(f"\n   {i}. {template['name']}")
        print(f"      Keywords: {', '.join(template['pattern_keywords'][:5])}")
        print(f"      Success count: {template['success_count']}")
        print(f"      Code preview: {template['template_code'][:100]}...")
    
    # 4. Save enhanced templates
    output_file = project_root / "knowledge_enhanced_templates.json"
    with open(output_file, 'w') as f:
        json.dump({
            "enhanced_templates": enhanced,
            "missing_keywords": list(missing_keywords) if missing_keywords else [],
            "total_enhanced": len(enhanced)
        }, f, indent=2)
    
    print(f"\n[4] Saved enhanced templates to: {output_file}")
    print(f"\n[5] Next step: Add these templates to mbpp_templates.py")
    
    return enhanced

if __name__ == "__main__":
    main()
