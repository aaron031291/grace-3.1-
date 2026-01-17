# GitHub & Similar Platforms - Knowledge Extraction Guide

**Date:** 2026-01-16  
**Purpose:** Extract healing knowledge from GitHub, Stack Overflow, and similar platforms

---

## 📋 Summary

**GitHub, Stack Overflow, and similar platforms** are excellent sources for healing knowledge. This guide shows how to extract fix patterns from:
- GitHub Issues (solved problems)
- GitHub Discussions
- Stack Overflow (Q&A)
- Reddit (r/learnpython, r/Python)
- Discord communities
- Other developer forums

---

## 1. 🔍 GitHub - Primary Source

### A. **GitHub Issues API**

**Best For:** Finding solved problems with code fixes

**API Endpoint:**
```
GET https://api.github.com/repos/{owner}/{repo}/issues
```

**Search Strategy:**
1. Search for error messages
2. Filter by "closed" status
3. Look for issues with solutions
4. Extract fix patterns

**Example: SQLAlchemy Table Redefinition**

```python
import requests

# Search SQLAlchemy issues
url = "https://api.github.com/repos/sqlalchemy/sqlalchemy/issues"
params = {
    "state": "closed",  # Only closed (solved) issues
    "q": "table already defined extend_existing",
    "per_page": 100
}

response = requests.get(url, params=params)
issues = response.json()

for issue in issues:
    # Check if issue has solution
    if issue["comments"] > 0:
        # Get comments (solutions)
        comments_url = issue["comments_url"]
        comments = requests.get(comments_url).json()
        
        # Extract fix from comments
        for comment in comments:
            if "extend_existing" in comment["body"]:
                # Found a solution!
                fix_pattern = extract_fix_pattern(comment["body"])
                add_to_knowledge_base(fix_pattern)
```

**What to Extract:**
- Error messages (exact text)
- Solutions (code fixes)
- Context (when/why it happens)
- Workarounds

---

### B. **GitHub Search API**

**Best For:** Finding code examples and solutions across all repos

**API Endpoint:**
```
GET https://api.github.com/search/issues
```

**Search Queries:**
```python
# Search for error messages
queries = [
    "ImportError cannot import name partially initialized",
    "SQLAlchemy table already defined extend_existing",
    "ModuleNotFoundError No module named",
    "circular import python solution",
    "database connection timeout python",
]

for query in queries:
    url = "https://api.github.com/search/issues"
    params = {
        "q": f"{query} is:closed",
        "sort": "reactions",  # Most upvoted solutions
        "order": "desc"
    }
    
    response = requests.get(url, params=params)
    results = response.json()["items"]
    
    for issue in results[:10]:  # Top 10
        # Extract solution
        solution = extract_solution(issue)
        if solution:
            add_fix_pattern(solution)
```

**Advanced Search:**
```python
# Search in specific languages
"ImportError python language:python"

# Search in code
"extend_existing=True code:python"

# Search in specific repos
"table already defined repo:sqlalchemy/sqlalchemy"
```

---

### C. **GitHub Code Search**

**Best For:** Finding actual code fixes in repositories

**API Endpoint:**
```
GET https://api.github.com/search/code
```

**Example:**
```python
# Find code that fixes table redefinition
url = "https://api.github.com/search/code"
params = {
    "q": "extend_existing=True language:python",
    "sort": "indexed",
    "order": "desc"
}

response = requests.get(url, params=params)
code_results = response.json()["items"]

for result in code_results:
    # Get file content
    file_url = result["html_url"]
    # Extract context (before/after fix)
    fix_context = extract_fix_context(file_url)
    # Create fix pattern
    pattern = create_pattern_from_code(fix_context)
```

---

### D. **GitHub Discussions**

**Best For:** Community solutions and best practices

**API Endpoint:**
```
GET https://api.github.com/repos/{owner}/{repo}/discussions
```

**Example:**
```python
# Get discussions about errors
url = "https://api.github.com/repos/python/cpython/discussions"
params = {
    "category": "General",  # or "Q&A", "Ideas"
    "per_page": 100
}

response = requests.get(url, params=params)
discussions = response.json()

for discussion in discussions:
    if "error" in discussion["title"].lower():
        # Extract solutions from discussion
        solutions = extract_solutions(discussion)
        for solution in solutions:
            add_to_knowledge_base(solution)
```

