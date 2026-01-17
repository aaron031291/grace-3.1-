# MBPP Template Expansion System

## Overview

Grace's MBPP integration now includes a comprehensive template library with human-written templates for common Python programming patterns. This allows Grace to generate code even when LLM services are unavailable.

## Features

### 1. Template Library (`backend/benchmarking/mbpp_templates.py`)

- **30+ Templates** covering common patterns:
  - List operations (sum, max, min, reverse, filter, etc.)
  - String operations (length, reverse, uppercase, lowercase, count, split, join)
  - Number operations (is_even, is_odd, is_prime, factorial, fibonacci)
  - Dictionary operations (get, keys)
  - Sorting and set operations
  - Mathematical operations (power, gcd, lcm)
  - Loop patterns (for, while)
  - Conditional patterns

### 2. Pattern Matching

Each template includes:
- **Keywords**: Words that indicate this pattern
- **Regex patterns**: More specific pattern matching
- **Confidence scoring**: Returns match confidence (0.0-1.0)

### 3. Code Generation

Templates can generate code by:
- Matching problem text and test cases
- Extracting function names and parameters
- Generating appropriate code structure

## Usage

### In MBPP Integration

The template system is integrated into `MBPPIntegration.run_evaluation()`:

```python
# Try templates first (faster)
results = mbpp_integration.run_evaluation(
    max_problems=50,
    use_templates=True,
    template_first=True  # Try templates before LLM
)

# Use templates as fallback (more accurate)
results = mbpp_integration.run_evaluation(
    max_problems=50,
    use_templates=True,
    template_first=False  # Try LLM first, templates as fallback
)
```

### Template Matching

```python
from backend.benchmarking.mbpp_templates import get_template_matcher

matcher = get_template_matcher()

# Find best match
match = matcher.find_best_match(
    problem_text="Sum all elements in a list",
    test_cases=["assert sum_list([1,2,3]) == 6"],
    function_name="sum_list"
)

if match:
    template, confidence = match
    print(f"Matched: {template.name} (confidence: {confidence:.2f})")
    
    # Generate code
    code = template.generate_code("sum_list", problem_text, test_cases)
    print(code)
```

## Template Structure

Each template includes:

```python
MBPPTemplate(
    name="list_sum",
    pattern_keywords=["sum", "list", "numbers", "elements"],
    pattern_regex=r"sum.*list|sum.*numbers",
    template_code="""def {function_name}({params}):
    return sum({params})
""",
    description="Sum elements in a list",
    examples=["sum([1, 2, 3])"]
)
```

## Adding New Templates

To add a new template:

1. **Identify the pattern**: What keywords/patterns indicate this problem type?
2. **Create template**: Add to `TEMPLATES` list in `mbpp_templates.py`
3. **Test matching**: Verify it matches appropriate problems
4. **Generate code**: Ensure template generates correct code structure

Example:

```python
MBPPTemplate(
    name="custom_pattern",
    pattern_keywords=["keyword1", "keyword2"],
    pattern_regex=r"pattern.*regex",
    template_code="""def {function_name}({params}):
    \"\"\"Description.\"\"\"
    # Implementation
    return result
""",
    description="What this template does",
    examples=["example usage"]
)
```

## Performance Benefits

1. **Speed**: Template matching is instant (no LLM calls)
2. **Reliability**: Templates always generate syntactically correct code
3. **Coverage**: Can handle common patterns even when LLM is unavailable
4. **Fallback**: Provides backup when LLM fails

## Results Tracking

The evaluation results now include:
- `template_matches`: Number of problems solved using templates
- `llm_generated`: Number of problems solved using LLM
- `generation_method`: Method used for each problem ("template", "llm", "template_fallback")

## Future Enhancements

1. **More Templates**: Add templates for more patterns
2. **Parameter Inference**: Better extraction of parameters from test cases
3. **Template Learning**: Learn new templates from successful solutions
4. **Hybrid Approach**: Combine template structure with LLM refinement

## Files

- `backend/benchmarking/mbpp_templates.py`: Template library and matcher
- `backend/benchmarking/mbpp_integration.py`: Integration with MBPP evaluation
- `MBPP_TEMPLATE_EXPANSION.md`: This documentation
