"""
RAG prompt utilities for injecting retrieved context into chat prompts.
"""

from typing import List, Optional


def build_rag_prompt(user_query: str, context: Optional[str] = None) -> str:
    """
    Build a RAG-augmented prompt by injecting retrieved context.
    
    Args:
        user_query: The original user message/query
        context: Retrieved context from the RAG system (optional)
        
    Returns:
        str: Formatted prompt with context injected
    """
    if not context or context.strip() == "":
        # No context, return original query
        return user_query
    
    # Format prompt with context injection
    prompt = f"""Based on the following context, answer the user's question:

<context>
{context}
</context>

User Question: {user_query}"""
    
    return prompt


def build_rag_system_prompt() -> str:
    """
    Build the system prompt for RAG-augmented responses.
    Strict mode: Only use information from the provided context.
    
    Returns:
        str: System prompt instructing the model to ONLY use provided context
    """
    return """You are a knowledge assistant that ONLY answers questions using the provided context.

CRITICAL RULES:
1. You MUST answer ONLY based on the information provided in the context below
2. You MUST NOT add any information from your training data
3. You MUST NOT make assumptions or inferences beyond what is explicitly stated in the context
4. You MUST NOT provide general knowledge unless it appears in the context
5. If the user's question cannot be directly answered from the context, you MUST say: "I cannot answer this question based on the available knowledge base."
6. Be precise, factual, and cite the context when possible
7. Do not add opinions, interpretations, or information not in the context

Remember: Your role is to convey the knowledge base faithfully, not to generate information."""
