"""Unit tests for Climate-Health Shield."""

import pytest
from unittest.mock import AsyncMock
from app.services.climate_service import ClimateService


@pytest.fixture
def service():
    return ClimateService(AsyncMock())


class TestWBGT:
    @pytest.mark.asyncio
    async def test_wbgt_calculation(self, service):
        """Test WBGT calculation."""
        result = await service.calculate_wbgt(
            temperature=35.0,
            humidity=70.0
        )
        assert 'wbgt' in result
        assert 'risk_level' in result


class TestHeatProtocols:
    @pytest.mark.asyncio
    async def test_work_rest_cycles(self, service):
        """Test work-rest cycle recommendations."""
        result = await service.get_heat_protocol(
            wbgt=32.0,
            activity_level='heavy'
        )
        assert 'work_minutes' in result
        assert 'rest_minutes' in result
