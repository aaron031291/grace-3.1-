"""
LLM Knowledge Distillation System

Extracts knowledge from open-source LLMs and converts it into Grace's
deterministic knowledge format (templates, facts, patterns).

Architecture:
1. Download open-source model weights (Llama, Mistral, DeepSeek, Phi)
2. Run inference to extract knowledge on benchmarks
3. Convert responses to Grace's format (facts, templates, patterns)
4. Store in Oracle knowledge base
5. Use for future inference WITHOUT the LLM

This gives Grace the KNOWLEDGE without LLM dependency.
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class DistillationSource(Enum):
    """Source models for knowledge distillation."""
    LLAMA_3_8B = "meta-llama/Meta-Llama-3-8B-Instruct"
    MISTRAL_7B = "mistralai/Mistral-7B-Instruct-v0.3"
    DEEPSEEK_CODER = "deepseek-ai/deepseek-coder-6.7b-instruct"
    PHI_3_MINI = "microsoft/Phi-3-mini-4k-instruct"
    QWEN_2 = "Qwen/Qwen2-7B-Instruct"
    CODELLAMA = "codellama/CodeLlama-7b-Instruct-hf"


@dataclass
class DistilledKnowledge:
    """Knowledge extracted from LLM."""
    source_model: str
    knowledge_type: str  # "fact", "template", "pattern", "reasoning_chain"
    domain: str  # "math", "code", "general", "science"
    content: Dict[str, Any]
    confidence: float
    verified: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class DistillationConfig:
    """Configuration for knowledge distillation."""
    model_name: str = "microsoft/Phi-3-mini-4k-instruct"
    cache_dir: str = "./models"
    device: str = "auto"
    quantization: str = "4bit"
    batch_size: int = 4


class LLMKnowledgeDistiller:
    """
    Distills knowledge from LLMs into Grace's format.
    """
    
    def __init__(self, config: DistillationConfig = None):
        self.config = config or DistillationConfig()
        self.model = None
        self.tokenizer = None
        self.distilled_knowledge: List[DistilledKnowledge] = []
        
        self.storage_path = Path(__file__).parent.parent / "oracle" / "distilled_knowledge"
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def download_model(self, model_name: str = None) -> bool:
        """Download model weights from HuggingFace."""
        model_name = model_name or self.config.model_name
        
        try:
            logger.info(f"[DISTILL] Downloading model: {model_name}")
            
            try:
                import torch
                from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
            except ImportError:
                logger.error("Required: pip install torch transformers accelerate bitsandbytes")
                return False
            
            cache_dir = Path(self.config.cache_dir)
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_name, cache_dir=str(cache_dir), trust_remote_code=True
            )
            
            if self.config.quantization == "4bit":
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16
                )
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_name, cache_dir=str(cache_dir), device_map="auto",
                    quantization_config=quantization_config, trust_remote_code=True
                )
            else:
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_name, cache_dir=str(cache_dir), device_map="auto",
                    torch_dtype=torch.float16, trust_remote_code=True
                )
            
            logger.info(f"[DISTILL] Model loaded!")
            return True
            
        except Exception as e:
            logger.error(f"[DISTILL] Failed: {e}")
            return False
    
    def generate(self, prompt: str, max_tokens: int = 512) -> str:
        """Generate response from loaded model."""
        if not self.model or not self.tokenizer:
            raise RuntimeError("Model not loaded")
        
        import torch
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs, max_new_tokens=max_tokens, temperature=0.1,
                do_sample=True, pad_token_id=self.tokenizer.eos_token_id
            )
        
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        return response[len(prompt):].strip()
    
    def distill_gsm8k_knowledge(self, problems: List[Dict]) -> List[DistilledKnowledge]:
        """Extract math reasoning patterns from GSM8K problems."""
        knowledge = []
        
        for problem in problems:
            prompt = f"""Solve this math problem step by step. Show your reasoning.

Problem: {problem['question']}

