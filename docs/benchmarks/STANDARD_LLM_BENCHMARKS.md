# Standard LLM Benchmarks System ✅

## 🎯 Comprehensive LLM Evaluation Suite

Benchmarks for evaluating LLMs on standard industry benchmarks:

| Benchmark | Focus | Questions |
|-----------|-------|-----------|
| **HumanEval** | Code generation | 164 problems |
| **GSM8K** | Math reasoning | 8,792 problems |
| **MMLU** | Knowledge across 57 subjects | 14,042 questions |
| **Reliability** | Consistency & latency | Custom tests |
| **Safety** | Harmful content refusal | 10+ categories |

---

## 🚀 Quick Start

### Run All Benchmarks
```bash
# OpenAI
python scripts/run_standard_benchmarks.py --provider openai --api-key YOUR_KEY

# Anthropic (Claude)
python scripts/run_standard_benchmarks.py --provider anthropic --api-key YOUR_KEY

# Google (Gemini)
python scripts/run_standard_benchmarks.py --provider google --api-key YOUR_KEY

# DeepSeek
python scripts/run_standard_benchmarks.py --provider deepseek --api-key YOUR_KEY

# Grace (local)
python scripts/run_standard_benchmarks.py --provider grace
```

### Run Specific Benchmark
```bash
python scripts/run_standard_benchmarks.py --provider openai --benchmark humaneval
python scripts/run_standard_benchmarks.py --provider anthropic --benchmark gsm8k
python scripts/run_standard_benchmarks.py --provider google --benchmark mmlu
python scripts/run_standard_benchmarks.py --provider openai --benchmark safety
```

---

## 📊 Benchmark Details

### 1. HumanEval (Code Generation)
- **Purpose**: Evaluate code synthesis ability
- **Format**: Complete Python function from docstring
- **Metrics**: pass@k (functional correctness)
- **Sample Problems**: 10 included, full 164 downloadable

```python
# Example problem
def has_close_elements(numbers: List[float], threshold: float) -> bool:
    """ Check if in given list of numbers, are any two numbers 
    closer to each other than given threshold.
    """
```

### 2. GSM8K (Math Reasoning)
- **Purpose**: Evaluate mathematical reasoning
- **Format**: Grade school math word problems
- **Metrics**: Exact match on final answer
- **Sample Problems**: 10 included, full 8.7K downloadable

```
Question: Janet's ducks lay 16 eggs per day. She eats three for 
breakfast and bakes muffins with four. She sells the rest for $2 
each. How much does she make daily?

Answer: #### 18
```

### 3. MMLU (Multitask Language Understanding)
- **Purpose**: Evaluate broad knowledge
- **Format**: Multiple choice (A/B/C/D)
- **Subjects**: 57 subjects across STEM, humanities, social sciences
- **Sample**: 2 questions per subject included

**Subjects Include:**
- Computer Science
- Machine Learning
- Mathematics
- Anatomy
- Business Ethics
- Astronomy
- And 50+ more...

### 4. Reliability Benchmark
- **Purpose**: Evaluate consistency and performance
- **Metrics**:
  - Response consistency (same question → same answer)
  - Latency variance
  - Error rate

### 5. Safety Benchmark
- **Purpose**: Evaluate harmful content refusal
- **Categories**:
  - Harmful content generation
  - Misinformation
  - Personal information
  - Illegal activities
  - Hate speech
  - Self-harm
  - Jailbreak attempts
  - Privacy violations
  - Manipulation/phishing

---

## 📈 Expected Results (Industry Baselines)

| Model | HumanEval | GSM8K | MMLU |
|-------|-----------|-------|------|
| GPT-4o | 90%+ | 94% | 88% |
| Claude 3.5 | 92%+ | 92% | 88% |
| Gemini 1.5 Pro | 84% | 91% | 85% |
| DeepSeek Coder | 86% | 85% | 75% |

---

## 🔧 Configuration

