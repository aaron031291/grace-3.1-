from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
import logging

logger = logging.getLogger(__name__)

class PrimitiveCategory(str, Enum):
    """Categories of primitive operations."""
    DISK_IO = "disk_io"
    NETWORK_IO = "network_io"
    CPU_COMPUTE = "cpu_compute"
    LLM_INFERENCE = "llm_inference"
    EMBEDDING = "embedding"
    DATABASE = "database"
    VECTOR_DB = "vector_db"
    MEMORY = "memory"


class PrimitiveType(str, Enum):
    """
    Specific primitive operation types.

    Each primitive represents an atomic, benchmarkable operation.
    """
    # Disk I/O primitives
    DISK_READ_SEQ = "disk_read_seq"          # Sequential read
    DISK_READ_RANDOM = "disk_read_random"    # Random read (seek-heavy)
    DISK_WRITE_SEQ = "disk_write_seq"        # Sequential write
    DISK_WRITE_RANDOM = "disk_write_random"  # Random write

    # Network I/O primitives
    NET_UPLOAD = "net_upload"                # Upload throughput
    NET_DOWNLOAD = "net_download"            # Download throughput
    NET_LATENCY = "net_latency"              # RTT latency
    NET_DNS = "net_dns"                      # DNS resolution

    # CPU compute primitives
    CPU_HASH_SHA256 = "cpu_hash_sha256"      # SHA256 hashing
    CPU_JSON_PARSE = "cpu_json_parse"        # JSON parsing
    CPU_JSON_SERIALIZE = "cpu_json_serialize" # JSON serialization
    CPU_GZIP_COMPRESS = "cpu_gzip_compress"  # Gzip compression
    CPU_GZIP_DECOMPRESS = "cpu_gzip_decompress"  # Gzip decompression
    CPU_REGEX_MATCH = "cpu_regex_match"      # Regex matching
    CPU_TEXT_CHUNK = "cpu_text_chunk"        # Text chunking

    # LLM inference primitives
    LLM_TOKENS_GENERATE = "llm_tokens_generate"  # Token generation (streaming)
    LLM_PROMPT_PROCESS = "llm_prompt_process"    # Prompt processing (TTFT)
    LLM_CONTEXT_LOAD = "llm_context_load"        # Context window loading

    # Embedding primitives
    EMBED_TEXT = "embed_text"                # Text embedding
    EMBED_BATCH = "embed_batch"              # Batch embedding

    # Database primitives
    DB_INSERT_SINGLE = "db_insert_single"    # Single record insert
    DB_INSERT_BATCH = "db_insert_batch"      # Batch insert
    DB_QUERY_SIMPLE = "db_query_simple"      # Simple query (indexed)
    DB_QUERY_COMPLEX = "db_query_complex"    # Complex query (joins, etc.)
    DB_QUERY_FULL_SCAN = "db_query_full_scan"  # Full table scan

    # Vector DB primitives
    VECTOR_INSERT = "vector_insert"          # Insert vectors
    VECTOR_SEARCH = "vector_search"          # Similarity search
    VECTOR_SEARCH_FILTERED = "vector_search_filtered"  # Filtered search

    # Memory primitives
    MEM_ALLOC = "mem_alloc"                  # Memory allocation
    MEM_COPY = "mem_copy"                    # Memory copy


class ScalingVariable(str, Enum):
    """Variables that primitives scale with."""
    BYTES = "bytes"                    # Data size in bytes
    TOKENS = "tokens"                  # Token count (LLM)
    NUM_RECORDS = "num_records"        # Database records
    NUM_VECTORS = "num_vectors"        # Vector count
    VECTOR_DIM = "vector_dim"          # Vector dimensions
    TOP_K = "top_k"                    # Top-K results
    CONCURRENCY = "concurrency"        # Parallel operations
    BLOCK_SIZE = "block_size"          # I/O block size
    COMPRESSION_RATIO = "compression_ratio"  # Estimated compression
    BATCH_SIZE = "batch_size"          # Batch size
    CONTEXT_LENGTH = "context_length"  # LLM context window


