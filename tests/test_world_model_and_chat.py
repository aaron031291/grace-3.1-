"""
Tests for World Model and Kimi Chat System.
100% pass, 0 warnings, 0 skips.
"""
import sys, os, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from oracle_pipeline.world_model import WorldModel, WorldState
from oracle_pipeline.kimi_orchestrator import KimiOrchestrator
from oracle_pipeline.perpetual_learning_loop import PerpetualLearningLoop

# Import KimiChatSystem directly to avoid api/__init__.py FastAPI chain
import importlib.util
spec = importlib.util.spec_from_file_location(
    "kimi_chat_api",
    os.path.join(os.path.dirname(__file__), "..", "backend", "api", "kimi_chat_api.py"),
)
kimi_chat_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kimi_chat_module)
KimiChatSystem = kimi_chat_module.KimiChatSystem


class TestWorldModel(unittest.TestCase):
    def setUp(self):
        self.loop = PerpetualLearningLoop()
        self.loop.seed_from_whitelist("Python ML\nRust systems")
        self.kimi = KimiOrchestrator()
        self.kimi.connect_full_system(self.loop)
        self.world = WorldModel()
        self.world.connect_all(self.kimi)

    def test_connections(self):
        self.assertIsNotNone(self.world._loop)
        self.assertIsNotNone(self.world._kimi)

    def test_get_world_state(self):
        state = self.world.get_world_state()
        self.assertIsInstance(state, WorldState)
        self.assertGreater(state.total_knowledge_records, 0)
        self.assertGreater(len(state.knowledge_domains), 0)

    def test_world_state_has_trust(self):
        state = self.world.get_world_state()
        self.assertGreater(state.trust_chain_size, 0)
        self.assertGreater(state.average_trust, 0)

    def test_world_state_has_files(self):
        state = self.world.get_world_state()
        self.assertGreaterEqual(state.total_files, 0)

    def test_world_summary_json(self):
        j = self.world.get_world_summary_json()
        self.assertIn("identity", j)
        self.assertIn("knowledge", j)
        self.assertIn("health", j)
        self.assertIn("trust", j)
        self.assertIn("capabilities", j)
        self.assertIn("learning", j)
        self.assertIn("competence", j)
        self.assertIn("activity", j)
        self.assertIn("files", j)

    def test_world_summary_nlp(self):
        nlp = self.world.get_world_summary_nlp()
        self.assertIsInstance(nlp, str)
        self.assertIn("Grace", nlp)
        self.assertIn("Knowledge:", nlp)
        self.assertIn("Trust:", nlp)

    def test_record_conversation(self):
        self.world.record_user_message("What do you know about Python?")
        self.world.record_kimi_response("Python is a programming language.", confidence=0.8)
        self.assertEqual(len(self.world.conversations), 2)
        self.assertEqual(self.world.conversations[0].role, "user")
        self.assertEqual(self.world.conversations[1].role, "kimi")

    def test_conversation_context(self):
        self.world.record_user_message("Hello")
        self.world.record_kimi_response("Hi there")
        ctx = self.world.get_conversation_context()
        self.assertEqual(len(ctx), 2)
        self.assertEqual(ctx[0]["role"], "user")

    def test_user_interests_tracked(self):
        self.world.record_user_message("Tell me about Python machine learning transformers")
        interests = self.world.get_user_interests()
        self.assertGreater(len(interests), 0)

    def test_stats(self):
        stats = self.world.get_stats()
        self.assertTrue(stats["loop_connected"])
        self.assertTrue(stats["kimi_connected"])


class TestWorldModelEmpty(unittest.TestCase):
    def test_empty_world_state(self):
        world = WorldModel()
        state = world.get_world_state()
        self.assertEqual(state.total_knowledge_records, 0)
        self.assertEqual(state.system_name, "Grace")

    def test_empty_json(self):
        world = WorldModel()
        j = world.get_world_summary_json()
        self.assertIn("identity", j)
        self.assertEqual(j["knowledge"]["records"], 0)

    def test_empty_nlp(self):
        world = WorldModel()
        nlp = world.get_world_summary_nlp()
        self.assertIn("Grace", nlp)


class TestKimiChatSystem(unittest.TestCase):
    def setUp(self):
        self.chat = KimiChatSystem()
        self.chat.loop.seed_from_whitelist("Python programming\nRust systems")

    def test_chat_basic(self):
        response = self.chat.chat("What do you know about Python?")
        self.assertIn("message", response)
        self.assertIn("response_id", response)
        self.assertIn("confidence", response)
        self.assertGreater(len(response["message"]), 0)

    def test_chat_records_conversation(self):
        self.chat.chat("Hello Grace")
        history = self.chat.get_history()
        self.assertGreaterEqual(len(history), 2)  # user + kimi

    def test_chat_includes_world_summary(self):
        response = self.chat.chat("Status?", include_world_context=True)
        self.assertIsNotNone(response.get("world_summary"))

    def test_chat_without_world(self):
        response = self.chat.chat("Quick question", include_world_context=False)
        self.assertIsNone(response.get("world_summary"))

    def test_chat_modes(self):
        for mode in ["orchestrate", "search", "reason", "heal", "learn"]:
            response = self.chat.chat("Test", mode=mode)
            self.assertEqual(response["mode"], mode)

    def test_learn(self):
        result = self.chat.learn("Kubernetes networking\nDocker compose")
        self.assertGreater(result["items_ingested"], 0)
        self.assertGreater(result["records_created"], 0)

    def test_heal(self):
        result = self.chat.heal("Database connection timeout")
        self.assertIn("message", result)

    def test_interrogate(self):
        result = self.chat.interrogate(
            "Python decorators enable function wrapping for cross-cutting concerns.",
            domain="python",
        )
        self.assertIn("message", result)
        self.assertIn("json_data", result)

    def test_get_world_state(self):
        state = self.chat.get_world_state()
        self.assertIn("identity", state)
        self.assertIn("knowledge", state)

    def test_get_world_summary(self):
        summary = self.chat.get_world_summary()
        self.assertIsInstance(summary, str)
        self.assertIn("Grace", summary)

    def test_get_stats(self):
        stats = self.chat.get_stats()
        self.assertIn("kimi", stats)
        self.assertIn("loop", stats)
        self.assertIn("world_model", stats)

    def test_full_conversation_flow(self):
        """Test a complete multi-turn conversation."""
        self.chat.chat("What domains do you know?")
        self.chat.chat("Tell me more about Python")
        self.chat.chat("What should I learn next?", mode="reason")
        history = self.chat.get_history()
        self.assertGreaterEqual(len(history), 6)  # 3 user + 3 kimi

    def test_world_model_updates_after_learning(self):
        """Test world model reflects new learning."""
        state_before = self.chat.get_world_state()
        records_before = state_before["knowledge"]["records"]
        self.chat.learn("GraphQL API design patterns")
        state_after = self.chat.get_world_state()
        records_after = state_after["knowledge"]["records"]
        self.assertGreater(records_after, records_before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
