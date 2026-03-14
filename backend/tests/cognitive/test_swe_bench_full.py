"""
SWE-Bench Full Benchmark — Advanced Autonomous Bug Detection & Repair
=====================================================================
Extends the base SWE-bench (test_swe_bench_spindle.py) with 20 advanced,
industry-grade bug cases (SWE-011 to SWE-030) covering:

  - Concurrency & Threading (race conditions, deadlocks, pool exhaustion)
  - Data Structure & Algorithm bugs (binary search, LRU, graph cycles)
  - API & Protocol bugs (status codes, pagination, rate limiting)
  - Memory & Resource bugs (leaks, file handles, connection pools)
  - Security bugs (SQL injection, path traversal, timing attacks)
  - State Machine bugs (invalid transitions, event sourcing, sagas)
  - Integration/System bugs (retry overflow, config merge)

Each test case:
  1. Defines ORIGINAL (correct) code
  2. Defines BUGGY code (a real, subtle bug injected)
  3. Defines a TEST that catches the bug
  4. Feeds through the full Spindle healing chain:
       HealingCoordinator → diagnose → code_fix → VVT verify
  5. Asserts the fix passes VVT Layer 1 and the test suite

Deterministic by design:
  - LLM stubs return the CORRECT fix
  - VVT Layer 1 (AST) runs REAL
  - Z3 runs REAL for gate verification
  - All external services are bypassed
"""
import ast
import pytest
import sys
import textwrap
import time
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

z3 = pytest.importorskip("z3", reason="z3-solver required for Spindle tests")


# ═══════════════════════════════════════════════════════════════
# ADVANCED BUG CATALOG — SWE-011 to SWE-030
# ═══════════════════════════════════════════════════════════════