class CacheState(str, Enum):
    """Cache state for I/O operations."""
    COLD = "cold"        # No caching, first access
    WARM = "warm"        # Partial cache
    HOT = "hot"          # Fully cached


@dataclass
class ScalingSpec:
    """
    Specifies how a primitive scales with its variables.

    The cost model is: time = overhead + (size / throughput)
    Or equivalently: time = a + b * size

    Where:
    - a = fixed overhead (startup, open/close, handshake)
    - b = time per unit (inverse of throughput)
    """
    primary_variable: ScalingVariable
    secondary_variables: List[ScalingVariable] = field(default_factory=list)

    # Expected scaling behavior
    scaling_type: str = "linear"  # linear, log, sqrt, constant

    # Whether cache state significantly affects this primitive
    cache_sensitive: bool = False

    # Whether concurrency affects throughput
    concurrency_sensitive: bool = False

    # Typical overhead range (ms)
    typical_overhead_ms: tuple = (0.1, 10.0)

    # Typical throughput range (units/sec)
    typical_throughput_range: tuple = (1.0, 1000000.0)


@dataclass
class Primitive:
    """
    Definition of a primitive operation.

    Each primitive is an atomic, benchmarkable operation that
    can be composed into larger tasks.
    """
    primitive_type: PrimitiveType
    category: PrimitiveCategory
    name: str
    description: str

    # Scaling specification
    scaling: ScalingSpec

    # Unit of measurement for the primary variable
    unit: str  # e.g., "bytes", "tokens", "records"

    # Time unit for results
    time_unit: str = "ms"  # milliseconds

    # Benchmark configuration
    benchmark_sizes: List[int] = field(default_factory=list)  # Sizes to test
    warmup_iterations: int = 3
    measurement_iterations: int = 10

    # Context tags for filtering
    tags: List[str] = field(default_factory=list)

    # Whether this primitive is available on current system
    available: bool = True
    availability_reason: Optional[str] = None

    def __post_init__(self):
        if not self.benchmark_sizes:
            # Default benchmark sizes based on category
            if self.category == PrimitiveCategory.DISK_IO:
                self.benchmark_sizes = [1024, 10240, 102400, 1048576, 10485760]  # 1KB to 10MB
            elif self.category == PrimitiveCategory.NETWORK_IO:
                self.benchmark_sizes = [1024, 10240, 102400, 1048576]  # 1KB to 1MB
            elif self.category == PrimitiveCategory.CPU_COMPUTE:
                self.benchmark_sizes = [1024, 10240, 102400, 1048576]  # 1KB to 1MB
            elif self.category == PrimitiveCategory.LLM_INFERENCE:
                self.benchmark_sizes = [10, 50, 100, 500, 1000]  # tokens
            elif self.category == PrimitiveCategory.EMBEDDING:
                self.benchmark_sizes = [100, 500, 1000, 5000]  # tokens
            elif self.category in (PrimitiveCategory.DATABASE, PrimitiveCategory.VECTOR_DB):
                self.benchmark_sizes = [1, 10, 100, 1000]  # records


