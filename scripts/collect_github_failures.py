#!/usr/bin/env python3
"""
Collect 10,000 Broken Code Examples from GitHub

This script searches GitHub for code examples that contain errors, failures, or broken patterns.
It collects:
- Code with error handling (try/except blocks)
- Code with assertions that fail
- Code with syntax errors
- Code from issues labeled as bugs
- Code from failed CI/CD runs
- Code with common error patterns

Usage:
    python scripts/collect_github_failures.py [--output OUTPUT_FILE] [--limit 10000]
"""

import sys
import json
import time
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import re
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# GitHub API configuration
GITHUB_API_BASE = "https://api.github.com"
RATE_LIMIT_DELAY = 0.5  # Delay between requests to respect rate limits
MAX_WORKERS = 5  # Parallel workers for API calls

# Error patterns to search for
ERROR_PATTERNS = [
    # Python error patterns
    r'raise\s+\w+Error',
    r'raise\s+\w+Exception',
    r'except\s+\w+Error',
    r'except\s+\w+Exception',
    r'assert\s+.*==.*',
    r'assert\s+.*!=.*',
    r'assert\s+.*is\s+None',
    r'assert\s+.*is\s+not\s+None',
    r'raise\s+ValueError',
    r'raise\s+TypeError',
    r'raise\s+KeyError',
    r'raise\s+AttributeError',
    r'raise\s+IndexError',
    r'raise\s+RuntimeError',
    r'raise\s+NotImplementedError',
    # Common error messages
    r'Error:',
    r'Exception:',
    r'Traceback',
    r'NameError',
    r'TypeError',
    r'ValueError',
    r'KeyError',
    r'AttributeError',
    r'IndexError',
    # Test failures
    r'assert.*failed',
    r'FAILED',
    r'FAILURE',
    r'Test.*failed',
    r'pytest.*FAILED',
    r'unittest.*FAILED',
    # Syntax errors
    r'SyntaxError',
    r'IndentationError',
    r'TabError',
]

# Search queries for GitHub Code Search API
SEARCH_QUERIES = [
    # Python error handling
    'language:python raise Exception',
    'language:python try except',
    'language:python assert failed',
    'language:python NameError',
    'language:python TypeError',
    'language:python ValueError',
    'language:python KeyError',
    'language:python AttributeError',
    'language:python IndexError',
    'language:python SyntaxError',
    'language:python IndentationError',
    # Test failures
    'language:python pytest FAILED',
    'language:python unittest FAILED',
    'language:python test failed',
    'language:python assert error',
    # Common bugs
    'language:python bug fix',
    'language:python error handling',
    'language:python exception handling',
    'language:python catch exception',
    # JavaScript/TypeScript errors
    'language:javascript throw Error',
    'language:javascript try catch',
    'language:typescript throw Error',
    'language:typescript try catch',
    # General error patterns
    'error handling code',
    'exception handling example',
    'bug fix code',
    'failed test case',
]


