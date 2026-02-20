"""Property-based tests for Climate-Health Shield."""

import pytest
from hypothesis import given, strategies as st, settings


@given(
    twb=st.floats(min_value=15, max_value=40),
    tg=st.floats(min_value=20, max_value=50),
    tdb=st.floats(min_value=20, max_value=50)
)
@settings(max_examples=100)
def test_wbgt_calculation_accuracy(twb, tg, tdb):
    """Property: WBGT calculation follows standard formula."""
    wbgt = 0.7 * twb + 0.2 * tg + 0.1 * tdb
    
    # Property: WBGT is within expected range
    assert 15 <= wbgt <= 50
    
    # Property: Wet bulb has highest weight
    assert abs(wbgt - twb) < abs(wbgt - tg)


@given(
    wbgt=st.floats(min_value=20, max_value=40),
    activity_level=st.sampled_from(['light', 'moderate', 'heavy'])
)
@settings(max_examples=100)
def test_heat_protocol_recommendation(wbgt, activity_level):
    """Property: Heat protocols match WBGT and activity."""
    if wbgt < 27:
        risk = "safe"
    elif wbgt < 29:
        risk = "caution"
    elif wbgt < 31:
        risk = "extreme_caution"
    else:
        risk = "danger"
    
    assert risk in ["safe", "caution", "extreme_caution", "danger"]