class PrimitiveRegistry:
    """
    Registry of all primitive operations.

    Provides the canonical catalog of primitives that can be
    benchmarked and composed into task estimates.
    """

    def __init__(self):
        self._primitives: Dict[PrimitiveType, Primitive] = {}
        self._by_category: Dict[PrimitiveCategory, List[Primitive]] = {}
        self._initialize_primitives()

    def _initialize_primitives(self):
        """Initialize the primitive catalog."""

        # ================================================================
        # DISK I/O PRIMITIVES
        # ================================================================

        self._register(Primitive(
            primitive_type=PrimitiveType.DISK_READ_SEQ,
            category=PrimitiveCategory.DISK_IO,
            name="Sequential Disk Read",
            description="Read data sequentially from disk",
            scaling=ScalingSpec(
                primary_variable=ScalingVariable.BYTES,
                secondary_variables=[ScalingVariable.BLOCK_SIZE],
                cache_sensitive=True,
                typical_overhead_ms=(0.5, 5.0),
                typical_throughput_range=(100_000_000, 500_000_000)  # 100-500 MB/s
            ),
            unit="bytes",
            tags=["disk", "read", "sequential"]
        ))

        self._register(Primitive(
            primitive_type=PrimitiveType.DISK_READ_RANDOM,
            category=PrimitiveCategory.DISK_IO,
            name="Random Disk Read",
            description="Read data with random seeks (simulates many small files)",
            scaling=ScalingSpec(
                primary_variable=ScalingVariable.BYTES,
                secondary_variables=[ScalingVariable.BLOCK_SIZE],
                cache_sensitive=True,
                typical_overhead_ms=(1.0, 20.0),
                typical_throughput_range=(10_000_000, 100_000_000)  # 10-100 MB/s
            ),
            unit="bytes",
            tags=["disk", "read", "random", "seek"]
        ))

        self._register(Primitive(
            primitive_type=PrimitiveType.DISK_WRITE_SEQ,
            category=PrimitiveCategory.DISK_IO,
            name="Sequential Disk Write",
            description="Write data sequentially to disk",
            scaling=ScalingSpec(
                primary_variable=ScalingVariable.BYTES,
                secondary_variables=[ScalingVariable.BLOCK_SIZE],
                cache_sensitive=False,
                typical_overhead_ms=(1.0, 10.0),
                typical_throughput_range=(50_000_000, 300_000_000)  # 50-300 MB/s
            ),
            unit="bytes",
            tags=["disk", "write", "sequential"]
        ))

        self._register(Primitive(
            primitive_type=PrimitiveType.DISK_WRITE_RANDOM,
            category=PrimitiveCategory.DISK_IO,
            name="Random Disk Write",
            description="Write data with random seeks",
            scaling=ScalingSpec(
                primary_variable=ScalingVariable.BYTES,
                secondary_variables=[ScalingVariable.BLOCK_SIZE],
                cache_sensitive=False,
                typical_overhead_ms=(2.0, 30.0),
                typical_throughput_range=(5_000_000, 50_000_000)  # 5-50 MB/s
            ),
            unit="bytes",
            tags=["disk", "write", "random", "seek"]
        ))

        # ================================================================
        # NETWORK I/O PRIMITIVES
        # ================================================================

        self._register(Primitive(
            primitive_type=PrimitiveType.NET_DOWNLOAD,
            category=PrimitiveCategory.NETWORK_IO,
            name="Network Download",
            description="Download data over network",
            scaling=ScalingSpec(
                primary_variable=ScalingVariable.BYTES,
                concurrency_sensitive=True,
                typical_overhead_ms=(10.0, 500.0),  # Connection setup
                typical_throughput_range=(1_000_000, 100_000_000)  # 1-100 MB/s
            ),
            unit="bytes",
            tags=["network", "download", "throughput"]
        ))

        self._register(Primitive(
            primitive_type=PrimitiveType.NET_UPLOAD,
            category=PrimitiveCategory.NETWORK_IO,
            name="Network Upload",
            description="Upload data over network",
            scaling=ScalingSpec(
                primary_variable=ScalingVariable.BYTES,
                concurrency_sensitive=True,
                typical_overhead_ms=(10.0, 500.0),
                typical_throughput_range=(500_000, 50_000_000)  # 0.5-50 MB/s
            ),
            unit="bytes",
            tags=["network", "upload", "throughput"]
        ))

        self._register(Primitive(
            primitive_type=PrimitiveType.NET_LATENCY,
            category=PrimitiveCategory.NETWORK_IO,
            name="Network Latency (RTT)",
            description="Round-trip time to server",
            scaling=ScalingSpec(
                primary_variable=ScalingVariable.BYTES,
                scaling_type="constant",  # Latency is mostly constant
                typical_overhead_ms=(1.0, 500.0),
                typical_throughput_range=(1.0, 1.0)  # N/A
            ),
            unit="requests",
            benchmark_sizes=[1],  # Just measure latency
            tags=["network", "latency", "rtt"]
        ))

        self._register(Primitive(
            primitive_type=PrimitiveType.NET_DNS,
            category=PrimitiveCategory.NETWORK_IO,
            name="DNS Resolution",
            description="DNS lookup time",
            scaling=ScalingSpec(
                primary_variable=ScalingVariable.BYTES,
                scaling_type="constant",
                cache_sensitive=True,
                typical_overhead_ms=(1.0, 100.0),
                typical_throughput_range=(1.0, 1.0)
            ),
            unit="lookups",
            benchmark_sizes=[1],
            tags=["network", "dns", "lookup"]
        ))

        # ================================================================
        # CPU COMPUTE PRIMITIVES
        # ================================================================

        self._register(Primitive(
            primitive_type=PrimitiveType.CPU_HASH_SHA256,
            category=PrimitiveCategory.CPU_COMPUTE,
            name="SHA256 Hash",
            description="Compute SHA256 hash of data",
            scaling=ScalingSpec(
                primary_variable=ScalingVariable.BYTES,
                typical_overhead_ms=(0.01, 0.1),
                typical_throughput_range=(100_000_000, 1_000_000_000)  # 100MB-1GB/s
            ),
            unit="bytes",
            tags=["cpu", "hash", "sha256", "crypto"]
        ))

        self._register(Primitive(
            primitive_type=PrimitiveType.CPU_JSON_PARSE,
            category=PrimitiveCategory.CPU_COMPUTE,
            name="JSON Parse",
            description="Parse JSON string to object",
            scaling=ScalingSpec(
                primary_variable=ScalingVariable.BYTES,
                typical_overhead_ms=(0.01, 0.5),
                typical_throughput_range=(50_000_000, 500_000_000)  # 50-500 MB/s
            ),
            unit="bytes",
            tags=["cpu", "json", "parse", "deserialize"]
        ))

        self._register(Primitive(
            primitive_type=PrimitiveType.CPU_JSON_SERIALIZE,
            category=PrimitiveCategory.CPU_COMPUTE,
            name="JSON Serialize",
            description="Serialize object to JSON string",
            scaling=ScalingSpec(
                primary_variable=ScalingVariable.BYTES,
                typical_overhead_ms=(0.01, 0.5),
                typical_throughput_range=(50_000_000, 300_000_000)  # 50-300 MB/s
            ),
            unit="bytes",
            tags=["cpu", "json", "serialize"]
        ))

        self._register(Primitive(
            primitive_type=PrimitiveType.CPU_GZIP_COMPRESS,
            category=PrimitiveCategory.CPU_COMPUTE,
            name="Gzip Compress",
            description="Compress data with gzip",
            scaling=ScalingSpec(
                primary_variable=ScalingVariable.BYTES,
                secondary_variables=[ScalingVariable.COMPRESSION_RATIO],
                typical_overhead_ms=(0.1, 1.0),
                typical_throughput_range=(10_000_000, 100_000_000)  # 10-100 MB/s
            ),
            unit="bytes",
            tags=["cpu", "gzip", "compress"]
        ))

        self._register(Primitive(
            primitive_type=PrimitiveType.CPU_GZIP_DECOMPRESS,
            category=PrimitiveCategory.CPU_COMPUTE,
            name="Gzip Decompress",
            description="Decompress gzip data",
            scaling=ScalingSpec(
                primary_variable=ScalingVariable.BYTES,
                typical_overhead_ms=(0.1, 0.5),
                typical_throughput_range=(100_000_000, 500_000_000)  # 100-500 MB/s
            ),
            unit="bytes",
            tags=["cpu", "gzip", "decompress"]
        ))

        self._register(Primitive(
            primitive_type=PrimitiveType.CPU_REGEX_MATCH,
            category=PrimitiveCategory.CPU_COMPUTE,
            name="Regex Match",
            description="Match regex pattern against text",
            scaling=ScalingSpec(
                primary_variable=ScalingVariable.BYTES,
                typical_overhead_ms=(0.01, 0.5),
                typical_throughput_range=(10_000_000, 200_000_000)  # 10-200 MB/s
            ),
            unit="bytes",
            tags=["cpu", "regex", "pattern", "text"]
        ))

        self._register(Primitive(
            primitive_type=PrimitiveType.CPU_TEXT_CHUNK,
            category=PrimitiveCategory.CPU_COMPUTE,
            name="Text Chunking",
            description="Split text into chunks with overlap",
            scaling=ScalingSpec(
                primary_variable=ScalingVariable.BYTES,
                typical_overhead_ms=(0.1, 1.0),
                typical_throughput_range=(50_000_000, 200_000_000)  # 50-200 MB/s
            ),
            unit="bytes",
            tags=["cpu", "text", "chunk", "split"]
        ))

        # ================================================================
        # LLM INFERENCE PRIMITIVES
        # ================================================================

        self._register(Primitive(
            primitive_type=PrimitiveType.LLM_TOKENS_GENERATE,
            category=PrimitiveCategory.LLM_INFERENCE,
            name="LLM Token Generation",
            description="Generate tokens (streaming output)",
            scaling=ScalingSpec(
                primary_variable=ScalingVariable.TOKENS,
                secondary_variables=[ScalingVariable.CONTEXT_LENGTH],
                typical_overhead_ms=(100.0, 2000.0),  # TTFT
                typical_throughput_range=(10.0, 100.0)  # 10-100 tokens/sec
            ),
            unit="tokens",
            tags=["llm", "generate", "inference", "tokens"]
        ))

        self._register(Primitive(
            primitive_type=PrimitiveType.LLM_PROMPT_PROCESS,
            category=PrimitiveCategory.LLM_INFERENCE,
            name="LLM Prompt Processing",
            description="Process input prompt (time to first token)",
            scaling=ScalingSpec(
                primary_variable=ScalingVariable.TOKENS,
                secondary_variables=[ScalingVariable.CONTEXT_LENGTH],
                typical_overhead_ms=(50.0, 500.0),
                typical_throughput_range=(100.0, 10000.0)  # 100-10000 tokens/sec prompt processing
            ),
            unit="tokens",
            tags=["llm", "prompt", "ttft", "inference"]
        ))

        self._register(Primitive(
            primitive_type=PrimitiveType.LLM_CONTEXT_LOAD,
            category=PrimitiveCategory.LLM_INFERENCE,
            name="LLM Context Load",
            description="Load context into model",
            scaling=ScalingSpec(
                primary_variable=ScalingVariable.TOKENS,
                cache_sensitive=True,
                typical_overhead_ms=(10.0, 100.0),
                typical_throughput_range=(1000.0, 50000.0)  # tokens/sec
            ),
            unit="tokens",
            tags=["llm", "context", "load"]
        ))

        # ================================================================
        # EMBEDDING PRIMITIVES
        # ================================================================

        self._register(Primitive(
            primitive_type=PrimitiveType.EMBED_TEXT,
            category=PrimitiveCategory.EMBEDDING,
            name="Text Embedding",
            description="Generate embedding vector for text",
            scaling=ScalingSpec(
                primary_variable=ScalingVariable.TOKENS,
                typical_overhead_ms=(10.0, 100.0),
                typical_throughput_range=(100.0, 5000.0)  # 100-5000 tokens/sec
            ),
            unit="tokens",
            benchmark_sizes=[50, 100, 256, 512],  # Common chunk sizes
            tags=["embedding", "vector", "text"]
        ))

        self._register(Primitive(
            primitive_type=PrimitiveType.EMBED_BATCH,
            category=PrimitiveCategory.EMBEDDING,
            name="Batch Text Embedding",
            description="Generate embeddings for multiple texts",
            scaling=ScalingSpec(
                primary_variable=ScalingVariable.TOKENS,
                secondary_variables=[ScalingVariable.BATCH_SIZE],
                concurrency_sensitive=True,
                typical_overhead_ms=(20.0, 200.0),
                typical_throughput_range=(500.0, 20000.0)  # tokens/sec with batching
            ),
            unit="tokens",
            tags=["embedding", "vector", "batch"]
        ))

        # ================================================================
        # DATABASE PRIMITIVES
        # ================================================================

        self._register(Primitive(
            primitive_type=PrimitiveType.DB_INSERT_SINGLE,
            category=PrimitiveCategory.DATABASE,
            name="Single Record Insert",
            description="Insert single record into database",
            scaling=ScalingSpec(
                primary_variable=ScalingVariable.NUM_RECORDS,
                scaling_type="constant",
                typical_overhead_ms=(0.5, 10.0),
                typical_throughput_range=(100.0, 10000.0)  # records/sec
            ),
            unit="records",
            benchmark_sizes=[1],
            tags=["database", "insert", "single"]
        ))

        self._register(Primitive(
            primitive_type=PrimitiveType.DB_INSERT_BATCH,
            category=PrimitiveCategory.DATABASE,
            name="Batch Record Insert",
            description="Insert multiple records in batch",
            scaling=ScalingSpec(
                primary_variable=ScalingVariable.NUM_RECORDS,
                secondary_variables=[ScalingVariable.BATCH_SIZE],
                typical_overhead_ms=(5.0, 50.0),
                typical_throughput_range=(1000.0, 100000.0)  # records/sec
            ),
            unit="records",
            tags=["database", "insert", "batch"]
        ))

        self._register(Primitive(
            primitive_type=PrimitiveType.DB_QUERY_SIMPLE,
            category=PrimitiveCategory.DATABASE,
            name="Simple Query (Indexed)",
            description="Query with indexed lookup",
            scaling=ScalingSpec(
                primary_variable=ScalingVariable.NUM_RECORDS,
                scaling_type="log",  # O(log n) with index
                typical_overhead_ms=(0.1, 5.0),
                typical_throughput_range=(1000.0, 100000.0)  # queries/sec
            ),
            unit="records",
            tags=["database", "query", "indexed"]
        ))

        self._register(Primitive(
            primitive_type=PrimitiveType.DB_QUERY_COMPLEX,
            category=PrimitiveCategory.DATABASE,
            name="Complex Query (Joins)",
            description="Query with joins or aggregations",
            scaling=ScalingSpec(
                primary_variable=ScalingVariable.NUM_RECORDS,
                typical_overhead_ms=(5.0, 100.0),
                typical_throughput_range=(10.0, 1000.0)  # queries/sec
            ),
            unit="records",
            tags=["database", "query", "join", "complex"]
        ))

        self._register(Primitive(
            primitive_type=PrimitiveType.DB_QUERY_FULL_SCAN,
            category=PrimitiveCategory.DATABASE,
            name="Full Table Scan",
            description="Query requiring full table scan",
            scaling=ScalingSpec(
                primary_variable=ScalingVariable.NUM_RECORDS,
                typical_overhead_ms=(10.0, 100.0),
                typical_throughput_range=(10000.0, 1000000.0)  # records/sec scanned
            ),
            unit="records",
            tags=["database", "query", "scan"]
        ))

        # ================================================================
        # VECTOR DB PRIMITIVES
        # ================================================================

        self._register(Primitive(
            primitive_type=PrimitiveType.VECTOR_INSERT,
            category=PrimitiveCategory.VECTOR_DB,
            name="Vector Insert",
            description="Insert vectors into vector database",
            scaling=ScalingSpec(
                primary_variable=ScalingVariable.NUM_VECTORS,
                secondary_variables=[ScalingVariable.VECTOR_DIM],
                typical_overhead_ms=(1.0, 20.0),
                typical_throughput_range=(100.0, 10000.0)  # vectors/sec
            ),
            unit="vectors",
            tags=["vector", "insert", "index"]
        ))

        self._register(Primitive(
            primitive_type=PrimitiveType.VECTOR_SEARCH,
            category=PrimitiveCategory.VECTOR_DB,
            name="Vector Similarity Search",
            description="Find similar vectors (approximate nearest neighbors)",
            scaling=ScalingSpec(
                primary_variable=ScalingVariable.NUM_VECTORS,
                secondary_variables=[ScalingVariable.VECTOR_DIM, ScalingVariable.TOP_K],
                scaling_type="log",  # O(log n) with HNSW
                cache_sensitive=True,
                typical_overhead_ms=(1.0, 50.0),
                typical_throughput_range=(100.0, 10000.0)  # queries/sec
            ),
            unit="vectors",
            tags=["vector", "search", "similarity", "ann"]
        ))

        self._register(Primitive(
            primitive_type=PrimitiveType.VECTOR_SEARCH_FILTERED,
            category=PrimitiveCategory.VECTOR_DB,
            name="Filtered Vector Search",
            description="Vector search with metadata filters",
            scaling=ScalingSpec(
                primary_variable=ScalingVariable.NUM_VECTORS,
                secondary_variables=[ScalingVariable.VECTOR_DIM, ScalingVariable.TOP_K],
                typical_overhead_ms=(5.0, 100.0),
                typical_throughput_range=(50.0, 5000.0)  # queries/sec
            ),
            unit="vectors",
            tags=["vector", "search", "filter", "metadata"]
        ))

        # ================================================================
        # MEMORY PRIMITIVES
        # ================================================================

        self._register(Primitive(
            primitive_type=PrimitiveType.MEM_ALLOC,
            category=PrimitiveCategory.MEMORY,
            name="Memory Allocation",
            description="Allocate memory buffer",
            scaling=ScalingSpec(
                primary_variable=ScalingVariable.BYTES,
                typical_overhead_ms=(0.001, 0.1),
                typical_throughput_range=(1_000_000_000, 100_000_000_000)  # 1-100 GB/s
            ),
            unit="bytes",
            tags=["memory", "alloc"]
        ))

        self._register(Primitive(
            primitive_type=PrimitiveType.MEM_COPY,
            category=PrimitiveCategory.MEMORY,
            name="Memory Copy",
            description="Copy data in memory",
            scaling=ScalingSpec(
                primary_variable=ScalingVariable.BYTES,
                typical_overhead_ms=(0.001, 0.01),
                typical_throughput_range=(5_000_000_000, 50_000_000_000)  # 5-50 GB/s
            ),
            unit="bytes",
            tags=["memory", "copy"]
        ))

        logger.info(f"[TIMESENSE] Initialized {len(self._primitives)} primitives in {len(self._by_category)} categories")

    def _register(self, primitive: Primitive):
        """Register a primitive in the catalog."""
        self._primitives[primitive.primitive_type] = primitive

        if primitive.category not in self._by_category:
            self._by_category[primitive.category] = []
        self._by_category[primitive.category].append(primitive)

    def get(self, primitive_type: PrimitiveType) -> Optional[Primitive]:
        """Get primitive by type."""
        return self._primitives.get(primitive_type)

    def get_by_category(self, category: PrimitiveCategory) -> List[Primitive]:
        """Get all primitives in a category."""
        return self._by_category.get(category, [])

    def get_all(self) -> List[Primitive]:
        """Get all registered primitives."""
        return list(self._primitives.values())

    def get_available(self) -> List[Primitive]:
        """Get all available primitives on this system."""
        return [p for p in self._primitives.values() if p.available]

    def search_by_tags(self, tags: List[str]) -> List[Primitive]:
        """Find primitives matching any of the given tags."""
        return [
            p for p in self._primitives.values()
            if any(tag in p.tags for tag in tags)
        ]

    def get_categories(self) -> List[PrimitiveCategory]:
        """Get all primitive categories."""
        return list(self._by_category.keys())


# Global registry instance
_primitive_registry: Optional[PrimitiveRegistry] = None


def get_primitive_registry() -> PrimitiveRegistry:
    """Get or create the global primitive registry."""
    global _primitive_registry
    if _primitive_registry is None:
        _primitive_registry = PrimitiveRegistry()
    return _primitive_registry
