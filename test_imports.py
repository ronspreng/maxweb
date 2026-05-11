import sys
sys.path.insert(0, '.')

print("Testing imports...")
try:
    from src.module1_offers.importer import CSVImporter
    print("[OK] Module1 importer")
except Exception as e:
    print(f"[FAIL] Module1 importer: {e}")
    import traceback
    traceback.print_exc()

try:
    from src.module2_competitive.analyzer import PatternAnalyzer
    print("[OK] Module2 analyzer")
except Exception as e:
    print(f"[FAIL] Module2 analyzer: {e}")
    import traceback
    traceback.print_exc()

try:
    import streamlit as st
    print(f"[OK] Streamlit {st.__version__}")
except Exception as e:
    print(f"[FAIL] Streamlit: {e}")
    import traceback
    traceback.print_exc()

print("\n[DONE] Import test completed")
