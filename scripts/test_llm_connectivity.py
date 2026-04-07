import sys
import os

# Add the project root to sys.path to ensure imports work
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from infrastructure.llm_implementations import OpenAIImplementation
from domain.supporting.config_loader import ConfigLoader

def test_openai_connection():
    print("--- Testing OpenAIImplementation Connection ---")
    try:
        print("Loading configuration...")
        config = ConfigLoader().get_delegation_config()
        print(f"Config loaded: Model={config.get('model')}, Base URL={config.get('base_url')}")
        
        print("Initializing OpenAIImplementation...")
        llm = OpenAIImplementation()
        print("Initialization successful.")

        test_prompt = "This is a connectivity test. If you receive this, the local LLM backend is responding."
        system_prompt = "You are a helpful assistant performing a connectivity check."
        
        print(f"Sending test prompt: '{test_prompt}'")
        print("Waiting for response (this may take a few seconds)...")
        
        response = llm.complete(test_prompt, system_prompt)
        
        print("\n--- Response Received ---")
        print(response)
        print("--------------------------")
        print("SUCCESS: Connectivity test passed!")
        
    except Exception as e:
        print("\n--- ERROR ---")
        print(f"An error occurred during the connectivity test: {e}")
        import traceback
        traceback.print_exc()
        print("--------------------------")
        print("FAILURE: Connectivity test failed.")
        sys.exit(1)

if __name__ == "__main__":
    test_openai_connection()
