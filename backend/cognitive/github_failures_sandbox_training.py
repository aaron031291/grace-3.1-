"""
GitHub Failures Sandbox Training System

Trains Grace by practicing fixing broken code examples collected from GitHub.
Each example is run in a sandbox, Grace attempts to fix it, and learns from the outcome.

Features:
- Loads broken code examples from GitHub collection
- Runs code in isolated sandbox
- Grace attempts to diagnose and fix errors
- Tests fixes automatically
- Learns from successes and failures
- Stores patterns in learning memory
"""

import logging
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import traceback
import re

logger = logging.getLogger(__name__)


class FixStatus(str, Enum):
    """Status of a fix attempt."""
    NOT_ATTEMPTED = "not_attempted"
    IN_PROGRESS = "in_progress"
    FIXED = "fixed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class FailureExample:
    """A broken code example from GitHub."""
    id: str
    code_snippet: str
    language: str
    repository: Optional[str]
    file_path: Optional[str]
    url: Optional[str]
    error_patterns: List[str]
    source: str
    collected_at: str


@dataclass
class FixAttempt:
    """A single fix attempt."""
    example_id: str
    original_code: str
    fixed_code: Optional[str]
    error_message: Optional[str]
    fix_explanation: Optional[str]
    status: FixStatus
    execution_result: Optional[Dict[str, Any]] = None
    learned_patterns: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TrainingProgress:
    """Training progress tracking."""
    total_examples: int = 0
    attempted: int = 0
    fixed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    success_rate: float = 0.0
    started_at: datetime = field(default_factory=datetime.utcnow)
    last_update: datetime = field(default_factory=datetime.utcnow)


