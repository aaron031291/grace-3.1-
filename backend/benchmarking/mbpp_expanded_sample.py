"""
Expanded MBPP Sample Problems

More MBPP problems for testing template expansion.
"""

MBPP_EXPANDED_PROBLEMS = [
    {
        "task_id": "mbpp_5",
        "text": "Write a function that checks if a number is prime.",
        "code": "def is_prime(n):\n    if n < 2:\n        return False\n    for i in range(2, int(n**0.5) + 1):\n        if n % i == 0:\n            return False\n    return True",
        "test_list": [
            "assert is_prime(2) == True",
            "assert is_prime(4) == False",
            "assert is_prime(17) == True",
            "assert is_prime(1) == False"
        ],
        "test_setup_code": ""
    },
    {
        "task_id": "mbpp_6",
        "text": "Write a function that calculates the factorial of a number.",
        "code": "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)",
        "test_list": [
            "assert factorial(0) == 1",
            "assert factorial(5) == 120",
            "assert factorial(3) == 6"
        ],
        "test_setup_code": ""
    },
    {
        "task_id": "mbpp_7",
        "text": "Write a function that reverses a string.",
        "code": "def reverse_string(s):\n    return s[::-1]",
        "test_list": [
            "assert reverse_string('hello') == 'olleh'",
            "assert reverse_string('python') == 'nohtyp'",
            "assert reverse_string('') == ''"
        ],
        "test_setup_code": ""
    },
    {
        "task_id": "mbpp_8",
        "text": "Write a function that finds the minimum value in a list of numbers.",
        "code": "def find_min(numbers):\n    if not numbers:\n        return None\n    return min(numbers)",
        "test_list": [
            "assert find_min([1, 5, 3, 9, 2]) == 1",
            "assert find_min([-1, -5, -3]) == -5",
            "assert find_min([42]) == 42"
        ],
        "test_setup_code": ""
    },
    {
        "task_id": "mbpp_9",
        "text": "Write a function that checks if a string contains only digits.",
        "code": "def is_digits(s):\n    return s.isdigit()",
        "test_list": [
            "assert is_digits('123') == True",
            "assert is_digits('12a') == False",
            "assert is_digits('') == False"
        ],
        "test_setup_code": ""
    },
    {
        "task_id": "mbpp_10",
        "text": "Write a function that calculates the sum of all numbers in a list.",
        "code": "def sum_list(numbers):\n    return sum(numbers)",
        "test_list": [
            "assert sum_list([1, 2, 3]) == 6",
            "assert sum_list([10, 20, 30]) == 60",
            "assert sum_list([]) == 0"
        ],
        "test_setup_code": ""
    },
    {
        "task_id": "mbpp_11",
        "text": "Write a function that counts the number of words in a string.",
        "code": "def count_words(text):\n    return len(text.split())",
        "test_list": [
            "assert count_words('hello world') == 2",
            "assert count_words('the quick brown fox') == 4",
            "assert count_words('') == 0"
        ],
        "test_setup_code": ""
    },
    {
        "task_id": "mbpp_12",
        "text": "Write a function that checks if two strings are anagrams.",
        "code": "def are_anagrams(s1, s2):\n    return sorted(s1.lower()) == sorted(s2.lower())",
        "test_list": [
            "assert are_anagrams('listen', 'silent') == True",
            "assert are_anagrams('hello', 'world') == False",
            "assert are_anagrams('a', 'a') == True"
        ],
        "test_setup_code": ""
    },
    {
        "task_id": "mbpp_13",
        "text": "Write a function that finds the average of a list of numbers.",
        "code": "def average(numbers):\n    if not numbers:\n        return 0\n    return sum(numbers) / len(numbers)",
        "test_list": [
            "assert average([1, 2, 3, 4]) == 2.5",
            "assert average([10, 20, 30]) == 20.0",
            "assert average([5]) == 5.0"
        ],
        "test_setup_code": ""
    },
    {
        "task_id": "mbpp_14",
        "text": "Write a function that capitalizes the first letter of each word in a string.",
        "code": "def capitalize_words(text):\n    return ' '.join(word.capitalize() for word in text.split())",
        "test_list": [
            "assert capitalize_words('hello world') == 'Hello World'",
            "assert capitalize_words('python programming') == 'Python Programming'",
            "assert capitalize_words('a') == 'A'"
        ],
        "test_setup_code": ""
    }
]
