"""
Unit tests for alternative product recommendations service.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from app.services.alternative_product_service import AlternativeProductService, Alternative


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = AsyncMock()
    return session


@pytest.fixture
def service(mock_db_session):
    """Create an AlternativeProductService instance."""
    return AlternativeProductService(mock_db_session)


class TestProductMatching:
    """Test product matching algorithm."""
    
    @pytest.mark.asyncio
    async def test_find_alternatives_by_category(self, service, mock_db_session):
        """Test finding alternatives by category."""
        # Mock database response
        mock_db_session.execute = AsyncMock(return_value=Mock(
            scalars=Mock(return_value=Mock(all=Mock(return_value=[])))
        ))
        
        result = await service.find_alternatives(
            scanned_product_name="Test Product",
            category="cosmetics",
            min_score=70.0
        )
        
        assert isinstance(result, dict)
        assert 'alternatives' in result
    
    @pytest.mark.asyncio
    async def test_find_alternatives_with_price_filter(self, service, mock_db_session):
        """Test finding alternatives with price constraints."""
        mock_db_session.execute = AsyncMock(return_value=Mock(
            scalars=Mock(return_value=Mock(all=Mock(return_value=[])))
        ))
        
        result = await service.find_alternatives(
            scanned_product_name="Test Product",
            category="food",
            max_price=500.0
        )
        
        assert isinstance(result, dict)


class TestRankingLogic:
    """Test alternative ranking logic."""
    
    def test_rank_alternatives_by_score(self, service):
        """Test ranking by score (descending)."""
        alternatives = [
            Mock(hormonal_health_score=60.0, price_range="100-200", availability="high"),
            Mock(hormonal_health_score=90.0, price_range="100-200", availability="high"),
            Mock(hormonal_health_score=75.0, price_range="100-200", availability="high"),
        ]
        
        ranked = service._rank_alternatives(alternatives)
        
        # Should be sorted by score descending
        assert ranked[0].hormonal_health_score == 90.0
        assert ranked[1].hormonal_health_score == 75.0
        assert ranked[2].hormonal_health_score == 60.0
    
    def test_rank_alternatives_by_price_when_scores_equal(self, service):
        """Test ranking by price when scores are equal."""
        alternatives = [
            Mock(hormonal_health_score=80.0, price_range="500-1000", availability="high"),
            Mock(hormonal_health_score=80.0, price_range="100-200", availability="high"),
            Mock(hormonal_health_score=80.0, price_range="200-500", availability="high"),
        ]
        
        ranked = service._rank_alternatives(alternatives)
        
        # Should be sorted by price ascending when scores equal
        assert ranked[0].price_range == "100-200"
        assert ranked[1].price_range == "200-500"
        assert ranked[2].price_range == "500-1000"


class TestShoppingList:
    """Test shopping list CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_add_to_shopping_list(self, service, mock_db_session):
        """Test adding product to shopping list."""
        mock_db_session.execute = AsyncMock(return_value=Mock(
            scalar_one_or_none=Mock(return_value=None)
        ))
        mock_db_session.commit = AsyncMock()
        
        result = await service.add_to_shopping_list(
            user_id="user123",
            product_id=1
        )
        
        assert result['success'] is True
        assert 'message' in result
    
    @pytest.mark.asyncio
    async def test_get_shopping_list(self, service, mock_db_session):
        """Test retrieving shopping list."""
        mock_db_session.execute = AsyncMock(return_value=Mock(
            scalars=Mock(return_value=Mock(all=Mock(return_value=[])))
        ))
        
        result = await service.get_shopping_list(user_id="user123")
        
        assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_remove_from_shopping_list(self, service, mock_db_session):
        """Test removing product from shopping list."""
        mock_item = Mock()
        mock_db_session.execute = AsyncMock(return_value=Mock(
            scalar_one_or_none=Mock(return_value=mock_item)
        ))
        mock_db_session.delete = AsyncMock()
        mock_db_session.commit = AsyncMock()
        
        result = await service.remove_from_shopping_list(
            user_id="user123",
            product_id=1
        )
        
        assert result['success'] is True
    
    @pytest.mark.asyncio
    async def test_remove_nonexistent_item(self, service, mock_db_session):
        """Test removing item that doesn't exist."""
        mock_db_session.execute = AsyncMock(return_value=Mock(
            scalar_one_or_none=Mock(return_value=None)
        ))
        
        result = await service.remove_from_shopping_list(
            user_id="user123",
            product_id=999
        )
        
        assert result['success'] is False


class TestNotifications:
    """Test notification system for new products."""
    
    @pytest.mark.asyncio
    async def test_create_new_product_notification(self, service, mock_db_session):
        """Test creating notification for new product."""
        mock_db_session.execute = AsyncMock(return_value=Mock(
            scalars=Mock(return_value=Mock(all=Mock(return_value=[])))
        ))
        mock_db_session.commit = AsyncMock()
        
        result = await service.create_new_product_notifications(
            product_id=1,
            category="cosmetics"
        )
        
        assert isinstance(result, dict)
        assert 'notifications_created' in result
    
    @pytest.mark.asyncio
    async def test_get_user_notifications(self, service, mock_db_session):
        """Test retrieving user notifications."""
        mock_db_session.execute = AsyncMock(return_value=Mock(
            scalars=Mock(return_value=Mock(all=Mock(return_value=[])))
        ))
        
        result = await service.get_user_notifications(
            user_id="user123",
            unread_only=True
        )
        
        assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_mark_notification_as_read(self, service, mock_db_session):
        """Test marking notification as read."""
        mock_notification = Mock(is_read=False)
        mock_db_session.execute = AsyncMock(return_value=Mock(
            scalar_one_or_none=Mock(return_value=mock_notification)
        ))
        mock_db_session.commit = AsyncMock()
        
        result = await service.mark_notification_as_read(
            notification_id=1,
            user_id="user123"
        )
        
        assert result['success'] is True
        assert mock_notification.is_read is True