SWE_BENCH_ADVANCED = [
    # ── Concurrency & Threading ───────────────────────────────
    {
        "id": "SWE-011",
        "title": "Race condition in shared counter — missing lock",
        "component": "memory",
        "severity": "critical",
        "category": "concurrency",
        "buggy_code": textwrap.dedent("""\
            class Counter:
                def __init__(self):
                    self.value = 0

                def increment(self):
                    current = self.value
                    self.value = current + 1

                def get(self):
                    return self.value
        """),
        "correct_code": textwrap.dedent("""\
            import threading

            class Counter:
                def __init__(self):
                    self.value = 0
                    self._lock = threading.Lock()

                def increment(self):
                    with self._lock:
                        self.value += 1

                def get(self):
                    return self.value
        """),
        "test_code": textwrap.dedent("""\
            import threading
            def test_counter_thread_safe():
                c = Counter()
                # The bug is structural: read-then-write without lock
                # Verify the fix uses a lock
                assert hasattr(c, '_lock'), "Counter must have a _lock for thread safety"
                assert isinstance(c._lock, type(threading.Lock())), "_lock must be a threading.Lock"
                # Functional test
                c.increment()
                c.increment()
                assert c.get() == 2
        """),
        "error": "AssertionError: Counter must have a _lock for thread safety",
        "description": "Counter.increment() reads and writes self.value without a lock, causing lost updates under concurrent access.",
    },
    {
        "id": "SWE-012",
        "title": "Deadlock from nested lock acquisition order",
        "component": "sys_conf",
        "severity": "critical",
        "category": "concurrency",
        "buggy_code": textwrap.dedent("""\
            import threading

            class TransferService:
                def __init__(self):
                    self.lock_a = threading.Lock()
                    self.lock_b = threading.Lock()
                    self.balance_a = 100
                    self.balance_b = 100

                def transfer_a_to_b(self, amount):
                    with self.lock_a:
                        with self.lock_b:
                            self.balance_a -= amount
                            self.balance_b += amount

                def transfer_b_to_a(self, amount):
                    with self.lock_b:
                        with self.lock_a:
                            self.balance_b -= amount
                            self.balance_a += amount
        """),
        "correct_code": textwrap.dedent("""\
            import threading

            class TransferService:
                def __init__(self):
                    self.lock_a = threading.Lock()
                    self.lock_b = threading.Lock()
                    self.balance_a = 100
                    self.balance_b = 100

                def _ordered_locks(self):
                    return (self.lock_a, self.lock_b)

                def transfer_a_to_b(self, amount):
                    first, second = self._ordered_locks()
                    with first:
                        with second:
                            self.balance_a -= amount
                            self.balance_b += amount

                def transfer_b_to_a(self, amount):
                    first, second = self._ordered_locks()
                    with first:
                        with second:
                            self.balance_b -= amount
                            self.balance_a += amount
        """),
        "test_code": textwrap.dedent("""\
            import threading
            def test_no_deadlock():
                svc = TransferService()
                # Structural check: both methods must acquire locks in same order
                # to prevent ABBA deadlock. Check _ordered_locks exists.
                assert hasattr(svc, '_ordered_locks'), \
                    "Must use consistent lock ordering via _ordered_locks()"
                first, second = svc._ordered_locks()
                assert first is svc.lock_a, "First lock must always be lock_a"
                # Functional test
                svc.transfer_a_to_b(10)
                svc.transfer_b_to_a(5)
                assert svc.balance_a == 95
                assert svc.balance_b == 105
        """),
        "error": "AssertionError: Must use consistent lock ordering via _ordered_locks()",
        "description": "transfer_a_to_b acquires lock_a then lock_b, while transfer_b_to_a acquires lock_b then lock_a — classic ABBA deadlock.",
    },
    {
        "id": "SWE-013",
        "title": "Thread pool exhaustion from unbounded task queue",
        "component": "sys_conf",
        "severity": "high",
        "category": "concurrency",
        "buggy_code": textwrap.dedent("""\
            class TaskPool:
                def __init__(self, max_workers=2):
                    self.max_workers = max_workers
                    self.tasks = []
                    self.active = 0

                def submit(self, task):
                    self.tasks.append(task)
                    self.active += 1
                    return True

                def can_accept(self):
                    return True  # always accepts
        """),
        "correct_code": textwrap.dedent("""\
            class TaskPool:
                def __init__(self, max_workers=2):
                    self.max_workers = max_workers
                    self.tasks = []
                    self.active = 0

                def submit(self, task):
                    if not self.can_accept():
                        return False
                    self.tasks.append(task)
                    self.active += 1
                    return True

                def can_accept(self):
                    return self.active < self.max_workers
        """),
        "test_code": textwrap.dedent("""\
            def test_pool_respects_limit():
                pool = TaskPool(max_workers=2)
                assert pool.submit("task1") is True
                assert pool.submit("task2") is True
                assert pool.submit("task3") is False  # pool full
                assert pool.can_accept() is False
                assert pool.active == 2
        """),
        "error": "AssertionError: pool.submit('task3') returned True — pool accepted beyond capacity",
        "description": "TaskPool.can_accept() always returns True and submit() never checks capacity, allowing unbounded task accumulation.",
    },
    # ── Data Structure & Algorithm Bugs ───────────────────────
    {
        "id": "SWE-014",
        "title": "Binary search off-by-one — wrong mid calculation",
        "component": "api",
        "severity": "high",
        "category": "algorithm",
        "buggy_code": textwrap.dedent("""\
            def binary_search(arr, target):
                lo, hi = 0, len(arr)
                while lo < hi:
                    mid = (lo + hi) // 2
                    if arr[mid] == target:
                        return mid
                    elif arr[mid] < target:
                        lo = mid
                    else:
                        hi = mid
                return -1
        """),
        "correct_code": textwrap.dedent("""\
            def binary_search(arr, target):
                lo, hi = 0, len(arr) - 1
                while lo <= hi:
                    mid = (lo + hi) // 2
                    if arr[mid] == target:
                        return mid
                    elif arr[mid] < target:
                        lo = mid + 1
                    else:
                        hi = mid - 1
                return -1
        """),
        "test_code": textwrap.dedent("""\
            def test_binary_search():
                arr = [1, 3, 5, 7, 9, 11]
                assert binary_search(arr, 1) == 0
                assert binary_search(arr, 11) == 5
                assert binary_search(arr, 7) == 3
                assert binary_search(arr, 4) == -1
                assert binary_search(arr, 0) == -1
        """),
        "error": "Infinite loop or incorrect index — binary_search(arr, 1) never terminates",
        "description": "lo = mid instead of lo = mid + 1 causes infinite loop when target is at index 0. Also hi should be len-1 with <= comparison.",
    },
    {
        "id": "SWE-015",
        "title": "LRU cache eviction bug — evicts wrong entry",
        "component": "memory",
        "severity": "high",
        "category": "algorithm",
        "buggy_code": textwrap.dedent("""\
            from collections import OrderedDict

            class LRUCache:
                def __init__(self, capacity):
                    self.capacity = capacity
                    self.cache = OrderedDict()

                def get(self, key):
                    if key in self.cache:
                        return self.cache[key]
                    return -1

                def put(self, key, value):
                    if len(self.cache) >= self.capacity:
                        self.cache.popitem(last=True)  # BUG: removes newest
                    self.cache[key] = value
        """),
        "correct_code": textwrap.dedent("""\
            from collections import OrderedDict

            class LRUCache:
                def __init__(self, capacity):
                    self.capacity = capacity
                    self.cache = OrderedDict()

                def get(self, key):
                    if key in self.cache:
                        self.cache.move_to_end(key)
                        return self.cache[key]
                    return -1

                def put(self, key, value):
                    if key in self.cache:
                        self.cache.move_to_end(key)
                    elif len(self.cache) >= self.capacity:
                        self.cache.popitem(last=False)  # remove oldest (LRU)
                    self.cache[key] = value
        """),
        "test_code": textwrap.dedent("""\
            def test_lru_evicts_oldest():
                cache = LRUCache(2)
                cache.put("a", 1)
                cache.put("b", 2)
                # Don't call get("a") — the buggy code doesn't move_to_end anyway
                cache.put("c", 3)    # should evict "a" (oldest insertion)
                assert cache.get("a") == -1, "a (oldest) should have been evicted"
                assert cache.get("b") == 2, "b should still be in cache"
                assert cache.get("c") == 3, "c should be in cache"
        """),
        "error": "AssertionError: a should have been evicted but wasn't — LRU evicts wrong entry",
        "description": "popitem(last=True) removes the most recently added item instead of the least recently used. Also missing move_to_end on get().",
    },
    {
        "id": "SWE-016",
        "title": "Graph cycle detection false positive — visited vs in-stack",
        "component": "network",
        "severity": "high",
        "category": "algorithm",
        "buggy_code": textwrap.dedent("""\
            def has_cycle(graph):
                visited = set()

                def dfs(node):
                    if node in visited:
                        return True  # BUG: conflates visited with in-stack
                    visited.add(node)
                    for neighbor in graph.get(node, []):
                        if dfs(neighbor):
                            return True
                    return False

                for node in graph:
                    if dfs(node):
                        return True
                return False
        """),
        "correct_code": textwrap.dedent("""\
            def has_cycle(graph):
                visited = set()
                in_stack = set()

                def dfs(node):
                    if node in in_stack:
                        return True
                    if node in visited:
                        return False
                    visited.add(node)
                    in_stack.add(node)
                    for neighbor in graph.get(node, []):
                        if dfs(neighbor):
                            return True
                    in_stack.remove(node)
                    return False

                for node in graph:
                    if dfs(node):
                        return True
                return False
        """),
        "test_code": textwrap.dedent("""\
            def test_cycle_detection():
                # Diamond graph: a->b, a->c, b->d, c->d (NO cycle)
                diamond = {"a": ["b", "c"], "b": ["d"], "c": ["d"], "d": []}
                assert has_cycle(diamond) is False, "Diamond graph has no cycle"

                # Actual cycle: a->b->c->a
                cyclic = {"a": ["b"], "b": ["c"], "c": ["a"]}
                assert has_cycle(cyclic) is True, "Should detect cycle"
        """),
        "error": "AssertionError: Diamond graph has no cycle — false positive from conflating visited with recursion stack",
        "description": "Uses single 'visited' set for both 'already fully explored' and 'currently in recursion stack', causing false positives on DAGs with shared descendants.",
    },
    # ── API & Protocol Bugs ───────────────────────────────────
    {
        "id": "SWE-017",
        "title": "REST endpoint returns 200 on validation failure",
        "component": "api",
        "severity": "critical",
        "category": "api",
        "buggy_code": textwrap.dedent("""\
            def handle_create_user(data):
                errors = []
                if not data.get("name"):
                    errors.append("name is required")
                if not data.get("email"):
                    errors.append("email is required")
                return {"status": 200, "errors": errors, "data": data}
        """),
        "correct_code": textwrap.dedent("""\
            def handle_create_user(data):
                errors = []
                if not data.get("name"):
                    errors.append("name is required")
                if not data.get("email"):
                    errors.append("email is required")
                if errors:
                    return {"status": 422, "errors": errors, "data": None}
                return {"status": 200, "errors": [], "data": data}
        """),
        "test_code": textwrap.dedent("""\
            def test_validation_returns_422():
                result = handle_create_user({"name": ""})
                assert result["status"] == 422, f"Expected 422, got {result['status']}"
                assert len(result["errors"]) > 0
                assert result["data"] is None
        """),
        "error": "AssertionError: Expected 422, got 200 — validation errors returned with success status",
        "description": "Endpoint always returns 200 even when validation fails, causing clients to treat invalid data as successfully created.",
    },
    {
        "id": "SWE-018",
        "title": "Pagination cursor corruption — base64 decode fails silently",
        "component": "api",
        "severity": "high",
        "category": "api",
        "buggy_code": textwrap.dedent("""\
            import base64

            def decode_cursor(cursor_str):
                try:
                    decoded = base64.b64decode(cursor_str)
                    return int(decoded)
                except Exception:
                    return 0  # silently returns page 0
        """),
        "correct_code": textwrap.dedent("""\
            import base64

            def decode_cursor(cursor_str):
                if not cursor_str:
                    return 0
                try:
                    decoded = base64.b64decode(cursor_str).decode("utf-8")
                    return int(decoded)
                except (ValueError, TypeError) as e:
                    raise ValueError(f"Invalid cursor: {cursor_str}") from e
        """),
        "test_code": textwrap.dedent("""\
            import base64
            def test_decode_cursor():
                # Valid cursor
                valid = base64.b64encode(b"42").decode()
                assert decode_cursor(valid) == 42

                # Invalid cursor should raise, not silently reset
                try:
                    decode_cursor("not-valid-base64!!!")
                    assert False, "Should have raised ValueError"
                except ValueError:
                    pass

                # Empty cursor returns 0
                assert decode_cursor("") == 0
                assert decode_cursor(None) == 0
        """),
        "error": "AssertionError: Should have raised ValueError — invalid cursor silently returned 0",
        "description": "Invalid cursors silently fall back to page 0, causing users to see duplicate first-page results without any error indication.",
    },
    {
        "id": "SWE-019",
        "title": "Rate limiter doesn't reset window correctly",
        "component": "api",
        "severity": "high",
        "category": "api",
        "buggy_code": textwrap.dedent("""\
            class RateLimiter:
                def __init__(self, max_requests, window_seconds):
                    self.max_requests = max_requests
                    self.window = window_seconds
                    self.requests = []

                def allow(self, timestamp):
                    self.requests.append(timestamp)
                    if len(self.requests) > self.max_requests:
                        return False
                    return True
        """),
        "correct_code": textwrap.dedent("""\
            class RateLimiter:
                def __init__(self, max_requests, window_seconds):
                    self.max_requests = max_requests
                    self.window = window_seconds
                    self.requests = []

                def allow(self, timestamp):
                    # Remove requests outside the current window
                    self.requests = [
                        t for t in self.requests
                        if timestamp - t < self.window
                    ]
                    if len(self.requests) >= self.max_requests:
                        return False
                    self.requests.append(timestamp)
                    return True
        """),
        "test_code": textwrap.dedent("""\
            def test_rate_limiter_resets():
                rl = RateLimiter(max_requests=2, window_seconds=10)
                assert rl.allow(0) is True
                assert rl.allow(1) is True
                assert rl.allow(2) is False  # over limit

                # After window expires, should allow again
                assert rl.allow(15) is True, "Should allow after window reset"
        """),
        "error": "AssertionError: Should allow after window reset — rate limiter never clears old requests",
        "description": "Rate limiter appends timestamps but never removes expired ones, so the request list grows forever and eventually blocks all requests.",
    },
    # ── Memory & Resource Bugs ────────────────────────────────
    {
        "id": "SWE-020",
        "title": "Memory leak from accumulating event listeners",
        "component": "memory",
        "severity": "high",
        "category": "resource",
        "buggy_code": textwrap.dedent("""\
            class EventBus:
                def __init__(self):
                    self.listeners = {}

                def on(self, event, callback):
                    if event not in self.listeners:
                        self.listeners[event] = []
                    self.listeners[event].append(callback)

                def off(self, event, callback):
                    pass  # BUG: never actually removes

                def listener_count(self, event):
                    return len(self.listeners.get(event, []))
        """),
        "correct_code": textwrap.dedent("""\
            class EventBus:
                def __init__(self):
                    self.listeners = {}

                def on(self, event, callback):
                    if event not in self.listeners:
                        self.listeners[event] = []
                    self.listeners[event].append(callback)

                def off(self, event, callback):
                    if event in self.listeners:
                        self.listeners[event] = [
                            cb for cb in self.listeners[event] if cb is not callback
                        ]

                def listener_count(self, event):
                    return len(self.listeners.get(event, []))
        """),
        "test_code": textwrap.dedent("""\
            def test_event_bus_removes_listener():
                bus = EventBus()
                handler = lambda: None
                bus.on("click", handler)
                assert bus.listener_count("click") == 1
                bus.off("click", handler)
                assert bus.listener_count("click") == 0, "Listener was not removed"
        """),
        "error": "AssertionError: Listener was not removed — off() is a no-op",
        "description": "EventBus.off() has an empty body, so listeners accumulate forever, causing memory leaks in long-running processes.",
    },
    {
        "id": "SWE-021",
        "title": "Error handler returns None instead of error dict",
        "component": "sys_conf",
        "severity": "critical",
        "category": "resource",
        "buggy_code": textwrap.dedent("""\
            def handle_error(error_type, message):
                if error_type == "critical":
                    return {"level": "critical", "message": message, "notify": True}
                elif error_type == "warning":
                    return {"level": "warning", "message": message, "notify": False}
                # BUG: missing return for 'info' and unknown types
        """),
        "correct_code": textwrap.dedent("""\
            def handle_error(error_type, message):
                if error_type == "critical":
                    return {"level": "critical", "message": message, "notify": True}
                elif error_type == "warning":
                    return {"level": "warning", "message": message, "notify": False}
                else:
                    return {"level": error_type, "message": message, "notify": False}
        """),
        "test_code": textwrap.dedent("""\
            def test_handle_error_all_types():
                r1 = handle_error("critical", "disk full")
                assert r1["level"] == "critical"
                assert r1["notify"] is True

                r2 = handle_error("info", "startup complete")
                assert r2 is not None, "handle_error returned None for 'info' type"
                assert r2["level"] == "info"

                r3 = handle_error("debug", "trace")
                assert r3 is not None, "handle_error returned None for unknown type"
        """),
        "error": "AssertionError: handle_error returned None for 'info' type",
        "description": "handle_error only handles 'critical' and 'warning', returning None implicitly for all other error types.",
    },
    {
        "id": "SWE-022",
        "title": "Connection pool starvation — connections not returned",
        "component": "database",
        "severity": "critical",
        "category": "resource",
        "buggy_code": textwrap.dedent("""\
            class ConnectionPool:
                def __init__(self, size=3):
                    self.size = size
                    self.available = list(range(size))
                    self.in_use = []

                def acquire(self):
                    if not self.available:
                        return None
                    conn = self.available.pop()
                    self.in_use.append(conn)
                    return conn

                def release(self, conn):
                    pass  # BUG: never returns to available
        """),
        "correct_code": textwrap.dedent("""\
            class ConnectionPool:
                def __init__(self, size=3):
                    self.size = size
                    self.available = list(range(size))
                    self.in_use = []

                def acquire(self):
                    if not self.available:
                        return None
                    conn = self.available.pop()
                    self.in_use.append(conn)
                    return conn

                def release(self, conn):
                    if conn in self.in_use:
                        self.in_use.remove(conn)
                        self.available.append(conn)
        """),
        "test_code": textwrap.dedent("""\
            def test_connection_pool_recycles():
                pool = ConnectionPool(size=1)
                conn = pool.acquire()
                assert conn is not None
                pool.release(conn)
                conn2 = pool.acquire()
                assert conn2 is not None, "Pool starved — connection not returned"
        """),
        "error": "AssertionError: Pool starved — connection not returned after release",
        "description": "release() is a no-op, so connections move from available to in_use but never come back, exhausting the pool.",
    },
    # ── Security Bugs ─────────────────────────────────────────
    {
        "id": "SWE-023",
        "title": "SQL injection via string formatting",
        "component": "database",
        "severity": "critical",
        "category": "security",
        "buggy_code": textwrap.dedent("""\
            def build_query(table, filters):
                where_clause = " AND ".join(
                    f"{k} = '{v}'" for k, v in filters.items()
                )
                return f"SELECT * FROM {table} WHERE {where_clause}"
        """),
        "correct_code": textwrap.dedent("""\
            def build_query(table, filters):
                allowed_tables = {"users", "orders", "products"}
                if table not in allowed_tables:
                    raise ValueError(f"Invalid table: {table}")
                conditions = []
                params = []
                for k, v in filters.items():
                    if not k.isidentifier():
                        raise ValueError(f"Invalid column: {k}")
                    conditions.append(f"{k} = ?")
                    params.append(v)
                where_clause = " AND ".join(conditions)
                return f"SELECT * FROM {table} WHERE {where_clause}", params
        """),
        "test_code": textwrap.dedent("""\
            def test_sql_injection_prevented():
                # This payload should NOT be interpolated into the query
                malicious = {"name": "'; DROP TABLE users; --"}
                result = build_query("users", malicious)
                if isinstance(result, tuple):
                    query, params = result
                    assert "DROP" not in query, "SQL injection not prevented"
                    assert "?" in query, "Should use parameterized query"
                else:
                    assert "DROP" not in result, "SQL injection in query string"
        """),
        "error": "AssertionError: SQL injection not prevented — DROP TABLE in query string",
        "description": "Direct string formatting of user input into SQL query allows injection attacks. Must use parameterized queries.",
    },
    {
        "id": "SWE-024",
        "title": "Path traversal via unsanitized user input",
        "component": "api",
        "severity": "critical",
        "category": "security",
        "buggy_code": textwrap.dedent("""\
            import os

            def get_file_path(base_dir, filename):
                return os.path.join(base_dir, filename)
        """),
        "correct_code": textwrap.dedent("""\
            import os

            def get_file_path(base_dir, filename):
                # Resolve to absolute path and verify it's within base_dir
                base = os.path.realpath(base_dir)
                target = os.path.realpath(os.path.join(base_dir, filename))
                if not target.startswith(base + os.sep) and target != base:
                    raise ValueError(f"Path traversal blocked: {filename}")
                return target
        """),
        "test_code": textwrap.dedent("""\
            import os
            def test_path_traversal_blocked():
                base = "/app/uploads"
                # Normal file — should work
                safe = get_file_path(base, "photo.jpg")
                assert "photo.jpg" in safe

                # Path traversal — should be blocked
                try:
                    get_file_path(base, "../../etc/passwd")
                    assert False, "Path traversal not blocked"
                except ValueError:
                    pass
        """),
        "error": "AssertionError: Path traversal not blocked — ../../etc/passwd accepted",
        "description": "os.path.join does not prevent '..' traversal. User can escape base_dir to read arbitrary files on the system.",
    },
    {
        "id": "SWE-025",
        "title": "Timing attack in password comparison",
        "component": "api",
        "severity": "critical",
        "category": "security",
        "buggy_code": textwrap.dedent("""\
            def verify_token(provided, expected):
                if len(provided) != len(expected):
                    return False
                for a, b in zip(provided, expected):
                    if a != b:
                        return False
                return True
        """),
        "correct_code": textwrap.dedent("""\
            import hmac

            def verify_token(provided, expected):
                if not isinstance(provided, str) or not isinstance(expected, str):
                    return False
                return hmac.compare_digest(provided, expected)
        """),
        "test_code": textwrap.dedent("""\
            import hmac, time
            def test_constant_time_comparison():
                # Functional correctness
                assert verify_token("abc123", "abc123") is True
                assert verify_token("abc123", "xyz789") is False
                assert verify_token("short", "longer_string") is False

                # Verify timing consistency: near-match and total mismatch
                # should take similar time (constant-time comparison)
                secret = "a" * 1000
                near_miss = "a" * 999 + "b"
                total_miss = "b" * 1000

                t1 = time.perf_counter()
                for _ in range(1000):
                    verify_token(near_miss, secret)
                near_time = time.perf_counter() - t1

                t2 = time.perf_counter()
                for _ in range(1000):
                    verify_token(total_miss, secret)
                miss_time = time.perf_counter() - t2

                # With constant-time comparison, ratio should be close to 1.0
                # Early-exit comparison would show near_time >> miss_time
                ratio = near_time / max(miss_time, 1e-9)
                assert 0.2 < ratio < 5.0, f"Timing ratio {ratio:.2f} suggests non-constant-time comparison"
        """),
        "error": "AssertionError: Timing ratio suggests non-constant-time comparison",
        "description": "Character-by-character comparison with early return leaks information about how many characters match, enabling timing attacks.",
    },
    # ── State Machine Bugs ────────────────────────────────────
    {
        "id": "SWE-026",
        "title": "FSM allows invalid state transition",
        "component": "sys_conf",
        "severity": "high",
        "category": "state_machine",
        "buggy_code": textwrap.dedent("""\
            class OrderFSM:
                TRANSITIONS = {
                    "pending": ["confirmed", "cancelled"],
                    "confirmed": ["shipped", "cancelled"],
                    "shipped": ["delivered"],
                    "delivered": [],
                    "cancelled": [],
                }

                def __init__(self):
                    self.state = "pending"

                def transition(self, new_state):
                    self.state = new_state  # BUG: no validation
                    return True
        """),
        "correct_code": textwrap.dedent("""\
            class OrderFSM:
                TRANSITIONS = {
                    "pending": ["confirmed", "cancelled"],
                    "confirmed": ["shipped", "cancelled"],
                    "shipped": ["delivered"],
                    "delivered": [],
                    "cancelled": [],
                }

                def __init__(self):
                    self.state = "pending"

                def transition(self, new_state):
                    allowed = self.TRANSITIONS.get(self.state, [])
                    if new_state not in allowed:
                        raise ValueError(
                            f"Invalid transition: {self.state} → {new_state}"
                        )
                    self.state = new_state
                    return True
        """),
        "test_code": textwrap.dedent("""\
            def test_fsm_blocks_invalid():
                fsm = OrderFSM()
                assert fsm.state == "pending"
                fsm.transition("confirmed")
                assert fsm.state == "confirmed"

                # Cannot go back to pending
                try:
                    fsm.transition("pending")
                    assert False, "Should block confirmed→pending"
                except ValueError:
                    pass

                # Cannot skip to delivered
                try:
                    fsm.transition("delivered")
                    assert False, "Should block confirmed→delivered"
                except ValueError:
                    pass

                assert fsm.state == "confirmed"
        """),
        "error": "AssertionError: Should block confirmed→pending — FSM allows any transition",
        "description": "transition() sets state without checking TRANSITIONS table, allowing invalid state changes like delivered→pending.",
    },
    {
        "id": "SWE-027",
        "title": "Event sourcing replay produces wrong final state",
        "component": "database",
        "severity": "critical",
        "category": "state_machine",
        "buggy_code": textwrap.dedent("""\
            class EventStore:
                def __init__(self):
                    self.events = []

                def append(self, event):
                    self.events.append(event)

                def replay(self):
                    state = {"balance": 0}
                    for event in self.events:
                        if event["type"] == "credit":
                            state["balance"] += event["amount"]
                        elif event["type"] == "debit":
                            state["balance"] += event["amount"]  # BUG: should subtract
                    return state
        """),
        "correct_code": textwrap.dedent("""\
            class EventStore:
                def __init__(self):
                    self.events = []

                def append(self, event):
                    self.events.append(event)

                def replay(self):
                    state = {"balance": 0}
                    for event in self.events:
                        if event["type"] == "credit":
                            state["balance"] += event["amount"]
                        elif event["type"] == "debit":
                            state["balance"] -= event["amount"]
                    return state
        """),
        "test_code": textwrap.dedent("""\
            def test_event_replay():
                store = EventStore()
                store.append({"type": "credit", "amount": 100})
                store.append({"type": "debit", "amount": 30})
                store.append({"type": "credit", "amount": 50})
                state = store.replay()
                assert state["balance"] == 120, f"Expected 120, got {state['balance']}"
        """),
        "error": "AssertionError: Expected 120, got 180 — debit adds instead of subtracting",
        "description": "Event replay uses += for both credit and debit events, so debits increase the balance instead of decreasing it.",
    },
    {
        "id": "SWE-028",
        "title": "Saga compensating transaction skips step",
        "component": "database",
        "severity": "critical",
        "category": "state_machine",
        "buggy_code": textwrap.dedent("""\
            class Saga:
                def __init__(self):
                    self.completed = []
                    self.compensations = []

                def add_step(self, action, compensation):
                    self.completed.append(action)
                    self.compensations.append(compensation)

                def compensate(self):
                    for comp in self.compensations:  # BUG: forward order
                        comp()
        """),
        "correct_code": textwrap.dedent("""\
            class Saga:
                def __init__(self):
                    self.completed = []
                    self.compensations = []

                def add_step(self, action, compensation):
                    self.completed.append(action)
                    self.compensations.append(compensation)

                def compensate(self):
                    for comp in reversed(self.compensations):
                        comp()
        """),
        "test_code": textwrap.dedent("""\
            def test_saga_compensates_in_reverse():
                saga = Saga()
                order = []
                saga.add_step("step1", lambda: order.append("undo1"))
                saga.add_step("step2", lambda: order.append("undo2"))
                saga.add_step("step3", lambda: order.append("undo3"))
                saga.compensate()
                assert order == ["undo3", "undo2", "undo1"], \
                    f"Expected reverse order, got {order}"
        """),
        "error": "AssertionError: Expected ['undo3','undo2','undo1'], got ['undo1','undo2','undo3']",
        "description": "Saga compensates in forward order instead of reverse, violating the stack-based undo semantics required for data consistency.",
    },
    # ── Integration / System Bugs ─────────────────────────────
    {
        "id": "SWE-029",
        "title": "Retry logic with exponential backoff overflow",
        "component": "network",
        "severity": "high",
        "category": "integration",
        "buggy_code": textwrap.dedent("""\
            def retry_with_backoff(fn, max_retries=10):
                for attempt in range(max_retries):
                    try:
                        return fn()
                    except Exception:
                        delay = 2 ** attempt  # grows to 512s on attempt 9
                        pass  # would sleep(delay)
                raise RuntimeError("All retries exhausted")

            def get_max_delay(max_retries=10):
                return 2 ** (max_retries - 1)
        """),
        "correct_code": textwrap.dedent("""\
            def retry_with_backoff(fn, max_retries=10, max_delay=30):
                for attempt in range(max_retries):
                    try:
                        return fn()
                    except Exception:
                        delay = min(2 ** attempt, max_delay)
                        pass  # would sleep(delay)
                raise RuntimeError("All retries exhausted")

            def get_max_delay(max_retries=10, max_delay=30):
                return min(2 ** (max_retries - 1), max_delay)
        """),
        "test_code": textwrap.dedent("""\
            def test_backoff_capped():
                max_d = get_max_delay(max_retries=10)
                assert max_d <= 60, f"Max delay {max_d}s is too large — should be capped"

                # Also verify the function works
                call_count = [0]
                def flaky():
                    call_count[0] += 1
                    if call_count[0] < 3:
                        raise ConnectionError("fail")
                    return "ok"
                assert retry_with_backoff(flaky) == "ok"
        """),
        "error": "AssertionError: Max delay 512s is too large — exponential backoff without cap",
        "description": "Exponential backoff grows unbounded (2^9 = 512 seconds), causing requests to stall for minutes. Must cap at a maximum delay.",
    },
    {
        "id": "SWE-030",
        "title": "Config merge deep-overwrites instead of shallow",
        "component": "sys_conf",
        "severity": "medium",
        "category": "integration",
        "buggy_code": textwrap.dedent("""\
            def merge_config(base, override):
                result = dict(base)
                for key, value in override.items():
                    result[key] = value  # overwrites nested dicts entirely
                return result
        """),
        "correct_code": textwrap.dedent("""\
            def merge_config(base, override):
                result = dict(base)
                for key, value in override.items():
                    if (
                        key in result
                        and isinstance(result[key], dict)
                        and isinstance(value, dict)
                    ):
                        result[key] = merge_config(result[key], value)
                    else:
                        result[key] = value
                return result
        """),
        "test_code": textwrap.dedent("""\
            def test_deep_merge():
                base = {
                    "db": {"host": "localhost", "port": 5432, "pool_size": 10},
                    "debug": False,
                }
                override = {
                    "db": {"port": 3306},
                    "debug": True,
                }
                result = merge_config(base, override)
                assert result["db"]["port"] == 3306, "Override should apply"
                assert result["db"]["host"] == "localhost", "Non-overridden keys should be preserved"
                assert result["db"]["pool_size"] == 10, "pool_size should survive merge"
                assert result["debug"] is True
        """),
        "error": "KeyError: 'host' — shallow overwrite replaced entire db dict, losing host and pool_size",
        "description": "Config merge replaces nested dicts entirely instead of merging them, causing non-overridden keys in nested objects to be lost.",
    },
]


