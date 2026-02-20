"""Debug test"""
from hypothesis import given, strategies as st
from app.core.config import settings as app_settings

print("Before decorator")

@given(language=st.sampled_from(app_settings.OCR_SUPPORTED_LANGUAGES))
def test_debug(language):
    """Debug test"""
    print(f"Test running with language: {language}")
    assert True

print("After decorator")
print("test_debug:", test_debug)