Solution:"""
            
            response = self.generate(prompt)
            
            extracted = self._extract_math_pattern(problem['question'], response, problem.get('numerical_answer'))
            if extracted:
                knowledge.append(extracted)
        
        self.distilled_knowledge.extend(knowledge)
        return knowledge
    
    def _extract_math_pattern(self, question: str, response: str, expected: float = None) -> Optional[DistilledKnowledge]:
        """Extract reusable math pattern from LLM response."""
        
        equations = re.findall(r'(\d+(?:\.\d+)?)\s*[+\-*/×÷]\s*(\d+(?:\.\d+)?)\s*=\s*(\d+(?:\.\d+)?)', response)
        
        keywords = []
        for word in ['total', 'remaining', 'profit', 'each', 'per', 'times', 'half', 'percent']:
            if word in question.lower():
                keywords.append(word)
        
        answer_match = re.search(r'(?:answer|result|total)[:\s]*\$?([\d,]+\.?\d*)', response, re.IGNORECASE)
        answer = float(answer_match.group(1).replace(',', '')) if answer_match else None
        
        verified = expected and answer and abs(answer - expected) < 0.01
        
        return DistilledKnowledge(
            source_model=self.config.model_name,
            knowledge_type="reasoning_chain",
            domain="math",
            content={
                "question_pattern": keywords,
                "equations": equations,
                "reasoning_steps": response.split('\n'),
                "final_answer": answer
            },
            confidence=0.9 if verified else 0.5,
            verified=verified
        )
    
    def distill_mmlu_knowledge(self, questions: List[Dict]) -> List[DistilledKnowledge]:
        """Extract factual knowledge from MMLU questions."""
        knowledge = []
        
        for q in questions:
            choices_text = "\n".join([f"{chr(65+i)}. {c}" for i, c in enumerate(q['choices'])])
            prompt = f"""Answer this question and explain why.

Question: {q['question']}
{choices_text}