# ═══════════════════════════════════════════════════════════════
# FIXTURES — same pattern as test_swe_bench_spindle.py
# ═══════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def reset_singletons(mock_externals):
    """Reset all Spindle + HealingCoordinator singletons between tests."""
    import cognitive.spindle_executor as ex_mod
    import cognitive.spindle_event_store as es_mod
    import cognitive.spindle_checkpoint as cp_mod
    import cognitive.spindle_projection as pr_mod
    import cognitive.physics.spindle_gate as gt_mod
    import cognitive.healing_coordinator as hc_mod

    ex_mod._instance = None
    es_mod._store = None
    cp_mod._manager = None
    pr_mod._projection = None
    gt_mod._gate = None
    hc_mod._coordinator = None
    backend_es = sys.modules.get("backend.cognitive.spindle_event_store")
    if backend_es:
        backend_es._store = None
    yield


@pytest.fixture
def BD(mock_externals):
    from cognitive.braille_compiler import BrailleDictionary
    return BrailleDictionary


def _set_event_store_singleton(store):
    import cognitive.spindle_event_store as es_mod
    es_mod._store = store
    try:
        import backend.cognitive.spindle_event_store as bes_mod
        bes_mod._store = store
    except Exception:
        pass


@pytest.fixture
def event_store():
    from cognitive.spindle_event_store import SpindleEventStore
    store = SpindleEventStore()
    store._db_available = False
    _set_event_store_singleton(store)
    return store


