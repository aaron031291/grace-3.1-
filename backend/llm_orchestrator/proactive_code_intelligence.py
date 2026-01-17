import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import threading
import time
from dataclasses import dataclass
from multi_llm_client import MultiLLMClient, TaskType
from repo_access import RepositoryAccessLayer
from learning_integration import LearningIntegration
class CodeAnalysis:
    logger = logging.getLogger(__name__)
    """Code analysis result."""
    file_path: str
    analysis_type: str  # "functionality", "pattern", "improvement", "learning"
    insights: List[str]
    code_snippets: List[Dict[str, Any]]
    trust_score: float
    learning_examples: List[Dict[str, Any]]
    timestamp: datetime


class ProactiveCodeIntelligence:
    """
    Makes LLMs proactively intelligent about source code.
    
    Features:
    - Always includes code context in prompts
    - Proactively analyzes code changes
    - Learns from code patterns
    - Continuously improves code understanding
    """
    
    def __init__(
        self,
        multi_llm_client: Optional[MultiLLMClient] = None,
        repo_access: Optional[RepositoryAccessLayer] = None,
        learning_integration: Optional[LearningIntegration] = None,
        monitor_interval_seconds: int = 300,  # Check every 5 minutes
        max_context_files: int = 10
    ):
        """
        Initialize proactive code intelligence.
        
        Args:
            multi_llm_client: Multi-LLM client
            repo_access: Repository access
            learning_integration: Learning integration
            monitor_interval_seconds: How often to check for code changes
            max_context_files: Maximum files to include in context
        """
        self.multi_llm = multi_llm_client
        self.repo_access = repo_access
        self.learning_integration = learning_integration
        
        self.monitor_interval = monitor_interval_seconds
        self.max_context_files = max_context_files
        
        # Code monitoring
        self.monitoring_thread: Optional[threading.Thread] = None
        self.running = False
        self.file_hashes: Dict[str, str] = {}
        self.analyzed_files: Set[str] = set()
        
        # Code knowledge base (cached insights)
        self.code_knowledge: Dict[str, Dict[str, Any]] = {}
    
    def start_monitoring(self):
        """Start proactive code monitoring."""
        if self.running:
            logger.warning("[CODE-INTELLIGENCE] Already monitoring")
            return
        
        self.running = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True,
            name="ProactiveCodeIntelligence"
        )
        self.monitoring_thread.start()
        logger.info("[CODE-INTELLIGENCE] Started proactive code monitoring")
    
    def stop_monitoring(self):
        """Stop code monitoring."""
        self.running = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        logger.info("[CODE-INTELLIGENCE] Stopped monitoring")
    
    def _monitoring_loop(self):
        """Background monitoring loop."""
        while self.running:
            try:
                self._check_code_changes()
                self._proactive_code_analysis()
            except Exception as e:
                logger.error(f"[CODE-INTELLIGENCE] Error in monitoring loop: {e}")
            
            time.sleep(self.monitor_interval)
    
    def _check_code_changes(self):
        """Check for code file changes."""
        if not self.repo_access:
            return
        
        # Get Python files
        code_files = self.repo_access.search_code(
            pattern=".*",
            file_pattern="*.py",
            max_results=100
        )
        
        changed_files = []
        for match in code_files:
            file_path = match.get("file", "")
            if not file_path:
                continue
            
            try:
                file_content = self.repo_access.read_file(file_path)
                if "error" in file_content:
                    continue
                
                content = file_content.get("content", "")
                file_hash = hashlib.sha256(content.encode()).hexdigest()
                
                if file_path in self.file_hashes:
                    if self.file_hashes[file_path] != file_hash:
                        changed_files.append(file_path)
                        self.file_hashes[file_path] = file_hash
                else:
                    self.file_hashes[file_path] = file_hash
                    # New file - analyze it
                    changed_files.append(file_path)
            
            except Exception as e:
                logger.debug(f"[CODE-INTELLIGENCE] Error checking file {file_path}: {e}")
        
        # Analyze changed files
        for file_path in changed_files:
            if file_path not in self.analyzed_files:
                self._analyze_code_file(file_path)
                self.analyzed_files.add(file_path)
    
    def _proactive_code_analysis(self):
        """Proactively analyze code for learning opportunities."""
        if not self.repo_access or not self.multi_llm:
            return
        
        # Analyze key files that haven't been analyzed recently
        key_files = [
            "backend/app.py",
            "backend/llm_orchestrator/llm_orchestrator.py",
            "backend/genesis/layer1_integration.py"
        ]
        
        for file_path in key_files:
            if file_path not in self.analyzed_files:
                self._analyze_code_file(file_path)
    
    def _analyze_code_file(self, file_path: str) -> Optional[CodeAnalysis]:
        """Analyze a code file for insights and learning opportunities."""
        if not self.repo_access or not self.multi_llm:
            return None
        
        logger.info(f"[CODE-INTELLIGENCE] Analyzing code file: {file_path}")
        
        try:
            file_content = self.repo_access.read_file(file_path)
            if "error" in file_content:
                return None
            
            content = file_content.get("content", "")
            if not content:
                return None
            
            # Use LLM to analyze the code
            analysis_prompt = f"""Analyze this code file and extract:
1. Key functionality and purpose
2. Important patterns or design decisions
3. Potential improvements or optimizations
4. Learning opportunities (what can we learn from this code?)

File: {file_path}
Code:
{content[:4000]}  # Limit to avoid token limits

Provide structured analysis with insights and code snippets."""
            
            response = self.multi_llm.generate(
                prompt=analysis_prompt,
                task_type=TaskType.CODE_EXPLANATION,
                system_prompt="You are an expert code analyst. Extract insights, patterns, and learning opportunities from code."
            )
            
            if not response.get("success"):
                return None
            
            # Parse insights from response
            insights = self._extract_insights(response.get("content", ""))
            
            # Create learning examples
            learning_examples = self._create_learning_examples(
                file_path=file_path,
                content=content,
                insights=insights
            )
            
            analysis = CodeAnalysis(
                file_path=file_path,
                analysis_type="proactive",
                insights=insights,
                code_snippets=[],
                trust_score=0.8,  # High trust for code analysis
                learning_examples=learning_examples,
                timestamp=datetime.now()
            )
            
            # Store in knowledge base
            self.code_knowledge[file_path] = {
                "insights": insights,
                "timestamp": datetime.now().isoformat(),
                "trust_score": analysis.trust_score
            }
            
            # Store learning examples
            if self.learning_integration and learning_examples:
                for example in learning_examples:
                    try:
                        self.learning_integration.trigger_autonomous_learning(
                            trigger_type="code_analysis",
                            trigger_data={
                                "file_path": file_path,
                                "example": example
                            }
                        )
                    except Exception as e:
                        logger.error(f"[CODE-INTELLIGENCE] Error storing learning example: {e}")
            
            return analysis
        
        except Exception as e:
            logger.error(f"[CODE-INTELLIGENCE] Error analyzing {file_path}: {e}")
            return None
    
    def _extract_insights(self, analysis_content: str) -> List[str]:
        """Extract insights from LLM analysis."""
        insights = []
        
        # Simple extraction - look for numbered lists or bullet points
        lines = analysis_content.split("\n")
        for line in lines:
            line = line.strip()
            if line and (line.startswith("-") or line.startswith("*") or 
                         (line[0].isdigit() and "." in line[:3])):
                insights.append(line)
        
        # If no structured format, split by sentences
        if not insights:
            sentences = analysis_content.split(". ")
            insights = [s.strip() + "." for s in sentences[:10] if s.strip()]
        
        return insights[:10]  # Limit to top 10
    
    def _create_learning_examples(
        self,
        file_path: str,
        content: str,
        insights: List[str]
    ) -> List[Dict[str, Any]]:
        """Create learning examples from code analysis."""
        examples = []
        
        # Create example for code understanding
        examples.append({
            "type": "code_understanding",
            "data": {
                "context": {
                    "file_path": file_path,
                    "code_preview": content[:500]
                },
                "expected": {
                    "understanding": insights[:3]  # Top 3 insights
                },
                "actual": {
                    "analysis": insights
                }
            }
        })
        
        return examples
    
    def enhance_prompt_with_code_context(
        self,
        prompt: str,
        task_type: TaskType,
        relevant_files: Optional[List[str]] = None
    ) -> str:
        """
        Enhance prompt with relevant code context.
        
        Makes LLMs always aware of source code when responding.
        """
        if not self.repo_access:
            return prompt
        
        # Get relevant code context
        code_context = self._get_relevant_code_context(prompt, task_type, relevant_files)
        
        if not code_context:
            return prompt
        
        enhanced_prompt = f"""{prompt}

---
RELEVANT SOURCE CODE CONTEXT:
{code_context}

When responding, reference actual code files and functions when relevant.
"""
        
        return enhanced_prompt
    
    def _get_relevant_code_context(
        self,
        prompt: str,
        task_type: TaskType,
        relevant_files: Optional[List[str]] = None
    ) -> str:
        """Get relevant code context for prompt."""
        context_parts = []
        
        # If specific files requested, use those
        if relevant_files:
            for file_path in relevant_files[:self.max_context_files]:
                try:
                    file_content = self.repo_access.read_file(file_path, max_lines=100)
                    if "error" not in file_content:
                        context_parts.append(f"File: {file_path}\n{file_content.get('content', '')[:1000]}\n")
                except Exception as e:
                    logger.debug(f"[CODE-INTELLIGENCE] Error reading {file_path}: {e}")
        
        # Otherwise, use RAG to find relevant code
        else:
            # Search for relevant code patterns
            if "function" in prompt.lower() or "def" in prompt.lower():
                code_matches = self.repo_access.search_code(
                    pattern="def.*",
                    file_pattern="*.py",
                    max_results=5
                )
                for match in code_matches:
                    file_path = match.get("file", "")
                    if file_path and file_path not in [p.split("File: ")[1].split("\n")[0] for p in context_parts]:
                        try:
                            file_content = self.repo_access.read_file(file_path, max_lines=50)
                            if "error" not in file_content:
                                context_parts.append(f"File: {file_path}\n{file_content.get('content', '')[:500]}\n")
                        except:
                            pass
        
        # Add cached insights
        for file_path, knowledge in list(self.code_knowledge.items())[:3]:
            if knowledge.get("insights"):
                context_parts.append(f"Insights about {file_path}:\n" + 
                                   "\n".join(knowledge["insights"][:3]) + "\n")
        
        return "\n---\n".join(context_parts)
    
    def get_code_knowledge(self, file_path: Optional[str] = None) -> Dict[str, Any]:
        """Get code knowledge base."""
        if file_path:
            return self.code_knowledge.get(file_path, {})
        return self.code_knowledge


# Global instance
_proactive_code_intelligence: Optional[ProactiveCodeIntelligence] = None


def get_proactive_code_intelligence(
    multi_llm_client: Optional[MultiLLMClient] = None,
    repo_access: Optional[RepositoryAccessLayer] = None,
    learning_integration: Optional[LearningIntegration] = None
) -> ProactiveCodeIntelligence:
    """Get or create global proactive code intelligence instance."""
    global _proactive_code_intelligence
    if _proactive_code_intelligence is None:
        _proactive_code_intelligence = ProactiveCodeIntelligence(
            multi_llm_client=multi_llm_client,
            repo_access=repo_access,
            learning_integration=learning_integration
        )
    return _proactive_code_intelligence