Answer:"""
            
            response = self.generate(prompt)
            
            extracted = self._extract_fact(q, response)
            if extracted:
                knowledge.append(extracted)
        
        self.distilled_knowledge.extend(knowledge)
        return knowledge
    
    def _extract_fact(self, question: Dict, response: str) -> Optional[DistilledKnowledge]:
        """Extract factual knowledge from MMLU response."""
        
        answer_match = re.match(r'^([A-D])', response.strip())
        predicted = answer_match.group(1) if answer_match else None
        
        verified = predicted == question.get('correct_answer')
        
        explanation = response[2:].strip() if predicted else response
        
        return DistilledKnowledge(
            source_model=self.config.model_name,
            knowledge_type="fact",
            domain=question.get('subject', 'general'),
            content={
                "question": question['question'],
                "correct_answer": question.get('correct_answer'),
                "explanation": explanation,
                "keywords": self._extract_keywords(question['question'])
            },
            confidence=0.9 if verified else 0.4,
            verified=verified
        )
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text."""
        important = ['algorithm', 'function', 'complexity', 'derivative', 'formula',
                     'definition', 'law', 'theorem', 'principle', 'structure']
        return [w for w in important if w in text.lower()]
    
    def distill_code_patterns(self, problems: List[Dict]) -> List[DistilledKnowledge]:
        """Extract code patterns from HumanEval/MBPP."""
        knowledge = []
        
        for problem in problems:
            prompt = f"""Complete this Python function:

{problem['prompt']}

Solution:"""
            
            response = self.generate(prompt, max_tokens=256)
            
            extracted = self._extract_code_pattern(problem, response)
            if extracted:
                knowledge.append(extracted)
        
        self.distilled_knowledge.extend(knowledge)
        return knowledge
    
    def _extract_code_pattern(self, problem: Dict, response: str) -> Optional[DistilledKnowledge]:
        """Extract reusable code pattern."""
        
        code_match = re.search(r'```python\s*(.*?)```', response, re.DOTALL)
        code = code_match.group(1) if code_match else response
        
        patterns = []
        if 'for ' in code: patterns.append('loop')
        if 'if ' in code: patterns.append('conditional')
        if 'return ' in code: patterns.append('return')
        if 'def ' in code: patterns.append('function')
        if '[' in code and 'for' in code: patterns.append('list_comprehension')
        if 'lambda' in code: patterns.append('lambda')
        if 'sorted(' in code or '.sort(' in code: patterns.append('sorting')
        if 'sum(' in code: patterns.append('aggregation')
        
        return DistilledKnowledge(
            source_model=self.config.model_name,
            knowledge_type="template",
            domain="code",
            content={
                "function_name": problem.get('entry_point', ''),
                "docstring": problem.get('prompt', '')[:200],
                "code": code,
                "patterns": patterns
            },
            confidence=0.7,
            verified=False
        )
    
    def save_knowledge(self, filename: str = None) -> str:
        """Save distilled knowledge to file."""
        if not filename:
            filename = f"distilled_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = self.storage_path / filename
        
        data = {
            "source_model": self.config.model_name,
            "timestamp": datetime.now().isoformat(),
            "total_items": len(self.distilled_knowledge),
            "knowledge": [
                {
                    "source_model": k.source_model,
                    "knowledge_type": k.knowledge_type,
                    "domain": k.domain,
                    "content": k.content,
                    "confidence": k.confidence,
                    "verified": k.verified,
                    "timestamp": k.timestamp
                }
                for k in self.distilled_knowledge
            ]
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"[DISTILL] Saved {len(self.distilled_knowledge)} items to {filepath}")
        return str(filepath)
    
    def load_knowledge(self, filepath: str) -> List[DistilledKnowledge]:
        """Load previously distilled knowledge."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        self.distilled_knowledge = [
            DistilledKnowledge(**k) for k in data.get('knowledge', [])
        ]
        
        logger.info(f"[DISTILL] Loaded {len(self.distilled_knowledge)} items")
        return self.distilled_knowledge
    
    def convert_to_oracle_format(self) -> Dict[str, Any]:
        """Convert distilled knowledge to Oracle storage format."""
        
        oracle_data = {
            "math_patterns": [],
            "code_templates": [],
            "facts": [],
            "reasoning_chains": []
        }
        
        for k in self.distilled_knowledge:
            if k.knowledge_type == "reasoning_chain" and k.domain == "math":
                oracle_data["math_patterns"].append({
                    "keywords": k.content.get("question_pattern", []),
                    "equations": k.content.get("equations", []),
                    "steps": k.content.get("reasoning_steps", []),
                    "confidence": k.confidence,
                    "verified": k.verified
                })
            
            elif k.knowledge_type == "template" and k.domain == "code":
                oracle_data["code_templates"].append({
                    "function_name": k.content.get("function_name", ""),
                    "docstring": k.content.get("docstring", ""),
                    "code": k.content.get("code", ""),
                    "patterns": k.content.get("patterns", []),
                    "confidence": k.confidence
                })
            
            elif k.knowledge_type == "fact":
                oracle_data["facts"].append({
                    "domain": k.domain,
                    "question": k.content.get("question", ""),
                    "answer": k.content.get("correct_answer", ""),
                    "explanation": k.content.get("explanation", ""),
                    "keywords": k.content.get("keywords", []),
                    "confidence": k.confidence,
                    "verified": k.verified
                })
        
        return oracle_data


class OracleKnowledgeStore:
    """
    Stores distilled knowledge in Grace's Oracle format.
    This is the bridge between LLM distillation and Grace's deterministic system.
    """
    
    def __init__(self):
        self.storage_path = Path(__file__).parent.parent / "oracle" / "knowledge_store"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.math_patterns: List[Dict] = []
        self.code_templates: List[Dict] = []
        self.facts: List[Dict] = []
        
        self._load_existing()
    
    def _load_existing(self):
        """Load existing knowledge from storage."""
        for category in ["math_patterns", "code_templates", "facts"]:
            filepath = self.storage_path / f"{category}.json"
            if filepath.exists():
                with open(filepath, 'r') as f:
                    setattr(self, category, json.load(f))
                logger.info(f"[ORACLE] Loaded {len(getattr(self, category))} {category}")
    
    def ingest_distilled_knowledge(self, oracle_data: Dict[str, Any]):
        """Ingest knowledge from distillation."""
        
        for pattern in oracle_data.get("math_patterns", []):
            if pattern not in self.math_patterns:
                self.math_patterns.append(pattern)
        
        for template in oracle_data.get("code_templates", []):
            if template not in self.code_templates:
                self.code_templates.append(template)
        
        for fact in oracle_data.get("facts", []):
            if fact not in self.facts:
                self.facts.append(fact)
        
        self._save()
        
        logger.info(f"[ORACLE] Ingested knowledge: {len(self.math_patterns)} math, "
                   f"{len(self.code_templates)} code, {len(self.facts)} facts")
    
    def _save(self):
        """Save knowledge to storage."""
        for category in ["math_patterns", "code_templates", "facts"]:
            filepath = self.storage_path / f"{category}.json"
            with open(filepath, 'w') as f:
                json.dump(getattr(self, category), f, indent=2)
    
    def query_math(self, keywords: List[str]) -> List[Dict]:
        """Query math patterns by keywords."""
        results = []
        for pattern in self.math_patterns:
            if any(kw in pattern.get("keywords", []) for kw in keywords):
                results.append(pattern)
        return sorted(results, key=lambda x: x.get("confidence", 0), reverse=True)
    
    def query_code(self, function_name: str = None, patterns: List[str] = None) -> List[Dict]:
        """Query code templates."""
        results = []
        for template in self.code_templates:
            if function_name and function_name in template.get("function_name", ""):
                results.append(template)
            elif patterns and any(p in template.get("patterns", []) for p in patterns):
                results.append(template)
        return results
    
    def query_facts(self, domain: str = None, keywords: List[str] = None) -> List[Dict]:
        """Query facts."""
        results = []
        for fact in self.facts:
            if domain and fact.get("domain") != domain:
                continue
            if keywords and not any(kw in fact.get("keywords", []) for kw in keywords):
                continue
            results.append(fact)
        return sorted(results, key=lambda x: x.get("confidence", 0), reverse=True)


def run_full_distillation(model_name: str = "microsoft/Phi-3-mini-4k-instruct"):
    """Run full knowledge distillation pipeline."""
    
    from backend.benchmarks.standard_llm_benchmarks import StandardLLMBenchmarks
    
    benchmarks = StandardLLMBenchmarks()
    
    config = DistillationConfig(model_name=model_name)
    distiller = LLMKnowledgeDistiller(config)
    
    logger.info("[DISTILL] Step 1: Downloading model...")
    if not distiller.download_model():
        logger.error("Model download failed")
        return None
    
    logger.info("[DISTILL] Step 2: Distilling GSM8K knowledge...")
    gsm8k_problems = [{"question": p.question, "numerical_answer": p.numerical_answer} 
                      for p in benchmarks.gsm8k_problems[:100]]
    distiller.distill_gsm8k_knowledge(gsm8k_problems)
    
    logger.info("[DISTILL] Step 3: Distilling MMLU knowledge...")
    mmlu_questions = []
    for subject, questions in list(benchmarks.mmlu_questions.items())[:10]:
        for q in questions[:10]:
            mmlu_questions.append({
                "question": q.question,
                "choices": q.choices,
                "correct_answer": q.correct_answer,
                "subject": q.subject
            })
    distiller.distill_mmlu_knowledge(mmlu_questions)
    
    logger.info("[DISTILL] Step 4: Distilling code patterns...")
    code_problems = [{"prompt": p.prompt, "entry_point": p.entry_point}
                     for p in benchmarks.humaneval_problems[:50]]
    distiller.distill_code_patterns(code_problems)
    
    logger.info("[DISTILL] Step 5: Saving and converting...")
    distiller.save_knowledge()
    oracle_data = distiller.convert_to_oracle_format()
    
    oracle = OracleKnowledgeStore()
    oracle.ingest_distilled_knowledge(oracle_data)
    
    logger.info("[DISTILL] Complete! Knowledge stored in Oracle.")
    return oracle


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_full_distillation()