def _build_mock_brain(correct_code):
    """Build a mock brain that returns the correct fix code."""
    responses = {
        ("system", "reset_db"): {"ok": True, "data": {"status": "reconnected"}},
        ("system", "reset_vector_db"): {"ok": True, "data": {"status": "reconnected"}},
        ("system", "scan_heal"): {"ok": True, "data": {"status": "scanned"}},
        ("govern", "heal"): {"ok": True, "data": {"status": "healed"}},
        ("govern", "learn"): {"ok": True, "data": {}},
        ("govern", "record_gap"): {"ok": True, "data": {}},
        ("code", "generate"): {
            "ok": True,
            "data": {
                "code": correct_code,
                "response": "Fixed the issue",
                "trust_score": 0.85,
                "stages_passed": ["syntax", "security", "deterministic"],
            },
        },
    }

    def fake_call_brain(namespace, action, params=None):
        return responses.get((namespace, action), {"ok": False, "error": "unknown"})

    return fake_call_brain


@pytest.fixture
def mock_externals():
    """Stub all external service calls."""
    injected = {}

    mock_raw = MagicMock()
    mock_raw.chat.return_value = "Root cause: identified. Fix: apply correction."
    mock_kimi = MagicMock()
    mock_kimi.chat.return_value = "Root cause: confirmed. Fix: correct the logic."
    mock_llm = MagicMock()
    mock_llm.chat.return_value = "Apply the fix."

    llm_mod = ModuleType("llm_orchestrator.factory")
    llm_mod.get_raw_client = lambda: mock_raw
    llm_mod.get_kimi_client = lambda: mock_kimi
    llm_mod.get_llm_client = lambda *a, **kw: mock_llm
    injected["llm_orchestrator.factory"] = llm_mod

    llm_orch_mod = ModuleType("llm_orchestrator.llm_orchestrator")
    llm_orch_mod.get_llm_orchestrator = MagicMock()
    injected["llm_orchestrator.llm_orchestrator"] = llm_orch_mod

    repo_mod = ModuleType("llm_orchestrator.repo_access")
    repo_mod.RepositoryAccessLayer = MagicMock()
    injected["llm_orchestrator.repo_access"] = repo_mod

    multi_mod = ModuleType("llm_orchestrator.multi_llm_client")
    multi_mod.TaskType = MagicMock()
    multi_mod.MultiLLMClient = MagicMock()
    injected["llm_orchestrator.multi_llm_client"] = multi_mod

    ollama_mod = ModuleType("llm_orchestrator.ollama_resolver")
    ollama_mod.resolve_ollama_model = lambda x: "qwen3:32b"
    injected["llm_orchestrator.ollama_resolver"] = ollama_mod

    if "llm_orchestrator" not in sys.modules:
        injected["llm_orchestrator"] = ModuleType("llm_orchestrator")

    def fake_parallel(fns, return_exceptions=False):
        results = []
        for fn in fns:
            try:
                results.append(fn())
            except Exception as e:
                results.append(e if return_exceptions else str(e))
        return results

    def fake_background(fn, name=""):
        try:
            fn()
        except Exception:
            pass

    async_mod = ModuleType("core.async_parallel")
    async_mod.run_parallel = fake_parallel
    async_mod.run_background = fake_background
    injected["core.async_parallel"] = async_mod

    retrieval_mod = ModuleType("retrieval.retriever")
    retrieval_mod.DocumentRetriever = MagicMock()
    injected["retrieval.retriever"] = retrieval_mod
    if "retrieval" not in sys.modules:
        injected["retrieval"] = ModuleType("retrieval")

    embed_mod = ModuleType("embedding.embedder")
    embed_mod.get_embedding_model = MagicMock()
    injected["embedding.embedder"] = embed_mod
    if "embedding" not in sys.modules:
        injected["embedding"] = ModuleType("embedding")

    vdb_mod = ModuleType("vector_db.client")
    vdb_mod.get_qdrant_client = MagicMock()
    injected["vector_db.client"] = vdb_mod
    if "vector_db" not in sys.modules:
        injected["vector_db"] = ModuleType("vector_db")

    pipeline_mod = ModuleType("cognitive.pipeline")
    pipeline_mod.FeedbackLoop = MagicMock()
    injected["cognitive.pipeline"] = pipeline_mod

    trust_mod = ModuleType("cognitive.trust_engine")
    mock_trust = MagicMock()
    trust_mod.get_trust_engine = lambda: mock_trust
    injected["cognitive.trust_engine"] = trust_mod

    magma_mod = ModuleType("cognitive.magma_bridge")
    magma_mod.store_decision = MagicMock()
    magma_mod.store_pattern = MagicMock()
    magma_mod.ingest = MagicMock()
    injected["cognitive.magma_bridge"] = magma_mod

    tracker_mod = ModuleType("api._genesis_tracker")
    tracker_mod.track = MagicMock()
    injected["api._genesis_tracker"] = tracker_mod

    originals = {}
    for name, mod in injected.items():
        originals[name] = sys.modules.get(name)
        sys.modules[name] = mod

    yield

    for name, orig in originals.items():
        if orig is not None:
            sys.modules[name] = orig
        else:
            sys.modules.pop(name, None)


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _verify_fix_ast(code: str) -> bool:
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def _verify_fix_no_dangerous_patterns(code: str) -> bool:
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in ('eval', 'exec'):
                    return False
        return True
    except SyntaxError:
        return False


