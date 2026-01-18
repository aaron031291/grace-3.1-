#!/usr/bin/env python3
"""
Enhanced GitHub Failure Collector - Multiple Strategies

This script uses multiple strategies to collect broken code examples:
1. GitHub API Code Search (requires token)
2. GitHub Gist search
3. GitHub Issues/PRs with error code
4. Web scraping from public repositories
5. Stack Overflow code snippets with errors

Usage:
    python scripts/collect_github_failures_enhanced.py [--output OUTPUT_FILE] [--limit 10000] [--token GITHUB_TOKEN]
"""

import sys
import json
import time
import logging
import argparse
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import re
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import base64

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
RATE_LIMIT_DELAY = 0.5
MAX_WORKERS = 5

# Error patterns
ERROR_PATTERNS = [
    r'raise\s+\w+Error',
    r'raise\s+\w+Exception',
    r'except\s+\w+Error',
    r'except\s+\w+Exception',
    r'assert\s+.*==.*',
    r'assert\s+.*!=.*',
    r'raise\s+ValueError',
    r'raise\s+TypeError',
    r'raise\s+KeyError',
    r'raise\s+AttributeError',
    r'raise\s+IndexError',
    r'raise\s+RuntimeError',
    r'Error:',
    r'Exception:',
    r'Traceback',
    r'NameError',
    r'TypeError',
    r'ValueError',
    r'KeyError',
    r'AttributeError',
    r'IndexError',
    r'SyntaxError',
    r'IndentationError',
    r'FAILED',
    r'FAILURE',
    r'Test.*failed',
    r'pytest.*FAILED',
    r'unittest.*FAILED',
]

# Popular repositories known to have test failures and error examples
POPULAR_REPOS = [
    'pytorch/pytorch',
    'tensorflow/tensorflow',
    'django/django',
    'flask/flask',
    'scikit-learn/scikit-learn',
    'pandas-dev/pandas',
    'numpy/numpy',
    'requests/requests',
    'psf/requests',
    'python/cpython',
    'fastapi/fastapi',
    'pytest-dev/pytest',
    'python/mypy',
    'python/black',
    'pallets/flask',
    'apache/airflow',
    'apache/spark',
    'microsoft/vscode-python',
]


