"""
Practical examples of cognitive blueprint integration with Grace.

These examples show how to apply the 12 invariants to real operations.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from .engine import CognitiveEngine, DecisionContext
from .decorators import cognitive_operation, blast_radius, enforce_reversibility


# ==================== Example 1: Simple File Ingestion ====================

@cognitive_operation(
    "ingest_single_file",
    is_reversible=True,
    impact_scope="local"
)
def ingest_single_file(filepath: str) -> Dict[str, Any]:
    """
    Ingest a single file with cognitive enforcement.

    Demonstrates basic invariant application.
    """
    # Implementation would go here
    return {
        "status": "success",
        "filepath": filepath,
        "chunks_created": 10
    }


# ==================== Example 2: RAG Query with Ambiguity Tracking ====================

def rag_query_with_cognitive(query: str, chat_id: int) -> Dict[str, Any]:
    """
    Execute RAG query with full cognitive enforcement.

    Demonstrates:
    - Invariant 1: OODA Loop
    - Invariant 2: Ambiguity Accounting
    - Invariant 4: Determinism (probabilistic zone)
    - Invariant 6: Observability
    - Invariant 12: Forward Simulation
    """
    engine = CognitiveEngine(enable_strict_mode=True)

    # Begin decision (OODA: Observe)
    context = engine.begin_decision(
        problem_statement=f"Answer query: {query}",
        goal="Provide accurate response using knowledge base only",
        success_criteria=[
            "Relevant documents retrieved",
            "Response generated from retrieved context",
            "Sources cited",
            "No hallucination"
        ]
    )

    # OBSERVE: Gather information
    observations = {
        'query': query,
        'query_length': len(query),
        'chat_id': chat_id,
        'timestamp': datetime.now().isoformat()
    }
    engine.observe(context, observations)

    # Track ambiguity
    context.ambiguity_ledger.add_known('query', query)
    context.ambiguity_ledger.add_known('chat_id', chat_id)

    # ORIENT: Understand constraints
    constraints = {
        'safety_critical': False,
        'impact_scope': 'local',
        'max_context_length': 4096,
        'min_confidence_score': 0.3
    }

    context_info = {
        'rag_available': True,  # Check if RAG system is up
        'vector_db_connected': True,
        'model_loaded': True,
        'determinism_required': False  # Semantic search is probabilistic
    }

    engine.orient(context, constraints, context_info)

    # Set operation characteristics
    context.requires_determinism = False  # Embeddings/search is probabilistic
    context.impact_scope = "local"
    context.is_reversible = True  # No permanent changes

    # DECIDE: Generate alternative strategies
    def generate_alternatives() -> List[Dict[str, Any]]:
        return [
            {
                'name': 'semantic_search_only',
                'immediate_value': 0.8,
                'future_options': 0.7,
                'simplicity': 1.0,
                'reversibility': 1.0,
                'complexity': 0.2,
                'strategy': 'vector_search'
            },
            {
                'name': 'hybrid_search',
                'immediate_value': 1.0,
                'future_options': 0.8,
                'simplicity': 0.7,
                'reversibility': 1.0,
                'complexity': 0.4,
                'strategy': 'vector + keyword'
            },
            {
                'name': 'rerank_results',
                'immediate_value': 0.9,
                'future_options': 0.9,
                'simplicity': 0.6,
                'reversibility': 1.0,
                'complexity': 0.5,
                'strategy': 'vector + rerank'
            }
        ]

    selected_path = engine.decide(context, generate_alternatives)

    # ACT: Execute selected strategy
    def action():
        # Simulate RAG retrieval
        strategy = selected_path.get('strategy', 'vector_search')

        # This would call actual retrieval system
        retrieved_docs = [
            {'text': 'Document 1 content', 'score': 0.85},
            {'text': 'Document 2 content', 'score': 0.72},
        ]

        # Track what was retrieved (ambiguity resolution)
        context.ambiguity_ledger.add_known(
            'retrieved_doc_count',
            len(retrieved_docs)
        )

        # Generate response
        response = f"Based on {len(retrieved_docs)} documents: [Generated response]"

        return {
            'response': response,
            'sources': retrieved_docs,
            'strategy_used': strategy,
            'confidence': 0.85
        }

    result = engine.act(context, action, dry_run=False)

    # Finalize
    engine.finalize_decision(context)

    return result


# ==================== Example 3: Database Migration (Irreversible) ====================

@cognitive_operation(
    "migrate_database",
    requires_determinism=True,
    is_safety_critical=True,
    is_reversible=False,
    impact_scope="systemic"
)
@enforce_reversibility(
    reversible=False,
    justification="Database schema changes cannot be automatically reversed"
)
@blast_radius("systemic")
def migrate_database(migration_name: str, dry_run: bool = True) -> Dict[str, Any]:
    """
    Execute database migration with strict cognitive enforcement.

    Demonstrates:
    - Invariant 3: Reversibility justification
    - Invariant 4: Deterministic execution
    - Invariant 5: Blast radius awareness
    - Invariant 6: Observability
    """
    if dry_run:
        return {
            "status": "dry_run",
            "migration": migration_name,
            "would_execute": True
        }

    # Actual migration logic would go here
    return {
        "status": "success",
        "migration": migration_name,
        "tables_affected": 3
    }


# ==================== Example 4: Batch Processing with Bounded Recursion ====================

def batch_process_documents(
    directory: str,
    max_depth: int = 3
) -> Dict[str, Any]:
    """
    Process documents in directory with recursion bounds.

    Demonstrates:
    - Invariant 9: Bounded Recursion
    - Invariant 11: Time-Bounded Reasoning
    """
    engine = CognitiveEngine(enable_strict_mode=True)

    context = engine.begin_decision(
        problem_statement=f"Process all documents in {directory}",
        goal="Ingest all valid documents recursively",
        success_criteria=[
            "All documents discovered",
            "All documents ingested",
            "No infinite loops"
        ]
    )

    # Set recursion bounds
    context.max_recursion_depth = max_depth
    context.max_iterations = 100  # Max files to process

    # Set time bound (30 minutes)
    context.decision_freeze_point = datetime.now() + timedelta(minutes=30)

    # Track recursion
    def process_directory_recursive(path: str, depth: int = 0):
        # Check recursion bound (Invariant 9)
        if depth >= context.max_recursion_depth:
            context.metadata['recursion_limit_hit'] = True
            return []

        # Check time bound (Invariant 11)
        if engine.enforce_decision_freeze(context):
            context.metadata['time_limit_hit'] = True
            return []

        # Check iteration bound
        if context.iteration_count >= context.max_iterations:
            context.metadata['iteration_limit_hit'] = True
            return []

        context.iteration_count += 1
        context.recursion_depth = depth

        # Process files (simplified)
        results = []
        # ... actual processing logic
        return results

    # OBSERVE
    engine.observe(context, {'directory': directory, 'max_depth': max_depth})

    # ORIENT
    engine.orient(context, {}, {})

    # DECIDE
    def generate_alternatives():
        return [{
            'name': 'recursive_processing',
            'immediate_value': 1.0,
            'future_options': 1.0,
            'simplicity': 0.8,
            'reversibility': 1.0,
            'complexity': 0.3
        }]

    engine.decide(context, generate_alternatives)

    # ACT
    def action():
        return process_directory_recursive(directory, depth=0)

    result = engine.act(context, action)

    # Check if bounds were hit
    if context.metadata.get('recursion_limit_hit'):
        result['warning'] = f"Recursion depth limit ({max_depth}) reached"

    if context.metadata.get('time_limit_hit'):
        result['warning'] = "Time limit (30 minutes) reached"

    engine.finalize_decision(context)

    return result


# ==================== Example 5: Forward Simulation for Path Selection ====================

def select_embedding_strategy(
    document_type: str,
    document_size: int
) -> Dict[str, Any]:
    """
    Select optimal embedding strategy using forward simulation.

    Demonstrates:
    - Invariant 10: Optionality > Optimization
    - Invariant 12: Forward Simulation (Chess Mode)
    """
    engine = CognitiveEngine(enable_strict_mode=True)

    context = engine.begin_decision(
        problem_statement=f"Select embedding strategy for {document_type}",
        goal="Choose strategy that optimizes quality while preserving options",
        success_criteria=[
            "Strategy selected",
            "Future flexibility maintained"
        ]
    )

    # OBSERVE
    engine.observe(context, {
        'document_type': document_type,
        'document_size': document_size
    })

    # ORIENT
    engine.orient(context, {}, {})

    # DECIDE: Generate multiple strategies (Chess Mode)
    def generate_alternatives() -> List[Dict[str, Any]]:
        return [
            {
                'name': 'small_model_fast',
                'immediate_value': 0.6,  # Lower quality
                'future_options': 1.0,    # Can always re-embed with better model
                'simplicity': 1.0,
                'reversibility': 1.0,
                'complexity': 0.1,
                'model': 'all-MiniLM-L6-v2',
                'dimensions': 384,
                'speed': 'fast'
            },
            {
                'name': 'medium_model_balanced',
                'immediate_value': 0.8,
                'future_options': 0.9,
                'simplicity': 0.8,
                'reversibility': 1.0,
                'complexity': 0.3,
                'model': 'all-mpnet-base-v2',
                'dimensions': 768,
                'speed': 'medium'
            },
            {
                'name': 'large_model_quality',
                'immediate_value': 1.0,
                'future_options': 0.7,  # Harder to switch later
                'simplicity': 0.6,
                'reversibility': 0.8,  # Expensive to redo
                'complexity': 0.6,
                'model': 'BAAI/bge-large-en-v1.5',
                'dimensions': 1024,
                'speed': 'slow'
            }
        ]

    # Engine will select based on optionality scoring (Invariant 10)
    selected_path = engine.decide(context, generate_alternatives)

    # ACT
    def action():
        return {
            'strategy': selected_path['name'],
            'model': selected_path['model'],
            'dimensions': selected_path['dimensions'],
            'reasoning': 'Selected for optimal balance of quality and flexibility'
        }

    result = engine.act(context, action)

    engine.finalize_decision(context)

    return result


# ==================== Example 6: Ambiguity Resolution ====================

def resolve_user_query_ambiguity(query: str) -> Dict[str, Any]:
    """
    Handle ambiguous user queries with explicit tracking.

    Demonstrates:
    - Invariant 2: Explicit Ambiguity Accounting
    """
    engine = CognitiveEngine(enable_strict_mode=True)

    context = engine.begin_decision(
        problem_statement=f"Resolve ambiguity in query: {query}",
        goal="Clarify query before processing",
        success_criteria=["All ambiguities resolved or escalated"]
    )

    # Analyze query for ambiguity
    ambiguous_terms = ['it', 'that', 'this', 'them']  # Pronouns without referents
    found_ambiguity = any(term in query.lower() for term in ambiguous_terms)

    if found_ambiguity:
        context.ambiguity_ledger.add_unknown(
            'query_referent',
            blocking=True,
            notes="Query contains ambiguous pronouns without clear referents"
        )
    else:
        context.ambiguity_ledger.add_known('query_referent', 'clear')

    # Check for blocking unknowns
    if context.ambiguity_ledger.has_blocking_unknowns():
        return {
            'status': 'needs_clarification',
            'query': query,
            'unknowns': [
                e.key for e in context.ambiguity_ledger.get_blocking_unknowns()
            ],
            'suggestion': 'Please rephrase with specific nouns'
        }

    return {
        'status': 'clear',
        'query': query,
        'can_proceed': True
    }