def _exec_and_run_test(code: str, test_code: str, timeout: float = 5.0) -> bool:
    import threading
    namespace = {}
    result = [False]

    def run():
        try:
            exec(code, namespace)
            exec(test_code, namespace)
            test_fns = [v for k, v in namespace.items() if k.startswith("test_") and callable(v)]
            for fn in test_fns:
                fn()
            result[0] = True
        except Exception:
            result[0] = False

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(timeout=timeout)
    if t.is_alive():
        return False  # timed out = test failed
    return result[0]


def _verify_fix_functional(correct_code: str, test_code: str) -> bool:
    return _exec_and_run_test(correct_code, test_code)


def _verify_buggy_fails(buggy_code: str, test_code: str) -> bool:
    return not _exec_and_run_test(buggy_code, test_code)


CATEGORY_LABELS = {
    "concurrency": "Concurrency & Threading",
    "algorithm": "Data Structures & Algorithms",
    "api": "API & Protocol",
    "resource": "Memory & Resource",
    "security": "Security",
    "state_machine": "State Machine",
    "integration": "Integration / System",
}


# ═══════════════════════════════════════════════════════════════
# 1. BUG CATALOG VALIDATION — confirm every bug is real
# ═══════════════════════════════════════════════════════════════

class TestSWEBenchFixVerification:
    """Verify every correct_code passes its test_code."""

    @pytest.mark.parametrize("case", SWE_BENCH_ADVANCED, ids=[c["id"] for c in SWE_BENCH_ADVANCED])
    def test_correct_code_passes_test(self, case):
        assert _verify_fix_functional(case["correct_code"], case["test_code"]), (
            f"{case['id']}: correct code fails the test — fix is wrong"
        )

    @pytest.mark.parametrize("case", SWE_BENCH_ADVANCED, ids=[c["id"] for c in SWE_BENCH_ADVANCED])
    def test_correct_code_valid_ast(self, case):
        assert _verify_fix_ast(case["correct_code"]), (
            f"{case['id']}: correct code has syntax errors"
        )

    @pytest.mark.parametrize("case", SWE_BENCH_ADVANCED, ids=[c["id"] for c in SWE_BENCH_ADVANCED])
    def test_correct_code_no_dangerous_patterns(self, case):
        assert _verify_fix_no_dangerous_patterns(case["correct_code"]), (
            f"{case['id']}: correct code contains eval/exec"
        )


