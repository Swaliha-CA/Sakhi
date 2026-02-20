"""Unit tests for micronutrient tracking."""

import pytest
from unittest.mock import AsyncMock, Mock
from app.services.micronutrient_service import MicronutrientService


@pytest.fixture
def service():
    return MicronutrientService(AsyncMock())


class TestLabResultExtraction:
    @pytest.mark.asyncio
    async def test_manual_entry(self, service):
        """Test manual lab result entry."""
        result = await service.log_lab_results(
            user_id="user123",
            hemoglobin=11.5,
            ferritin=20.0,
            b12=250.0
        )
        assert result['success'] is True
    
    @pytest.mark.asyncio
    async def test_deficiency_detection(self, service):
        """Test deficiency detection."""
        result = await service.check_deficiencies(
            hemoglobin=10.0,
            ferritin=10.0,
            b12=150.0
        )
        assert len(result['deficiencies']) > 0
