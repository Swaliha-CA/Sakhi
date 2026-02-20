"""Unit tests for predictive analytics."""

import pytest
from unittest.mock import AsyncMock
from app.services.anonymization_service import AnonymizationService
from app.services.correlation_analysis_service import CorrelationAnalysisService
from app.services.population_health_dashboard_service import PopulationHealthDashboardService


@pytest.fixture
def anon_service():
    return AnonymizationService(AsyncMock())


@pytest.fixture
def corr_service():
    return CorrelationAnalysisService(AsyncMock())


@pytest.fixture
def dashboard_service():
    return PopulationHealthDashboardService(AsyncMock())


class TestPIIScrubbing:
    @pytest.mark.asyncio
    async def test_remove_pii(self, anon_service):
        """Test PII removal."""
        data = {
            'name': 'Jane Doe',
            'phone': '1234567890',
            'age': 25,
            'condition': 'PCOS'
        }
        result = await anon_service.anonymize(data)
        assert 'name' not in result
        assert 'phone' not in result
        assert 'age' in result


class TestCorrelationAnalysis:
    @pytest.mark.asyncio
    async def test_edc_pcos_correlation(self, corr_service):
        """Test EDC-PCOS correlation analysis."""
        result = await corr_service.analyze_edc_pcos_correlation()
        assert 'correlation_coefficient' in result


class TestDashboards:
    @pytest.mark.asyncio
    async def test_generate_dashboard(self, dashboard_service):
        """Test dashboard generation."""
        result = await dashboard_service.generate_dashboard(region='test_region')
        assert 'metrics' in result
