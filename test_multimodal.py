import os
import unittest
from src.multimodal import Multimodal
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class TestMultimodal(unittest.TestCase):
    def setUp(self):
        """Set up the Multimodal instance before each test."""
        self.agent = Multimodal()
        self.user_id = "test_user_001"

    def test_text_generation_basic(self):
        """Test basic text generation."""
        print("\n--- Testing Basic Text Generation ---")
        prompt = "Hello, who are you?"
        response, _ = self.agent.generate_response(prompt, user_id=self.user_id)
        
        print(f"Prompt: {prompt}")
        print(f"Response: {response.get('response')}")
        
        self.assertIn("response", response)
        self.assertIsInstance(response["response"], str)
        self.assertGreater(len(response["response"]), 0)

    def test_memory_persistence(self):
        """Test if the agent remembers information across turns."""
        print("\n--- Testing Memory Persistence ---")
        
        # Turn 1: Tell the agent a fact
        fact = "My favorite color is bright neon green."
        print(f"User: {fact}")
        self.agent.generate_response(fact, user_id=self.user_id)
        
        # Turn 2: Ask about the fact
        question = "What is my favorite color?"
        print(f"User: {question}")
        response, _ = self.agent.generate_response(question, user_id=self.user_id)
        
        print(f"Response: {response.get('response')}")
        
        # We expect the agent to mention 'green' or 'neon'
        response_text = response["response"].lower()
        self.assertTrue("green" in response_text or "neon" in response_text, 
                        "Agent failed to recall the favorite color.")

    def test_image_intent_trigger(self):
        """Test if the agent triggers image generation intent."""
        print("\n--- Testing Image Generation Intent ---")
        prompt = "Generate a picture of a futuristic city."
        
        # We mock the actual generation to avoid API costs/latency in unit tests,
        # but here we are testing the full flow integration so we let it run.
        # Note: This requires valid API keys and might take a moment.
        response, _ = self.agent.generate_response(prompt, user_id=self.user_id)
        
        print(f"Response Text: {response.get('response')}")
        if "img" in response:
            print("Image generated successfully.")
        
        # Check if we got an image or a text saying it tried
        self.assertTrue("img" in response or "generated image" in response["response"].lower())

if __name__ == "__main__":
    unittest.main()