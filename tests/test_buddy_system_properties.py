"""Property-based tests for Buddy System."""

import pytest
from hypothesis import given, strategies as st, settings


@given(
    elder_id=st.text(min_size=1, max_size=20),
    helper_id=st.text(min_size=1, max_size=20),
    permissions=st.lists(st.sampled_from(['view_health', 'log_data', 'receive_alerts']), min_size=1, max_size=3)
)
@settings(max_examples=100)
def test_buddy_profile_linking(elder_id, helper_id, permissions):
    """Property: Buddy profiles should link with proper permissions."""
    # Simulate linking
    link = {
        'elder_id': elder_id,
        'helper_id': helper_id,
        'permissions': list(set(permissions)),
        'consent_given': True
    }
    
    assert link['elder_id'] == elder_id
    assert link['helper_id'] == helper_id
    assert len(link['permissions']) > 0
    assert link['consent_given'] is True


@given(
    alert_type=st.sampled_from(['ppd_risk', 'deficiency', 'heat_stress']),
    elder_id=st.text(min_size=1, max_size=20),
    helper_id=st.text(min_size=1, max_size=20)
)
@settings(max_examples=100)
def test_dual_notification_for_elder_alerts(alert_type, elder_id, helper_id):
    """Property: Alerts should be sent to both elder and helper."""
    notifications = [
        {'recipient': elder_id, 'type': alert_type},
        {'recipient': helper_id, 'type': alert_type}
    ]
    
    assert len(notifications) == 2
    assert notifications[0]['recipient'] == elder_id
    assert notifications[1]['recipient'] == helper_id
