"""
Sample MBPP Problems for Testing

A few sample problems from MBPP to test the system
when the full dataset isn't available.
"""

# Import expanded problems
try:
    from backend.benchmarking.mbpp_expanded_sample import MBPP_EXPANDED_PROBLEMS
    _expanded = MBPP_EXPANDED_PROBLEMS
except:
    _expanded = []

MBPP_SAMPLE_PROBLEMS = [
    {
        "task_id": "mbpp_0",
        "text": "Write a function that takes a list of numbers and returns the sum of all even numbers.",
        "code": "def sum_even(numbers):\n    return sum(x for x in numbers if x % 2 == 0)",
        "test_list": [
            "assert sum_even([1, 2, 3, 4, 5]) == 6",
            "assert sum_even([2, 4, 6]) == 12",
            "assert sum_even([1, 3, 5]) == 0"
        ],
        "test_setup_code": ""
    },
    {
        "task_id": "mbpp_1",
        "text": "Write a function that checks if a string is a palindrome (reads the same forwards and backwards).",
        "code": "def is_palindrome(s):\n    return s == s[::-1]",
        "test_list": [
            "assert is_palindrome('racecar') == True",
            "assert is_palindrome('hello') == False",
            "assert is_palindrome('a') == True"
        ],
        "test_setup_code": ""
    },
    {
        "task_id": "mbpp_2",
        "text": "Write a function that finds the maximum value in a list of numbers.",
        "code": "def find_max(numbers):\n    if not numbers:\n        return None\n    return max(numbers)",
        "test_list": [
            "assert find_max([1, 5, 3, 9, 2]) == 9",
            "assert find_max([-1, -5, -3]) == -1",
            "assert find_max([42]) == 42"
        ],
        "test_setup_code": ""
    },
    {
        "task_id": "mbpp_3",
        "text": "Write a function that counts the number of vowels in a string.",
        "code": "def count_vowels(s):\n    vowels = 'aeiouAEIOU'\n    return sum(1 for char in s if char in vowels)",
        "test_list": [
            "assert count_vowels('hello') == 2",
            "assert count_vowels('python') == 1",
            "assert count_vowels('aeiou') == 5"
        ],
        "test_setup_code": ""
    },
    {
        "task_id": "mbpp_4",
        "text": "Write a function that removes duplicates from a list while preserving order.",
        "code": "def remove_duplicates(lst):\n    seen = set()\n    result = []\n    for item in lst:\n        if item not in seen:\n            seen.add(item)\n            result.append(item)\n    return result",
        "test_list": [
            "assert remove_duplicates([1, 2, 2, 3, 3, 3]) == [1, 2, 3]",
            "assert remove_duplicates(['a', 'b', 'a', 'c']) == ['a', 'b', 'c']",
            "assert remove_duplicates([1, 1, 1]) == [1]"
        ],
        "test_setup_code": ""
    }
] + _expanded