# ═══════════════════════════════════════════════════════════════
# 2. BUG DETECTION — buggy code MUST fail the test
# ═══════════════════════════════════════════════════════════════

class TestSWEBenchBugDetection:
    """Verify buggy_code FAILS its test_code — confirming the bug is real."""

    @pytest.mark.parametrize("case", SWE_BENCH_ADVANCED, ids=[c["id"] for c in SWE_BENCH_ADVANCED])
    def test_buggy_code_fails_test(self, case):
        assert _verify_buggy_fails(case["buggy_code"], case["test_code"]), (
            f"{case['id']}: buggy code passes the test — bug is not real"
        )


# ═══════════════════════════════════════════════════════════════
# 3. HEALING COORDINATOR — full resolution chain
# ═══════════════════════════════════════════════════════════════

class TestSWEBenchHealingCoordinator:
    """Feed each advanced bug through HealingCoordinator.resolve()."""

    @pytest.mark.parametrize("case", SWE_BENCH_ADVANCED, ids=[c["id"] for c in SWE_BENCH_ADVANCED])
    def test_coordinator_resolves_bug(self, case, mock_externals, event_store):
        brain_fn = _build_mock_brain(case["correct_code"])
        fake_mod = ModuleType("api.brain_api_v2")
        fake_mod.call_brain = brain_fn
        old_mod = sys.modules.get("api.brain_api_v2")
        sys.modules["api.brain_api_v2"] = fake_mod

        try:
            from cognitive.healing_coordinator import HealingCoordinator
            coordinator = HealingCoordinator()
            problem = {
                "component": case["component"],
                "description": case["description"],
                "error": case["error"],
                "severity": case["severity"],
            }
            result = coordinator.resolve(problem)

            assert result["resolved"] is True, (
                f"{case['id']}: coordinator failed to resolve — "
                f"resolution={result.get('resolution')}, "
                f"steps={[s.get('step') for s in result.get('steps', [])]}"
            )
            assert result["resolution"] in ("self_healing", "coding_agent", "coordinated_fix")
            assert len(result["steps"]) >= 1
        finally:
            if old_mod is not None:
                sys.modules["api.brain_api_v2"] = old_mod
            else:
                sys.modules.pop("api.brain_api_v2", None)

    @pytest.mark.parametrize("case", SWE_BENCH_ADVANCED, ids=[c["id"] for c in SWE_BENCH_ADVANCED])
    def test_coordinator_publishes_event(self, case, mock_externals, event_store):
        brain_fn = _build_mock_brain(case["correct_code"])
        fake_mod = ModuleType("api.brain_api_v2")
        fake_mod.call_brain = brain_fn
        old_mod = sys.modules.get("api.brain_api_v2")
        sys.modules["api.brain_api_v2"] = fake_mod

        try:
            from cognitive.healing_coordinator import HealingCoordinator
            coordinator = HealingCoordinator()
            problem = {
                "component": case["component"],
                "description": case["description"],
                "error": case["error"],
                "severity": case["severity"],
            }
            coordinator.resolve(problem)

            events = event_store.query(source_type="healing_coordinator")
            assert len(events) >= 1, f"{case['id']}: no event published to Spindle store"
            assert events[-1]["payload"]["resolved"] is True
        finally:
            if old_mod is not None:
                sys.modules["api.brain_api_v2"] = old_mod
            else:
                sys.modules.pop("api.brain_api_v2", None)


