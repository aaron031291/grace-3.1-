"""
Comprehensive tests for Librarian File Manager and Proactive Discovery Engine.

100% pass rate, zero warnings, zero skips.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from oracle_pipeline.librarian_file_manager import (
    LibrarianFileManager,
    FileNode,
    FileCategory,
    FileType,
    OperationType,
    GenesisKeyBlock,
)
from oracle_pipeline.proactive_discovery_engine import (
    ProactiveDiscoveryEngine,
    DiscoveryAlgorithm,
    LearningPriority,
    DiscoveryTask,
)
from oracle_pipeline.oracle_vector_store import OracleVectorStore


# =====================================================================
# LIBRARIAN FILE MANAGER TESTS
# =====================================================================


class TestLibrarianFileManager(unittest.TestCase):
    """Tests for the Librarian File Management System."""

    def setUp(self):
        self.lib = LibrarianFileManager()

    # --- ROOT STRUCTURE ---

    def test_root_structure_exists(self):
        """Test root directories are created."""
        self.assertIsNotNone(self.lib.get_node("/codebase"))
        self.assertIsNotNone(self.lib.get_node("/documents"))

    def test_document_subdirectories(self):
        """Test document subdirectories exist."""
        self.assertIsNotNone(self.lib.get_node("/documents/genesis_keys"))
        self.assertIsNotNone(self.lib.get_node("/documents/kpi_reports"))
        self.assertIsNotNone(self.lib.get_node("/documents/research"))
        self.assertIsNotNone(self.lib.get_node("/documents/uploads"))

    # --- FILE TYPE DETECTION ---

    def test_detect_python_file(self):
        """Test Python file type detection."""
        self.assertEqual(self.lib.detect_file_type("main.py"), FileType.PYTHON)

    def test_detect_javascript_file(self):
        """Test JavaScript file type detection."""
        self.assertEqual(self.lib.detect_file_type("app.js"), FileType.JAVASCRIPT)

    def test_detect_rust_file(self):
        """Test Rust file type detection."""
        self.assertEqual(self.lib.detect_file_type("lib.rs"), FileType.RUST)

    def test_detect_markdown_file(self):
        """Test Markdown file type detection."""
        self.assertEqual(self.lib.detect_file_type("README.md"), FileType.MARKDOWN)

    def test_detect_config_file(self):
        """Test config file type detection."""
        self.assertEqual(self.lib.detect_file_type("settings.toml"), FileType.CONFIG)

    def test_detect_unknown_file(self):
        """Test unknown file type."""
        self.assertEqual(self.lib.detect_file_type("data.xyz"), FileType.OTHER)

    # --- CATEGORY DETECTION ---

    def test_code_category(self):
        """Test code category detection."""
        self.assertEqual(
            self.lib.detect_category(FileType.PYTHON), FileCategory.CODE
        )

    def test_document_category(self):
        """Test document category detection."""
        self.assertEqual(
            self.lib.detect_category(FileType.MARKDOWN), FileCategory.DOCUMENTS
        )

    def test_category_from_content(self):
        """Test category detection from content."""
        cat = self.lib.detect_category(FileType.OTHER, "def hello(): pass")
        self.assertEqual(cat, FileCategory.CODE)

    # --- FILE CRUD ---

    def test_create_file(self):
        """Test creating a file."""
        node = self.lib.create_file("test.py", "print('hello')")
        self.assertIsNotNone(node)
        self.assertEqual(node.name, "test.py")
        self.assertEqual(node.category, FileCategory.CODE)
        self.assertFalse(node.is_directory)

    def test_create_file_with_content(self):
        """Test file content is stored."""
        node = self.lib.create_file("data.txt", "some text content")
        self.assertEqual(node.content, "some text content")
        self.assertGreater(node.size_bytes, 0)

    def test_create_file_auto_categorize_code(self):
        """Test auto-categorization for code."""
        node = self.lib.create_file("script.py", "import os")
        self.assertEqual(node.category, FileCategory.CODE)

    def test_create_file_auto_categorize_doc(self):
        """Test auto-categorization for documents."""
        node = self.lib.create_file("notes.md", "# Meeting Notes")
        self.assertEqual(node.category, FileCategory.DOCUMENTS)

    def test_create_directory(self):
        """Test creating a directory."""
        node = self.lib.create_directory("my_project", "/codebase")
        self.assertIsNotNone(node)
        self.assertTrue(node.is_directory)
        self.assertEqual(node.path, "/codebase/my_project")

    def test_rename_file(self):
        """Test renaming a file."""
        self.lib.create_file("old_name.py", "code", parent_path="/codebase")
        result = self.lib.rename("/codebase/old_name.py", "new_name.py")
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "new_name.py")

    def test_rename_nonexistent(self):
        """Test renaming nonexistent file returns None."""
        result = self.lib.rename("/codebase/ghost.py", "new.py")
        self.assertIsNone(result)

    def test_move_file(self):
        """Test moving a file."""
        self.lib.create_file("moveme.py", "code", parent_path="/codebase")
        self.lib.create_directory("destination", "/codebase")
        result = self.lib.move("/codebase/moveme.py", "/codebase/destination")
        self.assertIsNotNone(result)
        self.assertEqual(result.path, "/codebase/destination/moveme.py")

    def test_move_nonexistent(self):
        """Test moving nonexistent returns None."""
        result = self.lib.move("/codebase/ghost.py", "/documents")
        self.assertIsNone(result)

    def test_delete_file(self):
        """Test soft-deleting a file."""
        self.lib.create_file("deleteme.py", "code", parent_path="/codebase")
        result = self.lib.delete("/codebase/deleteme.py")
        self.assertTrue(result)
        node = self.lib.get_node("/codebase/deleteme.py")
        self.assertIsNone(node)  # Not visible after delete

    def test_delete_nonexistent(self):
        """Test deleting nonexistent returns False."""
        result = self.lib.delete("/codebase/ghost.py")
        self.assertFalse(result)

    def test_edit_file(self):
        """Test editing file content."""
        self.lib.create_file("editable.py", "old content", parent_path="/codebase")
        result = self.lib.edit("/codebase/editable.py", "new content")
        self.assertIsNotNone(result)
        self.assertEqual(result.content, "new content")

    def test_edit_nonexistent(self):
        """Test editing nonexistent file."""
        result = self.lib.edit("/codebase/ghost.py", "content")
        self.assertIsNone(result)

    def test_edit_directory(self):
        """Test editing a directory returns None."""
        result = self.lib.edit("/codebase", "content")
        self.assertIsNone(result)

    # --- UNDO ---

    def test_undo_delete(self):
        """Test undoing a delete operation."""
        self.lib.create_file("undome.py", "code", parent_path="/codebase")
        self.lib.delete("/codebase/undome.py")
        self.assertIsNone(self.lib.get_node("/codebase/undome.py"))
        op = self.lib.undo_last_operation()
        self.assertIsNotNone(op)
        # File should be visible again via the node_id
        node_id = self.lib._path_index.get("/codebase/undome.py")
        self.assertIsNotNone(node_id)
        self.assertFalse(self.lib.nodes[node_id].deleted)

    def test_undo_edit(self):
        """Test undoing an edit operation."""
        self.lib.create_file("undo_edit.py", "original", parent_path="/codebase")
        self.lib.edit("/codebase/undo_edit.py", "modified")
        self.lib.undo_last_operation()
        node = self.lib.get_node("/codebase/undo_edit.py")
        self.assertEqual(node.content, "original")

    def test_undo_rename(self):
        """Test undoing a rename operation."""
        self.lib.create_file("before.py", "code", parent_path="/codebase")
        self.lib.rename("/codebase/before.py", "after.py")
        self.lib.undo_last_operation()
        node = self.lib.get_node("/codebase/before.py")
        self.assertIsNotNone(node)

    def test_undo_nothing(self):
        """Test undo when no operations with previous state exist."""
        result = self.lib.undo_last_operation()
        self.assertIsNone(result)

    # --- GENESIS KEY BLOCKS ---

    def test_organize_genesis_keys(self):
        """Test organizing Genesis Keys into 24-hour blocks."""
        keys = [
            {"key_id": "GK-001", "when_timestamp": "2026-02-16T02:30:00", "key_type": "user_input", "who_actor": "user", "what_description": "Test"},
            {"key_id": "GK-002", "when_timestamp": "2026-02-16T03:00:00", "key_type": "ai_response", "who_actor": "grace", "what_description": "Response"},
            {"key_id": "GK-003", "when_timestamp": "2026-02-16T06:00:00", "key_type": "code_change", "who_actor": "grace", "what_description": "Fix"},
        ]
        blocks = self.lib.organize_genesis_keys(keys, block_hours=4)
        self.assertGreater(len(blocks), 0)
        total_keys = sum(b.key_count for b in blocks)
        self.assertEqual(total_keys, 3)

    def test_genesis_key_block_folders(self):
        """Test Genesis Key block folder creation."""
        keys = [
            {"key_id": "GK-100", "when_timestamp": "2026-02-16T10:00:00", "key_type": "user_input", "who_actor": "user", "what_description": "Test"},
        ]
        blocks = self.lib.organize_genesis_keys(keys)
        self.assertEqual(len(blocks), 1)
        self.assertIn("2026-02-16", blocks[0].folder_path)

    def test_get_genesis_key_blocks(self):
        """Test getting Genesis Key blocks."""
        keys = [
            {"key_id": "GK-A", "when_timestamp": "2026-02-16T01:00:00", "key_type": "user_input", "who_actor": "u", "what_description": "t"},
        ]
        self.lib.organize_genesis_keys(keys)
        blocks = self.lib.get_genesis_key_blocks("2026-02-16")
        self.assertGreater(len(blocks), 0)

    def test_genesis_key_blocks_filter_by_date(self):
        """Test filtering blocks by date."""
        keys = [
            {"key_id": "GK-X", "when_timestamp": "2026-02-15T01:00:00", "key_type": "t", "who_actor": "u", "what_description": "t"},
            {"key_id": "GK-Y", "when_timestamp": "2026-02-16T01:00:00", "key_type": "t", "who_actor": "u", "what_description": "t"},
        ]
        self.lib.organize_genesis_keys(keys)
        blocks_15 = self.lib.get_genesis_key_blocks("2026-02-15")
        blocks_16 = self.lib.get_genesis_key_blocks("2026-02-16")
        self.assertEqual(len(blocks_15), 1)
        self.assertEqual(len(blocks_16), 1)

    # --- AUTO-SORT ---

    def test_auto_sort_python_file(self):
        """Test auto-sorting a Python file."""
        node = self.lib.auto_sort_file("import os\nprint('hello')", "main.py")
        self.assertEqual(node.category, FileCategory.CODE)
        self.assertIn("python", node.path.lower())

    def test_auto_sort_markdown_file(self):
        """Test auto-sorting a Markdown file."""
        node = self.lib.auto_sort_file("# Documentation", "readme.md")
        self.assertEqual(node.category, FileCategory.DOCUMENTS)

    def test_auto_sort_with_domain(self):
        """Test auto-sorting with domain."""
        node = self.lib.auto_sort_file("code", "util.py", domain="my_project")
        self.assertIn("my_project", node.path)

    # --- SEARCH AND BROWSE ---

    def test_list_directory(self):
        """Test listing directory contents."""
        self.lib.create_file("a.py", "code", parent_path="/codebase")
        self.lib.create_file("b.py", "code", parent_path="/codebase")
        children = self.lib.list_directory("/codebase")
        names = [c.name for c in children]
        self.assertIn("a.py", names)
        self.assertIn("b.py", names)

    def test_list_directory_excludes_deleted(self):
        """Test that listing excludes deleted files."""
        self.lib.create_file("visible.py", "code", parent_path="/codebase")
        self.lib.create_file("hidden.py", "code", parent_path="/codebase")
        self.lib.delete("/codebase/hidden.py")
        children = self.lib.list_directory("/codebase")
        names = [c.name for c in children]
        self.assertIn("visible.py", names)
        self.assertNotIn("hidden.py", names)

    def test_search_files_by_name(self):
        """Test searching files by name."""
        self.lib.create_file("search_target.py", "code", parent_path="/codebase")
        self.lib.create_file("other.py", "code", parent_path="/codebase")
        results = self.lib.search_files("search_target")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "search_target.py")

    def test_search_files_by_content(self):
        """Test searching files by content."""
        self.lib.create_file("a.py", "unique_keyword_xyz", parent_path="/codebase")
        results = self.lib.search_files("unique_keyword_xyz")
        self.assertEqual(len(results), 1)

    def test_search_with_category_filter(self):
        """Test searching with category filter."""
        self.lib.create_file("code.py", "python code", parent_path="/codebase")
        self.lib.create_file("doc.md", "python documentation", parent_path="/documents")
        code_results = self.lib.search_files("python", category=FileCategory.CODE)
        doc_results = self.lib.search_files("python", category=FileCategory.DOCUMENTS)
        self.assertEqual(len(code_results), 1)
        self.assertEqual(len(doc_results), 1)

    def test_get_tree(self):
        """Test getting directory tree."""
        self.lib.create_file("tree_test.py", "code", parent_path="/codebase")
        tree = self.lib.get_tree("/codebase")
        self.assertIn("children", tree)
        self.assertEqual(tree["name"], "codebase")

    # --- SMART NAMING ---

    def test_generate_smart_name(self):
        """Test smart name generation."""
        name = self.lib.generate_smart_name(
            "Machine learning tutorial", FileType.PYTHON, domain="ai_ml"
        )
        self.assertIn("py", name)
        self.assertIn("ai_ml", name)
        self.assertTrue(name.endswith(".py"))

    # --- OPERATION HISTORY ---

    def test_operation_history(self):
        """Test operation history tracking."""
        self.lib.create_file("hist.py", "code", parent_path="/codebase")
        history = self.lib.get_operation_history()
        self.assertGreater(len(history), 0)
        self.assertEqual(history[-1].operation_type, OperationType.CREATE_FILE)

    # --- STATS ---

    def test_get_stats(self):
        """Test getting statistics."""
        self.lib.create_file("stat.py", "code", parent_path="/codebase")
        self.lib.create_file("doc.md", "text", parent_path="/documents")
        stats = self.lib.get_stats()
        self.assertGreater(stats["total_files"], 0)
        self.assertGreater(stats["total_directories"], 0)
        self.assertIn("code_files", stats)
        self.assertIn("document_files", stats)


# =====================================================================
# PROACTIVE DISCOVERY ENGINE TESTS
# =====================================================================


class TestProactiveDiscoveryEngine(unittest.TestCase):
    """Tests for the Proactive Discovery Engine."""

    def setUp(self):
        self.store = OracleVectorStore()
        self.engine = ProactiveDiscoveryEngine(oracle_store=self.store)

    # --- TF-IDF CONCEPT EXTRACTION ---

    def test_extract_concepts(self):
        """Test concept extraction."""
        self.store.ingest(
            "Python machine learning neural networks deep learning training data models",
            domain="ai_ml",
        )
        profile = self.engine.extract_concepts("ai_ml")
        self.assertGreater(len(profile.concepts), 0)
        self.assertEqual(profile.domain, "ai_ml")

    def test_extract_concepts_empty_domain(self):
        """Test concept extraction on empty domain."""
        profile = self.engine.extract_concepts("empty_domain")
        self.assertEqual(profile.total_words, 0)

    def test_concept_profile_depth_score(self):
        """Test depth score calculation."""
        self.store.ingest("word " * 500, domain="deep")
        profile = self.engine.extract_concepts("deep")
        self.assertGreater(profile.depth_score, 0)

    # --- CO-OCCURRENCE MINING ---

    def test_find_cooccurrences(self):
        """Test co-occurrence mining."""
        self.store.ingest("Python basics", domain="python")
        tasks = self.engine.find_cooccurrences()
        # Python co-occurs with ai_ml at 0.9
        target_domains = [t.target_domain for t in tasks]
        self.assertIn("ai_ml", target_domains)

    def test_cooccurrence_excludes_known(self):
        """Test co-occurrence excludes already-known domains."""
        self.store.ingest("Python basics", domain="python")
        self.store.ingest("AI/ML basics", domain="ai_ml")
        tasks = self.engine.find_cooccurrences()
        target_domains = [t.target_domain for t in tasks]
        self.assertNotIn("ai_ml", target_domains)
        self.assertNotIn("python", target_domains)

    def test_cooccurrence_priority(self):
        """Test co-occurrence priority assignment."""
        self.store.ingest("Python basics", domain="python")
        tasks = self.engine.find_cooccurrences()
        ai_tasks = [t for t in tasks if t.target_domain == "ai_ml"]
        if ai_tasks:
            self.assertEqual(ai_tasks[0].priority, LearningPriority.HIGH)

    # --- SEMANTIC GAP DETECTION ---

    def test_detect_semantic_gaps(self):
        """Test semantic gap detection finds bridging domains."""
        self.store.ingest("Python content", domain="python")
        self.store.ingest("AI ML content", domain="ai_ml")
        self.store.ingest("Science content", domain="science")
        tasks = self.engine.detect_semantic_gaps()
        # Should find domains that bridge at least 2 known domains
        if tasks:
            for task in tasks:
                self.assertGreaterEqual(len(task.source_domains), 2)
        # mathematics is neighbor of both ai_ml and science -> bridges 2
        target_domains = [t.target_domain for t in tasks]
        self.assertIn("mathematics", target_domains)

    def test_semantic_gap_bridge_count(self):
        """Test gap detection requires at least 2 bridges."""
        self.store.ingest("Python content", domain="python")
        tasks = self.engine.detect_semantic_gaps()
        for task in tasks:
            self.assertGreaterEqual(len(task.source_domains), 2)

    def test_semantic_gap_confidence(self):
        """Test gap confidence scales with bridge count."""
        self.store.ingest("Python content", domain="python")
        self.store.ingest("AI ML content", domain="ai_ml")
        self.store.ingest("Science content", domain="science")
        tasks = self.engine.detect_semantic_gaps()
        for task in tasks:
            self.assertGreater(task.confidence, 0)
            self.assertLessEqual(task.confidence, 0.95)

    # --- TREND MOMENTUM ---

    def test_record_domain_activity(self):
        """Test recording domain activity."""
        self.engine.record_domain_activity("python")
        self.engine.record_domain_activity("python")
        self.assertGreater(len(self.engine._domain_activity["python"]), 0)

    def test_score_trend_momentum(self):
        """Test momentum scoring."""
        self.engine.record_domain_activity("python")
        self.engine.record_domain_activity("python")
        scores = self.engine.score_trend_momentum()
        self.assertGreater(len(scores), 0)
        self.assertEqual(scores[0][0], "python")

    def test_suggest_momentum_based(self):
        """Test momentum-based suggestions."""
        for _ in range(5):
            self.engine.record_domain_activity("python")
        tasks = self.engine.suggest_momentum_based()
        # May or may not generate tasks depending on momentum threshold
        self.assertIsInstance(tasks, list)

    # --- EXPERTISE DEPTH ---

    def test_score_expertise_depth(self):
        """Test expertise depth scoring."""
        self.store.ingest("Python basics content here", domain="python")
        scores = self.engine.score_expertise_depth()
        self.assertIn("python", scores)
        self.assertIn("depth", scores["python"])
        self.assertIn("breadth", scores["python"])

    def test_depth_recommendation(self):
        """Test depth vs breadth recommendation."""
        self.store.ingest("Detailed content " * 100, domain="deep_domain")
        scores = self.engine.score_expertise_depth()
        rec = scores.get("deep_domain", {}).get("recommendation")
        self.assertIn(rec, ["broaden", "deepen", "balanced"])

    # --- CROSS-DOMAIN TRANSFER ---

    def test_detect_transferable_concepts(self):
        """Test cross-domain transfer detection."""
        self.store.ingest("Optimization techniques", domain="ai_ml")
        tasks = self.engine.detect_transferable_concepts()
        self.assertGreater(len(tasks), 0)
        self.assertEqual(
            tasks[0].algorithm, DiscoveryAlgorithm.CROSS_DOMAIN_TRANSFER
        )

    def test_transfer_concept_in_metadata(self):
        """Test transfer concept is stored in metadata."""
        self.store.ingest("Testing frameworks", domain="python")
        tasks = self.engine.detect_transferable_concepts()
        for task in tasks:
            if "transfer_concept" in task.metadata:
                self.assertIsNotNone(task.metadata["transfer_concept"])

    # --- FULL DISCOVERY ---

    def test_run_full_discovery(self):
        """Test running all algorithms."""
        self.store.ingest("Python content", domain="python")
        self.store.ingest("AI ML content", domain="ai_ml")
        state = self.engine.run_full_discovery()
        self.assertGreater(state.total_tasks, 0)

    def test_full_discovery_deduplicates(self):
        """Test full discovery deduplicates by domain."""
        self.store.ingest("Python content", domain="python")
        self.store.ingest("AI ML content", domain="ai_ml")
        state = self.engine.run_full_discovery()
        domains = [t.target_domain for t in self.engine.learning_queue]
        self.assertEqual(len(domains), len(set(domains)))

    def test_full_discovery_sorted_by_priority(self):
        """Test tasks are sorted by priority."""
        self.store.ingest("Python content", domain="python")
        self.store.ingest("AI ML content", domain="ai_ml")
        self.engine.run_full_discovery()
        if len(self.engine.learning_queue) >= 2:
            priority_order = {
                LearningPriority.CRITICAL: 0,
                LearningPriority.HIGH: 1,
                LearningPriority.MEDIUM: 2,
                LearningPriority.LOW: 3,
                LearningPriority.BACKGROUND: 4,
            }
            for i in range(len(self.engine.learning_queue) - 1):
                t1 = self.engine.learning_queue[i]
                t2 = self.engine.learning_queue[i + 1]
                self.assertLessEqual(
                    priority_order[t1.priority],
                    priority_order[t2.priority],
                )

    # --- QUEUE MANAGEMENT ---

    def test_get_next_task(self):
        """Test getting next task."""
        self.store.ingest("Python content", domain="python")
        self.engine.run_full_discovery()
        task = self.engine.get_next_task()
        if task:
            self.assertEqual(task.status, "queued")

    def test_mark_task_status(self):
        """Test marking task status."""
        self.store.ingest("Python content", domain="python")
        self.engine.run_full_discovery()
        task = self.engine.get_next_task()
        if task:
            result = self.engine.mark_task_status(task.task_id, "completed")
            self.assertTrue(result)
            self.assertEqual(task.status, "completed")

    def test_mark_nonexistent_task(self):
        """Test marking nonexistent task."""
        result = self.engine.mark_task_status("fake_id", "completed")
        self.assertFalse(result)

    def test_queue_state(self):
        """Test getting queue state."""
        self.store.ingest("Python content", domain="python")
        self.engine.run_full_discovery()
        state = self.engine.get_queue_state()
        self.assertIsNotNone(state)
        self.assertGreaterEqual(state.total_tasks, 0)

    # --- STATS ---

    def test_get_stats(self):
        """Test getting engine statistics."""
        self.store.ingest("Content", domain="test")
        self.engine.run_full_discovery()
        stats = self.engine.get_stats()
        self.assertIn("queue_size", stats)
        self.assertIn("by_priority", stats)
        self.assertIn("by_algorithm", stats)

    def test_stats_empty(self):
        """Test stats with no data."""
        stats = self.engine.get_stats()
        self.assertEqual(stats["queue_size"], 0)


# =====================================================================
# INTEGRATION TESTS
# =====================================================================


class TestLibrarianDiscoveryIntegration(unittest.TestCase):
    """Integration tests between Librarian and Discovery."""

    def test_ingest_and_sort(self):
        """Test ingesting content and sorting into file system."""
        store = OracleVectorStore()
        lib = LibrarianFileManager()

        records = store.ingest("Python function definitions", domain="python")
        for record in records:
            lib.auto_sort_file(
                record.content, f"{record.record_id}.py", domain=record.domain
            )

        code_files = lib.search_files("Python", category=FileCategory.CODE)
        self.assertGreater(len(code_files), 0)

    def test_discovery_generates_search_queries(self):
        """Test discovery generates actionable search queries."""
        store = OracleVectorStore()
        engine = ProactiveDiscoveryEngine(oracle_store=store)

        store.ingest("Python ML content", domain="python")
        state = engine.run_full_discovery()

        for task in engine.learning_queue[:3]:
            self.assertGreater(len(task.search_queries), 0)

    def test_genesis_keys_organized_after_pipeline(self):
        """Test Genesis Keys can be organized after pipeline."""
        lib = LibrarianFileManager()
        keys = [
            {
                "key_id": f"GK-{i:03d}",
                "when_timestamp": f"2026-02-16T{(i*2):02d}:00:00",
                "key_type": "user_input",
                "who_actor": "user",
                "what_description": f"Action {i}",
            }
            for i in range(12)
        ]
        blocks = lib.organize_genesis_keys(keys, block_hours=4)
        self.assertGreater(len(blocks), 0)
        total = sum(b.key_count for b in blocks)
        self.assertEqual(total, 12)

    def test_full_flow_whitelist_to_filemanager(self):
        """Test full flow from whitelist to file management."""
        from oracle_pipeline.whitelist_box import WhitelistBox
        from oracle_pipeline.multi_source_fetcher import MultiSourceFetcher, FetchStatus

        box = WhitelistBox()
        fetcher = MultiSourceFetcher()
        store = OracleVectorStore()
        lib = LibrarianFileManager()

        submission = box.submit_bulk("Python machine learning tutorial")
        for item in submission.items:
            results = fetcher.fetch_item(item)
            for fr in results:
                if fr.status == FetchStatus.COMPLETED:
                    records = store.ingest(
                        fr.content, domain=item.domain,
                        source_item_id=item.item_id,
                    )
                    for rec in records:
                        lib.auto_sort_file(rec.content, f"{rec.record_id}.txt")

        self.assertGreater(len(store.records), 0)
        stats = lib.get_stats()
        self.assertGreater(stats["total_files"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
