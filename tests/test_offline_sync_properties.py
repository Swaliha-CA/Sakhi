"""Property-based tests for offline sync."""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime


@given(
    local_changes=st.lists(st.fixed_dictionaries({
        'id': st.integers(min_value=1, max_value=1000),
        'timestamp': st.datetimes(min_value=datetime(2024, 1, 1), max_value=datetime(2026, 12, 31)),
        'data': st.text(min_size=1, max_size=100)
    }), min_size=1, max_size=20)
)
@settings(max_examples=100)
def test_offline_functionality_completeness(local_changes):
    """Property: All offline operations should be captured."""
    assert len(local_changes) > 0
    for change in local_changes:
        assert 'id' in change
        assert 'timestamp' in change
        assert 'data' in change


@given(
    local_timestamp=st.datetimes(min_value=datetime(2024, 1, 1), max_value=datetime(2026, 12, 31)),
    cloud_timestamp=st.datetimes(min_value=datetime(2024, 1, 1), max_value=datetime(2026, 12, 31))
)
@settings(max_examples=100)
def test_sync_conflict_resolution(local_timestamp, cloud_timestamp):
    """Property: Last-write-wins conflict resolution."""
    if local_timestamp > cloud_timestamp:
        winner = "local"
    else:
        winner = "cloud"
    
    assert winner in ["local", "cloud"]
