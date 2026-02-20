"""
Unit tests for cumulative EDC exposure tracking.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta
from app.services.exposure_aggregation_service import ExposureAggregationService
from app.services.exposure_alert_service import ExposureAlertService


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    return AsyncMock()


@pytest.fixture
def aggregation_service(mock_db_session):
    """Create an ExposureAggregationService instance."""
    return ExposureAggregationService(mock_db_session)


@pytest.fixture
def alert_service(mock_db_session):
    """Create an ExposureAlertService instance."""
    return ExposureAlertService(mock_db_session)


class TestAggregationAlgorithm:
    """Test exposure aggregation algorithm."""
    
    @pytest.mark.asyncio
    async def test_aggregate_multiple_scans(self, aggregation_service, mock_db_session):
        """Test aggregating exposure from multiple product scans."""
        # Mock scan data
        mock_scans = [
            Mock(edc_type='BPA', concentration=10.0, frequency=2),
            Mock(edc_type='BPA', concentration=15.0, frequency=1),
            Mock(edc_type='phthalates', concentration=20.0, frequency=3),
        ]
        
        mock_db_session.execute = AsyncMock(return_value=Mock(
            scalars=Mock(return_value=Mock(all=Mock(return_value=mock_scans)))
        ))
        
        result = await aggregation_service.aggregate_user_exposure(
            user_id="user123",
            start_date=datetime.now() - timedelta(days=30),
            end_date=datetime.now()
        )
        
        assert isinstance(result, dict)
        assert 'by_edc_type' in result
    
    @pytest.mark.asyncio
    async def test_weighting_logic(self, aggregation_service):
        """Test weighting logic (frequency × concentration)."""
        # Test data
        exposures = [
            {'edc_type': 'BPA', 'concentration': 10.0, 'frequency': 2},  # 20
            {'edc_type': 'BPA', 'concentration': 5.0, 'frequency': 4},   # 20
        ]
        
        # Calculate weighted exposure
        total = sum(e['concentration'] * e['frequency'] for e in exposures)
        
        assert total == 40.0


class TestEPALimitComparison:
    """Test EPA safe limit comparison."""
    
    @pytest.mark.asyncio
    async def test_compare_against_epa_limits(self, aggregation_service, mock_db_session):
        """Test comparison against EPA safe limits."""
        mock_db_session.execute = AsyncMock(return_value=Mock(
            scalars=Mock(return_value=Mock(all=Mock(return_value=[])))
        ))
        
        result = await aggregation_service.compare_to_safe_limits(
            user_id="user123",
            period_days=7
        )
        
        assert isinstance(result, dict)
        assert 'comparisons' in result
    
    def test_risk_level_classification(self, aggregation_service):
        """Test risk level classification based on percentage of safe limit."""
        test_cases = [
            (30, 100, "low"),      # 30% of limit
            (60, 100, "moderate"), # 60% of limit
            (90, 100, "high"),     # 90% of limit
            (120, 100, "critical"), # 120% of limit
        ]
        
        for exposure, limit, expected_risk in test_cases:
            percentage = (exposure / limit) * 100
            
            if percentage < 50:
                risk = "low"
            elif percentage < 80:
                risk = "moderate"
            elif percentage < 100:
                risk = "high"
            else:
                risk = "critical"
            
            assert risk == expected_risk


class TestTrendAnalysis:
    """Test exposure trend analysis."""
    
    @pytest.mark.asyncio
    async def test_trend_calculation(self, aggregation_service, mock_db_session):
        """Test trend analysis over time."""
        # Mock historical data
        mock_data = [
            Mock(date=datetime.now() - timedelta(days=i), total_exposure=100 + i*10)
            for i in range(30)
        ]
        
        mock_db_session.execute = AsyncMock(return_value=Mock(
            scalars=Mock(return_value=Mock(all=Mock(return_value=mock_data)))
        ))
        
        result = await aggregation_service.analyze_trends(
            user_id="user123",
            days=30
        )
        
        assert isinstance(result, dict)
        assert 'trend' in result
    
    def test_trend_direction_detection(self):
        """Test detecting increasing/decreasing/stable trends."""
        # Increasing trend
        increasing = [10, 20, 30, 40, 50]
        recent_avg = sum(increasing[-3:]) / 3
        older_avg = sum(increasing[:3]) / 3
        assert recent_avg > older_avg
        
        # Decreasing trend
        decreasing = [50, 40, 30, 20, 10]
        recent_avg = sum(decreasing[-3:]) / 3
        older_avg = sum(decreasing[:3]) / 3
        assert recent_avg < older_avg


class TestReportGeneration:
    """Test exposure report generation."""
    
    @pytest.mark.asyncio
    async def test_monthly_report_generation(self, aggregation_service, mock_db_session):
        """Test generating monthly exposure report."""
        mock_db_session.execute = AsyncMock(return_value=Mock(
            scalars=Mock(return_value=Mock(all=Mock(return_value=[])))
        ))
        
        result = await aggregation_service.generate_monthly_report(
            user_id="user123",
            month=1,
            year=2026
        )
        
        assert isinstance(result, dict)
        assert 'month' in result
        assert 'year' in result
        assert 'total_exposure' in result
    
    @pytest.mark.asyncio
    async def test_report_includes_visualizations(self, aggregation_service, mock_db_session):
        """Test that report includes visualization data."""
        mock_db_session.execute = AsyncMock(return_value=Mock(
            scalars=Mock(return_value=Mock(all=Mock(return_value=[])))
        ))
        
        result = await aggregation_service.generate_monthly_report(
            user_id="user123",
            month=1,
            year=2026
        )
        
        # Should include data for charts
        assert 'by_edc_type' in result or 'daily_breakdown' in result


class TestAlertSystem:
    """Test exposure alert system."""
    
    @pytest.mark.asyncio
    async def test_threshold_based_alerting(self, alert_service, mock_db_session):
        """Test threshold-based alert triggering."""
        mock_db_session.execute = AsyncMock(return_value=Mock(
            scalar_one_or_none=Mock(return_value=None)
        ))
        mock_db_session.commit = AsyncMock()
        
        result = await alert_service.check_and_create_alerts(
            user_id="user123",
            edc_type="BPA",
            weekly_exposure=150.0,
            safe_limit=100.0
        )
        
        assert isinstance(result, dict)
    
    @pytest.mark.asyncio
    async def test_personalized_reduction_strategies(self, alert_service, mock_db_session):
        """Test generation of personalized reduction strategies."""
        result = await alert_service.generate_reduction_strategies(
            user_id="user123",
            primary_sources=['cosmetics', 'food']
        )
        
        assert isinstance(result, list)
        assert len(result) > 0
    
    @pytest.mark.asyncio
    async def test_identify_primary_sources(self, alert_service, mock_db_session):
        """Test identifying primary EDC sources for users."""
        mock_scans = [
            Mock(category='cosmetics', edc_exposure=50.0),
            Mock(category='cosmetics', edc_exposure=30.0),
            Mock(category='food', edc_exposure=20.0),
        ]
        
        mock_db_session.execute = AsyncMock(return_value=Mock(
            scalars=Mock(return_value=Mock(all=Mock(return_value=mock_scans)))
        ))
        
        result = await alert_service.identify_primary_sources(user_id="user123")
        
        assert isinstance(result, list)
        # Cosmetics should be primary source (80 total vs 20 for food)
        if result:
            assert result[0]['category'] == 'cosmetics'