---

## 2. 📚 Stack Overflow - Q&A Platform

### A. **Stack Overflow API**

**Best For:** Proven solutions with upvotes

**API Endpoint:**
```
GET https://api.stackexchange.com/2.3/search
```

**Search Strategy:**
```python
import requests

def search_stackoverflow(error_message):
    """Search Stack Overflow for error solutions."""
    url = "https://api.stackexchange.com/2.3/search"
    params = {
        "order": "desc",
        "sort": "votes",  # Most upvoted (best solutions)
        "tagged": "python",
        "intitle": error_message,
        "site": "stackoverflow",
        "filter": "withbody"  # Include answer body
    }
    
    response = requests.get(url, params=params)
    questions = response.json()["items"]
    
    solutions = []
    for question in questions:
        # Get accepted answer (usually best solution)
        if question.get("accepted_answer_id"):
            answer_id = question["accepted_answer_id"]
            answer = get_answer(answer_id)
            solutions.append({
                "error": error_message,
                "solution": extract_code_from_answer(answer),
                "upvotes": answer["score"],
                "is_accepted": True
            })
    
    return solutions

# Example usage
solutions = search_stackoverflow("ImportError cannot import name")
for solution in solutions:
    if solution["upvotes"] > 10:  # Only high-quality solutions
        add_fix_pattern(solution)
```

**What to Extract:**
- Error messages (exact match)
- Code solutions (working fixes)
- Upvote count (quality indicator)
- Accepted answers (verified solutions)

---

### B. **Stack Overflow Tags**

**Best For:** Finding solutions by error type

**Common Tags:**
- `python` + `importerror`
- `python` + `sqlalchemy`
- `python` + `circular-import`
- `python` + `module-not-found`

**Example:**
```python
tags = [
    "python;importerror",
    "python;sqlalchemy",
    "python;circular-import",
    "python;module-not-found",
    "python;database-connection",
]

for tag in tags:
    url = "https://api.stackoverflow.com/2.3/questions"
    params = {
        "tagged": tag,
        "sort": "votes",
        "order": "desc",
        "filter": "withbody",
        "site": "stackoverflow"
    }
    
    response = requests.get(url, params=params)
    questions = response.json()["items"]
    
    # Extract solutions
    for question in questions[:20]:  # Top 20
        solution = extract_solution(question)
        add_to_knowledge_base(solution)
```

---

## 3. 💬 Reddit - Community Discussions

### A. **Reddit API (PRAW)**

**Best For:** Real-world problems and solutions

**Install:**
```bash
pip install praw
```

**Example:**
```python
import praw

reddit = praw.Reddit(
    client_id="your_client_id",
    client_secret="your_client_secret",
    user_agent="Grace Healing Knowledge Extractor"
)

# Search r/learnpython
subreddit = reddit.subreddit("learnpython")

# Search for error-related posts
for submission in subreddit.search("ImportError", limit=100):
    # Get comments (solutions)
    submission.comments.replace_more(limit=0)
    for comment in submission.comments:
        if comment.score > 5:  # Upvoted solutions
            solution = extract_solution(comment.body)
            if solution:
                add_to_knowledge_base(solution)
```

**Subreddits to Monitor:**
- `r/learnpython` - Beginner questions
- `r/Python` - General Python discussions
- `r/SQLAlchemy` - SQLAlchemy-specific
- `r/flask` - Flask/web framework errors
- `r/django` - Django-specific errors

---

## 4. 🎮 Discord - Real-Time Community

### A. **Discord Bots / Webhooks**

**Best For:** Real-time error discussions

**Strategy:**
1. Join Python Discord servers
2. Monitor error-related channels
3. Extract solutions from discussions
4. Store in knowledge base

**Example Channels:**
- `#python-help` - General help
- `#sqlalchemy` - SQLAlchemy help
- `#errors` - Error discussions

**Note:** Requires manual monitoring or bot development

---

## 5. 🔧 Implementation Script

### Complete Extraction Script

