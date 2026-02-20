"""Unit tests for PPD prediction service."""

import pytest
from unittest.mock import Mock, AsyncMock
from app.services.ppd_prediction_service import PPDPredictionService


@pytest.fixture
def mock_db_session():
    return AsyncMock()


@pytest.fixture
def service(mock_db_session):
    return PPDPredictionService(mock_db_session)


class TestRiskModel:
    @pytest.mark.asyncio
    async def test_calculate_risk_score(self, service):
        """Test risk score calculation with various inputs."""
        result = await service.calculate_risk_score(
            user_id="user123",
            epds_score=15,
            hormonal_data={'progesterone': 10},
            environmental_data={'edc_exposure': 50},
            micronutrient_data={'hemoglobin': 10},
            social_factors={'support_score': 70}
        )
        assert 'risk_score' in result
        assert 0 <= result['risk_score'] <= 100
    
    def test_feature_weighting(self, service):
        """Test that feature weights sum to 1.0."""
        weights = service.get_feature_weights()
        assert abs(sum(weights.values()) - 1.0) < 0.01


class TestAlertSystem:
    @pytest.mark.asyncio
    async def test_alert_triggering(self, service, mock_db_session):
        """Test alert triggering for high-risk cases."""
        mock_db_session.commit = AsyncMock()
        result = await service.check_and_alert(
            user_id="user123",
            risk_score=85.0,
            asha_id="asha456"
        )
        assert result['alert_triggered'] is True
