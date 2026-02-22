# knowledge_compiler

Knowledge Compiler

## Location
`cognitive/knowledge_compiler.py`

## Classes
- **CompiledFact**: A single extracted fact. Queryable without LLM.
- **CompiledProcedure**: An extracted procedure. Executable without LLM.
- **CompiledDecisionRule**: A deterministic decision rule. No LLM needed to evaluate.
- **CompiledTopicIndex**: Topic classification for a document chunk.
- **CompiledEntityRelation**: Entity relationship extracted from text.
- **KnowledgeCompiler**: Compiles raw data into deterministic structures using LLM ONCE.
- **DistilledKnowledge**: Knowledge extracted directly from the LLM's weights.
- **LLMKnowledgeMiner**: Mines the LLM systematically to extract its knowledge into
- **KnowledgeIndexer**: Indexes internal knowledge sources into the vector store for RAG.
- **RetrievalQualityTracker**: Tracks which retrieved results were actually useful.

## Functions
- `get_llm_knowledge_miner()`
- `get_knowledge_compiler()`
- `get_knowledge_indexer()`
- `get_retrieval_quality_tracker()`

