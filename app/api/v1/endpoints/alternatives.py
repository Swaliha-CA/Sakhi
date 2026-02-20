"""API endpoints for alternative product recommendations"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.sqlite_manager import get_db
from app.services.alternative_product_service import AlternativeProductService
from app.core.logging import logger


router = APIRouter(prefix="/alternatives", tags=["alternatives"])


# Request/Response Models
class FindAlternativesRequest(BaseModel):
    """Request to find product alternatives"""
    product_category: str = Field(..., description="Category of product to replace")
    current_score: float = Field(..., ge=0, le=100, description="Current product's hormonal health score")
    flagged_edcs: Optional[List[str]] = Field(None, description="List of EDC types found in current product")
    price_preference: Optional[str] = Field(None, description="Price preference: budget, mid-range, premium")
    region: Optional[str] = Field(None, description="User's region for availability filtering")
    limit: int = Field(5, ge=1, le=20, description="Maximum number of alternatives to return")


class AlternativeResponse(BaseModel):
    """Alternative product response"""
    product_id: str
    name: str
    brand: Optional[str]
    category: str
    hormonal_health_score: float
    overall_score: float
    description: Optional[str]
    key_ingredients: List[str]
    free_from: List[str]
    price_range: Optional[str]
    availability: List[str]
    online_available: bool
    purchase_links: List[str]
    certifications: List[str]
    match_reason: str


class AddToShoppingListRequest(BaseModel):
    """Request to add product to shopping list"""
    user_id: int = Field(..., description="User ID")
    product_id: str = Field(..., description="Product ID to add")
    device_id: str = Field(..., description="Device ID for sync tracking")
    replaced_product_name: Optional[str] = Field(None, description="Name of product being replaced")
    replaced_product_category: Optional[str] = Field(None, description="Category of product being replaced")
    notes: Optional[str] = Field(None, description="User notes")
    priority: int = Field(0, ge=0, description="User-defined priority")


class ShoppingListItemResponse(BaseModel):
    """Shopping list item response"""
    id: int
    product_id: str
    name: str
    brand: Optional[str]
    category: str
    hormonal_health_score: float
    overall_score: float
    description: Optional[str]
    price_range: Optional[str]
    availability: List[str]
    online_available: bool
    purchase_links: List[str]
    replaced_product_name: Optional[str]
    replaced_product_category: Optional[str]
    notes: Optional[str]
    priority: int
    added_at: str


class NotificationResponse(BaseModel):
    """Product notification response"""
    id: int
    notification_type: str
    title: str
    message: str
    product: dict
    related_category: str
    sent: bool
    read: bool
    created_at: str
    sent_at: Optional[str]
    read_at: Optional[str]


# Endpoints
@router.post("/find", response_model=List[AlternativeResponse])
async def find_alternatives(
    request: FindAlternativesRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Find toxin-free alternatives for a product
    
    Returns alternatives ranked by:
    1. Hormonal Health Score (primary)
    2. Regional availability
    3. Price preference match
    4. Overall score
    """
    try:
        service = AlternativeProductService(db)
        
        alternatives = await service.find_alternatives(
            product_category=request.product_category,
            current_score=request.current_score,
            flagged_edcs=request.flagged_edcs,
            price_preference=request.price_preference,
            region=request.region,
            limit=request.limit
        )
        
        return [alt.to_dict() for alt in alternatives]
        
    except Exception as e:
        logger.error(f"Error finding alternatives: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to find alternatives: {str(e)}"
        )


@router.get("/fallback-categories/{category}", response_model=List[str])
async def get_fallback_categories(
    category: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get fallback product categories with lower EDC risk
    
    Used when no direct alternatives exist for a product.
    """
    try:
        service = AlternativeProductService(db)
        
        fallback_categories = await service.get_fallback_categories(category)
        
        return fallback_categories
        
    except Exception as e:
        logger.error(f"Error getting fallback categories: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get fallback categories: {str(e)}"
        )


@router.post("/shopping-list", response_model=dict)
async def add_to_shopping_list(
    request: AddToShoppingListRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Add a product to user's shopping list
    """
    try:
        service = AlternativeProductService(db)
        
        item = await service.add_to_shopping_list(
            user_id=request.user_id,
            product_id=request.product_id,
            device_id=request.device_id,
            replaced_product_name=request.replaced_product_name,
            replaced_product_category=request.replaced_product_category,
            notes=request.notes,
            priority=request.priority
        )
        
        return {
            "success": True,
            "item_id": item.id,
            "message": "Product added to shopping list"
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error adding to shopping list: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add to shopping list: {str(e)}"
        )


@router.get("/shopping-list/{user_id}", response_model=List[ShoppingListItemResponse])
async def get_shopping_list(
    user_id: int,
    sort_by_priority: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's shopping list
    """
    try:
        service = AlternativeProductService(db)
        
        shopping_list = await service.get_shopping_list(
            user_id=user_id,
            sort_by_priority=sort_by_priority
        )
        
        return shopping_list
        
    except Exception as e:
        logger.error(f"Error getting shopping list: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get shopping list: {str(e)}"
        )


@router.delete("/shopping-list/{user_id}/{item_id}", response_model=dict)
async def remove_from_shopping_list(
    user_id: int,
    item_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Remove an item from shopping list
    """
    try:
        service = AlternativeProductService(db)
        
        success = await service.remove_from_shopping_list(
            user_id=user_id,
            item_id=item_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shopping list item not found"
            )
        
        return {
            "success": True,
            "message": "Item removed from shopping list"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing from shopping list: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove from shopping list: {str(e)}"
        )


@router.get("/notifications/{user_id}", response_model=List[NotificationResponse])
async def get_notifications(
    user_id: int,
    unread_only: bool = False,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """
    Get product notifications for a user
    
    Notifications are created when new safer products are added to the database
    for categories the user has previously scanned.
    """
    try:
        service = AlternativeProductService(db)
        
        notifications = await service.get_user_notifications(
            user_id=user_id,
            unread_only=unread_only,
            limit=limit
        )
        
        return notifications
        
    except Exception as e:
        logger.error(f"Error getting notifications: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get notifications: {str(e)}"
        )


@router.post("/notifications/{user_id}/{notification_id}/read", response_model=dict)
async def mark_notification_read(
    user_id: int,
    notification_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Mark a notification as read
    """
    try:
        service = AlternativeProductService(db)
        
        success = await service.mark_notification_as_read(
            user_id=user_id,
            notification_id=notification_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )
        
        return {
            "success": True,
            "message": "Notification marked as read"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking notification as read: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark notification as read: {str(e)}"
        )


@router.post("/notify-new-product/{product_id}", response_model=dict)
async def notify_new_product(
    product_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Create notifications for users about a new safer product
    
    This endpoint is called when a new product is added to the database.
    It finds users who previously scanned high-risk products in the same category
    and creates notifications for them.
    """
    try:
        service = AlternativeProductService(db)
        
        count = await service.create_new_product_notifications(product_id)
        
        return {
            "success": True,
            "notifications_created": count,
            "message": f"Created {count} notifications for new product"
        }
        
    except Exception as e:
        logger.error(f"Error creating notifications: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create notifications: {str(e)}"
        )
