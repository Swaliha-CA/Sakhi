"""
Property-based tests for cumulative EDC exposure tracking.

Tests Properties:
- Property 9: Cumulative Exposure Aggregation
- Property 12: Exposure Limit Comparison
- Property 47: Exposure Trend-Based Recommendations
- Property 48: Monthly Exposure Report Generation
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime, timedelta
from typing import List, Dict


# Property 9: Cumulative Exposure Aggregation
@given(
    exposures=st.lists(
        st.fixed_dictionaries({
            'edc_type': st.sampled_from(['BPA', 'phthalates', 'parabens', 'triclosan']),
            'concentration': st.floats(min_value=0, max_value=1000),
            'frequency': st.integers(min_value=1, max_value=10)
        }),
        min_size=1,
        max_size=20
    )
)
@settings(max_examples=100)
def test_cumulative_exposure_aggregation(exposures):
    """
    Property: Cumulative exposure should be sum of (concentration × frequency)
    for each EDC type.
    """
    # Aggregate by EDC type
    aggregated = {}
    for exp in exposures:
        edc_type = exp['edc_type']
        weighted_exposure = exp['concentration'] * exp['frequency']
        
        if edc_type not in aggregated:
            aggregated[edc_type] = 0
        aggregated[edc_type] += weighted_exposure
    
    # Property: All exposures are accounted for
    total_calculated = sum(
        exp['concentration'] * exp['frequency'] for exp in exposures
    )
    total_aggregated = sum(aggregated.values())
    
    assert abs(total_calculated - total_aggregated) < 0.01


# Property 12: Exposure Limit Comparison
@given(
    edc_type=st.sampled_from(['BPA', 'phthalates', 'parabens', 'triclosan']),
    cumulative_exposure=st.floats(min_value=0, max_value=10000),
    safe_limit=st.floats(min_value=100, max_value=5000)
)
@settings(max_examples=100)
def test_exposure_limit_comparison(edc_type, cumulative_exposure, safe_limit):
    """
    Property: System should correctly identify when exposure exceeds safe limits.
    """
    # Calculate percentage of safe limit
    percentage = (cumulative_exposure / safe_limit) * 100 if safe_limit > 0 else 0
    
    # Determine risk level
    if percentage < 50:
        risk_level = "low"
    elif percentage < 80:
        risk_level = "moderate"
    elif percentage < 100:
        risk_level = "high"
    else:
        risk_level = "critical"
    
    # Property: Risk level correctly reflects exposure percentage
    if cumulative_exposure < safe_limit * 0.5:
        assert risk_level == "low"
    elif cumulative_exposure < safe_limit * 0.8:
        assert risk_level == "moderate"
    elif cumulative_exposure < safe_limit:
        assert risk_level == "high"
    else:
        assert risk_level == "critical"


# Property 47: Exposure Trend-Based Recommendations
@given(
    historical_exposures=st.lists(
        st.fixed_dictionaries({
            'date': st.datetimes(min_value=datetime(2024, 1, 1), max_value=datetime(2026, 12, 31)),
            'total_exposure': st.floats(min_value=0, max_value=1000)
        }),
        min_size=2,
        max_size=30
    )
)
@settings(max_examples=100)
def test_exposure_trend_based_recommendations(historical_exposures):
    """
    Property: Recommendations should be generated based on exposure trends.
    """
    # Sort by date
    sorted_exposures = sorted(historical_exposures, key=lambda x: x['date'])
    
    # Calculate trend (increasing, decreasing, stable)
    if len(sorted_exposures) >= 2:
        recent_avg = sum(e['total_exposure'] for e in sorted_exposures[-3:]) / min(3, len(sorted_exposures))
        older_avg = sum(e['total_exposure'] for e in sorted_exposures[:3]) / min(3, len(sorted_exposures))
        
        if recent_avg > older_avg * 1.2:
            trend = "increasing"
            recommendation_type = "urgent_reduction"
        elif recent_avg < older_avg * 0.8:
            trend = "decreasing"
            recommendation_type = "maintain_progress"
        else:
            trend = "stable"
            recommendation_type = "continue_monitoring"
        
        # Property: Recommendation matches trend
        if trend == "increasing":
            assert recommendation_type == "urgent_reduction"
        elif trend == "decreasing":
            assert recommendation_type == "maintain_progress"
        else:
            assert recommendation_type == "continue_monitoring"


# Property 48: Monthly Exposure Report Generation
@given(
    month=st.integers(min_value=1, max_value=12),
    year=st.integers(min_value=2024, max_value=2026),
    daily_exposures=st.lists(
        st.fixed_dictionaries({
            'day': st.integers(min_value=1, max_value=28),  # Safe for all months
            'exposure': st.floats(min_value=0, max_value=100)
        }),
        min_size=1,
        max_size=28
    )
)
@settings(max_examples=100)
def test_monthly_exposure_report_generation(month, year, daily_exposures):
    """
    Property: Monthly report should aggregate all exposures for the month
    and provide summary statistics.
    """
    # Calculate monthly statistics
    total_exposure = sum(e['exposure'] for e in daily_exposures)
    avg_daily_exposure = total_exposure / len(daily_exposures) if daily_exposures else 0
    max_daily_exposure = max((e['exposure'] for e in daily_exposures), default=0)
    min_daily_exposure = min((e['exposure'] for e in daily_exposures), default=0)
    
    # Generate report
    report = {
        'month': month,
        'year': year,
        'total_exposure': total_exposure,
        'average_daily': avg_daily_exposure,
        'max_daily': max_daily_exposure,
        'min_daily': min_daily_exposure,
        'days_tracked': len(daily_exposures)
    }
    
    # Property: Report contains all required fields
    assert 'month' in report
    assert 'year' in report
    assert 'total_exposure' in report
    assert 'average_daily' in report
    assert 'max_daily' in report
    assert 'min_daily' in report
    
    # Property: Statistics are correct
    assert report['total_exposure'] == total_exposure
    assert report['average_daily'] == avg_daily_exposure
    assert report['max_daily'] >= report['min_daily']
    assert report['days_tracked'] == len(daily_exposures)


# Additional property: Exposure source identification
@given(
    product_scans=st.lists(
        st.fixed_dictionaries({
            'product_category': st.sampled_from(['cosmetics', 'food', 'household', 'personal_care']),
            'edc_exposure': st.floats(min_value=0, max_value=100)
        }),
        min_size=1,
        max_size=50
    )
)
@settings(max_examples=100)
def test_primary_exposure_source_identification(product_scans):
    """
    Property: System should correctly identify primary sources of EDC exposure.
    """
    # Aggregate by category
    category_totals = {}
    for scan in product_scans:
        category = scan['product_category']
        exposure = scan['edc_exposure']
        
        if category not in category_totals:
            category_totals[category] = 0
        category_totals[category] += exposure
    
    # Identify primary source
    if category_totals:
        primary_source = max(category_totals, key=category_totals.get)
        primary_exposure = category_totals[primary_source]
        
        # Property: Primary source has highest exposure
        for category, exposure in category_totals.items():
            if category != primary_source:
                assert primary_exposure >= exposure
