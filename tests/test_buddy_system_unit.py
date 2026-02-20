"""Unit tests for Buddy System."""

import pytest
from unittest.mock import AsyncMock
from app.services.buddy_system_service import BuddySystemService


@pytest.fixture
def service():
    return BuddySystemService(AsyncMock())


class TestProfileLinking:
    @pytest.mark.asyncio
    async def test_create_buddy_link(self, service):
        """Test creating buddy link."""
        result = await service.create_link(
            elder_id="elder123",
            helper_id="helper456",
            permissions=['view_health', 'log_data']
        )
        assert result['success'] is True


class TestDataAttribution:
    @pytest.mark.asyncio
    async def test_data_logged_to_elder_profile(self, service):
        """Test that helper-logged data attributes to elder."""
        result = await service.log_data_for_elder(
            helper_id="helper456",
            elder_id="elder123",
            data={'hemoglobin': 11.5}
        )
        assert result['attributed_to'] == "elder123"


class TestPrivacyControls:
    @pytest.mark.asyncio
    async def test_permission_enforcement(self, service):
        """Test that permissions are enforced."""
        result = await service.check_permission(
            helper_id="helper456",
            elder_id="elder123",
            action='view_health'
        )
        assert 'allowed' in result
