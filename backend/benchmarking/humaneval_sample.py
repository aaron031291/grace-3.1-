"""
Sample HumanEval Problems for Testing

A few sample problems from HumanEval to test the system
when the full dataset isn't available.
"""

# Import expanded problems
try:
    from backend.benchmarking.humaneval_expanded_sample import HUMANEVAL_EXPANDED_PROBLEMS
    _expanded = HUMANEVAL_EXPANDED_PROBLEMS
except:
    _expanded = []

HUMANEVAL_SAMPLE_PROBLEMS = [
    {
        "task_id": "humaneval_0",
        "prompt": "def has_close_elements(numbers: list, threshold: float) -> bool:\n    \"\"\" Check if in given list of numbers, are any two numbers closer to each other than\n    given threshold.\n    >>> has_close_elements([1.0, 2.0, 3.0], 0.5)\n    False\n    >>> has_close_elements([1.0, 2.8, 3.0, 4.0, 5.0, 2.0], 0.3)\n    True\n    \"\"\"\n",
        "test": "def check(candidate):\n    assert candidate([1.0, 2.0, 3.0], 0.5) == False\n    assert candidate([1.0, 2.8, 3.0, 4.0, 5.0, 2.0], 0.3) == True\n    assert candidate([1.0, 2.0, 3.9], 0.3) == True\n    assert candidate([1.0, 2.0, 3.9], 0.05) == False\n    assert candidate([1.0] * 10 + [2.0], 0.1) == True\n",
        "entry_point": "has_close_elements",
        "canonical_solution": "def has_close_elements(numbers: list, threshold: float) -> bool:\n    for idx, elem in enumerate(numbers):\n        for idx2, elem2 in enumerate(numbers):\n            if idx != idx2:\n                distance = abs(elem - elem2)\n                if distance < threshold:\n                    return True\n    return False\n"
    },
    {
        "task_id": "humaneval_1",
        "prompt": "def separate_paren_groups(paren_string: str) -> list:\n    \"\"\" Input to this function is a string containing multiple groups of nested parentheses. Your\n    goal is to separate those groups into separate strings and return the list of all.\n    Separate groups are balanced (each open brace is properly closed) and not nested within each other\n    Ignore any spaces in the input string.\n    >>> separate_paren_groups('( ) (( )) (( )( ))')\n    ['()', '(())', '(()())']\n    \"\"\"\n",
        "test": "def check(candidate):\n    assert candidate('()()((()))') == ['()', '()', '((()))']\n    assert candidate('((()))') == ['((()))']\n    assert candidate('((()))(())()()(()())') == ['((()))', '(())', '()', '()', '(()())']\n    assert candidate('((())())(()(()()))') == ['((())())', '(()(()()))']\n",
        "entry_point": "separate_paren_groups",
        "canonical_solution": "def separate_paren_groups(paren_string: str) -> list:\n    result = []\n    current_string = []\n    depth = 0\n    for char in paren_string:\n        if char == '(':\n            depth += 1\n            current_string.append(char)\n        elif char == ')':\n            depth -= 1\n            current_string.append(char)\n            if depth == 0:\n                result.append(''.join(current_string))\n                current_string = []\n    return result\n"
    },
    {
        "task_id": "humaneval_2",
        "prompt": "def truncate_number(n: float) -> int:\n    \"\"\" Return the integer part of a number.\n    >>> truncate_number(5.5)\n    5\n    >>> truncate_number(7.7)\n    7\n    \"\"\"\n",
        "test": "def check(candidate):\n    assert candidate(5.5) == 5\n    assert candidate(7.7) == 7\n    assert candidate(0.0) == 0\n    assert candidate(-1.1) == -1\n",
        "entry_point": "truncate_number",
        "canonical_solution": "def truncate_number(n: float) -> int:\n    return int(n)\n"
    },
    {
        "task_id": "humaneval_3",
        "prompt": "def below_zero(operations: list) -> bool:\n    \"\"\" You're given a list of deposit and withdrawal operations on a bank account that starts with\n    zero balance. Write a function that returns True if the account balance goes below zero at any point\n    during the sequence of operations, otherwise False.\n    >>> below_zero([1, 2, -4, 5])\n    True\n    >>> below_zero([1, 2, -4, 5, 10])\n    False\n    \"\"\"\n",
        "test": "def check(candidate):\n    assert candidate([1, 2, -4, 5]) == True\n    assert candidate([1, 2, -4, 5, 10]) == False\n    assert candidate([1, -1, 2, -2, 5, -5, 4, -4]) == False\n    assert candidate([1, -1, 2, -2, 5, -5, 4, -5, 4, -4]) == True\n",
        "entry_point": "below_zero",
        "canonical_solution": "def below_zero(operations: list) -> bool:\n    balance = 0\n    for op in operations:\n        balance += op\n        if balance < 0:\n            return True\n    return False\n"
    },
    {
        "task_id": "humaneval_4",
        "prompt": "def mean_absolute_deviation(numbers: list) -> float:\n    \"\"\" You will be given a list of numbers. Calculate the mean absolute deviation of the numbers.\n    The mean absolute deviation is the mean of the absolute differences between each number and the mean of the numbers.\n    >>> mean_absolute_deviation([1, 2, 3, 4])\n    1.0\n    \"\"\"\n",
        "test": "def check(candidate):\n    assert abs(candidate([1, 2, 3, 4]) - 1.0) < 1e-6\n    assert abs(candidate([1, 2, 3, 4, 5]) - 1.2) < 1e-6\n    assert abs(candidate([10, 20, 30, 40]) - 10.0) < 1e-6\n",
        "entry_point": "mean_absolute_deviation",
        "canonical_solution": "def mean_absolute_deviation(numbers: list) -> float:\n    mean = sum(numbers) / len(numbers)\n    return sum(abs(x - mean) for x in numbers) / len(numbers)\n"
    }
] + _expanded
