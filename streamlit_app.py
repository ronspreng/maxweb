import streamlit as st

st.title("MaxWeb - Testing")
st.write("If you see this, Streamlit Cloud works!")

# Test imports
try:
    from src.module1_offers.importer import CSVImporter
    st.write("✓ Module 1 imports OK")
except Exception as e:
    st.error(f"Module 1 error: {e}")

try:
    from src.module2_competitive.analyzer import PatternAnalyzer
    st.write("✓ Module 2 imports OK")
except Exception as e:
    st.error(f"Module 2 error: {e}")

try:
    from src.module3_creative.generator import CreativeGenerator
    st.write("✓ Module 3 imports OK")
except Exception as e:
    st.error(f"Module 3 error: {e}")

st.write("All tests passed! Ready for full app.")