class GitHubFailuresSandboxTraining:
    """
    Sandbox training system for GitHub failures.
    
    Loads broken code examples, runs them in sandbox, attempts fixes, and learns.
    """
    
    def __init__(
        self,
        coding_agent=None,
        learning_memory=None,
        memory_mesh=None,
        sandbox_dir: Optional[Path] = None,
        max_examples: Optional[int] = None
    ):
        """
        Initialize GitHub failures sandbox training.
        
        Args:
            coding_agent: EnterpriseCodingAgent instance
            learning_memory: LearningMemoryManager instance
            memory_mesh: MemoryMeshIntegration instance
            sandbox_dir: Directory for sandbox execution
            max_examples: Maximum examples to process (None = all)
        """
        self.coding_agent = coding_agent
        self.learning_memory = learning_memory
        self.memory_mesh = memory_mesh
        self.max_examples = max_examples
        
        # Setup sandbox directory
        if sandbox_dir:
            self.sandbox_dir = Path(sandbox_dir)
        else:
            self.sandbox_dir = Path(tempfile.mkdtemp(prefix="grace_github_training_"))
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)
        
        # Progress tracking
        self.progress = TrainingProgress()
        self.fix_attempts: List[FixAttempt] = []
        self.examples: List[FailureExample] = []
        
        logger.info(f"[GITHUB-TRAINING] Initialized (sandbox: {self.sandbox_dir})")
    
    def load_failures_from_file(self, file_path: Path) -> List[FailureExample]:
        """
        Load failure examples from JSON file.
        
        Args:
            file_path: Path to GitHub failures JSON file
        
        Returns:
            List of FailureExample objects
        """
        logger.info(f"[GITHUB-TRAINING] Loading failures from {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            examples_data = data.get('examples', [])
            examples = []
            
            for ex_data in examples_data:
                example = FailureExample(
                    id=ex_data.get('id', ''),
                    code_snippet=ex_data.get('code_snippet', ''),
                    language=ex_data.get('language', 'python'),
                    repository=ex_data.get('repository'),
                    file_path=ex_data.get('file_path'),
                    url=ex_data.get('url'),
                    error_patterns=ex_data.get('error_patterns_found', []),
                    source=ex_data.get('source', 'github'),
                    collected_at=ex_data.get('collected_at', '')
                )
                examples.append(example)
            
            self.examples = examples[:self.max_examples] if self.max_examples else examples
            self.progress.total_examples = len(self.examples)
            
            logger.info(f"[GITHUB-TRAINING] Loaded {len(self.examples)} examples")
            return self.examples
            
        except Exception as e:
            logger.error(f"[GITHUB-TRAINING] Failed to load failures: {e}")
            traceback.print_exc()
            return []
    
    def run_code_in_sandbox(self, code: str, language: str = 'python') -> Dict[str, Any]:
        """
        Run code in sandbox and capture errors.
        
        Args:
            code: Code to execute
            language: Programming language
        
        Returns:
            Execution result with stdout, stderr, return_code, error_type
        """
        if language.lower() != 'python':
            return {
                'success': False,
                'error': f'Language {language} not supported yet',
                'return_code': -1
            }
        
        # Create temporary file in sandbox
        temp_file = self.sandbox_dir / f"test_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.py"
        
        try:
            # Write code to file
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(code)
            
            # Execute in sandbox
            result = subprocess.run(
                [sys.executable, str(temp_file)],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(self.sandbox_dir)
            )
            
            # Determine error type
            error_type = None
            if result.returncode != 0:
                stderr = result.stderr
                if 'SyntaxError' in stderr:
                    error_type = 'SyntaxError'
                elif 'NameError' in stderr:
                    error_type = 'NameError'
                elif 'TypeError' in stderr:
                    error_type = 'TypeError'
                elif 'ValueError' in stderr:
                    error_type = 'ValueError'
                elif 'KeyError' in stderr:
                    error_type = 'KeyError'
                elif 'AttributeError' in stderr:
                    error_type = 'AttributeError'
                elif 'IndexError' in stderr:
                    error_type = 'IndexError'
                elif 'IndentationError' in stderr:
                    error_type = 'IndentationError'
                else:
                    error_type = 'RuntimeError'
            
            return {
                'success': result.returncode == 0,
                'return_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'error_type': error_type
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Timeout',
                'return_code': -1,
                'error_type': 'TimeoutError'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'return_code': -1,
                'error_type': 'ExecutionError'
            }
        finally:
            # Cleanup
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except:
                    pass
    
    def diagnose_error(self, code: str, execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Diagnose the error in broken code.
        
        Args:
            code: Broken code
            execution_result: Result from run_code_in_sandbox
        
        Returns:
            Diagnosis with error type, location, and explanation
        """
        error_type = execution_result.get('error_type')
        stderr = execution_result.get('stderr', '')
        
        diagnosis = {
            'error_type': error_type,
            'error_message': stderr,
            'suspected_line': None,
            'explanation': None,
            'fix_suggestions': []
        }
        
        # Extract line number from error if available
        line_match = re.search(r'line (\d+)', stderr)
        if line_match:
            diagnosis['suspected_line'] = int(line_match.group(1))
        
        # Generate explanation based on error type
        if error_type == 'SyntaxError':
            diagnosis['explanation'] = 'Syntax error detected in code'
            diagnosis['fix_suggestions'] = [
                'Check for missing colons, parentheses, or brackets',
                'Verify indentation is correct',
                'Check for typos in keywords'
            ]
        elif error_type == 'NameError':
            diagnosis['explanation'] = 'Undefined variable or function name'
            diagnosis['fix_suggestions'] = [
                'Check if variable is defined before use',
                'Verify function name spelling',
                'Check if import statement is missing'
            ]
        elif error_type == 'TypeError':
            diagnosis['explanation'] = 'Type mismatch or incorrect function call'
            diagnosis['fix_suggestions'] = [
                'Check argument types match function signature',
                'Verify object has the method being called',
                'Check for None values'
            ]
        elif error_type == 'IndentationError':
            diagnosis['explanation'] = 'Indentation is incorrect'
            diagnosis['fix_suggestions'] = [
                'Ensure consistent indentation (spaces or tabs)',
                'Check for missing indentation after colons',
                'Verify all blocks are properly indented'
            ]
        else:
            diagnosis['explanation'] = f'{error_type} occurred during execution'
            diagnosis['fix_suggestions'] = [
                'Review error message for details',
                'Check variable values and types',
                'Verify logic flow'
            ]
        
        return diagnosis
    
    def attempt_fix(self, example: FailureExample, diagnosis: Dict[str, Any]) -> Optional[str]:
        """
        Attempt to fix the broken code using Grace's coding agent.
        
        Args:
            example: Failure example
            diagnosis: Error diagnosis
        
        Returns:
            Fixed code or None if fix failed
        """
        if not self.coding_agent:
            logger.warning("[GITHUB-TRAINING] No coding agent available for fix")
            return None
        
        try:
            # Build fix prompt
            error_type = diagnosis.get('error_type', 'Unknown')
            error_message = diagnosis.get('error_message', '')
            fix_suggestions = diagnosis.get('fix_suggestions', [])
            
            prompt = f"""Fix the following broken Python code.

Error Type: {error_type}
Error Message:
{error_message}

Broken Code:
```python
{example.code_snippet}
```

Fix Suggestions:
{chr(10).join(f'- {s}' for s in fix_suggestions)}

Please provide the corrected code that fixes the error."""

            # Use coding agent to generate fix
            from cognitive.enterprise_coding_agent import CodingTaskType
            
            task = self.coding_agent.create_task(
                task_type=CodingTaskType.CODE_GENERATION,
                description=prompt,
                context={
                    'original_code': example.code_snippet,
                    'error_type': error_type,
                    'error_message': error_message,
                    'fix_suggestions': fix_suggestions
                }
            )
            
            execution_result = self.coding_agent.execute_task(task.task_id)
            
            if execution_result.get('success'):
                generation = execution_result.get('result', {}).get('generation')
                if generation:
                    # Extract code from generation
                    if hasattr(generation, 'code_after'):
                        return generation.code_after
                    elif hasattr(generation, 'code'):
                        return generation.code
                    elif isinstance(generation, dict):
                        return generation.get('code', '') or generation.get('code_after', '')
                    else:
                        return str(generation)
            
            return None
            
        except Exception as e:
            logger.error(f"[GITHUB-TRAINING] Fix attempt failed: {e}")
            traceback.print_exc()
            return None
    
    def test_fix(self, original_code: str, fixed_code: str, language: str = 'python') -> Dict[str, Any]:
        """
        Test if the fix works by running the fixed code.
        
        Args:
            original_code: Original broken code
            fixed_code: Fixed code
            language: Programming language
        
        Returns:
            Test result
        """
        # Run fixed code
        execution_result = self.run_code_in_sandbox(fixed_code, language)
        
        return {
            'fix_works': execution_result.get('success', False),
            'execution_result': execution_result,
            'original_failed': not self.run_code_in_sandbox(original_code, language).get('success', True)
        }
    
    def extract_fix_pattern(self, attempt: FixAttempt, example: FailureExample) -> Optional[Dict[str, Any]]:
        """
        Extract a reusable fix pattern from successful fix.
        
        Args:
            attempt: Successful fix attempt
            example: Original failure example
        
        Returns:
            Fix pattern dict or None
        """
        if attempt.status != FixStatus.FIXED or not attempt.fixed_code:
            return None
        
        error_type = attempt.execution_result.get('error_type') if attempt.execution_result else None
        if not error_type:
            return None
        
        # Analyze the fix to extract pattern
        original = example.code_snippet
        fixed = attempt.fixed_code
        
        # Extract pattern: what changed?
        pattern = {
            'error_type': error_type,
            'error_patterns': example.error_patterns,
            'fix_type': self._classify_fix_type(original, fixed),
            'preconditions': {
                'language': example.language,
                'error_type': error_type,
                'has_error_patterns': len(example.error_patterns) > 0
            },
            'actions': {
                'original_snippet': original[:200],  # Truncated for storage
                'fixed_snippet': fixed[:200],
                'fix_explanation': attempt.fix_explanation
            },
            'success': True
        }
        
        return pattern
    
    def _classify_fix_type(self, original: str, fixed: str) -> str:
        """Classify the type of fix applied."""
        # Simple heuristics for fix classification
        if 'import' in fixed and 'import' not in original:
            return 'add_import'
        elif 'def ' in fixed and 'def ' not in original:
            return 'add_function'
        elif 'except' in fixed and 'except' not in original:
            return 'add_exception_handling'
        elif len(fixed) > len(original) * 1.5:
            return 'major_rewrite'
        elif len(fixed) < len(original) * 0.8:
            return 'simplification'
        else:
            return 'syntax_correction'
    
    def learn_from_attempt(self, attempt: FixAttempt, example: FailureExample):
        """
        Store learning from fix attempt in memory systems.
        
        Args:
            attempt: Fix attempt result
            example: Original failure example
        """
        if not self.learning_memory and not self.memory_mesh:
            return
        
        # Build learning data
        learning_type = "fix_success" if attempt.status == FixStatus.FIXED else "fix_failure"
        
        learning_data = {
            'context': {
                'original_code': example.code_snippet,
                'error_patterns': example.error_patterns,
                'language': example.language,
                'source': example.source,
                'error_type': attempt.execution_result.get('error_type') if attempt.execution_result else None
            },
            'expected': {
                'code': attempt.fixed_code if attempt.fixed_code else example.code_snippet,
                'should_execute': True,
                'error_type': attempt.execution_result.get('error_type') if attempt.execution_result else None
            },
            'actual': {
                'code': attempt.fixed_code,
                'execution_result': attempt.execution_result,
                'status': attempt.status.value,
                'fix_explanation': attempt.fix_explanation
            }
        }
        
        # Extract fix pattern if successful
        fix_pattern = None
        if attempt.status == FixStatus.FIXED:
            fix_pattern = self.extract_fix_pattern(attempt, example)
            if fix_pattern:
                learning_data['context']['fix_pattern'] = fix_pattern
                attempt.learned_patterns.append(fix_pattern.get('fix_type', 'unknown'))
        
        # Store in learning memory
        if self.learning_memory:
            try:
                learning_example = self.learning_memory.ingest_learning_data(
                    learning_type=learning_type,
                    learning_data=learning_data,
                    source=f"github_failures_training_{example.source}",
                    user_id=None,
                    genesis_key_id=None
                )
                logger.info(f"[GITHUB-TRAINING] Stored learning example: {learning_example.id}")
                
                # If successful fix, try to create/update procedural memory
                if fix_pattern and self.memory_mesh:
                    try:
                        from cognitive.procedural_memory import ProceduralRepository
                        procedural_repo = ProceduralRepository(self.learning_memory.session)
                        
                        # Check if procedure exists for this error type
                        goal = f"fix_{fix_pattern['error_type']}_error"
                        existing = procedural_repo.find_procedure(goal, fix_pattern['preconditions'])
                        
                        if existing:
                            # Update with new evidence
                            procedural_repo.update_procedure_evidence(
                                procedure_id=existing.id,
                                new_example=learning_example,
                                success=True
                            )
                            logger.info(f"[GITHUB-TRAINING] Updated procedure: {goal}")
                        else:
                            # Create new procedure if we have enough examples
                            from cognitive.learning_memory import LearningExample
                            similar_examples = self.learning_memory.session.query(
                                LearningExample
                            ).filter(
                                LearningExample.example_type == learning_type,
                                LearningExample.trust_score > 0.7
                            ).limit(5).all()
                            
                            if len(similar_examples) >= 2:
                                procedure = procedural_repo.create_procedure(
                                    goal=goal,
                                    action_sequence=[fix_pattern['actions']],
                                    preconditions=fix_pattern['preconditions'],
                                    supporting_examples=[learning_example] + similar_examples
                                )
                                logger.info(f"[GITHUB-TRAINING] Created new procedure: {goal}")
                    except Exception as e:
                        logger.debug(f"[GITHUB-TRAINING] Could not create procedure: {e}")
                        
            except Exception as e:
                logger.error(f"[GITHUB-TRAINING] Failed to store learning: {e}")
        
        # Store in memory mesh
        if self.memory_mesh:
            try:
                self.memory_mesh.ingest_learning_experience(
                    experience_type=learning_type,
                    context=learning_data['context'],
                    action_taken={'fix_attempted': True, 'fix_code': attempt.fixed_code, 'fix_pattern': fix_pattern},
                    outcome=learning_data['actual'],
                    expected_outcome=learning_data['expected'],
                    source=f"github_failures_training_{example.source}"
                )
            except Exception as e:
                logger.error(f"[GITHUB-TRAINING] Failed to store in memory mesh: {e}")
    
    def process_example(self, example: FailureExample) -> FixAttempt:
        """
        Process a single failure example: run, diagnose, fix, test, learn.
        
        Args:
            example: Failure example to process
        
        Returns:
            FixAttempt result
        """
        attempt = FixAttempt(
            example_id=example.id,
            original_code=example.code_snippet,
            status=FixStatus.IN_PROGRESS
        )
        
        try:
            # Step 1: Run original code to confirm it fails
            logger.info(f"[GITHUB-TRAINING] Processing example {example.id}")
            execution_result = self.run_code_in_sandbox(example.code_snippet, example.language)
            attempt.execution_result = execution_result
            
            # Skip if code actually runs (might be false positive)
            if execution_result.get('success'):
                attempt.status = FixStatus.SKIPPED
                attempt.fix_explanation = "Code executes successfully (not actually broken)"
                return attempt
            
            # Step 2: Diagnose error
            diagnosis = self.diagnose_error(example.code_snippet, execution_result)
            
            # Step 3: Attempt fix
            fixed_code = self.attempt_fix(example, diagnosis)
            
            if not fixed_code:
                attempt.status = FixStatus.FAILED
                attempt.fix_explanation = "Could not generate fix"
                return attempt
            
            attempt.fixed_code = fixed_code
            
            # Step 4: Test fix
            test_result = self.test_fix(example.code_snippet, fixed_code, example.language)
            
            if test_result.get('fix_works'):
                attempt.status = FixStatus.FIXED
                attempt.fix_explanation = f"Fixed {diagnosis.get('error_type', 'error')}"
            else:
                attempt.status = FixStatus.FAILED
                attempt.fix_explanation = "Fix did not resolve error"
            
            # Step 5: Learn from attempt
            self.learn_from_attempt(attempt, example)
            
        except Exception as e:
            logger.error(f"[GITHUB-TRAINING] Error processing example {example.id}: {e}")
            traceback.print_exc()
            attempt.status = FixStatus.ERROR
            attempt.error_message = str(e)
        
        return attempt
    
    def train(self, examples: Optional[List[FailureExample]] = None) -> TrainingProgress:
        """
        Run training on failure examples.
        
        Args:
            examples: List of examples (uses self.examples if None)
        
        Returns:
            Training progress
        """
        if examples is None:
            examples = self.examples
        
        if not examples:
            logger.warning("[GITHUB-TRAINING] No examples to train on")
            return self.progress
        
        logger.info(f"[GITHUB-TRAINING] Starting training on {len(examples)} examples")
        
        for i, example in enumerate(examples):
            if self.max_examples and i >= self.max_examples:
                break
            
            # Process example
            attempt = self.process_example(example)
            self.fix_attempts.append(attempt)
            
            # Update progress
            self.progress.attempted += 1
            if attempt.status == FixStatus.FIXED:
                self.progress.fixed += 1
            elif attempt.status == FixStatus.FAILED:
                self.progress.failed += 1
            elif attempt.status == FixStatus.ERROR:
                self.progress.errors += 1
            elif attempt.status == FixStatus.SKIPPED:
                self.progress.skipped += 1
            
            # Calculate success rate
            if self.progress.attempted > 0:
                self.progress.success_rate = (self.progress.fixed / self.progress.attempted) * 100
            
            self.progress.last_update = datetime.utcnow()
            
            # Log progress
            if (i + 1) % 10 == 0:
                logger.info(
                    f"[GITHUB-TRAINING] Progress: {i+1}/{len(examples)} "
                    f"(Fixed: {self.progress.fixed}, Failed: {self.progress.failed}, "
                    f"Success Rate: {self.progress.success_rate:.1f}%)"
                )
        
        logger.info(f"[GITHUB-TRAINING] Training complete!")
        logger.info(f"  Attempted: {self.progress.attempted}")
        logger.info(f"  Fixed: {self.progress.fixed}")
        logger.info(f"  Failed: {self.progress.failed}")
        logger.info(f"  Errors: {self.progress.errors}")
        logger.info(f"  Success Rate: {self.progress.success_rate:.1f}%")
        
        return self.progress
    
    def save_results(self, output_file: Path):
        """Save training results to JSON file."""
        results = {
            'metadata': {
                'total_examples': self.progress.total_examples,
                'attempted': self.progress.attempted,
                'fixed': self.progress.fixed,
                'failed': self.progress.failed,
                'errors': self.progress.errors,
                'skipped': self.progress.skipped,
                'success_rate': self.progress.success_rate,
                'started_at': self.progress.started_at.isoformat(),
                'last_update': self.progress.last_update.isoformat()
            },
            'fix_attempts': [
                {
                    'example_id': attempt.example_id,
                    'status': attempt.status.value,
                    'error_message': attempt.error_message,
                    'fix_explanation': attempt.fix_explanation,
                    'execution_result': attempt.execution_result,
                    'timestamp': attempt.timestamp.isoformat()
                }
                for attempt in self.fix_attempts
            ]
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"[GITHUB-TRAINING] Results saved to {output_file}")
