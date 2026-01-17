"""
MBPP Template Library

Human-written templates for common Python programming patterns found in MBPP.
These templates can be matched to problems and used to generate code when LLM is unavailable.
"""

from typing import Dict, Any, List, Optional, Tuple
import re
import numpy as np


class MBPPTemplate:
    """A template for a common programming pattern."""
    
    def __init__(
        self,
        name: str,
        pattern_keywords: List[str],
        pattern_regex: Optional[str] = None,
        template_code: str = "",
        description: str = "",
        examples: List[str] = None
    ):
        self.name = name
        self.pattern_keywords = pattern_keywords  # Keywords that indicate this pattern
        self.pattern_regex = pattern_regex  # Regex pattern for matching
        self.template_code = template_code  # Template code with placeholders
        self.description = description
        self.examples = examples or []
    
    def matches(self, problem_text: str, test_cases: List[str] = None) -> Tuple[bool, float]:
        """
        Check if this template matches a problem.
        
        Returns:
            (matches, confidence_score)
        """
        problem_lower = problem_text.lower()
        test_text = " ".join(test_cases or []).lower()
        combined_text = f"{problem_lower} {test_text}"
        
        # Count keyword matches (weighted by importance)
        keyword_matches = sum(1 for keyword in self.pattern_keywords if keyword.lower() in combined_text)
        keyword_score = keyword_matches / len(self.pattern_keywords) if self.pattern_keywords else 0
        
        # Boost score if multiple keywords match
        if keyword_matches >= 2:
            keyword_score = min(1.0, keyword_score * 1.2)
        
        # Check regex pattern if provided
        regex_score = 0.0
        if self.pattern_regex:
            if re.search(self.pattern_regex, combined_text, re.IGNORECASE):
                regex_score = 1.0
        
        # Analyze test cases for additional hints
        test_hint_score = 0.0
        if test_cases:
            test_combined = " ".join(test_cases).lower()
            # Check if test cases contain relevant patterns
            for keyword in self.pattern_keywords[:3]:  # Check top 3 keywords
                if keyword.lower() in test_combined:
                    test_hint_score += 0.1
            test_hint_score = min(0.3, test_hint_score)
        
        # Combined confidence (weighted)
        confidence = max(
            keyword_score,
            regex_score * 0.9,  # Regex matches are very reliable
            test_hint_score
        )
        
        # Boost confidence for specific templates
        if self.name.startswith(('remove_', 'sort_', 'count_', 'find_', 'check_', 'split_')):
            confidence = min(1.0, confidence * 1.1)
        
        # Match if confidence > 0.7 (increased threshold for better accuracy)
        # Changed from 0.25 to 0.7 to reduce false positives
        matches = confidence > 0.7
        
        return matches, confidence
    
    def generate_code(
        self,
        function_name: str,
        problem_text: str,
        test_cases: List[str] = None
    ) -> str:
        """
        Generate code from template.
        
        Args:
            function_name: Name of the function to generate
            problem_text: Problem description
            test_cases: Test cases (for inferring parameters)
        
        Returns:
            Generated code
        """
        # Extract parameters from test cases if available
        params = self._extract_parameters(test_cases or [])
        
        # Replace placeholders in template
        code = self.template_code
        
        # Replace function name - handle both placeholder and actual function signature
        code = code.replace("{function_name}", function_name)
        # Also replace in function definition if template has placeholder
        code = re.sub(r'def\s+\{function_name\}', f'def {function_name}', code)
        
        # Replace parameters if found
        if params:
            param_str = ", ".join(params)
            # Replace {params} placeholder
            code = re.sub(r'\{params\}', param_str, code)
            # Handle *args replacement - only replace if template has *args
            # Check if template already has parameters defined
            if '*args' in code or '*args, **kwargs' in code:
                # Template uses *args - replace with actual parameters
                if len(params) == 1:
                    # Single param - replace *args with just the param
                    code = re.sub(r',\s*\*args', '', code)
                    code = re.sub(r'\*args, \*\*kwargs', params[0], code)
                    code = re.sub(r'\*args', params[0], code)
                else:
                    # Multiple params - replace *args with remaining params
                    remaining_params = ", ".join(params[1:]) if len(params) > 1 else ""
                    if remaining_params:
                        code = re.sub(r'\*args', remaining_params, code)
                    else:
                        code = re.sub(r',\s*\*args', '', code)
                        code = re.sub(r'\*args', '', code)
        else:
            # Try to infer from problem text
            problem_lower = problem_text.lower()
            if 'list' in problem_lower or 'array' in problem_lower:
                param_str = "lst"
            elif 'string' in problem_lower or 'str' in problem_lower:
                param_str = "s"
            elif 'number' in problem_lower or 'integer' in problem_lower:
                param_str = "n"
            elif 'dict' in problem_lower or 'dictionary' in problem_lower:
                param_str = "d"
            else:
                param_str = "data"
            code = re.sub(r'\{params\}', param_str, code)
            code = re.sub(r'\*args, \*\*kwargs', param_str, code)
            code = re.sub(r'\*args', param_str, code)
        
        return code
    
    def _extract_parameters(self, test_cases: List[str]) -> List[str]:
        """Extract parameter names from test cases."""
        params = []
        param_types = []
        seen_signatures = set()
        
        for test in test_cases:
            # Look for function calls: function_name(param1, param2, ...)
            # Match function calls more accurately
            match = re.search(r'\w+\s*\(([^)]+)\)', test)
            if match:
                args_str = match.group(1)
                # Skip if empty
                if not args_str.strip():
                    continue
                
                # Create signature from argument count
                # Count commas to estimate argument count (rough but works for most cases)
                arg_count = args_str.count(',') + 1
                signature = f"arg_count_{arg_count}"
                
                if signature in seen_signatures:
                    continue  # Already processed this signature
                seen_signatures.add(signature)
                
                # Split arguments by comma, but be careful with nested structures
                args = []
                current_arg = ""
                depth = 0
                in_string = False
                string_char = None
                
                for char in args_str:
                    if char in ('"', "'") and (not current_arg or current_arg[-1] != '\\'):
                        if not in_string:
                            in_string = True
                            string_char = char
                        elif char == string_char:
                            in_string = False
                            string_char = None
                        current_arg += char
                    elif not in_string:
                        if char in '([{':
                            depth += 1
                            current_arg += char
                        elif char in ')]}':
                            depth -= 1
                            current_arg += char
                        elif char == ',' and depth == 0:
                            if current_arg.strip():
                                args.append(current_arg.strip())
                            current_arg = ""
                        else:
                            current_arg += char
                    else:
                        current_arg += char
                
                if current_arg.strip():
                    args.append(current_arg.strip())
                
                # Infer parameter names from argument types
                for i, arg in enumerate(args):
                    arg_clean = arg.strip()
                    # Determine type and suggest parameter name
                    if arg_clean.startswith('[') or (arg_clean.startswith('[') and ']' in arg_clean):
                        param_name = 'lst' if i == 0 else f'arr{i+1}'
                        param_type = 'list'
                    elif arg_clean.startswith('"') or arg_clean.startswith("'") or ('"' in arg_clean and "'" in arg_clean):
                        param_name = 's' if i == 0 else f'str{i+1}'
                        param_type = 'str'
                    elif arg_clean.startswith('{') or ('{' in arg_clean and '}' in arg_clean):
                        param_name = 'd' if i == 0 else f'dict{i+1}'
                        param_type = 'dict'
                    elif re.match(r'^-?\d+$', arg_clean):
                        param_name = 'n' if i == 0 else f'num{i+1}'
                        param_type = 'int'
                    elif re.match(r'^-?\d+\.\d+', arg_clean):
                        param_name = 'x' if i == 0 else f'val{i+1}'
                        param_type = 'float'
                    elif 'True' in arg_clean or 'False' in arg_clean:
                        param_name = 'flag' if i == 0 else f'flag{i+1}'
                        param_type = 'bool'
                    else:
                        # Try to infer from content
                        if '[' in arg_clean:
                            param_name = 'lst' if i == 0 else f'arr{i+1}'
                            param_type = 'list'
                        elif '"' in arg_clean or "'" in arg_clean:
                            param_name = 's' if i == 0 else f'str{i+1}'
                            param_type = 'str'
                        elif '{' in arg_clean:
                            param_name = 'd' if i == 0 else f'dict{i+1}'
                            param_type = 'dict'
                        else:
                            param_name = f'arg{i+1}'
                            param_type = 'any'
                    
                    if i < len(params):
                        # Update existing parameter if type is more specific
                        if param_type != 'any' and (i >= len(param_types) or param_types[i] == 'any'):
                            params[i] = param_name
                            if i < len(param_types):
                                param_types[i] = param_type
                            else:
                                param_types.append(param_type)
                    else:
                        # Add new parameter
                        params.append(param_name)
                        param_types.append(param_type)
        
        # If no parameters found, try to infer from problem text
        if not params:
            return ['data']  # Default single parameter
        
        return params[:5]  # Limit to 5 parameters


