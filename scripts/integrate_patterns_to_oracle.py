"""
Integrate Downloaded Coding Patterns into Oracle & Template System

This script:
1. Loads patterns from knowledge_base/coding_patterns/
2. Adds them to the template matching system
3. Updates proactive learning with new patterns
"""

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


def load_coding_patterns() -> dict:
    """Load the downloaded coding patterns."""
    patterns_file = Path(__file__).parent.parent / "knowledge_base" / "coding_patterns" / "coding_patterns_library.json"
    
    if not patterns_file.exists():
        print(f"ERROR: Patterns file not found: {patterns_file}")
        print("Run download_coding_patterns.py first!")
        return {}
    
    with open(patterns_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def integrate_to_template_system(patterns: dict) -> int:
    """Add patterns to mbpp_templates.py as learnable templates."""
    # Export to learned_templates.json format for template learning system
    learned_templates = []
    
    for category, data in patterns.get('categories', {}).items():
        # Process MBPP patterns (they have actual solutions)
        for p in data.get('mbpp_patterns', []):
            template = {
                'name': f"mbpp_{p.get('task_id', 'unknown')}",
                'keywords': p.get('keywords', []),
                'description': p.get('description', '')[:200],
                'template_code': p.get('solution', ''),
                'category': category,
                'source': 'mbpp_official',
                'operations': p.get('operations', [])
            }
            if template['template_code']:
                learned_templates.append(template)
        
        # Process HumanEval patterns
        for p in data.get('humaneval_patterns', []):
            template = {
                'name': f"humaneval_{p.get('task_id', 'unknown').replace('/', '_')}",
                'keywords': p.get('keywords', []),
                'description': p.get('description', '')[:200],
                'template_code': p.get('solution', ''),
                'entry_point': p.get('entry_point', ''),
                'category': category,
                'source': 'humaneval_official',
                'operations': p.get('operations', [])
            }
            if template['template_code']:
                learned_templates.append(template)
    
    # Add additional templates
    for t in patterns.get('additional_templates', []):
        learned_templates.append({
            'name': t.get('name', 'unknown'),
            'keywords': t.get('keywords', []),
            'template_code': t.get('template', ''),
            'category': t.get('category', 'general'),
            'source': 'additional',
            'confidence': 1.0
        })
    
    # Save as learned_templates.json (used by template learning system)
    output_file = Path(__file__).parent.parent / "knowledge_enhanced_templates.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(learned_templates, f, indent=2, ensure_ascii=False)
    
    print(f"Saved {len(learned_templates)} templates to {output_file}")
    return len(learned_templates)


def update_proactive_learning_paths():
    """Update proactive learning to include coding_patterns directory."""
    # Update enhanced_web_integration.py to include coding_patterns
    web_integration = Path(__file__).parent.parent / "backend" / "benchmarking" / "enhanced_web_integration.py"
    
    if web_integration.exists():
        content = web_integration.read_text(encoding='utf-8')
        
        # Check if coding_patterns already added
        if "coding_patterns" not in content:
            # Find the knowledge_base paths section and add coding_patterns
            old_line = 'project_root / "knowledge_base" / "ai research",'
            new_line = '''project_root / "knowledge_base" / "ai research",
            project_root / "knowledge_base" / "coding_patterns",'''
            
            if old_line in content:
                content = content.replace(old_line, new_line)
                web_integration.write_text(content, encoding='utf-8')
                print(f"Updated {web_integration} with coding_patterns path")
    
    # Update mbpp_parallel_integration.py
    parallel_integration = Path(__file__).parent.parent / "backend" / "benchmarking" / "mbpp_parallel_integration.py"
    
    if parallel_integration.exists():
        content = parallel_integration.read_text(encoding='utf-8')
        
        if "coding_patterns" not in content:
            old_line = 'project_root / "knowledge_base" / "ai research",'
            new_line = '''project_root / "knowledge_base" / "ai research",
            project_root / "knowledge_base" / "coding_patterns",'''
            
            if old_line in content:
                content = content.replace(old_line, new_line)
                parallel_integration.write_text(content, encoding='utf-8')
                print(f"Updated {parallel_integration} with coding_patterns path")


def create_pattern_index():
    """Create an index file for fast pattern lookup."""
    patterns_dir = Path(__file__).parent.parent / "knowledge_base" / "coding_patterns"
    
    # Load main library
    main_file = patterns_dir / "coding_patterns_library.json"
    if not main_file.exists():
        return
    
    with open(main_file, 'r', encoding='utf-8') as f:
        patterns = json.load(f)
    
    # Create keyword index for fast lookup
    keyword_index = {}
    
    for category, data in patterns.get('categories', {}).items():
        for p in data.get('mbpp_patterns', []) + data.get('humaneval_patterns', []):
            for keyword in p.get('keywords', []):
                if keyword not in keyword_index:
                    keyword_index[keyword] = []
                keyword_index[keyword].append({
                    'task_id': p.get('task_id'),
                    'category': category,
                    'has_solution': bool(p.get('solution') or p.get('template_code'))
                })
    
    # Save index
    index_file = patterns_dir / "keyword_index.json"
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump({
            'total_keywords': len(keyword_index),
            'keywords': keyword_index
        }, f, indent=2)
    
    print(f"Created keyword index with {len(keyword_index)} keywords")


def trigger_proactive_learning():
    """Trigger the proactive learning system to pick up new patterns."""
    try:
        from backend.benchmarking.template_learning_system import TemplateLearningSystem
        
        # Initialize learning system
        tls = TemplateLearningSystem()
        
        # Load knowledge enhanced templates
        templates_file = Path(__file__).parent.parent / "knowledge_enhanced_templates.json"
        if templates_file.exists():
            with open(templates_file, 'r', encoding='utf-8') as f:
                templates = json.load(f)
            
            # Add to learning system
            added = 0
            for t in templates[:100]:  # Start with top 100
                try:
                    tls.add_template_candidate(
                        name=t.get('name', 'unknown'),
                        keywords=t.get('keywords', []),
                        template_code=t.get('template_code', ''),
                        confidence=0.9,
                        source=t.get('source', 'knowledge_base')
                    )
                    added += 1
                except Exception as e:
                    pass
            
            print(f"Added {added} templates to learning system")
            return added
            
    except ImportError as e:
        print(f"Template learning system not available: {e}")
        return 0


def main():
    """Main integration process."""
    print("=" * 60)
    print("INTEGRATING CODING PATTERNS TO ORACLE & TEMPLATES")
    print("=" * 60)
    
    # 1. Load patterns
    print("\n[1/4] Loading coding patterns...")
    patterns = load_coding_patterns()
    if not patterns:
        return
    
    print(f"   Loaded {patterns.get('total_templates', 0)} patterns")
    
    # 2. Integrate to template system
    print("\n[2/4] Integrating to template system...")
    count = integrate_to_template_system(patterns)
    
    # 3. Update proactive learning paths
    print("\n[3/4] Updating proactive learning paths...")
    update_proactive_learning_paths()
    
    # 4. Create pattern index
    print("\n[4/4] Creating pattern index...")
    create_pattern_index()
    
    print("\n" + "=" * 60)
    print("INTEGRATION COMPLETE!")
    print("=" * 60)
    print(f"\nPatterns integrated: {count}")
    print("\nProactive learning will now pick up patterns from:")
    print("  - knowledge_base/coding_patterns/")
    print("  - knowledge_enhanced_templates.json")
    print("\nTo manually trigger learning, run:")
    print("  python scripts/integrate_patterns_to_oracle.py --trigger")


if __name__ == "__main__":
    if "--trigger" in sys.argv:
        trigger_proactive_learning()
    else:
        main()
