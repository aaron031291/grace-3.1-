"""
Tests for Ollama client model detection and response generation.
"""

import unittest
import time
from ollama_client.client import OllamaClient, get_ollama_client

try:
    from settings import settings
    OLLAMA_URL = settings.OLLAMA_URL
except ImportError:
    OLLAMA_URL = "http://localhost:11434"


class TestOllamaConnection(unittest.TestCase):
    """Test cases for Ollama service connectivity."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = get_ollama_client()
    
    def test_ollama_service_running(self):
        """Test that Ollama service is running and accessible."""
        print(f"\n  Checking Ollama service at {self.client.base_url}...")
        is_running = self.client.is_running()
        
        if is_running:
            print(f"  ✓ Ollama service is running")
        else:
            print(f"  ✗ Ollama service is not running at {self.client.base_url}")
        
        self.assertTrue(is_running, f"Ollama service not running at {self.client.base_url}")
    
    def test_get_available_models(self):
        """Test retrieving list of available models."""
        print(f"\n  Fetching available models...")
        
        try:
            models = self.client.get_all_models()
            
            print(f"  Found {len(models)} model(s):")
            for model in models:
                print(f"    - {model.name}")
            
            self.assertIsInstance(models, list)
            self.assertGreater(len(models), 0, "No models found in Ollama")
        except Exception as e:
            self.skipTest(f"Could not fetch models: {e}")
    
    def test_get_running_models(self):
        """Test retrieving list of running models."""
        print(f"\n  Fetching running models...")
        
        try:
            running = self.client.get_running_models()
            
            print(f"  Running models: {running}")
            self.assertIsInstance(running, list)
        except Exception as e:
            self.skipTest(f"Could not fetch running models: {e}")


class TestOllamaResponseGeneration(unittest.TestCase):
    """Test cases for generating responses from Ollama models."""
    
    @classmethod
    def setUpClass(cls):
        """Set up class fixtures."""
        cls.client = get_ollama_client()
        
        # Check if Ollama is running
        if not cls.client.is_running():
            raise unittest.SkipTest("Ollama service is not running")
        
        # Get available models
        try:
            models = cls.client.get_all_models()
            if not models:
                raise unittest.SkipTest("No models available in Ollama")
            cls.model_name = models[0].name
            print(f"\n  Using model: {cls.model_name}")
        except Exception as e:
            raise unittest.SkipTest(f"Could not get models: {e}")
        
        cls.response_times = {}
    
    @classmethod
    def tearDownClass(cls):
        """Tear down class fixtures."""
        if cls.response_times:
            print("\n" + "=" * 80)
            print("RESPONSE GENERATION PERFORMANCE SUMMARY")
            print("=" * 80)
            
            for test_name, metrics in sorted(cls.response_times.items()):
                print(f"\n{test_name}:")
                print(f"  Prompt: {metrics['prompt'][:60]}...")
                print(f"  Generation time: {metrics['gen_time']:.2f}s")
                print(f"  Response length: {len(metrics['response'])} characters")
                print(f"  Response preview: {metrics['response'][:100]}...")
    
    def setUp(self):
        """Set up for each test."""
        self.test_start_time = time.time()
    
    def tearDown(self):
        """Tear down for each test."""
        test_name = self._testMethodName
        # Store timing info if response was generated
        if hasattr(self, '_response_generated'):
            elapsed = time.time() - self.test_start_time
            self.__class__.response_times[test_name] = {
                'prompt': self._prompt,
                'response': self._response,
                'gen_time': elapsed
            }
    
    def test_simple_prompt(self):
        """Test generating response to a simple prompt."""
        print(f"\n  Test 1: Simple Prompt")
        print(f"  Model: {self.model_name}")
        
        prompt = "What is machine learning?"
        self._prompt = prompt
        
        print(f"  Prompt: '{prompt}'")
        print(f"  Generating response...")
        
        start_time = time.time()
        response = self.client.generate_response(
            model=self.model_name,
            prompt=prompt,
            stream=False,
            num_predict=100
        )
        gen_time = time.time() - start_time
        
        self._response = response
        self._response_generated = True
        
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)
        
        print(f"  ✓ Response generated in {gen_time:.2f}s")
        print(f"  Response length: {len(response)} characters")
        print(f"  Response: {response[:150]}...")
    
    def test_coding_question(self):
        """Test generating response to a coding question."""
        print(f"\n  Test 2: Coding Question")
        print(f"  Model: {self.model_name}")
        
        prompt = "Write a Python function to calculate factorial of a number"
        self._prompt = prompt
        
        print(f"  Prompt: '{prompt}'")
        print(f"  Generating response...")
        
        start_time = time.time()
        response = self.client.generate_response(
            model=self.model_name,
            prompt=prompt,
            stream=False,
            num_predict=150
        )
        gen_time = time.time() - start_time
        
        self._response = response
        self._response_generated = True
        
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)
        
        print(f"  ✓ Response generated in {gen_time:.2f}s")
        print(f"  Response length: {len(response)} characters")
        print(f"  Response: {response[:150]}...")
    
    def test_creative_writing(self):
        """Test generating creative response."""
        print(f"\n  Test 3: Creative Writing")
        print(f"  Model: {self.model_name}")
        
        prompt = "Write a short poem about artificial intelligence"
        self._prompt = prompt
        
        print(f"  Prompt: '{prompt}'")
        print(f"  Generating response...")
        
        start_time = time.time()
        response = self.client.generate_response(
            model=self.model_name,
            prompt=prompt,
            stream=False,
            temperature=0.9,
            num_predict=120
        )
        gen_time = time.time() - start_time
        
        self._response = response
        self._response_generated = True
        
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)
        
        print(f"  ✓ Response generated in {gen_time:.2f}s")
        print(f"  Response length: {len(response)} characters")
        print(f"  Response: {response[:150]}...")
    
    def test_factual_question(self):
        """Test generating response to a factual question."""
        print(f"\n  Test 4: Factual Question")
        print(f"  Model: {self.model_name}")
        
        prompt = "What is the capital of France?"
        self._prompt = prompt
        
        print(f"  Prompt: '{prompt}'")
        print(f"  Generating response...")
        
        start_time = time.time()
        response = self.client.generate_response(
            model=self.model_name,
            prompt=prompt,
            stream=False,
            temperature=0.3,
            num_predict=50
        )
        gen_time = time.time() - start_time
        
        self._response = response
        self._response_generated = True
        
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)
        
        # Check if response contains expected answer
        response_lower = response.lower()
        contains_paris = "paris" in response_lower
        
        print(f"  ✓ Response generated in {gen_time:.2f}s")
        print(f"  Response length: {len(response)} characters")
        print(f"  Contains 'Paris': {'✓' if contains_paris else '✗'}")
        print(f"  Response: {response[:150]}...")
    
    def test_multi_turn_conversation(self):
        """Test multi-turn conversation with context."""
        print(f"\n  Test 5: Multi-Turn Conversation")
        print(f"  Model: {self.model_name}")
        
        # First turn
        prompt1 = "What is Python?"
        self._prompt = prompt1
        
        print(f"  Turn 1 Prompt: '{prompt1}'")
        start_time = time.time()
        response1 = self.client.generate_response(
            model=self.model_name,
            prompt=prompt1,
            stream=False,
            num_predict=80
        )
        time1 = time.time() - start_time
        
        print(f"  ✓ Turn 1 response generated in {time1:.2f}s")
        print(f"  Response: {response1[:100]}...")
        
        # Second turn - building on first response
        prompt2 = f"Based on your previous answer about Python, what are its main uses?"
        
        print(f"\n  Turn 2 Prompt: '{prompt2}'")
        start_time = time.time()
        response2 = self.client.generate_response(
            model=self.model_name,
            prompt=prompt2,
            stream=False,
            num_predict=80
        )
        time2 = time.time() - start_time
        
        self._response = response2
        self._response_generated = True
        
        print(f"  ✓ Turn 2 response generated in {time2:.2f}s")
        print(f"  Response: {response2[:100]}...")
        
        self.assertIsInstance(response1, str)
        self.assertIsInstance(response2, str)
        self.assertGreater(len(response1), 0)
        self.assertGreater(len(response2), 0)
        
        print(f"\n  Multi-turn conversation completed successfully")
        print(f"  Total time: {time1 + time2:.2f}s")
    
    def test_response_with_different_temperatures(self):
        """Test that different temperature values produce different responses."""
        print(f"\n  Test 6: Temperature Effects")
        print(f"  Model: {self.model_name}")
        
        prompt = "Tell me something interesting"
        self._prompt = prompt
        
        print(f"  Prompt: '{prompt}'")
        print(f"  Testing different temperature values...")
        
        temperatures = [0.1, 0.5, 0.9]
        responses = []
        
        for temp in temperatures:
            print(f"\n    Temperature: {temp}")
            start_time = time.time()
            response = self.client.generate_response(
                model=self.model_name,
                prompt=prompt,
                stream=False,
                temperature=temp,
                num_predict=80
            )
            gen_time = time.time() - start_time
            responses.append(response)
            
            print(f"    Generated in {gen_time:.2f}s")
            print(f"    Response: {response[:80]}...")
        
        self._response = responses[-1]
        self._response_generated = True
        
        # Responses at different temperatures should be different
        self.assertNotEqual(responses[0], responses[2])
        print(f"\n  ✓ Different temperatures produced different responses")
    
    def test_chat_endpoint(self):
        """Test chat endpoint with message list."""
        print(f"\n  Test 7: Chat Endpoint")
        print(f"  Model: {self.model_name}")
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant that explains concepts simply."},
            {"role": "user", "content": "What is machine learning in simple terms?"}
        ]
        
        self._prompt = "Chat: ML explanation"
        
        print(f"  Sending chat messages...")
        start_time = time.time()
        response = self.client.chat(
            model=self.model_name,
            messages=messages,
            stream=False,
            num_predict=120
        )
        gen_time = time.time() - start_time
        
        self._response = response
        self._response_generated = True
        
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)
        
        print(f"  ✓ Chat response generated in {gen_time:.2f}s")
        print(f"  Response length: {len(response)} characters")
        print(f"  Response: {response[:150]}...")
    
    def test_chat_multi_turn(self):
        """Test chat endpoint with multi-turn conversation."""
        print(f"\n  Test 8: Chat Multi-Turn")
        print(f"  Model: {self.model_name}")
        
        messages = [
            {"role": "system", "content": "You are a coding expert."},
            {"role": "user", "content": "What is Python?"},
            {"role": "assistant", "content": "Python is a high-level programming language known for its simplicity and readability."},
            {"role": "user", "content": "What are its main uses?"}
        ]
        
        self._prompt = "Chat: Python uses"
        
        print(f"  Sending multi-turn chat...")
        start_time = time.time()
        response = self.client.chat(
            model=self.model_name,
            messages=messages,
            stream=False,
            num_predict=100
        )
        gen_time = time.time() - start_time
        
        self._response = response
        self._response_generated = True
        
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)
        
        print(f"  ✓ Chat response generated in {gen_time:.2f}s")
        print(f"  Response length: {len(response)} characters")
        print(f"  Response: {response[:150]}...")


if __name__ == "__main__":
    unittest.main()
