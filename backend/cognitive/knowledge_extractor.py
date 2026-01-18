import json
import re
import logging
import requests
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
logger = logging.getLogger(__name__)

class KnowledgeExtractor:
    """Extract fix patterns from multiple sources."""
    
    def __init__(self, github_token: Optional[str] = None):
        self.github_token = github_token
        self.patterns_extracted = []
        
    def extract_from_healing_results(self, results_path: str = "backend/tests/healing_results.json") -> List[Dict]:
        """Extract error patterns from healing results."""
        patterns = []
        
        try:
            with open(results_path) as f:
                results = json.load(f)
            
            # Extract from failed actions
            for action in results.get("healing_actions", []):
                execution = action.get("execution_results", {})
                
                # Failed actions
                for failed in execution.get("failed", []):
                    error_msg = failed.get("error", "") or failed.get("message", "")
                    if error_msg:
                        pattern = self._categorize_error(error_msg)
                        if pattern:
                            patterns.append({
                                "source": "healing_results",
                                "error": error_msg,
                                "pattern": pattern,
                                "timestamp": datetime.utcnow().isoformat()
                            })
                
                # Anomalies
                anomaly = action.get("anomaly", {})
                error_msg = anomaly.get("error_message", "") or anomaly.get("details", "")
                if error_msg:
                    pattern = self._categorize_error(error_msg)
                    if pattern:
                        patterns.append({
                            "source": "healing_results",
                            "error": error_msg,
                            "pattern": pattern,
                            "timestamp": datetime.utcnow().isoformat()
                        })
        
        except Exception as e:
            logger.error(f"Error extracting from healing results: {e}")
        
        return patterns
    
    def extract_from_stackoverflow(self, error_message: str, limit: int = 5) -> List[Dict]:
        """Extract solutions from Stack Overflow."""
        solutions = []
        
        try:
            url = "https://api.stackexchange.com/2.3/search"
            params = {
                "order": "desc",
                "sort": "votes",
                "tagged": "python",
                "intitle": error_message[:100],  # Limit length
                "site": "stackoverflow",
                "filter": "withbody",
                "pagesize": limit
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                questions = response.json().get("items", [])
                
                for question in questions:
                    # Get accepted answer
                    if question.get("accepted_answer_id"):
                        answer_id = question["accepted_answer_id"]
                        answer_url = f"https://api.stackexchange.com/2.3/answers/{answer_id}"
                        answer_params = {
                            "site": "stackoverflow",
                            "filter": "withbody"
                        }
                        answer_response = requests.get(answer_url, params=answer_params, timeout=10)
                        if answer_response.status_code == 200:
                            answer_data = answer_response.json().get("items", [])
                            if answer_data:
                                answer = answer_data[0]
                                solution = self._extract_code_from_markdown(answer["body"])
                                if solution:
                                    solutions.append({
                                        "source": "stackoverflow",
                                        "error": error_message,
                                        "solution": solution,
                                        "url": answer["link"],
                                        "upvotes": answer.get("score", 0),
                                        "is_accepted": True
                                    })
        except Exception as e:
            logger.debug(f"Stack Overflow extraction failed: {e}")
        
        return solutions
    
    def extract_from_github_issues(self, error_message: str, repo: str = "sqlalchemy/sqlalchemy", limit: int = 5) -> List[Dict]:
        """Extract solutions from GitHub issues."""
        solutions = []
        
        try:
            url = "https://api.github.com/search/issues"
            headers = {}
            if self.github_token:
                headers["Authorization"] = f"token {self.github_token}"
            
            # Search for error in closed issues
            query = f"{error_message[:100]} repo:{repo} is:closed"
            params = {
                "q": query,
                "sort": "reactions",
                "order": "desc",
                "per_page": limit
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                issues = response.json().get("items", [])
                
                for issue in issues:
                    # Get comments
                    if issue.get("comments", 0) > 0:
                        comments_url = issue["comments_url"]
                        comments_response = requests.get(comments_url, headers=headers, timeout=10)
                        if comments_response.status_code == 200:
                            comments = comments_response.json()
                            for comment in comments:
                                if self._contains_solution(comment["body"]):
                                    solution = self._extract_code_from_markdown(comment["body"])
                                    if solution:
                                        solutions.append({
                                            "source": "github",
                                            "error": error_message,
                                            "solution": solution,
                                            "url": comment["html_url"],
                                            "upvotes": comment.get("reactions", {}).get("+1", 0)
                                        })
        except Exception as e:
            logger.debug(f"GitHub extraction failed: {e}")
        
        return solutions
    
    def _categorize_error(self, error_message: str) -> Optional[Dict]:
        """Categorize error and return pattern info."""
        error_lower = error_message.lower()
        
        # SQLAlchemy table redefinition
        if "table" in error_lower and ("already defined" in error_lower or "redefinition" in error_lower):
            return {
                "type": "sqlalchemy_table_redefinition",
                "pattern": r"Table ['\"](\w+)['\"] is already defined",
                "confidence": 0.95
            }
        
        # Circular import
        if "cannot import name" in error_lower and "partially initialized" in error_lower:
            return {
                "type": "circular_import",
                "pattern": r"ImportError: cannot import name ['\"](\w+)['\"] from partially initialized module",
                "confidence": 0.80
            }
        
        # Missing module
        if "no module named" in error_lower or "modulenotfounderror" in error_lower:
            return {
                "type": "missing_import",
                "pattern": r"No module named ['\"](\w+)['\"]",
                "confidence": 0.85
            }
        
        # Connection timeout
        if "timeout" in error_lower or "timed out" in error_lower:
            return {
                "type": "connection_timeout",
                "pattern": r"(Connection timeout|Operation timed out|TimeoutError)",
                "confidence": 0.75
            }
        
        # Database connection
        if "database" in error_lower and ("connection" in error_lower or "failed" in error_lower):
            return {
                "type": "database_connection",
                "pattern": r"(database|Database).*connection.*(failed|error|unavailable)",
                "confidence": 0.80
            }
        
        return None
    
    def _contains_solution(self, text: str) -> bool:
        """Check if text contains a solution."""
        indicators = [
            "extend_existing",
            "import",
            "fix",
            "solution",
            "workaround",
            "try this",
            "here's how",
            "add",
            "change"
        ]
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in indicators)
    
    def _extract_code_from_markdown(self, markdown: str) -> Optional[str]:
        """Extract Python code from markdown."""
        # Look for code blocks
        code_blocks = re.findall(r'```python\n(.*?)\n```', markdown, re.DOTALL)
        if code_blocks:
            return code_blocks[0]
        
        # Look for code blocks without language
        code_blocks = re.findall(r'```\n(.*?)\n```', markdown, re.DOTALL)
        if code_blocks:
            return code_blocks[0]
        
        # Look for inline code with extend_existing (SQLAlchemy fix)
        if "extend_existing" in markdown:
            match = re.search(r'`([^`]*extend_existing[^`]*)`', markdown)
            if match:
                return match.group(1)
        
        return None
    
    def generate_fix_patterns(self, error_patterns: List[Dict]) -> List[Dict]:
        """Generate fix patterns from extracted errors."""
        fix_patterns = []
        
        # Group by error type
        error_groups = {}
        for pattern in error_patterns:
            error_type = pattern.get("pattern", {}).get("type")
            if error_type:
                if error_type not in error_groups:
                    error_groups[error_type] = []
                error_groups[error_type].append(pattern)
        
        # Generate fix pattern for each type
        for error_type, patterns in error_groups.items():
            if len(patterns) >= 1:  # At least one occurrence
                fix_pattern = self._create_fix_pattern(error_type, patterns)
                if fix_pattern:
                    fix_patterns.append(fix_pattern)
        
        return fix_patterns
    
    def _create_fix_pattern(self, error_type: str, patterns: List[Dict]) -> Optional[Dict]:
        """Create a fix pattern from error patterns."""
        
        # Get solutions from external sources
        solutions = []
        for pattern in patterns[:3]:  # Check first 3
            error_msg = pattern.get("error", "")
            if error_msg:
                # Try Stack Overflow
                so_solutions = self.extract_from_stackoverflow(error_msg, limit=2)
                solutions.extend(so_solutions)
                
                # Try GitHub (for SQLAlchemy)
                if "sqlalchemy" in error_type or "table" in error_msg.lower():
                    gh_solutions = self.extract_from_github_issues(error_msg, limit=2)
                    solutions.extend(gh_solutions)
        
        # Create fix pattern based on error type
        if error_type == "sqlalchemy_table_redefinition":
            return {
                "issue_type": "sqlalchemy_table_redefinition",
                "pattern": r"(Table ['\"](\w+)['\"] is already defined|table redefinition|already defined.*MetaData)",
                "fix_template": """# Fix: Add extend_existing=True to table definition
# For declarative base:
# Find: class {TableName}(Base):
#     __tablename__ = '{table_name}'
# Replace with: class {TableName}(Base):
#     __tablename__ = '{table_name}'
#     __table_args__ = {{'extend_existing': True}}

# For Table() constructor:
# Find: {table_name} = Table(...)
# Replace with: {table_name} = Table(..., extend_existing=True)""",
                "confidence": 0.95,
                "description": "SQLAlchemy table redefinition - add extend_existing=True",
                "examples": [
                    "Table 'users' is already defined for this MetaData instance",
                    "Table 'learning_examples' is already defined",
                    "Table redefinition errors - SQLAlchemy metadata issue"
                ],
                "solutions_found": len(solutions)
            }
        
        elif error_type == "circular_import":
            return {
                "issue_type": "circular_import",
                "pattern": r"ImportError: cannot import name ['\"](\w+)['\"] from partially initialized module",
                "fix_template": """# Fix: Break circular import
# Option 1: Move import inside function
# Before: from module_a import something
# After: 
#   def function():
#       from module_a import something

# Option 2: Use lazy import
# Before: from module_a import something
# After: import module_a; something = module_a.something

# Option 3: Reorganize modules to break cycle""",
                "confidence": 0.80,
                "description": "Circular import - break dependency cycle",
                "examples": [
                    "ImportError: cannot import name 'X' from partially initialized module",
                    "Circular import detected"
                ],
                "solutions_found": len(solutions)
            }
        
        elif error_type == "connection_timeout":
            return {
                "issue_type": "connection_timeout",
                "pattern": r"(Connection timeout|Operation timed out|TimeoutError|timeout)",
                "fix_template": """# Fix: Connection timeout
# 1. Increase timeout value
#    connection.timeout = 30  # seconds

# 2. Check network connectivity
# 3. Optimize query performance
# 4. Add retry logic with exponential backoff""",
                "confidence": 0.75,
                "description": "Connection timeout - increase timeout or optimize",
                "examples": [
                    "Connection timeout",
                    "Operation timed out",
                    "TimeoutError: Connection timed out"
                ],
                "solutions_found": len(solutions)
            }
        
        return None


def extract_and_add_knowledge():
    """Main function to extract knowledge and add to knowledge base."""
    logger.info("Starting knowledge extraction...")
    
    extractor = KnowledgeExtractor()
    
    # 1. Extract from healing results
    logger.info("Extracting from healing results...")
    healing_patterns = extractor.extract_from_healing_results()
    logger.info(f"Found {len(healing_patterns)} error patterns")
    
    # 2. Generate fix patterns
    logger.info("Generating fix patterns...")
    fix_patterns = extractor.generate_fix_patterns(healing_patterns)
    logger.info(f"Generated {len(fix_patterns)} fix patterns")
    
    # 3. Add to knowledge base
    logger.info("Adding to knowledge base...")
    from cognitive.healing_knowledge_base import get_healing_knowledge_base, IssueType
    
    kb = get_healing_knowledge_base()
    
    # Check what patterns we need to add
    existing_patterns = kb.get_all_fix_patterns()
    existing_types = {p.issue_type.value for p in existing_patterns}
    
    added_count = 0
    for fix_pattern in fix_patterns:
        issue_type_str = fix_pattern["issue_type"]
        
        # Check if we need to add this pattern
        if issue_type_str not in existing_types:
            logger.info(f"New pattern type found: {issue_type_str}")
            # Note: This would require modifying the knowledge base to add patterns dynamically
            # For now, we'll return the patterns to be added manually
            added_count += 1
    
    logger.info(f"Knowledge extraction complete. {added_count} new patterns found.")
    
    return {
        "patterns_found": len(healing_patterns),
        "fix_patterns_generated": len(fix_patterns),
        "new_patterns": fix_patterns,
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = extract_and_add_knowledge()
    print(json.dumps(result, indent=2))