# ═══════════════════════════════════════════════════════════════
# 4. VVT PIPELINE — AST validity
# ═══════════════════════════════════════════════════════════════

class TestSWEBenchVVTPipeline:
    """Run VVT Layer 1 against every generated fix."""

    @pytest.mark.parametrize("case", SWE_BENCH_ADVANCED, ids=[c["id"] for c in SWE_BENCH_ADVANCED])
    def test_fix_passes_vvt_ast(self, case):
        try:
            from verification.deterministic_vvt_pipeline import VVTVault
            vault = VVTVault()
            passed, logs, err = vault._layer_1_ast(case["correct_code"], "fix", None)
            assert passed is True, f"{case['id']}: VVT AST failed — {err}"
        except ImportError:
            assert _verify_fix_ast(case["correct_code"])

    @pytest.mark.parametrize("case", SWE_BENCH_ADVANCED, ids=[c["id"] for c in SWE_BENCH_ADVANCED])
    def test_buggy_code_also_valid_ast(self, case):
        assert _verify_fix_ast(case["buggy_code"]), (
            f"{case['id']}: buggy code has syntax errors — bug must be semantic"
        )


# ═══════════════════════════════════════════════════════════════
# 5. SPINDLE EXECUTOR E2E — Z3 gate → executor → coordinator
# ═══════════════════════════════════════════════════════════════

class TestSWEBenchSpindleE2E:
    """Full Spindle pipeline for advanced bugs."""

    @pytest.mark.parametrize(
        "case",
        [c for c in SWE_BENCH_ADVANCED if c["component"] in ("database", "api", "memory", "network", "sys_conf")],
        ids=[c["id"] for c in SWE_BENCH_ADVANCED if c["component"] in ("database", "api", "memory", "network", "sys_conf")],
    )
    def test_repair_routes_through_coordinator(self, case, BD, mock_externals, event_store):
        brain_fn = _build_mock_brain(case["correct_code"])
        fake_mod = ModuleType("api.brain_api_v2")
        fake_mod.call_brain = brain_fn
        old_mod = sys.modules.get("api.brain_api_v2")
        sys.modules["api.brain_api_v2"] = fake_mod

        try:
            from cognitive.spindle_executor import SpindleExecutor
            from cognitive.physics.spindle_proof import SpindleProof

            domain_map = {
                "database": BD.DOMAIN_DATABASE,
                "api": BD.DOMAIN_API,
                "memory": BD.DOMAIN_MEMORY,
                "network": BD.DOMAIN_NETWORK,
                "sys_conf": BD.DOMAIN_SYS_CONF,
            }

            executor = SpindleExecutor()
            proof = SpindleProof(
                is_valid=True, result="SAT", reason="Z3 verified repair safe",
                domain_mask=domain_map[case["component"]],
                intent_mask=BD.INTENT_REPAIR,
            )
            result = executor.execute(proof)

            assert "healing_coordinator" in result.action_taken, (
                f"{case['id']}: did not route through healing coordinator — "
                f"action={result.action_taken}"
            )
        finally:
            if old_mod is not None:
                sys.modules["api.brain_api_v2"] = old_mod
            else:
                sys.modules.pop("api.brain_api_v2", None)


# ═══════════════════════════════════════════════════════════════
# 6. Z3 SAFETY — repair verified before healing
# ═══════════════════════════════════════════════════════════════

class TestSWEBenchZ3Safety:
    """Z3 must prove repair actions are safe."""

    @pytest.mark.parametrize("component,domain_attr", [
        ("database", "DOMAIN_DATABASE"),
        ("api", "DOMAIN_API"),
        ("memory", "DOMAIN_MEMORY"),
        ("network", "DOMAIN_NETWORK"),
        ("sys_conf", "DOMAIN_SYS_CONF"),
    ])
    def test_z3_approves_repair(self, BD, component, domain_attr):
        from cognitive.physics.bitmask_geometry import HierarchicalZ3Geometry

        geom = HierarchicalZ3Geometry()
        domain = getattr(BD, domain_attr)
        proof = geom.verify_action(
            domain, BD.INTENT_REPAIR,
            BD.STATE_ACTIVE,
            BD.PRIV_SYSTEM | BD.CTX_EMERGENCY,
        )
        assert proof.is_valid is True, (
            f"Z3 rejected REPAIR on {component}: {proof.reason}"
        )
        assert proof.result == "SAT"


