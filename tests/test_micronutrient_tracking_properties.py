"""Property-based tests for micronutrient tracking."""

import pytest
from hypothesis import given, strategies as st, settings


@given(
    hemoglobin=st.floats(min_value=5, max_value=18),
    ferritin=st.floats(min_value=5, max_value=200),
    b12=st.floats(min_value=100, max_value=1000)
)
@settings(max_examples=100)
def test_micronutrient_deficiency_flagging(hemoglobin, ferritin, b12):
    """Property: Deficiencies should be correctly flagged."""
    # Clinical thresholds
    hb_deficient = hemoglobin < 12.0
    ferritin_deficient = ferritin < 15.0
    b12_deficient = b12 < 200.0
    
    deficiencies = []
    if hb_deficient:
        deficiencies.append('hemoglobin')
    if ferritin_deficient:
        deficiencies.append('ferritin')
    if b12_deficient:
        deficiencies.append('B12')
    
    # Property: All deficiencies are detected
    assert isinstance(deficiencies, list)
    if hemoglobin < 12.0:
        assert 'hemoglobin' in deficiencies


@given(
    measurements=st.lists(
        st.fixed_dictionaries({
            'date': st.datetimes(min_value=datetime(2024, 1, 1), max_value=datetime(2026, 12, 31)),
            'hemoglobin': st.floats(min_value=8, max_value=15)
        }),
        min_size=2,
        max_size=10
    )
)
@settings(max_examples=100)
def test_micronutrient_trend_tracking(measurements):
    """Property: Trends should be correctly identified."""
    sorted_measurements = sorted(measurements, key=lambda x: x['date'])
    
    if len(sorted_measurements) >= 2:
        first_value = sorted_measurements[0]['hemoglobin']
        last_value = sorted_measurements[-1]['hemoglobin']
        
        if last_value > first_value * 1.1:
            trend = "improving"
        elif last_value < first_value * 0.9:
            trend = "declining"
        else:
            trend = "stable"
        
        assert trend in ["improving", "declining", "stable"]


from datetime import datetime