```python
"""
Extract healing knowledge from GitHub, Stack Overflow, and Reddit.
"""
import requests
import json
from typing import List, Dict
import time

class KnowledgeExtractor:
    """Extract fix patterns from multiple sources."""
    
    def __init__(self):
        self.patterns = []
        self.github_token = "your_github_token"  # Optional, increases rate limit
        
    def extract_from_github_issues(self, error_message: str) -> List[Dict]:
        """Extract solutions from GitHub issues."""
        url = "https://api.github.com/search/issues"
        headers = {}
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"
        
        params = {
            "q": f"{error_message} is:closed language:python",
            "sort": "reactions",
            "order": "desc",
            "per_page": 20
        }
        
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            return []
        
        issues = response.json()["items"]
        solutions = []
        
        for issue in issues:
            # Get issue comments (solutions)
            comments_url = issue["comments_url"]
            comments_response = requests.get(comments_url, headers=headers)
            if comments_response.status_code == 200:
                comments = comments_response.json()
                for comment in comments:
                    if self._contains_solution(comment["body"]):
                        solution = self._extract_solution(comment["body"])
                        solutions.append({
                            "source": "github",
                            "error": error_message,
                            "solution": solution,
                            "url": comment["html_url"],
                            "upvotes": comment.get("reactions", {}).get("+1", 0)
                        })
            
            time.sleep(0.5)  # Rate limiting
        
        return solutions
    
    def extract_from_stackoverflow(self, error_message: str) -> List[Dict]:
        """Extract solutions from Stack Overflow."""
        url = "https://api.stackexchange.com/2.3/search"
        params = {
            "order": "desc",
            "sort": "votes",
            "tagged": "python",
            "intitle": error_message,
            "site": "stackoverflow",
            "filter": "withbody"
        }
        
        response = requests.get(url, params=params)
        if response.status_code != 200:
            return []
        
        questions = response.json()["items"]
        solutions = []
        
        for question in questions:
            # Get accepted answer
            if question.get("accepted_answer_id"):
                answer_id = question["accepted_answer_id"]
                answer_url = f"https://api.stackexchange.com/2.3/answers/{answer_id}"
                answer_params = {
                    "site": "stackoverflow",
                    "filter": "withbody"
                }
                answer_response = requests.get(answer_url, params=answer_params)
                if answer_response.status_code == 200:
                    answer = answer_response.json()["items"][0]
                    solution = self._extract_solution(answer["body"])
                    solutions.append({
                        "source": "stackoverflow",
                        "error": error_message,
                        "solution": solution,
                        "url": answer["link"],
                        "upvotes": answer["score"],
                        "is_accepted": True
                    })
        
        return solutions
    
    def _contains_solution(self, text: str) -> bool:
        """Check if text contains a solution."""
        solution_indicators = [
            "extend_existing",
            "import",
            "fix",
            "solution",
            "workaround",
            "try this",
            "here's how"
        ]
        return any(indicator in text.lower() for indicator in solution_indicators)
    
    def _extract_solution(self, text: str) -> str:
        """Extract code solution from text."""
        # Look for code blocks
        import re
        code_blocks = re.findall(r'```python\n(.*?)\n```', text, re.DOTALL)
        if code_blocks:
            return code_blocks[0]
        
        # Look for inline code
        inline_code = re.findall(r'`([^`]+)`', text)
        if inline_code:
            return inline_code[0]
        
        return text[:500]  # First 500 chars if no code found
    
    def extract_all_patterns(self, error_messages: List[str]) -> Dict:
        """Extract patterns for multiple error messages."""
        all_solutions = {}
        
        for error_message in error_messages:
            print(f"Extracting solutions for: {error_message}")
            
            # GitHub
            github_solutions = self.extract_from_github_issues(error_message)
            
            # Stack Overflow
            so_solutions = self.extract_from_stackoverflow(error_message)
            
            # Combine and rank
            all_solutions[error_message] = {
                "github": github_solutions,
                "stackoverflow": so_solutions,
                "total": len(github_solutions) + len(so_solutions)
            }
            
            time.sleep(1)  # Rate limiting
        
        return all_solutions

# Usage
extractor = KnowledgeExtractor()

error_messages = [
    "Table 'X' is already defined for this MetaData instance",
    "ImportError: cannot import name 'X' from partially initialized module",
    "ModuleNotFoundError: No module named",
    "Database connection timeout",
    "circular import python"
]

solutions = extractor.extract_all_patterns(error_messages)

# Save to knowledge base
with open("extracted_patterns.json", "w") as f:
    json.dump(solutions, f, indent=2)
```

---

## 6. 📊 Pattern Creation from Extracted Data

### Convert Solutions to Fix Patterns

```python
def create_fix_pattern_from_solutions(error_message: str, solutions: List[Dict]) -> Dict:
    """Create a fix pattern from extracted solutions."""
    
    # Find most common solution
    solution_counts = {}
    for solution in solutions:
        sol_text = solution["solution"]
        if sol_text not in solution_counts:
            solution_counts[sol_text] = {
                "count": 0,
                "upvotes": 0,
                "sources": []
            }
        solution_counts[sol_text]["count"] += 1
        solution_counts[sol_text]["upvotes"] += solution.get("upvotes", 0)
        solution_counts[sol_text]["sources"].append(solution["source"])
    
    # Get best solution (most common + most upvoted)
    best_solution = max(
        solution_counts.items(),
        key=lambda x: (x[1]["count"], x[1]["upvotes"])
    )
    
    # Create fix pattern
    pattern = {
        "error_pattern": create_regex_from_error(error_message),
        "fix_template": best_solution[0],
        "confidence": calculate_confidence(best_solution[1]),
        "sources": best_solution[1]["sources"],
        "examples": [s["url"] for s in solutions[:5]]
    }
    
    return pattern
```

---

## 7. 🎯 Quick Start

### Step 1: Get API Keys

**GitHub:**
1. Go to https://github.com/settings/tokens
2. Generate new token
3. Add to script

**Stack Overflow:**
- No key needed (but rate limited)
- Register app for higher limits: https://stackapps.com/apps/oauth/register

**Reddit:**
1. Go to https://www.reddit.com/prefs/apps
2. Create app
3. Get client_id and client_secret

### Step 2: Run Extraction

```python
# Extract for your specific errors
extractor = KnowledgeExtractor()

errors = [
    "Table 'users' is already defined",
    "ImportError: cannot import name",
    "ModuleNotFoundError: No module named"
]

solutions = extractor.extract_all_patterns(errors)
```

### Step 3: Add to Knowledge Base

```python
# Convert to fix patterns
for error, data in solutions.items():
    pattern = create_fix_pattern_from_solutions(error, data["github"] + data["stackoverflow"])
    add_to_healing_knowledge_base(pattern)
```

---

## 8. 📈 Best Practices

### Quality Filters:
- **Minimum upvotes**: Only solutions with 5+ upvotes
- **Accepted answers**: Prefer accepted answers on Stack Overflow
- **Multiple sources**: Solutions found in multiple places are more reliable
- **Recent solutions**: Prefer recent solutions (may be outdated)

### Rate Limiting:
- **GitHub**: 60 requests/hour (unauthenticated), 5000/hour (authenticated)
- **Stack Overflow**: 300 requests/day (unauthenticated)
- **Reddit**: Varies by subreddit

### Storage:
- Store raw solutions for reference
- Extract patterns for knowledge base
- Track source URLs for verification
- Update patterns when better solutions found

---

## 9. 🔗 Related Files

- `HEALING_KNOWLEDGE_SOURCES.md` - All knowledge sources
- `backend/cognitive/healing_knowledge_base.py` - Add patterns here
- `backend/tests/healing_results.json` - Your current errors

---

## ✅ Summary

**Best Platforms (Priority):**

1. **Stack Overflow** - Highest quality, proven solutions
2. **GitHub Issues** - Real code fixes, context-rich
3. **GitHub Code Search** - Actual implementations
4. **Reddit** - Real-world problems
5. **Discord** - Real-time help (manual)

**Next Steps:**
1. Get API keys (GitHub, Reddit)
2. Run extraction script for your errors
3. Filter by quality (upvotes, accepted)
4. Convert to fix patterns
5. Add to knowledge base

---

**Status:** 🔍 **READY TO EXTRACT FROM GITHUB & SIMILAR PLATFORMS**