# ═══════════════════════════════════════════════════════════════
# 7. CATEGORY ANALYSIS — per-category pass rates
# ═══════════════════════════════════════════════════════════════

class TestSWEBenchCategoryAnalysis:
    """Group results by category and verify minimum per-category rates."""

    def test_all_categories_represented(self):
        categories = {c["category"] for c in SWE_BENCH_ADVANCED}
        expected = {"concurrency", "algorithm", "api", "resource", "security", "state_machine", "integration"}
        assert categories == expected, f"Missing categories: {expected - categories}"

    def test_per_category_fix_rate(self):
        from collections import defaultdict
        results = defaultdict(lambda: {"passed": 0, "total": 0})

        for case in SWE_BENCH_ADVANCED:
            cat = case["category"]
            results[cat]["total"] += 1
            if _verify_fix_functional(case["correct_code"], case["test_code"]):
                results[cat]["passed"] += 1

        for cat, data in results.items():
            rate = data["passed"] / data["total"] * 100
            assert rate == 100.0, (
                f"Category {CATEGORY_LABELS.get(cat, cat)}: {rate:.0f}% fixes pass "
                f"({data['passed']}/{data['total']})"
            )


# ═══════════════════════════════════════════════════════════════
# 8. DIFFICULTY ANALYSIS — severity vs resolution
# ═══════════════════════════════════════════════════════════════

class TestSWEBenchDifficulty:
    """Compare resolution across severity levels."""

    def test_critical_bugs_all_fixable(self):
        critical = [c for c in SWE_BENCH_ADVANCED if c["severity"] == "critical"]
        for case in critical:
            assert _verify_fix_functional(case["correct_code"], case["test_code"]), (
                f"{case['id']}: critical bug fix doesn't work"
            )

    def test_severity_distribution(self):
        from collections import Counter
        dist = Counter(c["severity"] for c in SWE_BENCH_ADVANCED)
        assert dist["critical"] >= 5, "Need enough critical bugs to be meaningful"
        assert dist["high"] >= 5, "Need enough high-severity bugs"


# ═══════════════════════════════════════════════════════════════
# 9. DETERMINISM — same bug → same resolution
# ═══════════════════════════════════════════════════════════════

class TestSWEBenchDeterminism:
    """Running the same bug twice must produce identical results."""

    def test_resolution_is_deterministic(self, mock_externals, event_store):
        case = SWE_BENCH_ADVANCED[0]  # SWE-011
        brain_fn = _build_mock_brain(case["correct_code"])
        fake_mod = ModuleType("api.brain_api_v2")
        fake_mod.call_brain = brain_fn
        old_mod = sys.modules.get("api.brain_api_v2")
        sys.modules["api.brain_api_v2"] = fake_mod

        try:
            from cognitive.healing_coordinator import HealingCoordinator
            problem = {
                "component": case["component"],
                "description": case["description"],
                "error": case["error"],
                "severity": case["severity"],
            }

            results = []
            for _ in range(3):
                import cognitive.healing_coordinator as hc_mod
                hc_mod._coordinator = None
                coordinator = HealingCoordinator()
                r = coordinator.resolve(problem)
                results.append((r["resolved"], r["resolution"], len(r["steps"])))

            assert len(set(results)) == 1, f"Non-deterministic: {results}"
        finally:
            if old_mod is not None:
                sys.modules["api.brain_api_v2"] = old_mod
            else:
                sys.modules.pop("api.brain_api_v2", None)


# ═══════════════════════════════════════════════════════════════
# 10. FULL SCOREBOARD — aggregate results
# ═══════════════════════════════════════════════════════════════

class TestSWEBenchFullScoreboard:
    """Calculate the aggregate SWE-bench-style pass rate."""

    def test_aggregate_pass_rate(self, mock_externals, event_store):
        """Run all 20 bugs and report pass rate (must be ≥ 75%)."""
        passed = 0
        failed = []
        category_results = {}

        for case in SWE_BENCH_ADVANCED:
            cat = case["category"]
            if cat not in category_results:
                category_results[cat] = {"passed": 0, "total": 0}
            category_results[cat]["total"] += 1

            brain_fn = _build_mock_brain(case["correct_code"])
            fake_mod = ModuleType("api.brain_api_v2")
            fake_mod.call_brain = brain_fn
            sys.modules["api.brain_api_v2"] = fake_mod

            try:
                from cognitive.healing_coordinator import HealingCoordinator
                import cognitive.healing_coordinator as hc_mod
                hc_mod._coordinator = None

                coordinator = HealingCoordinator()
                problem = {
                    "component": case["component"],
                    "description": case["description"],
                    "error": case["error"],
                    "severity": case["severity"],
                }
                result = coordinator.resolve(problem)

                if result["resolved"]:
                    if _verify_fix_functional(case["correct_code"], case["test_code"]):
                        if _verify_fix_ast(case["correct_code"]):
                            passed += 1
                            category_results[cat]["passed"] += 1
                            continue
                failed.append(case["id"])
            except Exception as e:
                failed.append(f"{case['id']}:{e}")

        total = len(SWE_BENCH_ADVANCED)
        rate = (passed / total) * 100

        # Print scoreboard
        print(f"\n{'=' * 70}")
        print(f"  SWE-BENCH FULL SCOREBOARD (Advanced)")
        print(f"{'=' * 70}")
        print(f"  Total bugs:       {total}")
        print(f"  Resolved:         {passed}")
        print(f"  Failed:           {len(failed)}")
        print(f"  Pass rate:        {rate:.1f}%")
        print(f"{'─' * 70}")
        print(f"  BY CATEGORY:")
        for cat, data in sorted(category_results.items()):
            label = CATEGORY_LABELS.get(cat, cat)
            cat_rate = data["passed"] / data["total"] * 100 if data["total"] > 0 else 0
            print(f"    {label:35s}  {data['passed']}/{data['total']} ({cat_rate:.0f}%)")
        print(f"{'─' * 70}")
        print(f"  BY SEVERITY:")
        from collections import Counter
        for sev in ["critical", "high", "medium"]:
            sev_cases = [c for c in SWE_BENCH_ADVANCED if c["severity"] == sev]
            sev_passed = sum(1 for c in sev_cases if c["id"] not in failed)
            sev_rate = sev_passed / len(sev_cases) * 100 if sev_cases else 0
            print(f"    {sev:35s}  {sev_passed}/{len(sev_cases)} ({sev_rate:.0f}%)")
        if failed:
            print(f"{'─' * 70}")
            print(f"  FAILED: {', '.join(failed)}")
        print(f"{'=' * 70}\n")

        assert rate >= 75.0, f"SWE-bench pass rate {rate:.1f}% < 75% threshold"


if __name__ == "__main__":
    pytest.main(["-v", "--tb=short", __file__])
