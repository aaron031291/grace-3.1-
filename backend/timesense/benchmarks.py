"""
Calibration Benchmarking System for TimeSense

Runs empirical benchmarks for primitive operations to calibrate
Grace's time profiles. This is how Grace learns "on this machine,
reading 1 MB from disk takes ~X ms."

The calibration service:
1. Runs startup benchmarks for core primitives
2. Periodically recalibrates stale profiles
3. Adapts to system conditions (load, cache state)
"""

import os
import time
import json
import gzip
import hashlib
import tempfile
import random
import string
import re
import asyncio
import logging
import platform
import psutil
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any, Callable
from dataclasses import dataclass, field

from timesense.primitives import (
    PrimitiveType,
    PrimitiveCategory,
    Primitive,
    PrimitiveRegistry,
    get_primitive_registry,
    CacheState
)
from timesense.profiles import TimeProfile, ProfileManager, DistributionStats

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Result of a single benchmark run."""
    primitive_type: PrimitiveType
    size: int
    duration_ms: float
    throughput: float  # units/sec
    cache_state: CacheState = CacheState.WARM
    iteration: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CalibrationReport:
    """Report from a calibration session."""
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    primitives_calibrated: int
    measurements_collected: int
    profiles_updated: int
    errors: List[str]
    system_info: Dict[str, Any]


class BenchmarkRunner:
    """
    Runs individual benchmark tests for primitives.

    Each benchmark method returns a list of (size, duration_ms) tuples.
    """

    def __init__(self, temp_dir: Optional[str] = None):
        self.temp_dir = temp_dir or tempfile.gettempdir()
        self._test_files: Dict[int, str] = {}

    def _generate_test_data(self, size: int) -> bytes:
        """Generate random test data of specified size."""
        # Use random data to avoid compression benefits
        return os.urandom(size)

    def _generate_test_json(self, size: int) -> str:
        """Generate JSON string of approximately specified size."""
        # Create nested structure
        items = []
        item_size = 100
        num_items = max(1, size // item_size)

        for i in range(num_items):
            items.append({
                'id': i,
                'name': ''.join(random.choices(string.ascii_letters, k=20)),
                'value': random.random(),
                'tags': [''.join(random.choices(string.ascii_lowercase, k=5)) for _ in range(3)]
            })

        return json.dumps({'items': items})

    def _create_test_file(self, size: int) -> str:
        """Create a test file of specified size."""
        if size in self._test_files:
            return self._test_files[size]

        filepath = os.path.join(self.temp_dir, f'timesense_bench_{size}.dat')
        data = self._generate_test_data(size)

        with open(filepath, 'wb') as f:
            f.write(data)

        self._test_files[size] = filepath
        return filepath

    def cleanup(self):
        """Remove test files."""
        for filepath in self._test_files.values():
            try:
                os.remove(filepath)
            except Exception:
                pass
        self._test_files.clear()

    # ================================================================
    # DISK I/O BENCHMARKS
    # ================================================================

    def benchmark_disk_read_seq(
        self,
        sizes: List[int],
        iterations: int = 5,
        warmup: int = 2
    ) -> List[BenchmarkResult]:
        """Benchmark sequential disk read."""
        results = []

        for size in sizes:
            filepath = self._create_test_file(size)

            # Warmup (populate page cache)
            for _ in range(warmup):
                with open(filepath, 'rb') as f:
                    _ = f.read()

            # Cold read (drop cache simulation - best effort)
            # On Linux, would use: os.system(f"sync; echo 3 > /proc/sys/vm/drop_caches")
            # For portability, we skip actual cache drop

            # Warm read measurements
            for i in range(iterations):
                start = time.perf_counter()
                with open(filepath, 'rb') as f:
                    _ = f.read()
                duration_ms = (time.perf_counter() - start) * 1000

                throughput = (size / duration_ms) * 1000  # bytes/sec

                results.append(BenchmarkResult(
                    primitive_type=PrimitiveType.DISK_READ_SEQ,
                    size=size,
                    duration_ms=duration_ms,
                    throughput=throughput,
                    cache_state=CacheState.WARM,
                    iteration=i
                ))

        return results

    def benchmark_disk_write_seq(
        self,
        sizes: List[int],
        iterations: int = 5,
        warmup: int = 1
    ) -> List[BenchmarkResult]:
        """Benchmark sequential disk write."""
        results = []

        for size in sizes:
            data = self._generate_test_data(size)
            filepath = os.path.join(self.temp_dir, f'timesense_write_{size}.dat')

            # Warmup
            for _ in range(warmup):
                with open(filepath, 'wb') as f:
                    f.write(data)
                    f.flush()
                    os.fsync(f.fileno())

            # Measurements
            for i in range(iterations):
                start = time.perf_counter()
                with open(filepath, 'wb') as f:
                    f.write(data)
                    f.flush()
                    os.fsync(f.fileno())  # Ensure data is on disk
                duration_ms = (time.perf_counter() - start) * 1000

                throughput = (size / duration_ms) * 1000

                results.append(BenchmarkResult(
                    primitive_type=PrimitiveType.DISK_WRITE_SEQ,
                    size=size,
                    duration_ms=duration_ms,
                    throughput=throughput,
                    iteration=i
                ))

            # Cleanup
            try:
                os.remove(filepath)
            except Exception:
                pass

        return results

    # ================================================================
    # CPU COMPUTE BENCHMARKS
    # ================================================================

    def benchmark_cpu_hash_sha256(
        self,
        sizes: List[int],
        iterations: int = 10,
        warmup: int = 3
    ) -> List[BenchmarkResult]:
        """Benchmark SHA256 hashing."""
        results = []

        for size in sizes:
            data = self._generate_test_data(size)

            # Warmup
            for _ in range(warmup):
                hashlib.sha256(data).hexdigest()

            # Measurements
            for i in range(iterations):
                start = time.perf_counter()
                hashlib.sha256(data).hexdigest()
                duration_ms = (time.perf_counter() - start) * 1000

                throughput = (size / duration_ms) * 1000

                results.append(BenchmarkResult(
                    primitive_type=PrimitiveType.CPU_HASH_SHA256,
                    size=size,
                    duration_ms=duration_ms,
                    throughput=throughput,
                    iteration=i
                ))

        return results

    def benchmark_cpu_json_parse(
        self,
        sizes: List[int],
        iterations: int = 10,
        warmup: int = 3
    ) -> List[BenchmarkResult]:
        """Benchmark JSON parsing."""
        results = []

        for size in sizes:
            json_str = self._generate_test_json(size)
            actual_size = len(json_str.encode())

            # Warmup
            for _ in range(warmup):
                json.loads(json_str)

            # Measurements
            for i in range(iterations):
                start = time.perf_counter()
                json.loads(json_str)
                duration_ms = (time.perf_counter() - start) * 1000

                throughput = (actual_size / duration_ms) * 1000

                results.append(BenchmarkResult(
                    primitive_type=PrimitiveType.CPU_JSON_PARSE,
                    size=actual_size,
                    duration_ms=duration_ms,
                    throughput=throughput,
                    iteration=i
                ))

        return results

    def benchmark_cpu_json_serialize(
        self,
        sizes: List[int],
        iterations: int = 10,
        warmup: int = 3
    ) -> List[BenchmarkResult]:
        """Benchmark JSON serialization."""
        results = []

        for size in sizes:
            json_str = self._generate_test_json(size)
            obj = json.loads(json_str)
            actual_size = len(json_str.encode())

            # Warmup
            for _ in range(warmup):
                json.dumps(obj)

            # Measurements
            for i in range(iterations):
                start = time.perf_counter()
                json.dumps(obj)
                duration_ms = (time.perf_counter() - start) * 1000

                throughput = (actual_size / duration_ms) * 1000

                results.append(BenchmarkResult(
                    primitive_type=PrimitiveType.CPU_JSON_SERIALIZE,
                    size=actual_size,
                    duration_ms=duration_ms,
                    throughput=throughput,
                    iteration=i
                ))

        return results

    def benchmark_cpu_gzip_compress(
        self,
        sizes: List[int],
        iterations: int = 5,
        warmup: int = 2
    ) -> List[BenchmarkResult]:
        """Benchmark gzip compression."""
        results = []

        for size in sizes:
            # Use semi-compressible data (repeated patterns)
            pattern = self._generate_test_data(1024)
            data = pattern * (size // 1024 + 1)
            data = data[:size]

            # Warmup
            for _ in range(warmup):
                gzip.compress(data)

            # Measurements
            for i in range(iterations):
                start = time.perf_counter()
                compressed = gzip.compress(data)
                duration_ms = (time.perf_counter() - start) * 1000

                throughput = (size / duration_ms) * 1000
                compression_ratio = len(compressed) / size

                results.append(BenchmarkResult(
                    primitive_type=PrimitiveType.CPU_GZIP_COMPRESS,
                    size=size,
                    duration_ms=duration_ms,
                    throughput=throughput,
                    iteration=i,
                    metadata={'compression_ratio': compression_ratio}
                ))

        return results

    def benchmark_cpu_gzip_decompress(
        self,
        sizes: List[int],
        iterations: int = 5,
        warmup: int = 2
    ) -> List[BenchmarkResult]:
        """Benchmark gzip decompression."""
        results = []

        for size in sizes:
            # Create compressed data
            pattern = self._generate_test_data(1024)
            data = pattern * (size // 1024 + 1)
            data = data[:size]
            compressed = gzip.compress(data)

            # Warmup
            for _ in range(warmup):
                gzip.decompress(compressed)

            # Measurements
            for i in range(iterations):
                start = time.perf_counter()
                gzip.decompress(compressed)
                duration_ms = (time.perf_counter() - start) * 1000

                throughput = (size / duration_ms) * 1000  # Output size

                results.append(BenchmarkResult(
                    primitive_type=PrimitiveType.CPU_GZIP_DECOMPRESS,
                    size=size,
                    duration_ms=duration_ms,
                    throughput=throughput,
                    iteration=i
                ))

        return results

    def benchmark_cpu_regex_match(
        self,
        sizes: List[int],
        iterations: int = 10,
        warmup: int = 3
    ) -> List[BenchmarkResult]:
        """Benchmark regex matching."""
        results = []

        # Compile pattern once
        pattern = re.compile(r'\b[A-Za-z]+\b')

        for size in sizes:
            # Generate text with words
            words = [''.join(random.choices(string.ascii_letters, k=random.randint(3, 10)))
                     for _ in range(size // 10)]
            text = ' '.join(words)
            actual_size = len(text.encode())

            # Warmup
            for _ in range(warmup):
                pattern.findall(text)

            # Measurements
            for i in range(iterations):
                start = time.perf_counter()
                pattern.findall(text)
                duration_ms = (time.perf_counter() - start) * 1000

                throughput = (actual_size / duration_ms) * 1000

                results.append(BenchmarkResult(
                    primitive_type=PrimitiveType.CPU_REGEX_MATCH,
                    size=actual_size,
                    duration_ms=duration_ms,
                    throughput=throughput,
                    iteration=i
                ))

        return results

    def benchmark_cpu_text_chunk(
        self,
        sizes: List[int],
        iterations: int = 10,
        warmup: int = 3,
        chunk_size: int = 512,
        overlap: int = 50
    ) -> List[BenchmarkResult]:
        """Benchmark text chunking."""
        results = []

        for size in sizes:
            # Generate text
            words = [''.join(random.choices(string.ascii_letters, k=random.randint(3, 10)))
                     for _ in range(size // 10)]
            text = ' '.join(words)
            actual_size = len(text.encode())

            def chunk_text(t: str, cs: int, ov: int) -> List[str]:
                chunks = []
                start = 0
                while start < len(t):
                    end = start + cs
                    chunks.append(t[start:end])
                    start = end - ov
                return chunks

            # Warmup
            for _ in range(warmup):
                chunk_text(text, chunk_size, overlap)

            # Measurements
            for i in range(iterations):
                start = time.perf_counter()
                chunks = chunk_text(text, chunk_size, overlap)
                duration_ms = (time.perf_counter() - start) * 1000

                throughput = (actual_size / duration_ms) * 1000

                results.append(BenchmarkResult(
                    primitive_type=PrimitiveType.CPU_TEXT_CHUNK,
                    size=actual_size,
                    duration_ms=duration_ms,
                    throughput=throughput,
                    iteration=i,
                    metadata={'num_chunks': len(chunks)}
                ))

        return results

    # ================================================================
    # MEMORY BENCHMARKS
    # ================================================================

    def benchmark_mem_copy(
        self,
        sizes: List[int],
        iterations: int = 10,
        warmup: int = 3
    ) -> List[BenchmarkResult]:
        """Benchmark memory copy."""
        results = []

        for size in sizes:
            data = self._generate_test_data(size)

            # Warmup
            for _ in range(warmup):
                _ = bytes(data)

            # Measurements
            for i in range(iterations):
                start = time.perf_counter()
                _ = bytes(data)
                duration_ms = (time.perf_counter() - start) * 1000

                throughput = (size / duration_ms) * 1000

                results.append(BenchmarkResult(
                    primitive_type=PrimitiveType.MEM_COPY,
                    size=size,
                    duration_ms=duration_ms,
                    throughput=throughput,
                    iteration=i
                ))

        return results


class CalibrationService:
    """
    Service that runs calibration benchmarks and updates profiles.

    This is the "startup calibration" that gives Grace empirical
    knowledge of how long operations take on this machine.
    """

    def __init__(
        self,
        profile_manager: ProfileManager,
        primitive_registry: Optional[PrimitiveRegistry] = None
    ):
        self.profile_manager = profile_manager
        self.primitive_registry = primitive_registry or get_primitive_registry()
        self.runner = BenchmarkRunner()
        self._last_calibration: Optional[datetime] = None
        self._calibration_in_progress = False

    def get_system_info(self) -> Dict[str, Any]:
        """Collect system information for context."""
        try:
            cpu_freq = psutil.cpu_freq()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            return {
                'platform': platform.system(),
                'platform_version': platform.version(),
                'processor': platform.processor(),
                'cpu_count': psutil.cpu_count(),
                'cpu_freq_mhz': cpu_freq.current if cpu_freq else None,
                'memory_total_gb': memory.total / (1024 ** 3),
                'memory_available_gb': memory.available / (1024 ** 3),
                'disk_total_gb': disk.total / (1024 ** 3),
                'disk_free_gb': disk.free / (1024 ** 3),
                'python_version': platform.python_version()
            }
        except Exception as e:
            logger.warning(f"[TIMESENSE] Failed to get system info: {e}")
            return {'error': str(e)}

    def run_startup_calibration(
        self,
        quick: bool = False
    ) -> CalibrationReport:
        """
        Run startup calibration for core primitives.

        Args:
            quick: If True, run minimal benchmarks (faster startup)

        Returns:
            CalibrationReport with results
        """
        if self._calibration_in_progress:
            raise RuntimeError("Calibration already in progress")

        self._calibration_in_progress = True
        started_at = datetime.utcnow()
        errors = []
        measurements_collected = 0
        profiles_updated = 0

        logger.info("[TIMESENSE] Starting calibration benchmarks...")
        system_info = self.get_system_info()

        # Define benchmark sizes based on mode
        if quick:
            disk_sizes = [1024, 102400, 1048576]  # 1KB, 100KB, 1MB
            cpu_sizes = [1024, 102400]  # 1KB, 100KB
            iterations = 3
        else:
            disk_sizes = [1024, 10240, 102400, 1048576, 10485760]  # 1KB to 10MB
            cpu_sizes = [1024, 10240, 102400, 1048576]  # 1KB to 1MB
            iterations = 5

        # Run disk benchmarks
        try:
            logger.info("[TIMESENSE] Benchmarking disk read (sequential)...")
            results = self.runner.benchmark_disk_read_seq(disk_sizes, iterations)
            self._process_results(results)
            measurements_collected += len(results)
            profiles_updated += 1
        except Exception as e:
            errors.append(f"disk_read_seq: {e}")
            logger.error(f"[TIMESENSE] Disk read benchmark failed: {e}")

        try:
            logger.info("[TIMESENSE] Benchmarking disk write (sequential)...")
            results = self.runner.benchmark_disk_write_seq(disk_sizes, iterations)
            self._process_results(results)
            measurements_collected += len(results)
            profiles_updated += 1
        except Exception as e:
            errors.append(f"disk_write_seq: {e}")
            logger.error(f"[TIMESENSE] Disk write benchmark failed: {e}")

        # Run CPU benchmarks
        try:
            logger.info("[TIMESENSE] Benchmarking SHA256 hash...")
            results = self.runner.benchmark_cpu_hash_sha256(cpu_sizes, iterations)
            self._process_results(results)
            measurements_collected += len(results)
            profiles_updated += 1
        except Exception as e:
            errors.append(f"cpu_hash_sha256: {e}")
            logger.error(f"[TIMESENSE] SHA256 benchmark failed: {e}")

        try:
            logger.info("[TIMESENSE] Benchmarking JSON parse...")
            results = self.runner.benchmark_cpu_json_parse(cpu_sizes, iterations)
            self._process_results(results)
            measurements_collected += len(results)
            profiles_updated += 1
        except Exception as e:
            errors.append(f"cpu_json_parse: {e}")
            logger.error(f"[TIMESENSE] JSON parse benchmark failed: {e}")

        try:
            logger.info("[TIMESENSE] Benchmarking JSON serialize...")
            results = self.runner.benchmark_cpu_json_serialize(cpu_sizes, iterations)
            self._process_results(results)
            measurements_collected += len(results)
            profiles_updated += 1
        except Exception as e:
            errors.append(f"cpu_json_serialize: {e}")
            logger.error(f"[TIMESENSE] JSON serialize benchmark failed: {e}")

        if not quick:
            try:
                logger.info("[TIMESENSE] Benchmarking gzip compress...")
                results = self.runner.benchmark_cpu_gzip_compress(cpu_sizes, iterations)
                self._process_results(results)
                measurements_collected += len(results)
                profiles_updated += 1
            except Exception as e:
                errors.append(f"cpu_gzip_compress: {e}")

            try:
                logger.info("[TIMESENSE] Benchmarking gzip decompress...")
                results = self.runner.benchmark_cpu_gzip_decompress(cpu_sizes, iterations)
                self._process_results(results)
                measurements_collected += len(results)
                profiles_updated += 1
            except Exception as e:
                errors.append(f"cpu_gzip_decompress: {e}")

            try:
                logger.info("[TIMESENSE] Benchmarking regex match...")
                results = self.runner.benchmark_cpu_regex_match(cpu_sizes, iterations)
                self._process_results(results)
                measurements_collected += len(results)
                profiles_updated += 1
            except Exception as e:
                errors.append(f"cpu_regex_match: {e}")

            try:
                logger.info("[TIMESENSE] Benchmarking text chunking...")
                results = self.runner.benchmark_cpu_text_chunk(cpu_sizes, iterations)
                self._process_results(results)
                measurements_collected += len(results)
                profiles_updated += 1
            except Exception as e:
                errors.append(f"cpu_text_chunk: {e}")

            try:
                logger.info("[TIMESENSE] Benchmarking memory copy...")
                results = self.runner.benchmark_mem_copy(cpu_sizes, iterations)
                self._process_results(results)
                measurements_collected += len(results)
                profiles_updated += 1
            except Exception as e:
                errors.append(f"mem_copy: {e}")

        # Cleanup
        self.runner.cleanup()

        completed_at = datetime.utcnow()
        duration = (completed_at - started_at).total_seconds()

        self._last_calibration = completed_at
        self._calibration_in_progress = False

        report = CalibrationReport(
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration,
            primitives_calibrated=profiles_updated,
            measurements_collected=measurements_collected,
            profiles_updated=profiles_updated,
            errors=errors,
            system_info=system_info
        )

        logger.info(
            f"[TIMESENSE] Calibration complete: "
            f"{profiles_updated} primitives, {measurements_collected} measurements, "
            f"{duration:.1f}s, {len(errors)} errors"
        )

        return report

    def _process_results(self, results: List[BenchmarkResult]):
        """Process benchmark results and update profiles."""
        if not results:
            return

        # Group by primitive type
        primitive_type = results[0].primitive_type
        primitive = self.primitive_registry.get(primitive_type)

        measurements = [(r.size, r.duration_ms) for r in results]
        unit = primitive.unit if primitive else 'bytes'

        self.profile_manager.update_profile(
            primitive_type=primitive_type,
            measurements=measurements,
            unit=unit
        )

    async def calibrate_llm(
        self,
        generate_func: Callable,
        model_name: str,
        token_counts: List[int] = [10, 50, 100, 200]
    ):
        """
        Calibrate LLM token generation speed.

        Args:
            generate_func: Async function that generates tokens
            model_name: Name of the model being calibrated
            token_counts: Number of tokens to generate for each test
        """
        logger.info(f"[TIMESENSE] Calibrating LLM: {model_name}")

        measurements = []

        for target_tokens in token_counts:
            try:
                # Measure token generation
                start = time.perf_counter()
                result = await generate_func(max_tokens=target_tokens)
                duration_ms = (time.perf_counter() - start) * 1000

                # Get actual token count if available
                actual_tokens = result.get('tokens', target_tokens) if isinstance(result, dict) else target_tokens

                measurements.append((actual_tokens, duration_ms))
                logger.debug(f"[TIMESENSE] LLM {target_tokens} tokens: {duration_ms:.1f}ms")

            except Exception as e:
                logger.warning(f"[TIMESENSE] LLM calibration error: {e}")

        if measurements:
            self.profile_manager.update_profile(
                primitive_type=PrimitiveType.LLM_TOKENS_GENERATE,
                measurements=measurements,
                model_name=model_name,
                unit='tokens'
            )

    async def calibrate_embedding(
        self,
        embed_func: Callable,
        model_name: str,
        token_counts: List[int] = [50, 100, 256, 512]
    ):
        """
        Calibrate embedding generation speed.

        Args:
            embed_func: Async function that generates embeddings
            model_name: Name of the embedding model
            token_counts: Token counts to test
        """
        logger.info(f"[TIMESENSE] Calibrating embedding: {model_name}")

        measurements = []

        for tokens in token_counts:
            try:
                # Generate test text (approximate tokens)
                text = ' '.join(['word'] * tokens)

                start = time.perf_counter()
                await embed_func(text)
                duration_ms = (time.perf_counter() - start) * 1000

                measurements.append((tokens, duration_ms))
                logger.debug(f"[TIMESENSE] Embed {tokens} tokens: {duration_ms:.1f}ms")

            except Exception as e:
                logger.warning(f"[TIMESENSE] Embedding calibration error: {e}")

        if measurements:
            self.profile_manager.update_profile(
                primitive_type=PrimitiveType.EMBED_TEXT,
                measurements=measurements,
                model_name=model_name,
                unit='tokens'
            )

    async def calibrate_vector_db(
        self,
        search_func: Callable,
        insert_func: Optional[Callable] = None,
        vector_counts: List[int] = [100, 1000, 10000]
    ):
        """
        Calibrate vector database operations.

        Args:
            search_func: Async function that performs vector search
            insert_func: Optional async function that inserts vectors
            vector_counts: Number of vectors to test with
        """
        logger.info("[TIMESENSE] Calibrating vector database...")

        # Search calibration
        search_measurements = []

        for count in vector_counts:
            try:
                start = time.perf_counter()
                await search_func(top_k=10)
                duration_ms = (time.perf_counter() - start) * 1000

                search_measurements.append((count, duration_ms))
                logger.debug(f"[TIMESENSE] Vector search ({count} vectors): {duration_ms:.1f}ms")

            except Exception as e:
                logger.warning(f"[TIMESENSE] Vector search calibration error: {e}")

        if search_measurements:
            self.profile_manager.update_profile(
                primitive_type=PrimitiveType.VECTOR_SEARCH,
                measurements=search_measurements,
                unit='vectors'
            )

    def recalibrate_stale_profiles(
        self,
        max_age_hours: float = 24.0
    ) -> int:
        """
        Recalibrate profiles that are stale.

        Returns number of profiles recalibrated.
        """
        stale = self.profile_manager.get_stale_profiles(max_age_hours)

        if not stale:
            return 0

        logger.info(f"[TIMESENSE] Recalibrating {len(stale)} stale profiles...")

        recalibrated = 0

        for profile in stale:
            try:
                primitive = self.primitive_registry.get(profile.primitive_type)
                if not primitive or not primitive.available:
                    continue

                # Get benchmark method based on primitive type
                benchmark_method = self._get_benchmark_method(profile.primitive_type)
                if not benchmark_method:
                    continue

                results = benchmark_method(
                    primitive.benchmark_sizes,
                    iterations=primitive.measurement_iterations,
                    warmup=primitive.warmup_iterations
                )

                self._process_results(results)
                recalibrated += 1

            except Exception as e:
                logger.warning(f"[TIMESENSE] Failed to recalibrate {profile.primitive_type}: {e}")

        return recalibrated

    def _get_benchmark_method(self, primitive_type: PrimitiveType) -> Optional[Callable]:
        """Get the benchmark method for a primitive type."""
        method_map = {
            PrimitiveType.DISK_READ_SEQ: self.runner.benchmark_disk_read_seq,
            PrimitiveType.DISK_WRITE_SEQ: self.runner.benchmark_disk_write_seq,
            PrimitiveType.CPU_HASH_SHA256: self.runner.benchmark_cpu_hash_sha256,
            PrimitiveType.CPU_JSON_PARSE: self.runner.benchmark_cpu_json_parse,
            PrimitiveType.CPU_JSON_SERIALIZE: self.runner.benchmark_cpu_json_serialize,
            PrimitiveType.CPU_GZIP_COMPRESS: self.runner.benchmark_cpu_gzip_compress,
            PrimitiveType.CPU_GZIP_DECOMPRESS: self.runner.benchmark_cpu_gzip_decompress,
            PrimitiveType.CPU_REGEX_MATCH: self.runner.benchmark_cpu_regex_match,
            PrimitiveType.CPU_TEXT_CHUNK: self.runner.benchmark_cpu_text_chunk,
            PrimitiveType.MEM_COPY: self.runner.benchmark_mem_copy,
        }
        return method_map.get(primitive_type)