class GitHubFailureCollector:
    """Collect broken code examples from GitHub."""
    
    def __init__(self, github_token: Optional[str] = None, max_results: int = 10000):
        """
        Initialize collector.
        
        Args:
            github_token: GitHub personal access token (optional, increases rate limit)
            max_results: Maximum number of code examples to collect
        """
        self.github_token = github_token
        self.max_results = max_results
        self.collected = []
        self.lock = Lock()
        self.session = requests.Session()
        
        # Set up session headers
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'Grace-AI-Code-Collector'
        }
        if github_token:
            headers['Authorization'] = f'token {github_token}'
        self.session.headers.update(headers)
        
        self.stats = {
            'total_searched': 0,
            'total_collected': 0,
            'api_calls': 0,
            'rate_limit_hits': 0,
            'errors': 0
        }
    
    def _make_api_request(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make GitHub API request with rate limiting."""
        try:
            time.sleep(RATE_LIMIT_DELAY)  # Rate limiting
            response = self.session.get(url, params=params, timeout=30)
            self.stats['api_calls'] += 1
            
            # Check rate limit
            if response.status_code == 403:
                rate_limit_remaining = response.headers.get('X-RateLimit-Remaining', '0')
                if rate_limit_remaining == '0':
                    self.stats['rate_limit_hits'] += 1
                    reset_time = response.headers.get('X-RateLimit-Reset', '0')
                    wait_time = max(0, int(reset_time) - int(time.time())) + 1
                    logger.warning(f"Rate limit hit. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    return self._make_api_request(url, params)
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            self.stats['errors'] += 1
            return None
    
    def search_code(self, query: str, per_page: int = 100) -> List[Dict[str, Any]]:
        """
        Search GitHub code using Code Search API.
        
        Args:
            query: Search query
            per_page: Results per page (max 100)
        
        Returns:
            List of code search results
        """
        url = f"{GITHUB_API_BASE}/search/code"
        params = {
            'q': query,
            'per_page': min(per_page, 100),
            'page': 1
        }
        
        results = []
        max_pages = 10  # Limit pages to avoid excessive API calls
        
        for page in range(1, max_pages + 1):
            params['page'] = page
            data = self._make_api_request(url, params)
            
            if not data:
                break
            
            items = data.get('items', [])
            if not items:
                break
            
            results.extend(items)
            self.stats['total_searched'] += len(items)
            
            # Check if we have enough results
            if len(self.collected) >= self.max_results:
                break
            
            # Check if there are more pages
            if len(items) < per_page:
                break
        
        return results
    
    def get_file_content(self, repo: str, path: str, ref: str = 'master') -> Optional[str]:
        """
        Get file content from GitHub repository.
        
        Args:
            repo: Repository in format 'owner/repo'
            path: File path in repository
            ref: Git reference (branch/tag)
        
        Returns:
            File content as string
        """
        url = f"{GITHUB_API_BASE}/repos/{repo}/contents/{path}"
        params = {'ref': ref}
        
        data = self._make_api_request(url, params)
        if not data:
            return None
        
        # Decode base64 content
        import base64
        try:
            content = base64.b64decode(data.get('content', '')).decode('utf-8', errors='ignore')
            return content
        except Exception as e:
            logger.error(f"Failed to decode content: {e}")
            return None
    
    def extract_code_snippet(self, content: str, line_number: int, context_lines: int = 10) -> Optional[Dict[str, Any]]:
        """
        Extract code snippet around error line.
        
        Args:
            content: Full file content
            line_number: Line number where error occurs
            context_lines: Number of context lines before/after
        
        Returns:
            Code snippet with metadata
        """
        lines = content.split('\n')
        total_lines = len(lines)
        
        # Calculate snippet bounds
        start_line = max(0, line_number - context_lines - 1)
        end_line = min(total_lines, line_number + context_lines)
        
        snippet_lines = lines[start_line:end_line]
        snippet = '\n'.join(snippet_lines)
        
        # Check if snippet contains error patterns
        has_error_pattern = any(re.search(pattern, snippet, re.IGNORECASE) for pattern in ERROR_PATTERNS)
        
        if has_error_pattern:
            return {
                'snippet': snippet,
                'start_line': start_line + 1,
                'end_line': end_line,
                'error_line': line_number,
                'total_lines': total_lines
            }
        
        return None
    
    def process_search_result(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process a single search result and extract broken code.
        
        Args:
            item: GitHub code search result
        
        Returns:
            Extracted code example with metadata
        """
        try:
            repo = item['repository']['full_name']
            path = item['path']
            sha = item.get('sha', 'master')
            
            # Get file content
            content = self.get_file_content(repo, path, sha)
            if not content:
                return None
            
            # Extract snippet around matched line
            line_number = item.get('line_number', 1)
            snippet_data = self.extract_code_snippet(content, line_number)
            
            if not snippet_data:
                return None
            
            # Build result
            result = {
                'id': f"{repo}_{path}_{line_number}",
                'repository': repo,
                'file_path': path,
                'url': item.get('html_url', ''),
                'code_snippet': snippet_data['snippet'],
                'start_line': snippet_data['start_line'],
                'end_line': snippet_data['end_line'],
                'error_line': snippet_data['error_line'],
                'language': item.get('language', 'unknown'),
                'collected_at': datetime.utcnow().isoformat(),
                'error_patterns_found': [
                    pattern for pattern in ERROR_PATTERNS
                    if re.search(pattern, snippet_data['snippet'], re.IGNORECASE)
                ]
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing result: {e}")
            return None
    
    def collect_from_issues(self, language: str = 'python', max_issues: int = 1000) -> List[Dict[str, Any]]:
        """
        Collect code from GitHub issues labeled as bugs.
        
        Args:
            language: Programming language filter
            max_issues: Maximum issues to process
        
        Returns:
            List of code examples from issues
        """
        url = f"{GITHUB_API_BASE}/search/issues"
        query = f'label:bug language:{language} state:closed'
        params = {
            'q': query,
            'per_page': 100,
            'sort': 'updated',
            'order': 'desc'
        }
        
        results = []
        max_pages = max_issues // 100
        
        for page in range(1, max_pages + 1):
            params['page'] = page
            data = self._make_api_request(url, params)
            
            if not data:
                break
            
            issues = data.get('items', [])
            if not issues:
                break
            
            for issue in issues:
                # Extract code blocks from issue body
                body = issue.get('body', '')
                code_blocks = re.findall(r'```[\w]*\n(.*?)```', body, re.DOTALL)
                
                for code_block in code_blocks:
                    # Check if code contains error patterns
                    if any(re.search(pattern, code_block, re.IGNORECASE) for pattern in ERROR_PATTERNS):
                        result = {
                            'id': f"issue_{issue['number']}_{issue['repository']['full_name']}",
                            'repository': issue['repository']['full_name'],
                            'file_path': None,
                            'url': issue.get('html_url', ''),
                            'code_snippet': code_block.strip(),
                            'start_line': 1,
                            'end_line': len(code_block.split('\n')),
                            'error_line': 1,
                            'language': language,
                            'collected_at': datetime.utcnow().isoformat(),
                            'source': 'github_issue',
                            'issue_number': issue['number'],
                            'issue_title': issue.get('title', ''),
                            'error_patterns_found': [
                                pattern for pattern in ERROR_PATTERNS
                                if re.search(pattern, code_block, re.IGNORECASE)
                            ]
                        }
                        results.append(result)
                        
                        if len(self.collected) + len(results) >= self.max_results:
                            break
            
            if len(self.collected) + len(results) >= self.max_results:
                break
        
        return results
    
    def collect_all(self) -> List[Dict[str, Any]]:
        """Collect all broken code examples."""
        logger.info(f"Starting collection of {self.max_results} broken code examples...")
        
        # Strategy 1: Search code directly
        logger.info("Strategy 1: Searching GitHub code...")
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = []
            
            for query in SEARCH_QUERIES[:20]:  # Limit queries to avoid rate limits
                if len(self.collected) >= self.max_results:
                    break
                
                future = executor.submit(self.search_code, query, per_page=50)
                futures.append((future, query))
            
            for future, query in futures:
                if len(self.collected) >= self.max_results:
                    break
                
                try:
                    search_results = future.result(timeout=60)
                    logger.info(f"Found {len(search_results)} results for query: {query}")
                    
                    # Process results
                    for item in search_results:
                        if len(self.collected) >= self.max_results:
                            break
                        
                        result = self.process_search_result(item)
                        if result:
                            with self.lock:
                                self.collected.append(result)
                                self.stats['total_collected'] += 1
                                
                                if self.stats['total_collected'] % 100 == 0:
                                    logger.info(f"Collected {self.stats['total_collected']}/{self.max_results} examples...")
                
                except Exception as e:
                    logger.error(f"Error processing query {query}: {e}")
        
        # Strategy 2: Collect from issues
        if len(self.collected) < self.max_results:
            logger.info("Strategy 2: Collecting from GitHub issues...")
            issue_results = self.collect_from_issues(max_issues=2000)
            self.collected.extend(issue_results)
            self.stats['total_collected'] = len(self.collected)
        
        logger.info(f"Collection complete! Collected {len(self.collected)} examples")
        return self.collected
    
    def save_results(self, output_file: Path):
        """Save collected results to JSON file."""
        output_data = {
            'metadata': {
                'total_collected': len(self.collected),
                'collection_date': datetime.utcnow().isoformat(),
                'stats': self.stats
            },
            'examples': self.collected
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results saved to {output_file}")
        logger.info(f"Total examples: {len(self.collected)}")
        logger.info(f"API calls made: {self.stats['api_calls']}")
        logger.info(f"Rate limit hits: {self.stats['rate_limit_hits']}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Collect broken code examples from GitHub"
    )
    parser.add_argument(
        '--output',
        type=str,
        default='github_failures_collection.json',
        help='Output file path (default: github_failures_collection.json)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=10000,
        help='Maximum number of examples to collect (default: 10000)'
    )
    parser.add_argument(
        '--token',
        type=str,
        default=None,
        help='GitHub personal access token (optional, increases rate limit)'
    )
    
    args = parser.parse_args()
    
    # Check for token in environment
    github_token = args.token or os.environ.get('GITHUB_TOKEN')
    
    # Initialize collector
    collector = GitHubFailureCollector(
        github_token=github_token,
        max_results=args.limit
    )
    
    # Collect examples
    collector.collect_all()
    
    # Save results
    output_path = Path(args.output)
    collector.save_results(output_path)
    
    print("\n" + "="*80)
    print("COLLECTION COMPLETE")
    print("="*80)
    print(f"Total examples collected: {len(collector.collected)}")
    print(f"Output file: {output_path}")
    print(f"API calls: {collector.stats['api_calls']}")
    print(f"Rate limit hits: {collector.stats['rate_limit_hits']}")
    print("="*80)


if __name__ == "__main__":
    import os
    main()