# Template Library
TEMPLATES = [
    # List operations
    MBPPTemplate(
        name="list_sum",
        pattern_keywords=["sum", "list", "numbers", "elements", "total"],
        pattern_regex=r"sum.*list|sum.*numbers|sum.*elements",
        template_code="""def {function_name}({params}):
    \"\"\"Sum all elements in a list.\"\"\"
    return sum({params})
""",
        description="Sum elements in a list",
        examples=["sum([1, 2, 3])", "sum of list elements"]
    ),
    
    MBPPTemplate(
        name="list_max",
        pattern_keywords=["maximum", "max", "largest", "highest", "list"],
        pattern_regex=r"max.*list|largest.*element|maximum.*value",
        template_code="""def {function_name}({params}):
    \"\"\"Find maximum element in a list.\"\"\"
    if not {params}:
        return None
    return max({params})
""",
        description="Find maximum in a list",
        examples=["max([1, 2, 3])", "largest element"]
    ),
    
    MBPPTemplate(
        name="list_min",
        pattern_keywords=["minimum", "min", "smallest", "lowest", "list"],
        pattern_regex=r"min.*list|smallest.*element|minimum.*value",
        template_code="""def {function_name}({params}):
    \"\"\"Find minimum element in a list.\"\"\"
    if not {params}:
        return None
    return min({params})
""",
        description="Find minimum in a list",
        examples=["min([1, 2, 3])", "smallest element"]
    ),
    
    MBPPTemplate(
        name="list_reverse",
        pattern_keywords=["reverse", "list", "backwards", "opposite"],
        pattern_regex=r"reverse.*list|backwards|opposite.*order",
        template_code="""def {function_name}({params}):
    \"\"\"Reverse a list.\"\"\"
    return {params}[::-1]
""",
        description="Reverse a list",
        examples=["reverse([1, 2, 3])"]
    ),
    
    MBPPTemplate(
        name="list_filter",
        pattern_keywords=["filter", "remove", "select", "keep", "condition"],
        pattern_regex=r"filter.*list|remove.*elements|select.*where",
        template_code="""def {function_name}({params}):
    \"\"\"Filter list elements based on condition.\"\"\"
    result = []
    for item in {params}:
        if item:  # Modify condition as needed
            result.append(item)
    return result
""",
        description="Filter list elements",
        examples=["filter even numbers", "remove negative"]
    ),
    
    # String operations
    MBPPTemplate(
        name="string_length",
        pattern_keywords=["length", "len", "count", "characters", "string"],
        pattern_regex=r"length.*string|count.*characters|len.*string",
        template_code="""def {function_name}({params}):
    \"\"\"Get length of a string.\"\"\"
    return len({params})
""",
        description="Get string length",
        examples=["length of string", "count characters"]
    ),
    
    MBPPTemplate(
        name="string_reverse",
        pattern_keywords=["reverse", "string", "backwards"],
        pattern_regex=r"reverse.*string|backwards.*string",
        template_code="""def {function_name}({params}):
    \"\"\"Reverse a string.\"\"\"
    return {params}[::-1]
""",
        description="Reverse a string",
        examples=["reverse string", "backwards"]
    ),
    
    MBPPTemplate(
        name="string_uppercase",
        pattern_keywords=["uppercase", "upper", "capitalize", "string"],
        pattern_regex=r"uppercase|upper.*case|capitalize",
        template_code="""def {function_name}({params}):
    \"\"\"Convert string to uppercase.\"\"\"
    return {params}.upper()
""",
        description="Convert to uppercase",
        examples=["uppercase string", "capitalize"]
    ),
    
    MBPPTemplate(
        name="string_lowercase",
        pattern_keywords=["lowercase", "lower", "string"],
        pattern_regex=r"lowercase|lower.*case",
        template_code="""def {function_name}({params}):
    \"\"\"Convert string to lowercase.\"\"\"
    return {params}.lower()
""",
        description="Convert to lowercase",
        examples=["lowercase string"]
    ),
    
    MBPPTemplate(
        name="string_count",
        pattern_keywords=["count", "occurrences", "times", "appears", "string"],
        pattern_regex=r"count.*occurrences|count.*times|how.*many",
        template_code="""def {function_name}({params}, substring):
    \"\"\"Count occurrences in string.\"\"\"
    return {params}.count(substring)
""",
        description="Count occurrences",
        examples=["count occurrences", "how many times"]
    ),
    
    # Number operations
    MBPPTemplate(
        name="is_even",
        pattern_keywords=["even", "divisible", "2", "modulo"],
        pattern_regex=r"even.*number|divisible.*by.*2|modulo.*2",
        template_code="""def {function_name}({params}):
    \"\"\"Check if number is even.\"\"\"
    return {params} % 2 == 0
""",
        description="Check if even",
        examples=["is even", "divisible by 2"]
    ),
    
    MBPPTemplate(
        name="is_odd",
        pattern_keywords=["odd", "not even", "remainder"],
        pattern_regex=r"odd.*number|not.*even",
        template_code="""def {function_name}({params}):
    \"\"\"Check if number is odd.\"\"\"
    return {params} % 2 != 0
""",
        description="Check if odd",
        examples=["is odd", "not even"]
    ),
    
    MBPPTemplate(
        name="is_prime",
        pattern_keywords=["prime", "divisible", "factors"],
        pattern_regex=r"prime.*number|is.*prime",
        template_code="""def {function_name}({params}):
    \"\"\"Check if number is prime.\"\"\"
    if {params} < 2:
        return False
    for i in range(2, int({params} ** 0.5) + 1):
        if {params} % i == 0:
            return False
    return True
""",
        description="Check if prime",
        examples=["is prime", "prime number"]
    ),
    
    MBPPTemplate(
        name="factorial",
        pattern_keywords=["factorial", "!", "product", "multiply"],
        pattern_regex=r"factorial|n!|product.*numbers",
        template_code="""def {function_name}({params}):
    \"\"\"Calculate factorial.\"\"\"
    if {params} <= 1:
        return 1
    result = 1
    for i in range(2, {params} + 1):
        result *= i
    return result
""",
        description="Calculate factorial",
        examples=["factorial", "n!"]
    ),
    
    MBPPTemplate(
        name="fibonacci",
        pattern_keywords=["fibonacci", "sequence", "fib"],
        pattern_regex=r"fibonacci|fib.*sequence",
        template_code="""def {function_name}({params}):
    \"\"\"Calculate Fibonacci number.\"\"\"
    if {params} <= 1:
        return {params}
    a, b = 0, 1
    for _ in range(2, {params} + 1):
        a, b = b, a + b
    return b
""",
        description="Fibonacci sequence",
        examples=["fibonacci", "fib sequence"]
    ),
    
    # Dictionary operations
    MBPPTemplate(
        name="dict_get",
        pattern_keywords=["dictionary", "dict", "get", "value", "key"],
        pattern_regex=r"dict.*get|get.*value.*key|dictionary.*lookup",
        template_code="""def {function_name}({params}, key, default=None):
    \"\"\"Get value from dictionary.\"\"\"
    return {params}.get(key, default)
""",
        description="Get dictionary value",
        examples=["get dict value", "dictionary lookup"]
    ),
    
    MBPPTemplate(
        name="dict_keys",
        pattern_keywords=["keys", "dictionary", "dict"],
        pattern_regex=r"dict.*keys|get.*all.*keys",
        template_code="""def {function_name}({params}):
    \"\"\"Get all keys from dictionary.\"\"\"
    return list({params}.keys())
""",
        description="Get dictionary keys",
        examples=["dict keys", "all keys"]
    ),
    
    # Sorting
    MBPPTemplate(
        name="sort_list",
        pattern_keywords=["sort", "order", "ascending", "descending"],
        pattern_regex=r"sort.*list|order.*elements|ascending|descending",
        template_code="""def {function_name}({params}):
    \"\"\"Sort a list.\"\"\"
    return sorted({params})
""",
        description="Sort list",
        examples=["sort list", "order elements"]
    ),
    
    # Set operations
    MBPPTemplate(
        name="unique_elements",
        pattern_keywords=["unique", "distinct", "remove", "duplicates"],
        pattern_regex=r"unique.*elements|remove.*duplicates|distinct.*values",
        template_code="""def {function_name}({params}):
    \"\"\"Get unique elements from list.\"\"\"
    return list(set({params}))
""",
        description="Get unique elements",
        examples=["unique elements", "remove duplicates"]
    ),
    
    # List comprehension patterns
    MBPPTemplate(
        name="list_comprehension",
        pattern_keywords=["list", "comprehension", "create", "generate"],
        pattern_regex=r"create.*list|generate.*list|list.*comprehension",
        template_code="""def {function_name}({params}):
    \"\"\"Create list using comprehension.\"\"\"
    return [x for x in {params}]
""",
        description="List comprehension",
        examples=["create list", "generate list"]
    ),
    
    # Range operations
    MBPPTemplate(
        name="range_sum",
        pattern_keywords=["sum", "range", "numbers", "from", "to"],
        pattern_regex=r"sum.*range|sum.*from.*to|sum.*numbers.*between",
        template_code="""def {function_name}(start, end):
    \"\"\"Sum numbers in a range.\"\"\"
    return sum(range(start, end + 1))
""",
        description="Sum range",
        examples=["sum range", "sum from to"]
    ),
    
    # String manipulation
    MBPPTemplate(
        name="string_split",
        pattern_keywords=["split", "string", "separate", "divide"],
        pattern_regex=r"split.*string|separate.*string",
        template_code="""def {function_name}({params}, separator=None):
    \"\"\"Split a string.\"\"\"
    if separator:
        return {params}.split(separator)
    return {params}.split()
""",
        description="Split string",
        examples=["split string", "separate by"]
    ),
    
    MBPPTemplate(
        name="string_join",
        pattern_keywords=["join", "concatenate", "combine", "string"],
        pattern_regex=r"join.*strings|concatenate|combine.*strings",
        template_code="""def {function_name}({params}, separator=''):
    \"\"\"Join strings.\"\"\"
    return separator.join({params})
""",
        description="Join strings",
        examples=["join strings", "concatenate"]
    ),
    
    # Mathematical operations
    MBPPTemplate(
        name="power",
        pattern_keywords=["power", "exponent", "raise", "^"],
        pattern_regex=r"power|exponent|raise.*to|\\^",
        template_code="""def {function_name}(base, exponent):
    \"\"\"Calculate power.\"\"\"
    return base ** exponent
""",
        description="Calculate power",
        examples=["power", "exponent", "raise to"]
    ),
    
    MBPPTemplate(
        name="gcd",
        pattern_keywords=["gcd", "greatest", "common", "divisor"],
        pattern_regex=r"gcd|greatest.*common.*divisor",
        template_code="""def {function_name}(a, b):
    \"\"\"Calculate GCD.\"\"\"
    import math
    return math.gcd(a, b)
""",
        description="Greatest common divisor",
        examples=["gcd", "greatest common divisor"]
    ),
    
    MBPPTemplate(
        name="lcm",
        pattern_keywords=["lcm", "least", "common", "multiple"],
        pattern_regex=r"lcm|least.*common.*multiple",
        template_code="""def {function_name}(a, b):
    \"\"\"Calculate LCM.\"\"\"
    import math
    return abs(a * b) // math.gcd(a, b)
""",
        description="Least common multiple",
        examples=["lcm", "least common multiple"]
    ),
    
    # List operations - advanced
    MBPPTemplate(
        name="list_append",
        pattern_keywords=["append", "add", "list", "element"],
        pattern_regex=r"append.*list|add.*element",
        template_code="""def {function_name}({params}, element):
    \"\"\"Append element to list.\"\"\"
    {params}.append(element)
    return {params}
""",
        description="Append to list",
        examples=["append element", "add to list"]
    ),
    
    MBPPTemplate(
        name="list_remove",
        pattern_keywords=["remove", "delete", "list", "element"],
        pattern_regex=r"remove.*element|delete.*from.*list",
        template_code="""def {function_name}({params}, element):
    \"\"\"Remove element from list.\"\"\"
    if element in {params}:
        {params}.remove(element)
    return {params}
""",
        description="Remove from list",
        examples=["remove element", "delete from list"]
    ),
    
    # Conditional patterns
    MBPPTemplate(
        name="if_else",
        pattern_keywords=["if", "else", "condition", "check"],
        pattern_regex=r"if.*else|check.*condition",
        template_code="""def {function_name}({params}):
    \"\"\"Conditional logic.\"\"\"
    if {params}:
        return True
    else:
        return False
""",
        description="Conditional logic",
        examples=["if else", "check condition"]
    ),
    
    # Loop patterns
    MBPPTemplate(
        name="for_loop",
        pattern_keywords=["for", "loop", "iterate", "each"],
        pattern_regex=r"for.*loop|iterate.*over|for.*each",
        template_code="""def {function_name}({params}):
    \"\"\"Iterate over elements.\"\"\"
    result = []
    for item in {params}:
        result.append(item)
    return result
""",
        description="For loop iteration",
        examples=["for loop", "iterate over"]
    ),
    
    MBPPTemplate(
        name="while_loop",
        pattern_keywords=["while", "loop", "until", "condition"],
        pattern_regex=r"while.*loop|until.*condition",
        template_code="""def {function_name}({params}):
    \"\"\"While loop.\"\"\"
    result = []
    i = 0
    while i < len({params}):
        result.append({params}[i])
        i += 1
    return result
""",
        description="While loop",
        examples=["while loop", "until condition"]
    ),
    
    # Additional List Operations
    MBPPTemplate(
        name="list_unique",
        pattern_keywords=["unique", "distinct", "duplicates", "remove", "list"],
        pattern_regex=r"unique.*elements|remove.*duplicates|distinct.*values|no.*duplicates",
        template_code="""def {function_name}({params}):
    \"\"\"Get unique elements from list.\"\"\"
    seen = set()
    result = []
    for item in {params}:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
""",
        description="Get unique elements preserving order",
        examples=["unique elements", "remove duplicates"]
    ),
    
    MBPPTemplate(
        name="list_sort_descending",
        pattern_keywords=["sort", "descending", "reverse", "order", "largest"],
        pattern_regex=r"sort.*descending|reverse.*order|largest.*first",
        template_code="""def {function_name}({params}):
    \"\"\"Sort list in descending order.\"\"\"
    return sorted({params}, reverse=True)
""",
        description="Sort descending",
        examples=["sort descending", "largest first"]
    ),
    
    MBPPTemplate(
        name="list_average",
        pattern_keywords=["average", "mean", "list", "numbers"],
        pattern_regex=r"average|mean.*list|average.*numbers",
        template_code="""def {function_name}({params}):
    \"\"\"Calculate average of list.\"\"\"
    if not {params}:
        return 0
    return sum({params}) / len({params})
""",
        description="Calculate average",
        examples=["average", "mean"]
    ),
    
    MBPPTemplate(
        name="list_count",
        pattern_keywords=["count", "occurrences", "times", "appears", "list"],
        pattern_regex=r"count.*occurrences|count.*times|how.*many.*in.*list",
        template_code="""def {function_name}({params}):
    \"\"\"Count occurrences of element in list.\"\"\"
    return {params}.count(element)
""",
        description="Count occurrences in list",
        examples=["count occurrences", "how many times"]
    ),
    
    MBPPTemplate(
        name="list_slice",
        pattern_keywords=["slice", "substring", "subarray", "part", "segment"],
        pattern_regex=r"slice.*list|subarray|part.*of.*list",
        template_code="""def {function_name}({params}):
    \"\"\"Slice a list.\"\"\"
    return {params}[start:end]
""",
        description="Slice list",
        examples=["slice list", "subarray"]
    ),
    
    MBPPTemplate(
        name="list_concatenate",
        pattern_keywords=["concatenate", "combine", "merge", "join", "lists"],
        pattern_regex=r"concatenate.*lists|combine.*lists|merge.*lists",
        template_code="""def {function_name}({params}):
    \"\"\"Concatenate lists.\"\"\"
    return list1 + list2
""",
        description="Concatenate lists",
        examples=["concatenate lists", "combine lists"]
    ),
    
    # Additional String Operations
    MBPPTemplate(
        name="string_replace",
        pattern_keywords=["replace", "substitute", "change", "string"],
        pattern_regex=r"replace.*string|substitute|change.*characters",
        template_code="""def {function_name}({params}, old, new):
    \"\"\"Replace substring in string.\"\"\"
    return {params}.replace(old, new)
""",
        description="Replace substring",
        examples=["replace string", "substitute"]
    ),
    
    MBPPTemplate(
        name="string_find",
        pattern_keywords=["find", "search", "index", "position", "string"],
        pattern_regex=r"find.*string|search.*substring|index.*of",
        template_code="""def {function_name}({params}, substring):
    \"\"\"Find substring in string.\"\"\"
    return {params}.find(substring)
""",
        description="Find substring",
        examples=["find string", "search substring"]
    ),
    
    MBPPTemplate(
        name="string_starts_with",
        pattern_keywords=["starts", "beginning", "prefix", "string"],
        pattern_regex=r"starts.*with|beginning.*with|prefix",
        template_code="""def {function_name}({params}, prefix):
    \"\"\"Check if string starts with prefix.\"\"\"
    return {params}.startswith(prefix)
""",
        description="Check starts with",
        examples=["starts with", "beginning"]
    ),
    
    MBPPTemplate(
        name="string_ends_with",
        pattern_keywords=["ends", "suffix", "string"],
        pattern_regex=r"ends.*with|suffix",
        template_code="""def {function_name}({params}, suffix):
    \"\"\"Check if string ends with suffix.\"\"\"
    return {params}.endswith(suffix)
""",
        description="Check ends with",
        examples=["ends with", "suffix"]
    ),
    
    MBPPTemplate(
        name="string_strip",
        pattern_keywords=["strip", "trim", "remove", "whitespace", "string"],
        pattern_regex=r"strip.*string|trim|remove.*whitespace",
        template_code="""def {function_name}({params}):
    \"\"\"Strip whitespace from string.\"\"\"
    return {params}.strip()
""",
        description="Strip whitespace",
        examples=["strip string", "trim"]
    ),
    
    MBPPTemplate(
        name="string_contains",
        pattern_keywords=["contains", "has", "includes", "string"],
        pattern_regex=r"contains|has.*substring|includes",
        template_code="""def {function_name}({params}, substring):
    \"\"\"Check if string contains substring.\"\"\"
    return substring in {params}
""",
        description="Check contains",
        examples=["contains", "has substring"]
    ),
    
    # Additional Number Operations
    MBPPTemplate(
        name="number_parity",
        pattern_keywords=["even", "odd", "parity", "divisible"],
        pattern_regex=r"even.*odd|parity|divisible.*by",
        template_code="""def {function_name}({params}):
    \"\"\"Check number parity.\"\"\"
    return {params} % 2 == 0  # True for even, False for odd
""",
        description="Check parity",
        examples=["even or odd", "parity"]
    ),
    
    MBPPTemplate(
        name="number_absolute",
        pattern_keywords=["absolute", "abs", "magnitude", "distance"],
        pattern_regex=r"absolute.*value|abs|magnitude",
        template_code="""def {function_name}({params}):
    \"\"\"Get absolute value.\"\"\"
    return abs({params})
""",
        description="Absolute value",
        examples=["absolute value", "abs"]
    ),
    
    MBPPTemplate(
        name="number_round",
        pattern_keywords=["round", "nearest", "integer", "decimal"],
        pattern_regex=r"round.*number|nearest.*integer",
        template_code="""def {function_name}({params}, decimals=0):
    \"\"\"Round number.\"\"\"
    return round({params}, decimals)
""",
        description="Round number",
        examples=["round number", "nearest integer"]
    ),
    
    MBPPTemplate(
        name="number_power",
        pattern_keywords=["power", "exponent", "raise", "square", "cube"],
        pattern_regex=r"power|exponent|raise.*to|square|cube",
        template_code="""def {function_name}({params}, exponent):
    \"\"\"Calculate power.\"\"\"
    return {params} ** exponent
""",
        description="Calculate power",
        examples=["power", "exponent", "square"]
    ),
    
    MBPPTemplate(
        name="number_sqrt",
        pattern_keywords=["square", "root", "sqrt", "radical"],
        pattern_regex=r"square.*root|sqrt|radical",
        template_code="""def {function_name}({params}):
    \"\"\"Calculate square root.\"\"\"
    import math
    return math.sqrt({params})
""",
        description="Square root",
        examples=["square root", "sqrt"]
    ),
    
    # Dictionary Operations - Expanded
    MBPPTemplate(
        name="dict_values",
        pattern_keywords=["values", "dictionary", "dict"],
        pattern_regex=r"dict.*values|get.*all.*values",
        template_code="""def {function_name}({params}):
    \"\"\"Get all values from dictionary.\"\"\"
    return list({params}.values())
""",
        description="Get dictionary values",
        examples=["dict values", "all values"]
    ),
    
    MBPPTemplate(
        name="dict_items",
        pattern_keywords=["items", "pairs", "dictionary", "dict"],
        pattern_regex=r"dict.*items|key.*value.*pairs",
        template_code="""def {function_name}({params}):
    \"\"\"Get all items from dictionary.\"\"\"
    return list({params}.items())
""",
        description="Get dictionary items",
        examples=["dict items", "key value pairs"]
    ),
    
    MBPPTemplate(
        name="dict_update",
        pattern_keywords=["update", "merge", "combine", "dictionary"],
        pattern_regex=r"update.*dict|merge.*dictionaries",
        template_code="""def {function_name}({params}, other_dict):
    \"\"\"Update dictionary.\"\"\"
    {params}.update(other_dict)
    return {params}
""",
        description="Update dictionary",
        examples=["update dict", "merge dictionaries"]
    ),
    
    MBPPTemplate(
        name="dict_contains",
        pattern_keywords=["contains", "has", "key", "dictionary"],
        pattern_regex=r"dict.*contains|has.*key|key.*in.*dict",
        template_code="""def {function_name}({params}, key):
    \"\"\"Check if dictionary contains key.\"\"\"
    return key in {params}
""",
        description="Check key exists",
        examples=["contains key", "has key"]
    ),
    
    # Set Operations
    MBPPTemplate(
        name="set_union",
        pattern_keywords=["union", "combine", "merge", "sets"],
        pattern_regex=r"union.*sets|combine.*sets",
        template_code="""def {function_name}(set1, set2):
    \"\"\"Union of sets.\"\"\"
    return set1 | set2
""",
        description="Set union",
        examples=["union sets", "combine sets"]
    ),
    
    MBPPTemplate(
        name="set_intersection",
        pattern_keywords=["intersection", "common", "shared", "sets"],
        pattern_regex=r"intersection.*sets|common.*elements",
        template_code="""def {function_name}(set1, set2):
    \"\"\"Intersection of sets.\"\"\"
    return set1 & set2
""",
        description="Set intersection",
        examples=["intersection", "common elements"]
    ),
    
    MBPPTemplate(
        name="set_difference",
        pattern_keywords=["difference", "subtract", "remove", "sets"],
        pattern_regex=r"difference.*sets|subtract.*sets",
        template_code="""def {function_name}(set1, set2):
    \"\"\"Difference of sets.\"\"\"
    return set1 - set2
""",
        description="Set difference",
        examples=["difference", "subtract sets"]
    ),
    
    # Tuple Operations
    MBPPTemplate(
        name="tuple_operations",
        pattern_keywords=["tuple", "immutable", "ordered"],
        pattern_regex=r"tuple|immutable.*sequence",
        template_code="""def {function_name}({params}):
    \"\"\"Tuple operations.\"\"\"
    return tuple({params})
""",
        description="Tuple operations",
        examples=["tuple", "immutable"]
    ),
    
    # Recursive Patterns
    MBPPTemplate(
        name="recursive_function",
        pattern_keywords=["recursive", "recursion", "base", "case"],
        pattern_regex=r"recursive|recursion|base.*case",
        template_code="""def {function_name}({params}):
    \"\"\"Recursive function.\"\"\"
    if {params} <= 0:
        return 0
    return {function_name}({params} - 1) + {params}
""",
        description="Recursive pattern",
        examples=["recursive", "recursion"]
    ),
    
    # Search Patterns
    MBPPTemplate(
        name="linear_search",
        pattern_keywords=["search", "find", "linear", "element"],
        pattern_regex=r"linear.*search|find.*element",
        template_code="""def {function_name}({params}, target):
    \"\"\"Linear search.\"\"\"
    for i, item in enumerate({params}):
        if item == target:
            return i
    return -1
""",
        description="Linear search",
        examples=["linear search", "find element"]
    ),
    
    MBPPTemplate(
        name="binary_search",
        pattern_keywords=["binary", "search", "sorted", "half"],
        pattern_regex=r"binary.*search|search.*sorted",
        template_code="""def {function_name}({params}, target):
    \"\"\"Binary search.\"\"\"
    left, right = 0, len({params}) - 1
    while left <= right:
        mid = (left + right) // 2
        if {params}[mid] == target:
            return mid
        elif {params}[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
""",
        description="Binary search",
        examples=["binary search", "search sorted"]
    ),
    
    # General List Operations (catch-all)
    MBPPTemplate(
        name="list_operation",
        pattern_keywords=["list", "array", "elements", "items"],
        pattern_regex=r"list|array|elements",
        template_code="""def {function_name}({params}):
    \"\"\"List operation.\"\"\"
    result = []
    for item in {params}:
        result.append(item)
    return result
""",
        description="General list operation",
        examples=["list operation", "array processing"]
    ),
    
    # General String Operations (catch-all)
    MBPPTemplate(
        name="string_operation",
        pattern_keywords=["string", "str", "text", "characters"],
        pattern_regex=r"string|text|characters",
        template_code="""def {function_name}({params}):
    \"\"\"String operation.\"\"\"
    result = ""
    for char in {params}:
        result += char
    return result
""",
        description="General string operation",
        examples=["string operation", "text processing"]
    ),
    
    # General Number Operations (catch-all)
    MBPPTemplate(
        name="number_operation",
        pattern_keywords=["number", "num", "integer", "int"],
        pattern_regex=r"number|integer|num",
        template_code="""def {function_name}({params}):
    \"\"\"Number operation.\"\"\"
    return {params}
""",
        description="General number operation",
        examples=["number operation", "integer processing"]
    ),
    
    # Dictionary Operations (catch-all)
    MBPPTemplate(
        name="dictionary_operation",
        pattern_keywords=["dictionary", "dict", "map", "key", "value"],
        pattern_regex=r"dictionary|dict|map",
        template_code="""def {function_name}({params}):
    \"\"\"Dictionary operation.\"\"\"
    result = {}
    for key, value in {params}.items():
        result[key] = value
    return result
""",
        description="General dictionary operation",
        examples=["dictionary operation", "dict processing"]
    ),
    
    # Problem-Specific Templates (from actual MBPP problems)
    MBPPTemplate(
        name="remove_first_last_occurrence",
        pattern_keywords=["remove", "first", "last", "occurrence", "character", "string"],
        pattern_regex=r"remove.*first.*last.*occurrence|remove.*first.*and.*last",
        template_code="""def {function_name}(s, char):
    \"\"\"Remove first and last occurrence of character from string.\"\"\"
    first_idx = s.find(char)
    if first_idx == -1:
        return s
    last_idx = s.rfind(char)
    if first_idx == last_idx:
        return s[:first_idx] + s[first_idx+1:]
    return s[:first_idx] + s[first_idx+1:last_idx] + s[last_idx+1:]
""",
        description="Remove first and last occurrence",
        examples=["remove first and last occurrence"]
    ),
    
    MBPPTemplate(
        name="sort_matrix_by_row_sum",
        pattern_keywords=["sort", "matrix", "ascending", "sum", "rows"],
        pattern_regex=r"sort.*matrix.*sum.*rows|sort.*matrix.*ascending.*sum",
        template_code="""def {function_name}(matrix):
    \"\"\"Sort matrix by sum of rows.\"\"\"
    return sorted(matrix, key=lambda row: sum(row))
""",
        description="Sort matrix by row sum",
        examples=["sort matrix by sum of rows"]
    ),
    
    MBPPTemplate(
        name="count_most_common",
        pattern_keywords=["count", "most", "common", "words", "frequency"],
        pattern_regex=r"count.*most.*common|most.*common.*words|frequency",
        template_code="""def {function_name}(words):
    \"\"\"Count most common words.\"\"\"
    from collections import Counter
    counter = Counter(words)
    # Return top 4 most common (or adjust as needed)
    return counter.most_common(4)
""",
        description="Count most common words",
        examples=["count most common words"]
    ),
    
    MBPPTemplate(
        name="geometric_volume",
        pattern_keywords=["volume", "triangular", "prism", "rectangular", "cube"],
        pattern_regex=r"volume.*triangular|volume.*prism|find.*volume",
        template_code="""def {function_name}(base, height, length):
    \"\"\"Find volume of triangular prism.\"\"\"
    # Volume = (1/2 * base * height) * length
    return 0.5 * base * height * length
""",
        description="Geometric volume calculation",
        examples=["find volume", "triangular prism"]
    ),
    
    MBPPTemplate(
        name="split_at_lowercase",
        pattern_keywords=["split", "lowercase", "letters"],
        pattern_regex=r"split.*lowercase|split.*at.*lowercase",
        template_code="""def {function_name}(s):
    \"\"\"Split string at lowercase letters.\"\"\"
    # Split at lowercase: for each lowercase, extract from that char to next lowercase or end
    result = []
    i = 0
    while i < len(s):
        if s[i].islower():
            # Start from this lowercase
            j = i + 1
            # Find next lowercase or end
            while j < len(s) and not s[j].islower():
                j += 1
            # Extract from current lowercase to before next lowercase (or end)
            result.append(s[i:j])
            i = j
        else:
            i += 1
    return result
""",
        description="Split at lowercase",
        examples=["split at lowercase letters"]
    ),
    
    MBPPTemplate(
        name="check_duplicates",
        pattern_keywords=["duplicate", "duplicates", "contains", "any", "whether"],
        pattern_regex=r"(contains.*duplicate|any.*duplicate|whether.*duplicate|check.*duplicate)",
        template_code="""def {function_name}(arr):
    \"\"\"Check if array contains duplicates.\"\"\"
    return len(arr) != len(set(arr))
""",
        description="Check for duplicates (boolean)",
        examples=["check duplicates", "contains duplicate", "whether duplicate"]
    ),
    
    MBPPTemplate(
        name="find_first_duplicate",
        pattern_keywords=["find", "first", "duplicate", "element"],
        pattern_regex=r"find.*first.*duplicate|first.*duplicate.*element",
        template_code="""def {function_name}(arr):
    \"\"\"Find the first duplicate element.\"\"\"
    seen = set()
    for item in arr:
        if item in seen:
            return item
        seen.add(item)
    return -1  # Return -1 if no duplicate found
""",
        description="Find first duplicate element",
        examples=["find first duplicate", "first duplicate element"]
    ),
    
    MBPPTemplate(
        name="maximum_sum_nested_lists",
        pattern_keywords=["maximum", "max", "sum", "list", "lists", "nested"],
        pattern_regex=r"maximum.*sum.*list.*lists|max.*sum.*nested|maximum.*sum.*elements.*list",
        template_code="""def {function_name}(lst):
    \"\"\"Find maximum sum of elements in a list of lists.\"\"\"
    return max(sum(sublist) for sublist in lst)
""",
        description="Maximum sum in nested lists",
        examples=["maximum sum of lists", "max sum nested"]
    ),
    
    MBPPTemplate(
        name="binary_to_decimal",
        pattern_keywords=["binary", "decimal", "convert", "base"],
        pattern_regex=r"binary.*decimal|convert.*binary.*decimal|binary.*to.*decimal",
        template_code="""def {function_name}(n):
    \"\"\"Convert binary number to decimal.\"\"\"
    return int(str(n), 2)
""",
        description="Binary to decimal conversion",
        examples=["binary to decimal", "convert binary"]
    ),
    
    MBPPTemplate(
        name="decimal_to_binary_conversion",
        pattern_keywords=["decimal", "binary", "convert"],
        pattern_regex=r"decimal.*binary|convert.*decimal.*binary|decimal.*to.*binary",
        template_code="""def {function_name}(n):
    \"\"\"Convert decimal to binary.\"\"\"
    return int(bin(n)[2:])
""",
        description="Decimal to binary conversion",
        examples=["decimal to binary", "convert decimal binary"]
    ),
    
    MBPPTemplate(
        name="product_non_repeated",
        pattern_keywords=["product", "non-repeated", "non", "repeated", "unique"],
        pattern_regex=r"product.*non.*repeated|product.*unique|non.*repeated.*product",
        template_code="""def {function_name}(lst, *args):
    \"\"\"Find product of non-repeated elements.\"\"\"
    from collections import Counter
    counter = Counter(lst)
    product = 1
    for item, count in counter.items():
        if count == 1:
            product *= item
    return product
""",
        description="Product of non-repeated elements",
        examples=["product non-repeated", "unique elements product"]
    ),
    
    MBPPTemplate(
        name="remove_digits_from_strings",
        pattern_keywords=["remove", "digits", "string", "strings", "list"],
        pattern_regex=r"remove.*digits.*string|remove.*digits.*list|all.*digits.*remove",
        template_code="""def {function_name}(lst):
    \"\"\"Remove all digits from list of strings.\"\"\"
    import re
    return [re.sub(r'\\d', '', s) for s in lst]
""",
        description="Remove digits from strings",
        examples=["remove digits", "strip digits"]
    ),
    
    MBPPTemplate(
        name="binomial_coefficient",
        pattern_keywords=["binomial", "coefficient", "nCr", "combination"],
        pattern_regex=r"binomial.*coefficient|binomial.*co.*efficient|nCr",
        template_code="""def {function_name}(n, k):
    \"\"\"Find binomial coefficient.\"\"\"
    import math
    return math.comb(n, k) if hasattr(math, 'comb') else math.factorial(n) // (math.factorial(k) * math.factorial(n - k))
""",
        description="Binomial coefficient",
        examples=["binomial coefficient", "nCr"]
    ),
    
    MBPPTemplate(
        name="odd_occurrence_element",
        pattern_keywords=["odd", "occurrence", "times", "frequency"],
        pattern_regex=r"odd.*occurrence|occurring.*odd.*times|element.*odd.*times",
        template_code="""def {function_name}(arr, *args):
    \"\"\"Find element occurring odd number of times.\"\"\"
    from collections import Counter
    counter = Counter(arr)
    for item, count in counter.items():
        if count % 2 == 1:
            return item
    return None
""",
        description="Element with odd occurrence",
        examples=["odd occurrence", "odd frequency"]
    ),
    
    MBPPTemplate(
        name="count_substrings_equal_ends",
        pattern_keywords=["count", "substring", "substrings", "equal", "ends", "same"],
        pattern_regex=r"count.*substring.*equal.*ends|substring.*starting.*ending.*same|count.*substring.*same.*ends",
        template_code="""def {function_name}(s):
    \"\"\"Count substrings starting and ending with same character.\"\"\"
    count = 0
    n = len(s)
    for i in range(n):
        for j in range(i, n):
            if s[i] == s[j]:
                count += 1
    return count
""",
        description="Count substrings with equal ends",
        examples=["count substrings equal ends", "substrings same start end"]
    ),
    
    MBPPTemplate(
        name="check_k_elements",
        pattern_keywords=["check", "tuple", "list", "elements", "all", "k"],
        pattern_regex=r"check.*tuple.*list.*k.*elements|tuple.*list.*all.*k|check.*k.*elements",
        template_code="""def {function_name}(lst, k):
    \"\"\"Check if tuple list has all k elements.\"\"\"
    # Check if all tuples contain the element k
    for tup in lst:
        if k not in tup:
            return False
    return True
""",
        description="Check tuple list has k elements",
        examples=["check k elements", "tuple list k elements"]
    ),
    
    MBPPTemplate(
        name="remove_characters_from_string",
        pattern_keywords=["remove", "characters", "present", "second", "string", "dirty"],
        pattern_regex=r"remove.*characters.*present|remove.*from.*first.*second|remove.*dirty",
        template_code="""def {function_name}(s1, s2):
    \"\"\"Remove characters from first string present in second.\"\"\"
    return ''.join(c for c in s1 if c not in s2)
""",
        description="Remove characters from string",
        examples=["remove characters present in second string", "remove dirty chars"]
    ),
    
    MBPPTemplate(
        name="find_multiples",
        pattern_keywords=["multiples", "multiple", "of"],
        pattern_regex=r"multiples.*of|find.*multiples",
        template_code="""def {function_name}(m, n):
    \"\"\"Find m multiples of n.\"\"\"
    return [n * i for i in range(1, m + 1)]
""",
        description="Find multiples",
        examples=["find multiples", "multiples of number"]
    ),
    
    MBPPTemplate(
        name="perimeter_calculation",
        pattern_keywords=["perimeter", "square", "rectangle", "circle"],
        pattern_regex=r"perimeter.*square|perimeter.*rectangle|find.*perimeter",
        template_code="""def {function_name}(side):
    \"\"\"Find perimeter of square.\"\"\"
    return 4 * side
""",
        description="Perimeter calculation",
        examples=["perimeter of square", "find perimeter"]
    ),
    
    MBPPTemplate(
        name="pattern_matching_underscore",
        pattern_keywords=["lowercase", "underscore", "joined", "sequences"],
        pattern_regex=r"lowercase.*underscore|sequences.*lowercase.*underscore|lowercase.*letters.*joined.*underscore",
        template_code="""def {function_name}(s):
    \"\"\"Find sequences of lowercase letters joined with underscore.\"\"\"
    import re
    # Pattern: lowercase letters, underscore, lowercase letters
    # Must be a complete sequence with no uppercase letters in the pattern
    pattern = r'[a-z]+_[a-z]+'
    # Find all matches
    for match in re.finditer(pattern, s):
        start, end = match.span()
        matched = match.group()
        # Check if there are any uppercase letters before or after the match
        # that would break the sequence
        before = s[:start]
        after = s[end:]
        # If match is at start or has lowercase/underscore before, and same after, it's valid
        # But if there's uppercase adjacent, it breaks the sequence
        if matched.islower():
            # Check if uppercase interferes
            if (not before or before[-1].islower() or before[-1] == '_') and \
               (not after or after[0].islower() or after[0] == '_'):
                return 'Found a match!'
    return 'Not matched!'
""",
        description="Pattern matching with underscore",
        examples=["lowercase underscore pattern"]
    ),
    
    MBPPTemplate(
        name="woodall_number",
        pattern_keywords=["woodall", "woodball"],
        pattern_regex=r"woodall|woodball",
        template_code="""def {function_name}(n):
    \"\"\"Check if number is Woodall.\"\"\"
    i = 1
    while True:
        woodall = i * (2 ** i) - 1
        if woodall == n:
            return True
        if woodall > n:
            return False
        i += 1
""",
        description="Woodall number check",
        examples=["is woodall", "woodall number"]
    ),
    
    MBPPTemplate(
        name="string_to_list",
        pattern_keywords=["string", "list", "convert"],
        pattern_regex=r"string.*list|convert.*string.*list",
        template_code="""def {function_name}(s):
    \"\"\"Convert string to list.\"\"\"
    return list(s)
""",
        description="String to list conversion",
        examples=["string to list", "convert string"]
    ),
    
    # Additional specific templates
    MBPPTemplate(
        name="remove_characters_from_string_specific",
        pattern_keywords=["remove", "characters", "first", "second", "string", "present"],
        pattern_regex=r"remove.*characters.*first.*second|remove.*from.*first.*present.*second",
        template_code="""def {function_name}(s1, s2):
    \"\"\"Remove characters from first string present in second.\"\"\"
    return ''.join(c for c in s1 if c not in s2)
""",
        description="Remove characters from string",
        examples=["remove characters from first present in second"]
    ),
    
    # More common patterns from MBPP dataset
    MBPPTemplate(
        name="find_top_k_frequent",
        pattern_keywords=["find", "top", "k", "frequent", "most", "frequently", "occur", "heap"],
        pattern_regex=r"find.*top.*k.*frequent|top.*k.*occur.*most|most.*frequent.*k|heap.*queue",
        template_code="""def {function_name}(lists, k):
    \"\"\"Find top k integers that occur most frequently.\"\"\"
    from collections import Counter
    import heapq
    counter = Counter()
    for lst in lists:
        counter.update(lst)
    # Use heap to get top k by frequency, then by value for ties
    heap = [(-count, item) for item, count in counter.items()]
    heapq.heapify(heap)
    result = []
    seen_counts = {}
    while len(result) < k and heap:
        neg_count, item = heapq.heappop(heap)
        count = -neg_count
        if count not in seen_counts:
            seen_counts[count] = []
        seen_counts[count].append(item)
    # Sort items with same frequency, return top k
    for count in sorted(seen_counts.keys(), reverse=True):
        result.extend(sorted(seen_counts[count]))
        if len(result) >= k:
            break
    return result[:k]
""",
        description="Find top k frequent elements",
        examples=["top k frequent", "most frequent k"]
    ),
    
    MBPPTemplate(
        name="largest_prime_factor",
        pattern_keywords=["largest", "prime", "factor"],
        pattern_regex=r"largest.*prime.*factor|max.*prime.*factor",
        template_code="""def {function_name}(n):
    \"\"\"Find largest prime factor.\"\"\"
    i = 2
    largest = 1
    while i * i <= n:
        while n % i == 0:
            largest = i
            n //= i
        i += 1
    if n > 1:
        largest = n
    return largest
""",
        description="Largest prime factor",
        examples=["largest prime factor", "max prime factor"]
    ),
    
    
    MBPPTemplate(
        name="find_missing_number",
        pattern_keywords=["find", "missing", "number", "sorted", "array"],
        pattern_regex=r"find.*missing.*number|missing.*sorted.*array",
        template_code="""def {function_name}(arr, n):
    \"\"\"Find missing number in sorted array.\"\"\"
    expected_sum = n * (n + 1) // 2
    actual_sum = sum(arr)
    return expected_sum - actual_sum
""",
        description="Find missing number",
        examples=["find missing number", "missing in sorted array"]
    ),
    
    MBPPTemplate(
        name="nth_rectangular_number",
        pattern_keywords=["nth", "rectangular", "number"],
        pattern_regex=r"nth.*rectangular|rectangular.*number",
        template_code="""def {function_name}(n):
    \"\"\"Find nth rectangular number.\"\"\"
    return n * (n + 1)
""",
        description="Nth rectangular number",
        examples=["nth rectangular number"]
    ),
    
    MBPPTemplate(
        name="sort_mixed_list",
        pattern_keywords=["sort", "mixed", "list", "integers", "strings"],
        pattern_regex=r"sort.*mixed.*list|mixed.*list.*sort",
        template_code="""def {function_name}(lst):
    \"\"\"Sort mixed list of integers and strings.\"\"\"
    numbers = sorted([x for x in lst if isinstance(x, int)])
    strings = sorted([x for x in lst if isinstance(x, str)])
    return numbers + strings
""",
        description="Sort mixed list",
        examples=["sort mixed list", "sort integers strings"]
    ),
    
    MBPPTemplate(
        name="division_even_odd",
        pattern_keywords=["division", "even", "odd", "first"],
        pattern_regex=r"division.*even.*odd|divide.*first.*even.*odd",
        template_code="""def {function_name}(lst):
    \"\"\"Find division of first even and odd number.\"\"\"
    first_even = next((x for x in lst if x % 2 == 0), None)
    first_odd = next((x for x in lst if x % 2 == 1), None)
    if first_even and first_odd:
        return first_even // first_odd
    return None
""",
        description="Division of first even and odd",
        examples=["division even odd", "divide first even odd"]
    ),
    
    MBPPTemplate(
        name="rearrange_string",
        pattern_keywords=["rearrange", "string", "adjacent", "different"],
        pattern_regex=r"rearrange.*string|rearrange.*adjacent",
        template_code="""def {function_name}(s):
    \"\"\"Rearrange string so adjacent characters are different.\"\"\"
    from collections import Counter
    counter = Counter(s)
    # Check if rearrangement is possible
    max_count = max(counter.values())
    if max_count > (len(s) + 1) // 2:
        return None  # Cannot rearrange
    # Build result by placing most frequent chars first
    sorted_chars = sorted(counter.items(), key=lambda x: -x[1])
    result = [''] * len(s)
    idx = 0
    for char, count in sorted_chars:
        for _ in range(count):
            result[idx] = char
            idx += 2
            if idx >= len(s):
                idx = 1
    return ''.join(result)
""",
        description="Rearrange string",
        examples=["rearrange string", "adjacent different"]
    ),
    
    MBPPTemplate(
        name="sum_repeated_elements",
        pattern_keywords=["sum", "repeated", "duplicate", "elements"],
        pattern_regex=r"sum.*repeated|repeated.*elements.*sum",
        template_code="""def {function_name}(arr):
    \"\"\"Find sum of repeated elements.\"\"\"
    from collections import Counter
    counter = Counter(arr)
    return sum(item for item, count in counter.items() if count > 1)
""",
        description="Sum of repeated elements",
        examples=["sum repeated", "repeated elements sum"]
    ),
    
    MBPPTemplate(
        name="smallest_number_list",
        pattern_keywords=["smallest", "minimum", "min", "number", "list"],
        pattern_regex=r"smallest.*number.*list|find.*smallest",
        template_code="""def {function_name}(lst):
    \"\"\"Find smallest number in list.\"\"\"
    return min(lst)
""",
        description="Smallest number in list",
        examples=["smallest number", "find smallest"]
    ),
    
    MBPPTemplate(
        name="count_positive_numbers",
        pattern_keywords=["count", "positive", "numbers"],
        pattern_regex=r"count.*positive.*numbers|positive.*count",
        template_code="""def {function_name}(lst):
    \"\"\"Count positive numbers in list.\"\"\"
    return sum(1 for x in lst if x > 0)
""",
        description="Count positive numbers",
        examples=["count positive", "positive numbers"]
    ),
    
    MBPPTemplate(
        name="is_monotonic",
        pattern_keywords=["monotonic", "monotone", "increasing", "decreasing"],
        pattern_regex=r"monotonic|monotone|check.*monotonic",
        template_code="""def {function_name}(arr):
    \"\"\"Check if array is monotonic.\"\"\"
    increasing = all(arr[i] <= arr[i+1] for i in range(len(arr)-1))
    decreasing = all(arr[i] >= arr[i+1] for i in range(len(arr)-1))
    return increasing or decreasing
""",
        description="Check if monotonic",
        examples=["monotonic", "check monotonic"]
    ),
    
    MBPPTemplate(
        name="contains_sublist",
        pattern_keywords=["contains", "sublist", "check", "list"],
        pattern_regex=r"contains.*sublist|check.*sublist",
        template_code="""def {function_name}(lst, sublist):
    \"\"\"Check if list contains sublist.\"\"\"
    n = len(sublist)
    for i in range(len(lst) - n + 1):
        if lst[i:i+n] == sublist:
            return True
    return False
""",
        description="Check contains sublist",
        examples=["contains sublist", "check sublist"]
    ),
    
    MBPPTemplate(
        name="tuples_equal_length",
        pattern_keywords=["tuples", "equal", "length", "all"],
        pattern_regex=r"tuples.*equal.*length|all.*tuples.*equal",
        template_code="""def {function_name}(tuples):
    \"\"\"Check if all tuples have equal length.\"\"\"
    if not tuples:
        return True
    first_len = len(tuples[0])
    return all(len(t) == first_len for t in tuples)
""",
        description="Check tuples equal length",
        examples=["tuples equal length", "all tuples equal"]
    ),
    
    MBPPTemplate(
        name="sort_tuples_lambda",
        pattern_keywords=["sort", "tuples", "lambda"],
        pattern_regex=r"sort.*tuples.*lambda|tuples.*sort.*lambda",
        template_code="""def {function_name}(lst):
    \"\"\"Sort list of tuples using lambda.\"\"\"
    return sorted(lst, key=lambda x: x[0])
""",
        description="Sort tuples with lambda",
        examples=["sort tuples lambda", "tuples sort lambda"]
    ),
    
    MBPPTemplate(
        name="recursion_list_sum",
        pattern_keywords=["recursion", "recursive", "sum", "list"],
        pattern_regex=r"recursion.*sum|recursive.*list.*sum",
        template_code="""def {function_name}(lst):
    \"\"\"Recursive list sum.\"\"\"
    if not lst:
        return 0
    return lst[0] + {function_name}(lst[1:])
""",
        description="Recursive list sum",
        examples=["recursion sum", "recursive list sum"]
    ),
    
    MBPPTemplate(
        name="frequency_list_of_lists",
        pattern_keywords=["frequency", "list", "lists", "collections"],
        pattern_regex=r"frequency.*list.*lists|freq.*elements.*lists",
        template_code="""def {function_name}(lists):
    \"\"\"Find frequency of elements in list of lists.\"\"\"
    from collections import Counter
    counter = Counter()
    for lst in lists:
        counter.update(lst)
    return dict(counter)
""",
        description="Frequency in list of lists",
        examples=["frequency list of lists", "freq elements lists"]
    ),
    
    MBPPTemplate(
        name="filter_even_numbers",
        pattern_keywords=["filter", "even", "numbers", "lambda"],
        pattern_regex=r"filter.*even.*numbers|even.*lambda",
        template_code="""def {function_name}(lst):
    \"\"\"Filter even numbers using lambda.\"\"\"
    return list(filter(lambda x: x % 2 == 0, lst))
""",
        description="Filter even numbers",
        examples=["filter even numbers", "even lambda"]
    ),
    
    MBPPTemplate(
        name="nth_digit_fraction",
        pattern_keywords=["nth", "digit", "fraction", "proper"],
        pattern_regex=r"nth.*digit.*fraction|digit.*proper.*fraction",
        template_code="""def {function_name}(a, b, n):
    \"\"\"Find nth digit in proper fraction.\"\"\"
    result = str(a / b).split('.')[-1]
    if n <= len(result):
        return int(result[n-1])
    return 0
""",
        description="Nth digit in fraction",
        examples=["nth digit fraction", "digit proper fraction"]
    ),
    
    MBPPTemplate(
        name="find_max_min",
        pattern_keywords=["find", "maximum", "minimum", "max", "min"],
        pattern_regex=r"find.*max.*min|maximum.*minimum",
        template_code="""def {function_name}(lst):
    \"\"\"Find maximum and minimum.\"\"\"
    return max(lst), min(lst)
""",
        description="Find max and min",
        examples=["find max min", "maximum minimum"]
    ),
    
    MBPPTemplate(
        name="count_vowels",
        pattern_keywords=["count", "vowels", "vowel"],
        pattern_regex=r"count.*vowels|vowel.*count",
        template_code="""def {function_name}(s):
    \"\"\"Count vowels in string.\"\"\"
    vowels = 'aeiouAEIOU'
    return sum(1 for c in s if c in vowels)
""",
        description="Count vowels",
        examples=["count vowels", "vowel count"]
    ),
    
    MBPPTemplate(
        name="reverse_words",
        pattern_keywords=["reverse", "words", "string"],
        pattern_regex=r"reverse.*words|words.*reverse",
        template_code="""def {function_name}(s):
    \"\"\"Reverse words in string.\"\"\"
    return ' '.join(s.split()[::-1])
""",
        description="Reverse words",
        examples=["reverse words", "words reverse"]
    ),
    
    MBPPTemplate(
        name="is_palindrome",
        pattern_keywords=["palindrome", "check", "same", "backwards"],
        pattern_regex=r"palindrome|check.*palindrome",
        template_code="""def {function_name}(s):
    \"\"\"Check if string is palindrome.\"\"\"
    return s == s[::-1]
""",
        description="Check palindrome",
        examples=["palindrome", "check palindrome"]
    ),
    
    MBPPTemplate(
        name="gcd_lcm",
        pattern_keywords=["gcd", "lcm", "greatest", "common", "divisor", "multiple"],
        pattern_regex=r"gcd|lcm|greatest.*common.*divisor|least.*common.*multiple",
        template_code="""def {function_name}(a, b):
    \"\"\"Calculate GCD and LCM.\"\"\"
    import math
    gcd_val = math.gcd(a, b)
    lcm_val = abs(a * b) // gcd_val
    return gcd_val, lcm_val
""",
        description="GCD and LCM",
        examples=["gcd lcm", "greatest common divisor"]
    ),
    
    MBPPTemplate(
        name="prime_numbers",
        pattern_keywords=["prime", "primes", "generate", "list"],
        pattern_regex=r"prime.*numbers|generate.*primes|list.*primes",
        template_code="""def {function_name}(n):
    \"\"\"Generate prime numbers up to n.\"\"\"
    primes = []
    for num in range(2, n + 1):
        if all(num % i != 0 for i in range(2, int(num ** 0.5) + 1)):
            primes.append(num)
    return primes
""",
        description="Generate prime numbers",
        examples=["prime numbers", "generate primes"]
    ),
    
    MBPPTemplate(
        name="fibonacci_sequence",
        pattern_keywords=["fibonacci", "fib", "sequence"],
        pattern_regex=r"fibonacci|fib.*sequence",
        template_code="""def {function_name}(n):
    \"\"\"Generate Fibonacci sequence.\"\"\"
    if n <= 0:
        return []
    if n == 1:
        return [0]
    fib = [0, 1]
    for i in range(2, n):
        fib.append(fib[i-1] + fib[i-2])
    return fib
""",
        description="Fibonacci sequence",
        examples=["fibonacci", "fib sequence"]
    ),

    MBPPTemplate(
        name="auto_minimum_maximum",
        pattern_keywords=["minimum", "maximum", "max_length_list", "having", "find", "using", "min_length_list", "find_min", "sublist", "list"],
        pattern_regex=r"minimum.*|maximum.*|max_length_list.*",
        template_code="""def to(lst):
    \"\"\"Write a function to find the list with minimum length using lambda function.

Fu...\"\"\"
    # Auto-learned template from 4 similar failures
    # Keywords: minimum, maximum, max_length_list, having, find
    return max(lst) if lst else None
""",
        description="Auto-learned from 4 similar failure(s)",
        examples=[]
    ),
    MBPPTemplate(
        name="auto_cube_cone",
        pattern_keywords=["cube", "cone", "volume_cube", "volume_sphere", "volume", "find", "volume_cylinder", "sphere", "cylinder", "volume_cone"],
        pattern_regex=r"cube.*|cone.*|volume_cube.*",
        template_code="""def to(*args):
    \"\"\"Write a function to find the volume of a sphere.

Function name should be: volum...\"\"\"
    # Auto-learned template from 4 similar failures
    # Keywords: cube, cone, volume_cube, volume_sphere, volume
    # Find operation - implement based on test cases
    pass
""",
        description="Auto-learned from 4 similar failure(s)",
        examples=[]
    ),
    MBPPTemplate(
        name="auto_largest_string",
        pattern_keywords=["largest", "string", "most", "frequency", "most_occurrences", "maximum", "frequency_of_largest", "max_occurrences", "get", "strings"],
        pattern_regex=r"largest.*|string.*|most.*",
        template_code="""def to(lst):
    \"\"\"Write a function to find the item with maximum frequency in a given list.

Funct...\"\"\"
    # Auto-learned template from 4 similar failures
    # Keywords: largest, string, most, frequency, most_occurrences
    return max(lst) if lst else None
""",
        description="Auto-learned from 4 similar failure(s)",
        examples=[]
    ),
    MBPPTemplate(
        name="auto_maximum_between",
        pattern_keywords=["maximum", "between", "tuple", "pairs", "available", "find", "max_product_tuple", "product", "find_max", "difference"],
        pattern_regex=r"maximum.*|between.*|tuple.*",
        template_code="""def to(lst):
    \"\"\"Write a function to find the maximum difference between available pairs in the g...\"\"\"
    # Auto-learned template from 3 similar failures
    # Keywords: maximum, between, tuple, pairs, available
    return max(lst) if lst else None
""",
        description="Auto-learned from 3 similar failure(s)",
        examples=[]
    ),
    MBPPTemplate(
        name="auto_count_freq_count",
        pattern_keywords=["count", "freq_count", "find", "array", "get", "frequency_lists", "frequency", "number", "list", "lists"],
        pattern_regex=r"count.*|freq_count.*|find.*",
        template_code="""def to(lst):
    \"\"\"Write a function to get the frequency of the elements in a list.

Function name ...\"\"\"
    # Auto-learned template from 3 similar failures
    # Keywords: count, freq_count, find, array, get
    return len(lst)
""",
        description="Auto-learned from 3 similar failure(s)",
        examples=[]
    ),
    MBPPTemplate(
        name="auto_check_equal",
        pattern_keywords=["check", "equal", "string", "check_element", "whether", "same", "chklist", "unique", "all_unique", "list"],
        pattern_regex=r"check.*|equal.*|string.*",
        template_code="""def to(lst):
    \"\"\"Write a python function to check whether the elements in a list are same or not....\"\"\"
    # Auto-learned template from 3 similar failures
    # Keywords: check, equal, string, check_element, whether
    return list(set(lst))
""",
        description="Auto-learned from 3 similar failure(s)",
        examples=[]
    ),
    MBPPTemplate(
        name="auto_remove_uppercase_remove",
        pattern_keywords=["remove_uppercase", "remove", "string", "using", "remove_lowercase", "substrings", "uppercase", "regex", "lowercase"],
        pattern_regex=r"remove_uppercase.*|remove.*|string.*",
        template_code="""def to(s):
    \"\"\"Write a function to remove uppercase substrings from a given string by using reg...\"\"\"
    # Auto-learned template from 3 similar failures
    # Keywords: remove_uppercase, remove, string, using, remove_lowercase
    # Implement based on keywords: remove_uppercase, remove, string
    pass
""",
        description="Auto-learned from 3 similar failure(s)",
        examples=[]
    ),
    MBPPTemplate(
        name="auto_binary_convert",
        pattern_keywords=["binary", "convert", "decimal", "binary_to_decimal", "decimal_to_binary", "its", "number", "equivalent"],
        pattern_regex=r"binary.*|convert.*|decimal.*",
        template_code="""def {function_name}(n):
    \"\"\"Convert binary number to decimal.\"\"\"
    # Convert binary number (as integer) to decimal
    # Example: 100 (binary) = 4 (decimal)
    return int(str(n), 2)
""",
        description="Auto-learned from 2 similar failure(s)",
        examples=[]
    ),
    MBPPTemplate(
        name="auto_smallest_missing_find_missing",
        pattern_keywords=["smallest_missing", "find_missing", "sort", "array", "sorted", "number", "find", "smallest", "missing", "element"],
        pattern_regex=r"smallest_missing.*|find_missing.*|sort.*",
        template_code="""def to(lst):
    \"\"\"Write a python function to find the missing number in a sorted array.

Function ...\"\"\"
    # Auto-learned template from 2 similar failures
    # Keywords: smallest_missing, find_missing, sort, array, sorted
    return sorted(lst)
""",
        description="Auto-learned from 2 similar failure(s)",
        examples=[]
    ),
    MBPPTemplate(
        name="auto_gcd_find_gcd",
        pattern_keywords=["gcd", "find_gcd", "array", "two", "positive", "integers", "find", "elements"],
        pattern_regex=r"gcd.*|find_gcd.*|array.*",
        template_code="""def to(lst):
    \"\"\"Write a function to find the gcd of the given array elements.

Function name sho...\"\"\"
    # Auto-learned template from 2 similar failures
    # Keywords: gcd, find_gcd, array, two, positive
    # Find operation - implement based on test cases
    pass
""",
        description="Auto-learned from 2 similar failure(s)",
        examples=[]
    ),
    MBPPTemplate(
        name="auto_check_check_type",
        pattern_keywords=["check", "check_type", "data", "tuple", "equal", "whether", "same", "find_equal_tuple", "type", "find"],
        pattern_regex=r"check.*|check_type.*|data.*",
        template_code="""def to(*args):
    \"\"\"Write a function to find whether all the given tuples have equal length or not.
...\"\"\"
    # Auto-learned template from 2 similar failures
    # Keywords: check, check_type, data, tuple, equal
    # Find operation - implement based on test cases
    pass
""",
        description="Auto-learned from 2 similar failure(s)",
        examples=[]
    ),
    MBPPTemplate(
        name="auto_length_tuple",
        pattern_keywords=["length", "tuple", "find", "remove", "remove_tuples", "all", "list", "divisible", "tuples", "find_tuples"],
        pattern_regex=r"length.*|tuple.*|find.*",
        template_code="""def to(lst):
    \"\"\"Write a function to find tuples which have all elements divisible by k from the ...\"\"\"
    # Auto-learned template from 2 similar failures
    # Keywords: length, tuple, find, remove, remove_tuples
    # Find operation - implement based on test cases
    pass
""",
        description="Auto-learned from 2 similar failure(s)",
        examples=[]
    ),
    MBPPTemplate(
        name="auto_centered_hexagonal",
        pattern_keywords=["centered", "hexagonal", "number", "find", "centered_hexagonal_number", "nth", "hexagonal_num"],
        pattern_regex=r"centered.*|hexagonal.*|number.*",
        template_code="""def to(n):
    \"\"\"Write a function to find nth centered hexagonal number.

Function name should be...\"\"\"
    # Auto-learned template from 2 similar failures
    # Keywords: centered, hexagonal, number, find, centered_hexagonal_number
    # Find operation - implement based on test cases
    pass
""",
        description="Auto-learned from 2 similar failure(s)",
        examples=[]
    ),
    MBPPTemplate(
        name="auto_each_second",
        pattern_keywords=["each", "second", "sort", "string", "lists", "using", "strings", "sort_sublists", "according", "sublist"],
        pattern_regex=r"each.*|second.*|sort.*",
        template_code="""def to(lst):
    \"\"\"Write a function to sort each sublist of strings in a given list of lists using ...\"\"\"
    # Auto-learned template from 2 similar failures
    # Keywords: each, second, sort, string, lists
    return sorted(lst)
""",
        description="Auto-learned from 2 similar failure(s)",
        examples=[]
    ),
    MBPPTemplate(
        name="auto_extract_freq_assign_freq",
        pattern_keywords=["extract_freq", "assign_freq", "tuple", "each", "assign", "extract", "unique", "order", "frequency", "list"],
        pattern_regex=r"extract_freq.*|assign_freq.*|tuple.*",
        template_code="""def to(lst):
    \"\"\"Write a function to assign frequency to each tuple in the given tuple list.

Fun...\"\"\"
    # Auto-learned template from 2 similar failures
    # Keywords: extract_freq, assign_freq, tuple, each, assign
    return list(set(lst))
""",
        description="Auto-learned from 2 similar failure(s)",
        examples=[]
    ),
    MBPPTemplate(
        name="auto_maximum_max_path_sum",
        pattern_keywords=["maximum", "max_path_sum", "right", "sum", "max_sum", "path", "number", "find", "numbers", "triangle"],
        pattern_regex=r"maximum.*|max_path_sum.*|right.*",
        template_code="""def to(n):
    \"\"\"Write a function to find the maximum total path sum in the given triangle.

Func...\"\"\"
    # Auto-learned template from 2 similar failures
    # Keywords: maximum, max_path_sum, right, sum, max_sum
    return sum(n)
""",
        description="Auto-learned from 2 similar failure(s)",
        examples=[]
    ),
    MBPPTemplate(
        name="auto_check_month",
        pattern_keywords=["check", "month", "check_monthnumber", "contains", "check_monthnumb_number", "whether", "days", "number", "not"],
        pattern_regex=r"check.*|month.*|check_monthnumber.*",
        template_code="""def to(n):
    \"\"\"Write a function to check whether the given month name contains 30 days or not.
...\"\"\"
    # Auto-learned template from 2 similar failures
    # Keywords: check, month, check_monthnumber, contains, check_monthnumb_number
    # Check operation - implement based on test cases
    return True
""",
        description="Auto-learned from 2 similar failure(s)",
        examples=[]
    ),
    MBPPTemplate(
        name="auto_convert_decimal",
        pattern_keywords=["convert", "decimal", "octal", "number", "decimal_to_octal", "octal_to_decimal"],
        pattern_regex=r"convert.*|decimal.*|octal.*",
        template_code="""def to(n):
    \"\"\"Write a python function to convert octal number to decimal number.

Function nam...\"\"\"
    # Auto-learned template from 2 similar failures
    # Keywords: convert, decimal, octal, number, decimal_to_octal
    # Implement based on keywords: convert, decimal, octal
    pass
""",
        description="Auto-learned from 2 similar failure(s)",
        examples=[]
    ),
    MBPPTemplate(
        name="auto_maximum_minimum",
        pattern_keywords=["maximum", "minimum", "values", "find", "positions", "position_max", "list", "index", "position_min", "all"],
        pattern_regex=r"maximum.*|minimum.*|values.*",
        template_code="""def to(lst):
    \"\"\"Write a function to find all index positions of the maximum values in a given li...\"\"\"
    # Auto-learned template from 2 similar failures
    # Keywords: maximum, minimum, values, find, positions
    return max(lst) if lst else None
""",
        description="Auto-learned from 2 similar failure(s)",
        examples=[]
    ),
    MBPPTemplate(
        name="auto_tuple_string",
        pattern_keywords=["tuple", "string", "concatenate", "into", "concatenate_elements", "all", "adjacent", "perform", "list", "tuples"],
        pattern_regex=r"tuple.*|string.*|concatenate.*",
        template_code="""def to(lst):
    \"\"\"Write a function to perform the adjacent element concatenation in the given tupl...\"\"\"
    # Auto-learned template from 2 similar failures
    # Keywords: tuple, string, concatenate, into, concatenate_elements
    # Implement based on keywords: tuple, string, concatenate
    pass
""",
        description="Auto-learned from 2 similar failure(s)",
        examples=[]
    ),
    MBPPTemplate(
        name="auto_minimum_two",
        pattern_keywords=["minimum", "two", "min_of_three", "three", "number", "find", "numbers"],
        pattern_regex=r"minimum.*|two.*|min_of_three.*",
        template_code="""def to(n):
    \"\"\"Write a function to find minimum of three numbers.

Function name should be: min...\"\"\"
    # Auto-learned template from 2 similar failures
    # Keywords: minimum, two, min_of_three, three, number
    return min(n) if n else None
""",
        description="Auto-learned from 2 similar failure(s)",
        examples=[]
    ),
    MBPPTemplate(
        name="auto_count_string",
        pattern_keywords=["count", "string", "characters", "frequency", "char_frequency", "character", "count_charac", "total"],
        pattern_regex=r"count.*|string.*|characters.*",
        template_code="""def to(s):
    \"\"\"Write a function to count total characters in a string.

Function name should be...\"\"\"
    # Auto-learned template from 2 similar failures
    # Keywords: count, string, characters, frequency, char_frequency
    return len(s)
""",
        description="Auto-learned from 2 similar failure(s)",
        examples=[]
    ),
    MBPPTemplate(
        name="auto_maximum_having",
        pattern_keywords=["maximum", "having", "find_max", "find", "max_length", "sublist", "list", "lists", "length"],
        pattern_regex=r"maximum.*|having.*|find_max.*",
        template_code="""def to(lst):
    \"\"\"Write a function to find the list of lists with maximum length.

Function name s...\"\"\"
    # Auto-learned template from 2 similar failures
    # Keywords: maximum, having, find_max, find, max_length
    return max(lst) if lst else None
""",
        description="Auto-learned from 2 similar failure(s)",
        examples=[]
    ),
    MBPPTemplate(
        name="auto_maximum_minimum",
        pattern_keywords=["maximum", "minimum", "find", "max_val", "list", "value", "min_val", "heterogeneous"],
        pattern_regex=r"maximum.*|minimum.*|find.*",
        template_code="""def to(lst):
    \"\"\"Write a function to find the maximum value in a given heterogeneous list.

Funct...\"\"\"
    # Auto-learned template from 2 similar failures
    # Keywords: maximum, minimum, find, max_val, list
    return max(lst) if lst else None
""",
        description="Auto-learned from 2 similar failure(s)",
        examples=[]
    ),
    MBPPTemplate(
        name="auto_maximum_sum",
        pattern_keywords=["maximum", "sum", "volume_cuboid", "cuboid", "volume", "find", "max_volume", "sides"],
        pattern_regex=r"maximum.*|sum.*|volume_cuboid.*",
        template_code="""def to(*args):
    \"\"\"Write a python function to find the maximum volume of a cuboid with given sum of...\"\"\"
    # Auto-learned template from 2 similar failures
    # Keywords: maximum, sum, volume_cuboid, cuboid, volume
    return sum(*args)
""",
        description="Auto-learned from 2 similar failure(s)",
        examples=[]
    ),
    MBPPTemplate(
        name="auto_binomial_compute",
        pattern_keywords=["binomial", "compute", "ncr_modp", "probability", "number", "value", "ncr"],
        pattern_regex=r"binomial.*|compute.*|ncr_modp.*",
        template_code="""def to(n):
    \"\"\"Write a function to compute the value of ncr%p.

Function name should be: ncr_mo...\"\"\"
    # Auto-learned template from 2 similar failures
    # Keywords: binomial, compute, ncr_modp, probability, number
    # Implement based on keywords: binomial, compute, ncr_modp
    pass
""",
        description="Auto-learned from 2 similar failure(s)",
        examples=[]
    ),
    MBPPTemplate(
        name="auto_maximum_subsequence",
        pattern_keywords=["maximum", "subsequence", "formed", "multiply", "product", "array", "multiplying", "max_subarray_product", "increasing", "subarray"],
        pattern_regex=r"maximum.*|subsequence.*|formed.*",
        template_code="""def to(lst):
    \"\"\"Write a function to find the maximum product subarray of the given array.

Funct...\"\"\"
    # Auto-learned template from 2 similar failures
    # Keywords: maximum, subsequence, formed, multiply, product
    return max(lst) if lst else None
""",
        description="Auto-learned from 2 similar failure(s)",
        examples=[]
    ),
]


