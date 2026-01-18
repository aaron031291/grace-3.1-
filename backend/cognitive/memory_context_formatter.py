import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import re
logger = logging.getLogger(__name__)

class MemoryContextFormatter:
    """
    Formats memories for LLM context windows with token awareness.
    
    Features:
    - Token counting (tiktoken or approximation)
    - Context window limit enforcement
    - Smart prioritization and truncation
    - Compact formatting when space is limited
    - Optimized for LLM consumption
    """
    
    def __init__(
        self,
        model_name: str = "gpt-4",
        default_max_tokens: int = 4000,
        compact_threshold: float = 0.8  # Use compact format when >80% of context used
    ):
        """
        Initialize memory context formatter.
        
        Args:
            model_name: LLM model name for token counting
            default_max_tokens: Default max tokens if model not recognized
            compact_threshold: Use compact format when this % of context is used
        """
        self.model_name = model_name
        self.default_max_tokens = default_max_tokens
        self.compact_threshold = compact_threshold
        
        # Initialize tokenizer if available
        self.encoding = None
        if TIKTOKEN_AVAILABLE:
            try:
                # Try to get encoding for model
                try:
                    self.encoding = tiktoken.encoding_for_model(model_name)
                except KeyError:
                    # Fall back to cl100k_base (GPT-4) encoding
                    self.encoding = tiktoken.get_encoding("cl100k_base")
                logger.info(f"[MEMORY-CONTEXT-FORMATTER] Using tiktoken encoding for {model_name}")
            except Exception as e:
                logger.warning(f"[MEMORY-CONTEXT-FORMATTER] Could not initialize tiktoken: {e}")
                self.encoding = None
        
        # Model context window sizes (approximate)
        self.model_context_sizes = {
            "gpt-4": 8192,
            "gpt-4-turbo": 128000,
            "gpt-3.5-turbo": 16385,
            "claude-3-opus": 200000,
            "claude-3-sonnet": 200000,
            "claude-3-haiku": 200000,
            "llama-2": 4096,
            "llama-3": 8192,
            "mistral": 32768
        }
        
        self.max_context_tokens = self.model_context_sizes.get(model_name.lower(), default_max_tokens)
        logger.info(f"[MEMORY-CONTEXT-FORMATTER] Max context tokens: {self.max_context_tokens}")
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Token count
        """
        if not text:
            return 0
        
        if self.encoding:
            try:
                return len(self.encoding.encode(text))
            except Exception as e:
                logger.warning(f"[MEMORY-CONTEXT-FORMATTER] Token counting error: {e}")
                # Fall back to approximation
        
        # Approximate token counting (rough: 1 token ≈ 4 characters)
        return len(text) // 4
    
    def format_memory_compact(self, memory: Dict[str, Any]) -> str:
        """
        Format memory in compact form (minimal tokens).
        
        Args:
            memory: Memory dictionary
            
        Returns:
            Compact formatted string
        """
        parts = []
        
        # Type and ID
        mem_type = memory.get("type", "memory")
        mem_id = memory.get("id", "unknown")
        parts.append(f"[{mem_type}:{mem_id}]")
        
        # Key information (minimal)
        if mem_type == "learning":
            example_type = memory.get("memory", {}).example_type if hasattr(memory.get("memory"), "example_type") else None
            trust = memory.get("trust_score", 0.0)
            parts.append(f"type={example_type}, trust={trust:.2f}")
        elif mem_type == "episodic":
            trust = memory.get("memory", {}).trust_score if hasattr(memory.get("memory"), "trust_score") else 0.0
            parts.append(f"trust={trust:.2f}")
        elif mem_type == "procedural":
            success = memory.get("memory", {}).success_rate if hasattr(memory.get("memory"), "success_rate") else 0.0
            parts.append(f"success={success:.2f}")
        
        # Truncated description (max 100 chars)
        desc = str(memory.get("description", memory.get("summary", "")))
        if len(desc) > 100:
            desc = desc[:97] + "..."
        if desc:
            parts.append(f"desc={desc}")
        
        return " | ".join(parts)
    
    def format_memory_standard(self, memory: Dict[str, Any]) -> str:
        """
        Format memory in standard form (readable).
        
        Args:
            memory: Memory dictionary
            
        Returns:
            Standard formatted string
        """
        mem_obj = memory.get("memory")
        if not mem_obj:
            return self.format_memory_compact(memory)
        
        parts = []
        
        # Header
        mem_type = memory.get("type", "memory")
        parts.append(f"=== {mem_type.upper()} MEMORY ===")
        
        # ID and type
        mem_id = memory.get("id", "unknown")
        parts.append(f"ID: {mem_id}")
        
        # Type-specific information
        if hasattr(mem_obj, "example_type"):
            parts.append(f"Type: {mem_obj.example_type}")
        if hasattr(mem_obj, "trust_score"):
            parts.append(f"Trust Score: {mem_obj.trust_score:.2f}")
        if hasattr(mem_obj, "success_rate"):
            parts.append(f"Success Rate: {mem_obj.success_rate:.2%}")
        
        # Description/context
        desc = getattr(mem_obj, "input_context", None) or getattr(mem_obj, "problem", None) or getattr(mem_obj, "description", None) or ""
        if desc:
            parts.append(f"Context: {desc}")
        
        # Solution/outcome (if available)
        solution = getattr(mem_obj, "solution", None) or getattr(mem_obj, "outcome", None) or ""
        if solution:
            # Truncate if too long
            if len(solution) > 500:
                solution = solution[:497] + "..."
            parts.append(f"Solution: {solution}")
        
        # Timestamp
        created = getattr(mem_obj, "created_at", None) or getattr(mem_obj, "timestamp", None)
        if created:
            parts.append(f"Date: {created.strftime('%Y-%m-%d')}")
        
        return "\n".join(parts)
    
    def format_memories_for_context(
        self,
        memories: List[Dict[str, Any]],
        max_tokens: Optional[int] = None,
        reserved_tokens: int = 1000,  # Reserve for prompt/system message
        priority_scores: Optional[Dict[str, float]] = None,
        format_style: Optional[str] = None  # "compact", "standard", "auto"
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Format memories for LLM context window.
        
        Args:
            memories: List of memory dictionaries
            max_tokens: Maximum tokens (default: model context size)
            reserved_tokens: Tokens reserved for prompt/system
            priority_scores: Optional priority scores for each memory
            format_style: Format style ("compact", "standard", "auto")
            
        Returns:
            (formatted_context, metadata) where metadata includes:
            - total_tokens: Total tokens used
            - memories_included: Number of memories included
            - memories_excluded: Number of memories excluded
            - format_style_used: Format style used
        """
        max_tokens = max_tokens or self.max_context_tokens
        available_tokens = max_tokens - reserved_tokens
        
        if available_tokens <= 0:
            logger.warning(f"[MEMORY-CONTEXT-FORMATTER] No tokens available after reservation")
            return "", {
                "total_tokens": 0,
                "memories_included": 0,
                "memories_excluded": len(memories),
                "format_style_used": "none"
            }
        
        # Determine format style
        if format_style is None or format_style == "auto":
            # Estimate tokens if we used standard format
            estimated_tokens = sum(self.count_tokens(self.format_memory_standard(m)) for m in memories)
            
            if estimated_tokens > available_tokens * self.compact_threshold:
                format_style = "compact"
            else:
                format_style = "standard"
        elif format_style not in ["compact", "standard"]:
            format_style = "standard"
        
        # Select format function
        format_func = self.format_memory_compact if format_style == "compact" else self.format_memory_standard
        
        # Sort memories by priority if provided
        if priority_scores:
            memories = sorted(memories, key=lambda m: priority_scores.get(str(m.get("id", "")), 0.0), reverse=True)
        elif all("priority" in m for m in memories):
            memories = sorted(memories, key=lambda m: m.get("priority", 0.0), reverse=True)
        
        # Build context, including memories until token limit
        formatted_parts = []
        total_tokens = 0
        memories_included = 0
        memories_excluded = 0
        
        # Add header
        header = f"=== MEMORY CONTEXT ({len(memories)} memories) ===\n"
        header_tokens = self.count_tokens(header)
        total_tokens += header_tokens
        formatted_parts.append(header)
        
        # Add memories
        for memory in memories:
            formatted_memory = format_func(memory)
            memory_tokens = self.count_tokens(formatted_memory)
            
            # Check if we have space
            if total_tokens + memory_tokens <= available_tokens:
                formatted_parts.append(formatted_memory)
                formatted_parts.append("\n")  # Separator
                total_tokens += memory_tokens + 1  # +1 for separator
                memories_included += 1
            else:
                memories_excluded += 1
                logger.debug(f"[MEMORY-CONTEXT-FORMATTER] Excluding memory {memory.get('id')} (tokens: {memory_tokens}, available: {available_tokens - total_tokens})")
        
        # Build final context
        formatted_context = "\n".join(formatted_parts).strip()
        
        # Verify final token count
        final_token_count = self.count_tokens(formatted_context)
        
        metadata = {
            "total_tokens": final_token_count,
            "available_tokens": available_tokens,
            "memories_included": memories_included,
            "memories_excluded": memories_excluded,
            "format_style_used": format_style,
            "model_name": self.model_name,
            "max_context_tokens": max_tokens
        }
        
        logger.info(
            f"[MEMORY-CONTEXT-FORMATTER] Formatted {memories_included}/{len(memories)} memories, "
            f"{final_token_count}/{available_tokens} tokens, style={format_style}"
        )
        
        return formatted_context, metadata
    
    def format_memories_summary(
        self,
        memories: List[Dict[str, Any]],
        max_tokens: int = 500
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Format a compact summary of memories.
        
        Args:
            memories: List of memory dictionaries
            max_tokens: Maximum tokens for summary
            
        Returns:
            (summary_string, metadata)
        """
        # Group by type
        by_type = {}
        for mem in memories:
            mem_type = mem.get("type", "unknown")
            if mem_type not in by_type:
                by_type[mem_type] = []
            by_type[mem_type].append(mem)
        
        # Build summary
        summary_parts = []
        total_tokens = 0
        
        summary_parts.append("=== MEMORY SUMMARY ===\n")
        total_tokens += self.count_tokens(summary_parts[-1])
        
        for mem_type, mems in by_type.items():
            type_summary = f"{mem_type.upper()}: {len(mems)} memories"
            
            # Add average trust/success
            if mem_type == "learning":
                avg_trust = sum(m.get("trust_score", 0.0) for m in mems) / len(mems)
                type_summary += f" (avg trust: {avg_trust:.2f})"
            elif mem_type == "procedural":
                avg_success = sum(m.get("memory", {}).success_rate if hasattr(m.get("memory"), "success_rate") else 0.0 for m in mems) / len(mems)
                type_summary += f" (avg success: {avg_success:.2%})"
            
            type_tokens = self.count_tokens(type_summary)
            if total_tokens + type_tokens <= max_tokens:
                summary_parts.append(type_summary)
                total_tokens += type_tokens + 1
            else:
                break
        
        summary = "\n".join(summary_parts).strip()
        
        metadata = {
            "total_tokens": self.count_tokens(summary),
            "memories_covered": len(memories),
            "types_covered": len(by_type)
        }
        
        return summary, metadata


def get_memory_context_formatter(
    model_name: str = "gpt-4",
    max_tokens: int = 4000
) -> MemoryContextFormatter:
    """Factory function to get memory context formatter."""
    return MemoryContextFormatter(model_name=model_name, default_max_tokens=max_tokens)
