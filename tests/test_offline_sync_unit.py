"""Unit tests for offline sync."""

import pytest
from unittest.mock import AsyncMock
from app.services.sync_service import SyncService


@pytest.fixture
def service():
    return SyncService(AsyncMock())


class TestLocalStorage:
    @pytest.mark.asyncio
    async def test_local_crud_operations(self, service):
        """Test local storage CRUD."""
        result = await service.store_locally(
            user_id="user123",
            data={'test': 'data'}
        )
        assert result['success'] is True


class TestSync:
    @pytest.mark.asyncio
    async def test_sync_upload(self, service):
        """Test syncing local changes to cloud."""
        result = await service.sync_to_cloud(user_id="user123")
        assert 'synced_count' in result
    
    @pytest.mark.asyncio
    async def test_sync_download(self, service):
        """Test syncing cloud changes to local."""
        result = await service.sync_from_cloud(user_id="user123")
        assert 'synced_count' in result