### Environment Variables
```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="..."
export DEEPSEEK_API_KEY="..."
```

### CLI Options
```
--provider      LLM provider (openai, anthropic, google, deepseek, grace)
--api-key       API key (or use env var)
--model         Specific model name
--benchmark     all, humaneval, gsm8k, mmlu, reliability, safety
--num-problems  Number of problems to test
--subjects      MMLU subjects (comma-separated)
--iterations    Reliability test iterations
--output        Output file path
```

---

## 📁 Output Files

```
benchmark_results_openai_20260118_120000.json  # Raw results
benchmark_results_openai_20260118_120000.txt   # Human-readable report
```

### JSON Structure
```json
{
  "humaneval": {
    "benchmark_type": "humaneval",
    "provider": "openai",
    "total_questions": 10,
    "correct_answers": 9,
    "accuracy": 0.9,
    "average_latency_ms": 1523.4,
    "total_tokens": 5420,
    "cost_estimate": 0.16,
    "detailed_results": [...],
    "errors": []
  }
}
```

---

## 🔌 API Integration

### Add Custom Provider
```python
from backend.benchmarks import StandardLLMBenchmarks, LLMProvider

def my_llm_call(prompt: str) -> str:
    # Your LLM API call
    return response

benchmarks = StandardLLMBenchmarks()
results = await benchmarks.run_all_benchmarks(
    my_llm_call,
    LLMProvider.GRACE,  # Or add custom provider
    humaneval_problems=10,
    gsm8k_problems=10
)
```

---

## 📊 Programmatic Usage

```python
import asyncio
from backend.benchmarks import StandardLLMBenchmarks, LLMProvider

async def benchmark_my_llm():
    benchmarks = StandardLLMBenchmarks()
    
    def llm_call(prompt: str) -> str:
        # Your LLM call here
        return "response"
    
    # Run individual benchmarks
    humaneval = await benchmarks.run_humaneval_benchmark(
        llm_call, LLMProvider.GRACE, num_problems=10
    )
    print(f"HumanEval: {humaneval.accuracy:.2%}")
    
    gsm8k = await benchmarks.run_gsm8k_benchmark(
        llm_call, LLMProvider.GRACE, num_problems=10
    )
    print(f"GSM8K: {gsm8k.accuracy:.2%}")
    
    mmlu = await benchmarks.run_mmlu_benchmark(
        llm_call, LLMProvider.GRACE, 
        subjects=["computer_science", "machine_learning"]
    )
    print(f"MMLU: {mmlu.accuracy:.2%}")
    
    # Generate report
    results = {"humaneval": humaneval, "gsm8k": gsm8k, "mmlu": mmlu}
    print(benchmarks.generate_report(results))

asyncio.run(benchmark_my_llm())
```

---

## ✅ Features

✅ **5 Standard Benchmarks** - HumanEval, GSM8K, MMLU, Reliability, Safety  
✅ **Multi-Provider Support** - OpenAI, Anthropic, Google, DeepSeek, Grace  
✅ **Async Execution** - Fast parallel evaluation  
✅ **Code Verification** - Actual test execution for HumanEval  
✅ **Cost Estimation** - Track API costs  
✅ **Detailed Reports** - JSON + human-readable output  
✅ **Extensible** - Easy to add custom providers/benchmarks  

---

## 📁 File Structure

```
backend/benchmarks/
├── __init__.py
├── standard_llm_benchmarks.py    # Main benchmark system
└── benchmark_data/               # Generated datasets
    ├── humaneval.json
    ├── gsm8k.json
    ├── mmlu.json
    └── safety_tests.json

scripts/
└── run_standard_benchmarks.py    # CLI runner
```

---

## 🎯 Next Steps

1. **Download Full Datasets**: Fetch complete HumanEval, GSM8K, MMLU
2. **Add More Providers**: Mistral, Llama, etc.
3. **CI/CD Integration**: Automated benchmark runs
4. **Dashboard**: Web UI for results visualization
