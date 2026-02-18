# Machine Learning Fundamentals

## Core Concepts

### Supervised Learning
Learning from labeled data. Given input X and output Y, find function f where Y = f(X).
- **Classification**: Predict categories (spam/not spam, positive/negative)
- **Regression**: Predict continuous values (price, temperature)

### Unsupervised Learning
Learning from unlabeled data. Find structure and patterns.
- **Clustering**: Group similar items (K-means, DBSCAN)
- **Dimensionality Reduction**: Reduce features while preserving information (PCA, t-SNE)
- **Anomaly Detection**: Find unusual patterns

### Reinforcement Learning
Learning through interaction with an environment. Agent takes actions, receives rewards, learns optimal policy.

## Neural Networks

### Architecture
- **Input Layer**: Receives raw data
- **Hidden Layers**: Transform data through learned weights
- **Output Layer**: Produces predictions
- **Activation Functions**: ReLU, Sigmoid, Tanh, Softmax

### Training Process
1. Forward pass: Input → Hidden layers → Output
2. Loss calculation: Compare output to target
3. Backward pass: Calculate gradients
4. Weight update: Adjust weights using optimizer (Adam, SGD)

### Transformers
The architecture behind modern LLMs.
- **Self-Attention**: Each token attends to all other tokens
- **Multi-Head Attention**: Multiple attention patterns in parallel
- **Positional Encoding**: Adds position information to embeddings
- **Feed-Forward Layers**: Process attention outputs

## Embeddings and Vector Search

### What are Embeddings?
Dense vector representations of text/images. Similar content has similar vectors (high cosine similarity).

### Embedding Models
- **Sentence Transformers**: all-MiniLM-L6-v2 (384 dimensions, fast)
- **OpenAI**: text-embedding-3-small (1536 dimensions)
- **Cohere**: embed-english-v3.0

### Vector Databases
- **Qdrant**: Rust-based, fast, supports filtering
- **ChromaDB**: Python-native, simple API
- **Pinecone**: Cloud-managed, scalable
- **FAISS**: Facebook's library, in-memory

### Retrieval-Augmented Generation (RAG)
1. User asks a question
2. Embed the question into a vector
3. Search vector DB for similar content chunks
4. Pass retrieved chunks as context to LLM
5. LLM generates answer grounded in the context

### Chunking Strategies
- **Fixed size**: Split every N characters with overlap
- **Semantic**: Split at paragraph/sentence boundaries using embeddings
- **Recursive**: Split by sections, then paragraphs, then sentences

## Trust and Confidence Scoring

### Source Reliability
- Official documentation: 0.95
- Academic papers: 0.90
- Verified tutorials: 0.80
- Community Q&A: 0.60
- Unverified sources: 0.40

### Content Quality Indicators
- Well-structured with headings
- Contains code examples
- Has citations/references
- Up-to-date (recency decay)
- Consistent with existing knowledge

### Contradiction Detection
When new content contradicts existing knowledge:
1. Compare embeddings of claims
2. Identify semantic contradictions
3. Weight by source reliability
4. Flag for human review if both sources are high-trust

## LLM Orchestration

### Model Selection
Different models for different tasks:
- **Code generation**: DeepSeek Coder, Qwen Coder
- **Reasoning**: DeepSeek-R1, Llama 3
- **Quick queries**: Mistral 7B, Phi-3
- **Validation**: Gemma 2, multiple models for consensus

### Hallucination Mitigation
1. Repository grounding — claims must reference actual data
2. Cross-model consensus — multiple models must agree
3. Contradiction detection — check against existing knowledge
4. Confidence scoring — honest uncertainty
5. Trust system verification — validate against learning memory
