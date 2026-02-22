# GitHub AI Research Repositories — Grace Training Sources

## Foundational AI/ML Repositories

### Machine Learning
- **scikit-learn** (github.com/scikit-learn/scikit-learn): Industry-standard ML library. Classification, regression, clustering, dimensionality reduction. Grace should understand every algorithm here.
- **XGBoost** (github.com/dmlc/xgboost): Gradient boosting framework. Dominant in tabular ML. Understand tree-based methods.
- **LightGBM** (github.com/microsoft/LightGBM): Microsoft's fast gradient boosting. Key for understanding efficiency trade-offs.
- **CatBoost** (github.com/catboost/catboost): Yandex's gradient boosting with native categorical support.

### Deep Learning Frameworks
- **PyTorch** (github.com/pytorch/pytorch): Primary deep learning framework. Grace must understand tensors, autograd, nn.Module, DataLoaders.
- **TensorFlow** (github.com/tensorflow/tensorflow): Google's ML framework. Understand Keras API, tf.data, SavedModel.
- **JAX** (github.com/google/jax): Composable transformations of NumPy programs. Understand vmap, jit, grad.
- **Hugging Face Transformers** (github.com/huggingface/transformers): THE library for pretrained models. Understand tokenizers, model loading, pipelines, fine-tuning.

### Large Language Models
- **llama** (github.com/meta-llama/llama): Meta's open LLM. Understand architecture, training, inference.
- **ollama** (github.com/ollama/ollama): Run LLMs locally. Grace's own LLM runtime.
- **vLLM** (github.com/vllm-project/vllm): High-throughput LLM serving. PagedAttention for efficient inference.
- **text-generation-webui** (github.com/oobabooga/text-generation-webui): UI for running LLMs locally.
- **LangChain** (github.com/langchain-ai/langchain): LLM application framework. Chains, agents, retrieval.
- **LlamaIndex** (github.com/run-llama/llama_index): Data framework for LLM apps. Indexing, retrieval, query engines.
- **OpenRouter** (github.com/OpenRouterTeam): Multi-model routing — similar concept to Grace's reasoning router.

### Retrieval-Augmented Generation (RAG)
- **Qdrant** (github.com/qdrant/qdrant): Grace's vector database. Understand HNSW indexing, payload filtering, quantization.
- **ChromaDB** (github.com/chroma-core/chroma): Simple vector DB. Understand the API patterns.
- **FAISS** (github.com/facebookresearch/faiss): Facebook's similarity search. Understand IVF, PQ, flat indexing.
- **sentence-transformers** (github.com/UKPLab/sentence-transformers): Embedding models. Understand bi-encoders, cross-encoders, fine-tuning.

### AI Agents
- **AutoGPT** (github.com/Significant-Gravitas/AutoGPT): Autonomous AI agent. Understand task decomposition, tool use, memory.
- **MetaGPT** (github.com/geekan/MetaGPT): Multi-agent framework. Understand role assignment, workflow, code generation.
- **CrewAI** (github.com/crewAIInc/crewAI): AI agent orchestration. Understand crews, tasks, tools.
- **OpenDevin** (github.com/OpenDevin/OpenDevin): Open-source Devin. Understand autonomous coding agents.
- **SWE-agent** (github.com/princeton-nlp/SWE-agent): Software engineering agent from Princeton. Understand how agents navigate codebases.
- **Aider** (github.com/paul-gauthier/aider): AI pair programming. Understand git integration, code editing patterns.

### Neuro-Symbolic AI
- **DeepProbLog** (github.com/ML-KULeuven/deepproblog): Neural networks + probabilistic logic.
- **NeuralLog** (github.com/ML-KULeuven/NeuralLog): Differentiable logic programming.
- **Logic Tensor Networks** (github.com/logictensornetworks/logictensornetworks): Real-valued logic + neural networks.

### Self-Improving / Autonomous Systems
- **Voyager** (github.com/MineDojo/Voyager): LLM-powered autonomous agent that learns continuously.
- **BabyAGI** (github.com/yoheinakajima/babyagi): Task-driven autonomous agent. Understand task creation, prioritization, execution loop.
- **SuperAGI** (github.com/TransformerOptimus/SuperAGI): Infrastructure for autonomous agents.

## Software Engineering Specific

### Code Generation & Understanding
- **StarCoder** (github.com/bigcode-project/starcoder): Open code LLM. 15B+ parameters trained on permissive code.
- **CodeLlama** (github.com/meta-llama/codellama): Meta's code-specialized LLM.
- **DeepSeek-Coder** (github.com/deepseek-ai/DeepSeek-Coder): Grace's primary code model.
- **Qwen-Coder** (github.com/QwenLM/Qwen2.5-Coder): Alibaba's code model. Strong on code understanding.
- **tree-sitter** (github.com/tree-sitter/tree-sitter): Parser framework for code analysis. Understand AST parsing.

### Code Quality & Testing
- **ruff** (github.com/astral-sh/ruff): Fast Python linter. Written in Rust.
- **pytest** (github.com/pytest-dev/pytest): Python testing framework.
- **coverage.py** (github.com/nedbat/coveragepy): Code coverage measurement.
- **mypy** (github.com/python/mypy): Static type checker for Python.
- **Black** (github.com/psf/black): Python code formatter.

### DevOps & Infrastructure
- **Kubernetes** (github.com/kubernetes/kubernetes): Container orchestration.
- **Terraform** (github.com/hashicorp/terraform): Infrastructure as code.
- **Ansible** (github.com/ansible/ansible): IT automation.
- **Docker Compose** (github.com/docker/compose): Multi-container applications.
- **GitHub Actions** (github.com/actions): CI/CD automation.

## Key Websites for Training Data

### Documentation Aggregators
- **DevDocs.io** — 400+ language/framework docs in one searchable interface
- **MDN Web Docs** (developer.mozilla.org) — Gold standard for web technologies
- **docs.python.org** — Official Python documentation
- **docs.rs** — Rust crate documentation

### Tutorial & Learning Platforms (Free)
- **freeCodeCamp** (freecodecamp.org/news) — Thousands of free tutorials
- **Real Python** (realpython.com) — In-depth Python tutorials
- **GeeksforGeeks** (geeksforgeeks.org) — Algorithm explanations with code
- **Refactoring Guru** (refactoring.guru) — Design patterns and refactoring
- **Patterns.dev** (patterns.dev) — Modern web design patterns

### Research Papers
- **Papers With Code** (paperswithcode.com) — ML papers with implementations
- **arXiv CS** (arxiv.org/list/cs.AI) — Latest AI research
- **Semantic Scholar** (semanticscholar.org) — AI-powered research discovery

### API & Standards References
- **OpenAPI Specification** (spec.openapis.org) — API design standard
- **JSON Schema** (json-schema.org) — Data validation
- **OWASP** (owasp.org) — Security standards and cheat sheets
- **12factor.net** — The Twelve-Factor App methodology

### Community Knowledge
- **Stack Overflow** (stackoverflow.com) — Via Stack Exchange API
- **Hacker News** (news.ycombinator.com/best) — Tech community discussions
- **Reddit r/programming** (reddit.com/r/programming) — Community knowledge
- **Dev.to** (dev.to) — Developer community articles
