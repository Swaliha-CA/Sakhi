"""Simple property test"""
from hypothesis import given, strategies as st, settings
from app.core.config import settings as app_settings

@given(language=st.sampled_from(app_settings.OCR_SUPPORTED_LANGUAGES))
@settings(max_examples=10)
def test_simple_property(language):
    """Simple property test"""
    assert language in app_settings.OCR_SUPPORTED_LANGUAGES