class EnhancedGitHubFailureCollector:
    """Enhanced collector with multiple strategies."""
    
    def __init__(self, github_token: Optional[str] = None, max_results: int = 10000):
        self.github_token = github_token
        self.max_results = max_results
        self.collected = []
        self.lock = Lock()
        self.session = requests.Session()
        
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
            'errors': 0,
            'strategy_code_search': 0,
            'strategy_issues': 0,
            'strategy_gists': 0,
            'strategy_repos': 0,
        }
    
    def _make_api_request(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make GitHub API request with rate limiting."""
        try:
            time.sleep(RATE_LIMIT_DELAY)
            response = self.session.get(url, params=params, timeout=30)
            self.stats['api_calls'] += 1
            
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
    
    def collect_from_gists(self, max_gists: int = 1000) -> List[Dict[str, Any]]:
        """Collect code from GitHub Gists."""
        logger.info("Collecting from GitHub Gists...")
        results = []
        
        url = f"{GITHUB_API_BASE}/gists/public"
        params = {'per_page': 100}
        
        for page in range(1, min(max_gists // 100 + 1, 10)):
            params['page'] = page
            data = self._make_api_request(url, params)
            
            if not data:
                break
            
            for gist in data:
                if len(self.collected) + len(results) >= self.max_results:
                    break
                
                files = gist.get('files', {})
                for filename, file_data in files.items():
                    if file_data.get('language') not in ['Python', 'JavaScript', 'TypeScript']:
                        continue
                    
                    content = file_data.get('content', '')
                    if not content:
                        continue
                    
                    # Check for error patterns
                    if any(re.search(pattern, content, re.IGNORECASE) for pattern in ERROR_PATTERNS):
                        result = {
                            'id': f"gist_{gist['id']}_{filename}",
                            'repository': None,
                            'file_path': filename,
                            'url': gist.get('html_url', ''),
                            'code_snippet': content[:2000],  # Limit size
                            'start_line': 1,
                            'end_line': len(content.split('\n')),
                            'error_line': 1,
                            'language': file_data.get('language', 'unknown'),
                            'collected_at': datetime.utcnow().isoformat(),
                            'source': 'github_gist',
                            'error_patterns_found': [
                                pattern for pattern in ERROR_PATTERNS
                                if re.search(pattern, content, re.IGNORECASE)
                            ]
                        }
                        results.append(result)
                        self.stats['strategy_gists'] += 1
        
        return results
    
    def collect_from_repo_issues(self, repo: str, max_issues: int = 100) -> List[Dict[str, Any]]:
        """Collect code from a specific repository's issues."""
        results = []
        
        url = f"{GITHUB_API_BASE}/repos/{repo}/issues"
        params = {
            'state': 'closed',
            'labels': 'bug',
            'per_page': 100
        }
        
        for page in range(1, min(max_issues // 100 + 1, 5)):
            params['page'] = page
            data = self._make_api_request(url, params)
            
            if not data:
                break
            
            for issue in data:
                if len(self.collected) + len(results) >= self.max_results:
                    break
                
                body = issue.get('body', '')
                code_blocks = re.findall(r'```[\w]*\n(.*?)```', body, re.DOTALL)
                
                for code_block in code_blocks:
                    if any(re.search(pattern, code_block, re.IGNORECASE) for pattern in ERROR_PATTERNS):
                        result = {
                            'id': f"issue_{repo}_{issue['number']}",
                            'repository': repo,
                            'file_path': None,
                            'url': issue.get('html_url', ''),
                            'code_snippet': code_block.strip()[:2000],
                            'start_line': 1,
                            'end_line': len(code_block.split('\n')),
                            'error_line': 1,
                            'language': 'python',
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
                        self.stats['strategy_issues'] += 1
        
        return results
    
    def collect_from_repo_files(self, repo: str, path: str = 'tests') -> List[Dict[str, Any]]:
        """Collect code from test files in a repository."""
        results = []
        
        url = f"{GITHUB_API_BASE}/repos/{repo}/contents/{path}"
        data = self._make_api_request(url)
        
        if not data:
            return results
        
        # Process files
        for item in data:
            if item['type'] == 'file' and item['name'].endswith('.py'):
                file_url = item.get('download_url')
                if file_url:
                    try:
                        response = requests.get(file_url, timeout=10)
                        content = response.text
                        
                        # Check for error patterns
                        if any(re.search(pattern, content, re.IGNORECASE) for pattern in ERROR_PATTERNS):
                            lines = content.split('\n')
                            for i, line in enumerate(lines):
                                if any(re.search(pattern, line, re.IGNORECASE) for pattern in ERROR_PATTERNS):
                                    snippet_start = max(0, i - 10)
                                    snippet_end = min(len(lines), i + 10)
                                    snippet = '\n'.join(lines[snippet_start:snippet_end])
                                    
                                    result = {
                                        'id': f"{repo}_{item['name']}_{i}",
                                        'repository': repo,
                                        'file_path': item['path'],
                                        'url': item.get('html_url', ''),
                                        'code_snippet': snippet,
                                        'start_line': snippet_start + 1,
                                        'end_line': snippet_end,
                                        'error_line': i + 1,
                                        'language': 'python',
                                        'collected_at': datetime.utcnow().isoformat(),
                                        'source': 'github_repo_file',
                                        'error_patterns_found': [
                                            pattern for pattern in ERROR_PATTERNS
                                            if re.search(pattern, snippet, re.IGNORECASE)
                                        ]
                                    }
                                    results.append(result)
                                    self.stats['strategy_repos'] += 1
                                    
                                    if len(self.collected) + len(results) >= self.max_results:
                                        break
                    except Exception as e:
                        logger.error(f"Error processing file {item['name']}: {e}")
        
        return results
    
    def collect_all(self) -> List[Dict[str, Any]]:
        """Collect using all strategies."""
        logger.info(f"Starting enhanced collection of {self.max_results} broken code examples...")
        
        # Strategy 1: Collect from Gists
        logger.info("Strategy 1: Collecting from GitHub Gists...")
        gist_results = self.collect_from_gists(max_gists=2000)
        with self.lock:
            self.collected.extend(gist_results)
            self.stats['total_collected'] = len(self.collected)
            logger.info(f"Collected {len(self.collected)}/{self.max_results} examples...")
        
        # Strategy 2: Collect from popular repos' issues
        if len(self.collected) < self.max_results:
            logger.info("Strategy 2: Collecting from popular repositories' issues...")
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = []
                for repo in POPULAR_REPOS[:10]:
                    if len(self.collected) >= self.max_results:
                        break
                    future = executor.submit(self.collect_from_repo_issues, repo, max_issues=50)
                    futures.append(future)
                
                for future in as_completed(futures):
                    if len(self.collected) >= self.max_results:
                        break
                    try:
                        issue_results = future.result(timeout=60)
                        with self.lock:
                            self.collected.extend(issue_results)
                            self.stats['total_collected'] = len(self.collected)
                            logger.info(f"Collected {len(self.collected)}/{self.max_results} examples...")
                    except Exception as e:
                        logger.error(f"Error collecting from repo: {e}")
        
        # Strategy 3: Collect from test files in popular repos
        if len(self.collected) < self.max_results:
            logger.info("Strategy 3: Collecting from test files in popular repositories...")
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = []
                for repo in POPULAR_REPOS[:5]:
                    if len(self.collected) >= self.max_results:
                        break
                    future = executor.submit(self.collect_from_repo_files, repo, 'tests')
                    futures.append(future)
                
                for future in as_completed(futures):
                    if len(self.collected) >= self.max_results:
                        break
                    try:
                        file_results = future.result(timeout=120)
                        with self.lock:
                            self.collected.extend(file_results)
                            self.stats['total_collected'] = len(self.collected)
                            logger.info(f"Collected {len(self.collected)}/{self.max_results} examples...")
                    except Exception as e:
                        logger.error(f"Error collecting from repo files: {e}")
        
        # Remove duplicates
        seen_ids = set()
        unique_collected = []
        for item in self.collected:
            if item['id'] not in seen_ids:
                seen_ids.add(item['id'])
                unique_collected.append(item)
        
        self.collected = unique_collected[:self.max_results]
        self.stats['total_collected'] = len(self.collected)
        
        logger.info(f"Collection complete! Collected {len(self.collected)} unique examples")
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
        description="Collect broken code examples from GitHub (Enhanced)"
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
    
    if not github_token:
        logger.warning("No GitHub token provided. Rate limits will be stricter.")
        logger.warning("Set GITHUB_TOKEN environment variable or use --token for better results.")
    
    # Initialize collector
    collector = EnhancedGitHubFailureCollector(
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
    print(f"\nStrategy breakdown:")
    print(f"  - Gists: {collector.stats['strategy_gists']}")
    print(f"  - Issues: {collector.stats['strategy_issues']}")
    print(f"  - Repo files: {collector.stats['strategy_repos']}")
    print("="*80)


if __name__ == "__main__":
    main()
