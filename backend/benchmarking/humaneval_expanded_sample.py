"""
Expanded HumanEval Sample Problems

More HumanEval problems for testing template expansion.
"""

HUMANEVAL_EXPANDED_PROBLEMS = [
    {
        "task_id": "humaneval_5",
        "prompt": "def filter_integers(values: list) -> list:\n    \"\"\" Filter given list of any values only for integers.\n    >>> filter_integers(['a', 3.14, 5])\n    [5]\n    >>> filter_integers([1, 2, 3, 'abc', {}, []])\n    [1, 2, 3]\n    \"\"\"\n",
        "test": "def check(candidate):\n    assert candidate(['a', 3.14, 5]) == [5]\n    assert candidate([1, 2, 3, 'abc', {}, []]) == [1, 2, 3]\n    assert candidate([1, 2, 3, 4]) == [1, 2, 3, 4]\n    assert candidate(['a', 'b', 'c']) == []\n",
        "entry_point": "filter_integers",
        "canonical_solution": "def filter_integers(values: list) -> list:\n    return [x for x in values if isinstance(x, int)]\n"
    },
    {
        "task_id": "humaneval_6",
        "prompt": "def find_words(text: str, length: int) -> list:\n    \"\"\" Find all words in the text that are exactly the given length.\n    >>> find_words('The quick brown fox', 3)\n    ['The', 'fox']\n    >>> find_words('The quick brown fox', 4)\n    ['quick', 'brown']\n    \"\"\"\n",
        "test": "def check(candidate):\n    assert candidate('The quick brown fox', 3) == ['The', 'fox']\n    assert candidate('The quick brown fox', 4) == ['quick', 'brown']\n    assert candidate('Hello world', 5) == ['Hello', 'world']\n",
        "entry_point": "find_words",
        "canonical_solution": "def find_words(text: str, length: int) -> list:\n    return [word for word in text.split() if len(word) == length]\n"
    },
    {
        "task_id": "humaneval_7",
        "prompt": "def count_occurrences(text: str, word: str) -> int:\n    \"\"\" Count how many times a word appears in the text.\n    >>> count_occurrences('hello world hello', 'hello')\n    2\n    >>> count_occurrences('the cat sat on the mat', 'the')\n    2\n    \"\"\"\n",
        "test": "def check(candidate):\n    assert candidate('hello world hello', 'hello') == 2\n    assert candidate('the cat sat on the mat', 'the') == 2\n    assert candidate('a b c d', 'e') == 0\n",
        "entry_point": "count_occurrences",
        "canonical_solution": "def count_occurrences(text: str, word: str) -> int:\n    return text.split().count(word)\n"
    },
    {
        "task_id": "humaneval_8",
        "prompt": "def reverse_words(text: str) -> str:\n    \"\"\" Reverse the order of words in the text.\n    >>> reverse_words('hello world')\n    'world hello'\n    >>> reverse_words('the quick brown fox')\n    'fox brown quick the'\n    \"\"\"\n",
        "test": "def check(candidate):\n    assert candidate('hello world') == 'world hello'\n    assert candidate('the quick brown fox') == 'fox brown quick the'\n    assert candidate('a') == 'a'\n",
        "entry_point": "reverse_words",
        "canonical_solution": "def reverse_words(text: str) -> str:\n    return ' '.join(reversed(text.split()))\n"
    },
    {
        "task_id": "humaneval_9",
        "prompt": "def is_sorted(numbers: list) -> bool:\n    \"\"\" Check if a list of numbers is sorted in ascending order.\n    >>> is_sorted([1, 2, 3, 4])\n    True\n    >>> is_sorted([1, 3, 2, 4])\n    False\n    \"\"\"\n",
        "test": "def check(candidate):\n    assert candidate([1, 2, 3, 4]) == True\n    assert candidate([1, 3, 2, 4]) == False\n    assert candidate([1]) == True\n    assert candidate([4, 3, 2, 1]) == False\n",
        "entry_point": "is_sorted",
        "canonical_solution": "def is_sorted(numbers: list) -> bool:\n    return numbers == sorted(numbers)\n"
    },
    {
        "task_id": "humaneval_10",
        "prompt": "def remove_vowels(text: str) -> str:\n    \"\"\" Remove all vowels from the text.\n    >>> remove_vowels('hello')\n    'hll'\n    >>> remove_vowels('python')\n    'pythn'\n    \"\"\"\n",
        "test": "def check(candidate):\n    assert candidate('hello') == 'hll'\n    assert candidate('python') == 'pythn'\n    assert candidate('aeiou') == ''\n",
        "entry_point": "remove_vowels",
        "canonical_solution": "def remove_vowels(text: str) -> str:\n    vowels = 'aeiouAEIOU'\n    return ''.join(c for c in text if c not in vowels)\n"
    }
]
