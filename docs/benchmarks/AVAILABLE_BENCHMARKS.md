# Available Open Source Benchmarks for Grace

## ✅ **Currently Integrated Benchmarks**

Grace already has integrations for the following benchmarks:

### 1. **BigCodeBench** ✅
- **Status:** Integrated (with dependency issues)
- **Tasks:** 1,140 Python tasks across 7 domains, 139 libraries
- **Script:** `scripts/test_bigcodebench_simple.py` (working)
- **Script:** `scripts/test_bigcodebench_baseline.py` (requires full installation)
- **Script:** `scripts/run_bigcodebench_evaluation.py` (full evaluation)
- **Integration:** `backend/benchmarking/bigcodebench_integration.py`
- **Current Performance:** 100% on style test (10 tasks)
- **Note:** Full installation has dependency conflicts (vllm/torch version)

### 2. **HumanEval** ✅
- **Status:** Integrated
- **Tasks:** 164 hand-written Python problems
- **Integration:** `backend/benchmarking/humaneval_integration.py`
- **Leaderboard:** GPT-4 (67%), Claude-3.5-Sonnet (84.9%), DeepSeek-Coder-V2 (90.2%)
- **Run:** Via `scripts/run_all_benchmarks.py --benchmarks humaneval`

### 3. **MBPP (Mostly Basic Python Problems)** ✅
- **Status:** Integrated
- **Tasks:** ~974 basic Python programming tasks
- **Integration:** `backend/benchmarking/mbpp_integration.py`
- **Run:** Via `scripts/run_all_benchmarks.py --benchmarks mbpp`

### 4. **Benchmark Harness** ✅
- **Status:** Integrated
- **Purpose:** Unified interface to run multiple benchmarks
- **Integration:** `backend/benchmarking/benchmark_harness.py`
- **Run:** `scripts/run_all_benchmarks.py` (runs all registered benchmarks)

---

## 🚀 **Additional Benchmarks Available for Integration**

Based on research, here are other open-source benchmarks that could be integrated:

### **High Priority - Recommended**

#### 1. **LiveCodeBench** (2024)
- **Focus:** Holistic, contamination-free evaluation with competitive programming
- **Tasks:** ~400 problems from LeetCode, AtCoder, CodeForces
- **Strengths:** 
  - Real contest problems (2023-2024)
  - Tests functional correctness + test prediction + execution behavior
  - More realistic than tiny Python-only snippets
- **Difficulty:** More challenging than HumanEval/MBPP
- **GitHub:** Likely available via HuggingFace datasets
- **Integration Effort:** Medium

#### 2. **DS-1000** (Data Science Benchmark)
- **Focus:** Real data science tasks using NumPy, Pandas, etc.
- **Tasks:** 1,000 problems across 7 libraries
- **Strengths:**
  - Domain-specific (data science)
  - Realistic constraints
  - Tests include perturbations to reduce memorization
- **Best Public Models:** ~43% accuracy
- **Website:** https://ds1000-code-gen.github.io/
- **Integration Effort:** Medium

#### 3. **DS-Bench** (2025)
- **Focus:** More complex data science tasks vs DS-1000
- **Tasks:** Longer, heavier solutions with realistic descriptions
- **Strengths:**
  - Builds on DS-1000 but increases difficulty
  - Better library coverage
  - More robust metrics
- **Top Model Performance:** GPT-4o ~20.2% (shows difficulty)
- **Integration Effort:** Medium

#### 4. **EvoCodeBench-2403**
- **Focus:** Repository-aligned tasks with domain labels
- **Tasks:** 275 samples across 25 repos (first version)
- **Strengths:**
  - Uses code from real repos (not isolated functions)
  - Domain tags for measuring performance in specific code types
  - Reduces data leakage
- **GPT-4 Performance:** ~20.7% Pass@1 (much harder than HumanEval)
- **Integration Effort:** Medium-High

### **Medium Priority**

#### 5. **SWE-Bench**
- **Focus:** Real-world software engineering tasks (bug fixes, feature additions)
- **Tasks:** GitHub issues from real repositories
- **Strengths:**
  - Tests real-world software engineering skills
  - Multi-file code changes
  - Repository context required
- **Integration Effort:** High (requires repo cloning)

#### 6. **DOMAINEVAL**
- **Focus:** Multi-domain code generation (system programming, cryptography, etc.)
- **Tasks:** Six domains
- **Strengths:**
  - Tests domain generality
  - Reveals where models fail (e.g., cryptography ~12% pass)
- **Integration Effort:** Medium

#### 7. **CoderEval**
- **Focus:** Code generation evaluation
- **Tasks:** Multiple programming languages
- **Strengths:** Multi-language support
- **Integration Effort:** Medium

#### 8. **Deep-Bench** (2025)
- **Focus:** Deep learning workflows (model construction, training loops)
- **Tasks:** Function-level benchmarks for DL tasks
- **Strengths:**
  - Much harder than general snippets
  - Tests across phases and input types
- **GPT-4o Performance:** ~31% (lower than DS-1000)
- **Integration Effort:** Medium

### **Lower Priority**