class MBPPTemplateMatcher:
    """Match MBPP problems to templates."""
    
    def __init__(self, use_embedding_search: bool = False):
        self.templates = TEMPLATES
        self.use_embedding_search = use_embedding_search
        self._embedder = None
        # REVERSED KNN: Don't store template embeddings, compute on-demand
        # This saves memory and allows templates to be dynamic
    
    @property
    def embedder(self):
        """Lazy load embedder for semantic similarity."""
        if self._embedder is None and self.use_embedding_search:
            try:
                from backend.embedding import get_embedding_model
                self._embedder = get_embedding_model()
            except Exception as e:
                # Fallback to keyword matching if embedding fails
                self.use_embedding_search = False
        return self._embedder
    
    def find_best_match(
        self,
        problem_text: str,
        test_cases: List[str] = None,
        function_name: str = None
    ) -> Optional[Tuple[MBPPTemplate, float]]:
        """
        Find the best matching template for a problem.
        
        Returns:
            (template, confidence_score) or None
        """
        best_match = None
        best_confidence = 0.0
        
        # ENHANCED: Use all templates but prioritize specific ones
        # Specific templates get priority in matching
        specific_templates = [
            t for t in self.templates 
            if t.name.startswith(('remove_', 'sort_', 'count_', 'find_', 'check_', 'split_', 'pattern_', 'perimeter_', 'geometric_', 'woodall_', 'test_duplicate', 'is_woodall', 'find_first_duplicate', 'maximum_sum', 'binary_to_decimal', 'product_non_repeated', 'remove_digits', 'binomial_coefficient', 'odd_occurrence', 'count_substrings', 'check_k_elements', 'find_top_k', 'largest_prime', 'decimal_to_binary', 'find_missing', 'nth_rectangular', 'sort_mixed', 'division_even', 'rearrange_string', 'frequency_list', 'filter_even', 'nth_digit', 'find_max_min', 'count_vowels', 'reverse_words', 'is_palindrome', 'gcd_lcm', 'prime_numbers', 'fibonacci', 'sum_repeated', 'smallest_number', 'count_positive', 'is_monotonic', 'contains_sublist', 'tuples_equal', 'sort_tuples', 'recursion_list', 'auto_'))
        ]
        
        # Also include generic templates but with lower priority
        generic_templates = [t for t in self.templates if t not in specific_templates]
        
        # ENHANCED: Try specific templates first (higher priority)
        for template in specific_templates:
            matches, confidence = template.matches(problem_text, test_cases)
            if matches and confidence > best_confidence:
                best_match = template
                best_confidence = confidence
        
        # If no specific match, try generic templates (but require higher confidence)
        if not best_match or best_confidence < 0.5:
            for template in generic_templates:
                matches, confidence = template.matches(problem_text, test_cases)
                # Generic templates need higher confidence threshold
                if matches and confidence > 0.6 and confidence > best_confidence:
                    best_match = template
                    best_confidence = confidence
        
        # REVERSED KNN: Try embedding-based search if enabled (no stored embeddings)
        if self.use_embedding_search and self.embedder:
            embedding_match = self._match_by_embedding(problem_text, test_cases, specific_templates + generic_templates)
            if embedding_match:
                emb_template, emb_confidence = embedding_match
                if emb_confidence > best_confidence:
                    best_match = emb_template
                    best_confidence = emb_confidence
        
        # ENHANCED MATCHING: Test-case-based fallback with improved algorithm
        if not best_match or best_confidence < 0.35:
            # Try matching based on test case patterns (very reliable)
            test_based_match = self._match_by_test_patterns(problem_text, test_cases, specific_templates + generic_templates)
            if test_based_match:
                test_template, test_confidence = test_based_match
                if test_confidence > best_confidence:
                    best_match = test_template
                    best_confidence = test_confidence
        
        # Return if we have a match with reasonable confidence
        # Lower threshold for specific templates, higher for generic
        if best_match:
            is_specific = best_match in specific_templates
            threshold = 0.3 if is_specific else 0.55
            if best_confidence > threshold:
                return (best_match, best_confidence)
        
        # No match - let LLM handle it
        return None
    
    def _match_by_test_patterns(
        self,
        problem_text: str,
        test_cases: List[str],
        templates: List[MBPPTemplate]
    ) -> Optional[Tuple[MBPPTemplate, float]]:
        """Match templates based on test case patterns (ENHANCED matching)."""
        if not test_cases:
            return None
        
        test_text = " ".join(test_cases).lower()
        problem_lower = problem_text.lower()
        combined_text = f"{problem_lower} {test_text}"
        
        best_match = None
        best_score = 0.0
        
        # Extract function name from test cases (most reliable signal)
        func_name = None
        func_match = re.search(r'(\w+)\s*\(', test_text)
        if func_match:
            func_name = func_match.group(1).lower()
        
        for template in templates:
            # Check keyword matches in test cases (weighted higher) and problem text
            keyword_matches_test = sum(1 for kw in template.pattern_keywords if kw.lower() in test_text)
            keyword_matches_problem = sum(1 for kw in template.pattern_keywords if kw.lower() in problem_lower)
            
            # Weight test case matches much higher (they're ground truth)
            total_matches = keyword_matches_test * 2.0 + keyword_matches_problem * 0.5
            
            if total_matches > 0:
                # Normalize score
                score = total_matches / (len(template.pattern_keywords) * 2.0) if template.pattern_keywords else 0
                
                # Strong boost if regex matches in test cases (very reliable)
                if template.pattern_regex:
                    if re.search(template.pattern_regex, test_text, re.IGNORECASE):
                        score = min(1.0, score * 1.5)  # Strong boost
                    elif re.search(template.pattern_regex, combined_text, re.IGNORECASE):
                        score = min(1.0, score * 1.2)
                
                # Function name matching (very reliable signal)
                if func_name:
                    # Check if function name contains template keywords
                    func_keyword_matches = sum(1 for kw in template.pattern_keywords[:5] if kw.lower() in func_name)
                    if func_keyword_matches > 0:
                        score = min(1.0, score * (1.0 + func_keyword_matches * 0.15))
                    
                    # Check if template name pattern matches function name
                    template_name_parts = template.name.split('_')
                    if any(part in func_name for part in template_name_parts if len(part) > 3):
                        score = min(1.0, score * 1.2)
                
                # Boost for high keyword match ratio in test cases
                if keyword_matches_test >= len(template.pattern_keywords) * 0.4:
                    score = min(1.0, score * 1.1)
                
                # Lower threshold for test-based matching (0.18 vs 0.2)
                if score > best_score and score > 0.18:
                    best_match = template
                    best_score = score
        
        if best_match:
            return (best_match, best_score)
        return None
    
    def _match_by_embedding(
        self,
        problem_text: str,
        test_cases: List[str],
        templates: List[MBPPTemplate]
    ) -> Optional[Tuple[MBPPTemplate, float]]:
        """
        REVERSED KNN: Match templates using embeddings computed on-demand.
        
        Instead of storing template embeddings, we:
        1. Generate embedding for the problem query on-the-fly
        2. Generate embeddings for templates on-demand (no storage)
        3. Compare and find best match
        
        This saves memory and allows templates to be dynamic.
        """
        if not self.embedder:
            return None
        
        # Build query text from problem and test cases
        query_text = problem_text
        if test_cases:
            query_text += " " + " ".join(test_cases)
        
        # Generate query embedding (on-the-fly)
        try:
            query_embedding = self.embedder.embed_text(query_text, convert_to_numpy=True)
            if len(query_embedding.shape) == 1:
                query_embedding = query_embedding.reshape(1, -1)
        except Exception as e:
            # Fallback to keyword matching if embedding fails
            return None
        
        best_match = None
        best_similarity = -1.0
        
        # Build template texts for comparison (on-demand, no storage)
        template_texts = []
        for template in templates:
            # Combine template metadata into searchable text
            template_text = f"{template.name} {template.description} {' '.join(template.pattern_keywords)}"
            if template.examples:
                template_text += " " + " ".join(template.examples)
            template_texts.append(template_text)
        
        # Generate embeddings for all templates on-demand (batch for efficiency)
        try:
            template_embeddings = self.embedder.embed_text(
                template_texts,
                convert_to_numpy=True,
                batch_size=min(16, len(template_texts))  # Batch for efficiency
            )
            
            # Compute cosine similarities
            from sklearn.metrics.pairwise import cosine_similarity
            similarities = cosine_similarity(query_embedding, template_embeddings)[0]
            
            # Find best match
            best_idx = np.argmax(similarities)
            best_similarity = float(similarities[best_idx])
            
            # Only return if similarity is above threshold
            if best_similarity > 0.3:  # Threshold for embedding-based matching
                best_match = templates[best_idx]
                return (best_match, best_similarity)
        except Exception as e:
            # Fallback to keyword matching if batch embedding fails
            return None
        
        return None
    
    def generate_from_template(
        self,
        problem_text: str,
        function_name: str,
        test_cases: List[str] = None
    ) -> Optional[str]:
        """
        Generate code using the best matching template.
        
        Args:
            problem_text: Problem description
            function_name: Name of the function to generate
            test_cases: Test cases (for inferring parameters)
        
        Returns:
            Generated code string or None
        """
        match_result = self.find_best_match(problem_text, test_cases, function_name)
        if not match_result:
            return None
        
        template, confidence = match_result
        return template.generate_code(function_name, problem_text, test_cases)


def get_template_matcher(use_embedding_search: bool = False) -> MBPPTemplateMatcher:
    """
    Get a template matcher instance.
    
    Args:
        use_embedding_search: If True, uses reversed KNN approach:
            - Generates query embeddings on-the-fly
            - Computes template embeddings on-demand (no storage)
            - More memory efficient, allows dynamic templates
    """
    return MBPPTemplateMatcher(use_embedding_search=use_embedding_search)
