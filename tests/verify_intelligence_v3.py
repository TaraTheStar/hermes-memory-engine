import os
import sys
import shutil

# Ensure the project root is in the path so we can import the library
root = os.path.abspath(os.path.dirname(__file__))
if root not in sys.path:
    sys.path.insert(0, root)

from domain.core.semantic_memory import SemanticMemory
from domain.core.state_registry import StateRegistry
from domain.core.acl.llm_translator import LLMTranslator
from domain.core.events import InfrastructureErrorEvent, EventSeverity

def run_verification():
    print("🚀 Starting VERBOSE Intelligence Verification...")
    
    # Clean up previous test data to ensure a fresh state
    test_db_dir = "/tmp/hermes_test_semantic_v3"
    if os.path.exists(test_db_dir):
        shutil.rmtree(test_db_dir)
    os.makedirs(test_db_dir, exist_ok=True)

    sm = SemanticMemory(persist_directory=test_db_dir)
    
    # Add events with unique keywords per context
    print("\n[Setup] Adding events...")
    # Marketing context event
    sm.add_event("marketing_secret_alpha", {"type": "msg"}, context_id="marketing")
    # Core context event (semantically different from marketing)
    sm.add_event("core_stability_beta", {"type": "msg"}, context_id="core")
    print("[Setup] Done.")

    # Test 1: Semantic Context Isolation
    print("\n--- [1/3] Testing Semantic Context Isolation ---")
    
    # A. Query marketing context for marketing keyword
    print("Querying 'marketing' context for 'marketing_secret_alpha'...")
    m_results = sm.query_context("marketing_secret_alpha", context_id="marketing")
    print(f"Results found: {len(m_results)}")
    if len(m_results) > 0:
        print(f"  - Found correct event: {m_results[0]['id']} with context {m_results[0]['metadata'].get('context_id')}")
    
    # B. Query core context for marketing keyword (Should return 0 due to isolation)
    print("Querying 'core' context for 'marketing_secret_alpha'...")
    c_results_for_m = sm.query_context("marketing_secret_alpha", context_id="core")
    print(f"Results found: {len(c_results_for_m)}")
    
    if len(c_results_for_m) == 0:
        print("✅ SUCCESS: Context isolation verified (No leakage).")
    else:
        print("❌ FAILURE: Context isolation failed (Leakage detected).")
        for r in c_results_for_m:
            print(f"  LEAKED EVENT: {r['id']} with context {r['metadata'].get('context_id')}")

    # 2. Test ACL Transformation
    print("\n--- [2/3] Testing ACL Transformation ---")
    translator = LLMTranslator()
    try:
        raise ConnectionError("Connection refused by remote server")
    except Exception as e:
        event = translator.translate_exception(e)
        print(f"Caught Exception: {e}")
        print(f"Translated Event: {event}")
        
        if isinstance(event, InfrastructureErrorEvent) and event.severity == EventSeverity.ERROR:
            print("✅ SUCCESS: ACL transformation verified.")
        else:
            print("❌ FAILURE: ACL transformation failed.")

    # 3. Test State Registry
    print("\n--- [3/3] Testing State Registry ---")
    registry = StateRegistry()
    registry.set_state("active_protocol", "alpha", context_id="research")
    registry.set_state("active_protocol", "omega", context_id="combat")
    
    res_research = registry.get_state("active_protocol", context_id="research")
    res_combat = registry.get_state("active_protocol", context_id="combat")
    
    print(f"Research protocol: {res_research}")
    print(f"Combat protocol: {res_combat}")
    
    if res_research == "alpha" and res_combat == "omega":
        print("✅ SUCCESS: State Registry context isolation verified.")
    else:
        print("❌ FAILURE: State Registry isolation failed.")

if __name__ == "__main__":
    try:
        run_verification()
    except Exception as e:
        print(f"Verification script failed with error: {e}")
        import traceback
        traceback.print_exc()