#### 9. **Mercury**
- **Status:** Mentioned in benchmark harness but not detailed
- **Integration Effort:** Unknown

#### 10. **COMPASS**
- **Status:** Mentioned in benchmark harness but not detailed
- **Integration Effort:** Unknown

---

## 📊 **Benchmark Comparison**

| Benchmark | Tasks | Difficulty | Domain | Integration Status |
|-----------|-------|------------|--------|-------------------|
| **HumanEval** | 164 | Medium | General Python | ✅ Integrated |
| **MBPP** | ~974 | Easy-Medium | General Python | ✅ Integrated |
| **BigCodeBench** | 1,140 | Medium-Hard | Multi-domain (7 domains) | ✅ Integrated (partial) |
| **LiveCodeBench** | ~400 | Hard | Competitive Programming | ❌ Not Integrated |
| **DS-1000** | 1,000 | Medium-Hard | Data Science | ❌ Not Integrated |
| **DS-Bench** | ~1,000+ | Hard | Data Science | ❌ Not Integrated |
| **EvoCodeBench** | 275+ | Very Hard | Real Repos | ❌ Not Integrated |
| **SWE-Bench** | 2,000+ | Very Hard | Software Engineering | ❌ Not Integrated |
| **DOMAINEVAL** | ~600 | Hard | Multi-domain | ❌ Not Integrated |

---

## 🛠️ **How to Run Current Benchmarks**

### Run All Benchmarks
```bash
python scripts/run_all_benchmarks.py
```

### Run Specific Benchmarks
```bash
# HumanEval only
python scripts/run_all_benchmarks.py --benchmarks humaneval

# MBPP only
python scripts/run_all_benchmarks.py --benchmarks mbpp

# Multiple benchmarks
python scripts/run_all_benchmarks.py --benchmarks humaneval mbpp

# Limit number of problems per benchmark
python scripts/run_all_benchmarks.py --benchmarks humaneval --max-problems 10
```

### Run BigCodeBench Style Test
```bash
python scripts/test_bigcodebench_simple.py
```

### Run BigCodeBench Baseline (if dependencies fixed)
```bash
python scripts/test_bigcodebench_baseline.py
```

---

## 🎯 **Recommended Next Steps**

### **Immediate (Easy Wins)**
1. ✅ **Run HumanEval** - Already integrated, just needs execution
   ```bash
   python scripts/run_all_benchmarks.py --benchmarks humaneval --max-problems 20
   ```

2. ✅ **Run MBPP** - Already integrated
   ```bash
   python scripts/run_all_benchmarks.py --benchmarks mbpp --max-problems 20
   ```

### **Short Term (High Value)**
3. **Integrate DS-1000** - Data science is important domain
   - Good balance of difficulty and realism
   - Well-documented benchmark
   - Tests domain-specific knowledge

4. **Integrate LiveCodeBench** - Competitive programming focus
   - Tests algorithmic problem-solving
   - More realistic than HumanEval
   - Good for measuring improvement

### **Medium Term**
5. **Integrate EvoCodeBench** - Real repository tasks
   - Tests real-world code understanding
   - Multi-file context
   - Domain-specific performance

6. **Fix BigCodeBench Full Installation** - Resolve dependency conflicts
   - Fix vllm/torch version conflicts
   - Enable full 1,140 task evaluation

### **Long Term**
7. **Integrate SWE-Bench** - Real software engineering
   - Requires more complex setup (repo cloning)
   - Tests bug fixing and feature addition
   - Most realistic benchmark

---

## 📈 **Current Performance Summary**

Based on latest test runs:

- **BigCodeBench-Style:** 100% (10/10 tasks) ✅
- **HumanEval:** Not yet run (ready to test)
- **MBPP:** Not yet run (ready to test)

---

## 🔗 **Resources**

- **HumanEval:** https://github.com/openai/human-eval
- **MBPP:** Available via HuggingFace datasets
- **BigCodeBench:** https://github.com/bigcode-project/bigcodebench
- **DS-1000:** https://ds1000-code-gen.github.io/
- **LiveCodeBench:** Likely via HuggingFace or GitHub
- **EvoCodeBench:** Research paper + GitHub repo
- **SWE-Bench:** https://www.swebench.com/

---

## 💡 **Integration Pattern**

To integrate a new benchmark, follow this pattern:

1. Create integration file: `backend/benchmarking/{benchmark}_integration.py`
2. Implement class with:
   - `install_{benchmark}()` method
   - `get_{benchmark}_problems()` method
   - `evaluate_solution()` method
   - `run_evaluation()` method
3. Register in `benchmark_harness.py`:
   ```python
   try:
       from backend.benchmarking.{benchmark}_integration import get_{benchmark}_integration
       benchmark = get_{benchmark}_integration(coding_agent=coding_agent)
       harness.register_benchmark("{benchmark}", benchmark)
   except:
       pass
   ```
4. Test with sample problems first
5. Add to `run_all_benchmarks.py` script

---

**Last Updated:** Current Session  
**Status:** Ready to run HumanEval and MBPP, BigCodeBench working with style test
