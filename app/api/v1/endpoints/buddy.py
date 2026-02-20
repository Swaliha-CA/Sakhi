"""Buddy System API endpoints

Provides REST API for intergenerational profile linking:
- Create buddy link requests
- Accept/reject requests
- Manage permissions
- Revoke links
- Log data on behalf of elder
- Get linked profiles
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.sqlite_manager import get_db
from app.services.buddy_system_service import (
    get_buddy_system_service,
    BuddySystemService,
    BuddyRole,
    BuddyPermission,
    BuddyLinkInfo,
    LinkRequestInfo
)
from app.core.logging import logger


router = APIRouter(prefix="/buddy", tags=["buddy"])


# Request/Response Models

class CreateLinkRequestModel(BaseModel):
    """Request to create a buddy link"""
    requester_id: int = Field(..., description="User ID of person initiating request")
    recipient_id: int = Field(..., description="User ID of person receiving request")
    requester_role: str = Field(..., description="Role of requester (elder or digital_helper)")
    recipient_role: str = Field(..., description="Role of recipient (elder or digital_helper)")
    proposed_permissions: List[str] = Field(..., description="List of requested permissions")
    message: Optional[str] = Field(None, description="Optional message to recipient")


class RespondToRequestModel(BaseModel):
    """Response to a buddy link request"""
    recipient_id: int = Field(..., description="User ID of recipient responding")
    response_message: Optional[str] = Field(None, description="Optional response message")


class RevokeLinkModel(BaseModel):
    """Request to revoke a buddy link"""
    user_id: int = Field(..., description="User ID of person revoking link")
    reason: Optional[str] = Field(None, description="Optional reason for revocation")


class UpdatePermissionsModel(BaseModel):
    """Request to update buddy link permissions"""
    elder_id: int = Field(..., description="Elder user ID (must match link's elder)")
    new_permissions: List[str] = Field(..., description="New list of permissions")


class LogDataForElderModel(BaseModel):
    """Request to log data on behalf of elder"""
    helper_id: int = Field(..., description="Digital helper user ID")
    elder_id: int = Field(..., description="Elder user ID")
    event_type: str = Field(..., description="Type of health event")
    event_data: dict = Field(..., description="Event data")
    device_id: str = Field(..., description="Device ID")


class BuddyLinkResponse(BaseModel):
    """Response model for buddy link"""
    link_id: int
    elder_id: int
    elder_name: str
    helper_id: int
    helper_name: str
    permissions: List[str]
    created_at: str
    is_active: bool
    revoked_at: Optional[str] = None
    revoked_by: Optional[int] = None
    revocation_reason: Optional[str] = None


class LinkRequestResponse(BaseModel):
    """Response model for link request"""
    request_id: int
    requester_id: int
    requester_name: str
    requester_role: str
    recipient_id: int
    recipient_name: str
    recipient_role: str
    proposed_permissions: List[str]
    message: Optional[str]
    status: str
    requested_at: str
    responded_at: Optional[str] = None
    response_message: Optional[str] = None


# Endpoints

@router.post("/request", response_model=LinkRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_link_request(
    request: CreateLinkRequestModel,
    db: Session = Depends(get_db),
    service: BuddySystemService = Depends(get_buddy_system_service)
):
    """
    Create a buddy link request requiring consent from both parties
    
    One user must be elder, one must be digital_helper.
    Request will be pending until recipient accepts or rejects.
    """
    try:
        # Convert string roles to enum
        requester_role = BuddyRole(request.requester_role)
        recipient_role = BuddyRole(request.recipient_role)
        
        # Convert string permissions to enum
        permissions = [BuddyPermission(p) for p in request.proposed_permissions]
        
        # Create request
        result = service.create_link_request(
            db=db,
            requester_id=request.requester_id,
            recipient_id=request.recipient_id,
            requester_role=requester_role,
            recipient_role=recipient_role,
            proposed_permissions=permissions,
            message=request.message
        )
        
        return LinkRequestResponse(
            request_id=result.request_id,
            requester_id=result.requester_id,
            requester_name=result.requester_name,
            requester_role=result.requester_role,
            recipient_id=result.recipient_id,
            recipient_name=result.recipient_name,
            recipient_role=result.recipient_role,
            proposed_permissions=result.proposed_permissions,
            message=result.message,
            status=result.status,
            requested_at=result.requested_at.isoformat()
        )
    
    except ValueError as e:
        logger.error(f"Invalid request: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating link request: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/request/{request_id}/accept", response_model=BuddyLinkResponse)
async def accept_link_request(
    request_id: int,
    response: RespondToRequestModel,
    db: Session = Depends(get_db),
    service: BuddySystemService = Depends(get_buddy_system_service)
):
    """
    Accept a buddy link request and create active link
    
    Only the recipient can accept the request.
    Creates an active buddy link with the proposed permissions.
    """
    try:
        result = service.accept_link_request(
            db=db,
            request_id=request_id,
            recipient_id=response.recipient_id,
            response_message=response.response_message
        )
        
        return BuddyLinkResponse(
            link_id=result.link_id,
            elder_id=result.elder_id,
            elder_name=result.elder_name,
            helper_id=result.helper_id,
            helper_name=result.helper_name,
            permissions=result.permissions,
            created_at=result.created_at.isoformat(),
            is_active=result.is_active
        )
    
    except ValueError as e:
        logger.error(f"Invalid request: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error accepting link request: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/request/{request_id}/reject")
async def reject_link_request(
    request_id: int,
    response: RespondToRequestModel,
    db: Session = Depends(get_db),
    service: BuddySystemService = Depends(get_buddy_system_service)
):
    """
    Reject a buddy link request
    
    Only the recipient can reject the request.
    """
    try:
        result = service.reject_link_request(
            db=db,
            request_id=request_id,
            recipient_id=response.recipient_id,
            response_message=response.response_message
        )
        
        return result
    
    except ValueError as e:
        logger.error(f"Invalid request: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error rejecting link request: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/link/{link_id}/revoke")
async def revoke_link(
    link_id: int,
    request: RevokeLinkModel,
    db: Session = Depends(get_db),
    service: BuddySystemService = Depends(get_buddy_system_service)
):
    """
    Revoke an active buddy link
    
    Either the elder or helper can revoke the link.
    """
    try:
        result = service.revoke_link(
            db=db,
            link_id=link_id,
            user_id=request.user_id,
            reason=request.reason
        )
        
        return result
    
    except ValueError as e:
        logger.error(f"Invalid request: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error revoking link: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/user/{user_id}/links", response_model=List[BuddyLinkResponse])
async def get_user_links(
    user_id: int,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    service: BuddySystemService = Depends(get_buddy_system_service)
):
    """
    Get all buddy links for a user
    
    Returns links where user is either elder or helper.
    """
    try:
        links = service.get_user_links(
            db=db,
            user_id=user_id,
            include_inactive=include_inactive
        )
        
        return [
            BuddyLinkResponse(
                link_id=link.link_id,
                elder_id=link.elder_id,
                elder_name=link.elder_name,
                helper_id=link.helper_id,
                helper_name=link.helper_name,
                permissions=link.permissions,
                created_at=link.created_at.isoformat(),
                is_active=link.is_active,
                revoked_at=link.revoked_at.isoformat() if link.revoked_at else None,
                revoked_by=link.revoked_by,
                revocation_reason=link.revocation_reason
            )
            for link in links
        ]
    
    except Exception as e:
        logger.error(f"Error getting user links: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/user/{user_id}/requests", response_model=List[LinkRequestResponse])
async def get_pending_requests(
    user_id: int,
    db: Session = Depends(get_db),
    service: BuddySystemService = Depends(get_buddy_system_service)
):
    """
    Get pending buddy link requests for a user
    
    Returns both sent and received requests.
    """
    try:
        requests = service.get_pending_requests(db=db, user_id=user_id)
        
        return [
            LinkRequestResponse(
                request_id=req.request_id,
                requester_id=req.requester_id,
                requester_name=req.requester_name,
                requester_role=req.requester_role,
                recipient_id=req.recipient_id,
                recipient_name=req.recipient_name,
                recipient_role=req.recipient_role,
                proposed_permissions=req.proposed_permissions,
                message=req.message,
                status=req.status,
                requested_at=req.requested_at.isoformat(),
                responded_at=req.responded_at.isoformat() if req.responded_at else None,
                response_message=req.response_message
            )
            for req in requests
        ]
    
    except Exception as e:
        logger.error(f"Error getting pending requests: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.put("/link/{link_id}/permissions", response_model=BuddyLinkResponse)
async def update_permissions(
    link_id: int,
    request: UpdatePermissionsModel,
    db: Session = Depends(get_db),
    service: BuddySystemService = Depends(get_buddy_system_service)
):
    """
    Update permissions for a buddy link
    
    Only the elder can update permissions.
    """
    try:
        # Convert string permissions to enum
        permissions = [BuddyPermission(p) for p in request.new_permissions]
        
        result = service.update_permissions(
            db=db,
            link_id=link_id,
            elder_id=request.elder_id,
            new_permissions=permissions
        )
        
        return BuddyLinkResponse(
            link_id=result.link_id,
            elder_id=result.elder_id,
            elder_name=result.elder_name,
            helper_id=result.helper_id,
            helper_name=result.helper_name,
            permissions=result.permissions,
            created_at=result.created_at.isoformat(),
            is_active=result.is_active
        )
    
    except ValueError as e:
        logger.error(f"Invalid request: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating permissions: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/log-data")
async def log_data_for_elder(
    request: LogDataForElderModel,
    db: Session = Depends(get_db),
    service: BuddySystemService = Depends(get_buddy_system_service)
):
    """
    Log health data on behalf of an elder
    
    Helper must have LOG_DATA permission.
    Data is attributed to the elder, not the helper.
    """
    try:
        result = service.log_data_for_elder(
            db=db,
            helper_id=request.helper_id,
            elder_id=request.elder_id,
            event_type=request.event_type,
            event_data=request.event_data,
            device_id=request.device_id
        )
        
        return result
    
    except ValueError as e:
        logger.error(f"Invalid request: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error logging data for elder: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/check-permission/{helper_id}/{elder_id}/{permission}")
async def check_permission(
    helper_id: int,
    elder_id: int,
    permission: str,
    db: Session = Depends(get_db),
    service: BuddySystemService = Depends(get_buddy_system_service)
):
    """
    Check if a helper has a specific permission for an elder
    
    Returns True if permission granted, False otherwise.
    """
    try:
        # Convert string permission to enum
        perm = BuddyPermission(permission)
        
        has_permission = service.check_permission(
            db=db,
            helper_id=helper_id,
            elder_id=elder_id,
            permission=perm
        )
        
        return {
            "helper_id": helper_id,
            "elder_id": elder_id,
            "permission": permission,
            "granted": has_permission
        }
    
    except ValueError as e:
        logger.error(f"Invalid permission: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error checking permission: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


# Heritage Recipe Models

class AddHeritageRecipeModel(BaseModel):
    """Request to add a heritage recipe"""
    user_id: int = Field(..., description="User ID (elder or helper)")
    name: str = Field(..., description="Recipe name")
    region: str = Field(..., description="Region (north, south, east, west, central)")
    ingredients: List[str] = Field(..., description="List of ingredients")
    preparation: str = Field(..., description="Preparation instructions")
    nutritional_benefits: List[str] = Field(..., description="List of nutritional benefits")
    micronutrients: dict = Field(..., description="Dict of micronutrient levels")
    voice_recording_url: Optional[str] = Field(None, description="Optional URL to voice recording")
    season: Optional[str] = Field(None, description="Optional season (summer, monsoon, winter, spring)")
    tags: Optional[List[str]] = Field(None, description="Optional list of tags")


class HeritageRecipeResponse(BaseModel):
    """Response model for heritage recipe"""
    recipe_id: str
    name: str
    region: str
    ingredients: List[str]
    preparation: str
    nutritional_benefits: List[str]
    micronutrients: dict
    voice_recording_url: Optional[str]
    contributed_by: Optional[str]
    season: Optional[str]
    tags: Optional[List[str]]
    created_at: str


# Heritage Recipe Endpoints

@router.post("/heritage-recipe", status_code=status.HTTP_201_CREATED)
async def add_heritage_recipe(
    request: AddHeritageRecipeModel,
    db: Session = Depends(get_db),
    service: BuddySystemService = Depends(get_buddy_system_service)
):
    """
    Add a voice-recorded heritage recipe to the family knowledge base
    
    Recipes are shared across all linked family members.
    """
    try:
        result = service.add_heritage_recipe(
            db=db,
            user_id=request.user_id,
            name=request.name,
            region=request.region,
            ingredients=request.ingredients,
            preparation=request.preparation,
            nutritional_benefits=request.nutritional_benefits,
            micronutrients=request.micronutrients,
            voice_recording_url=request.voice_recording_url,
            season=request.season,
            tags=request.tags
        )
        
        return result
    
    except ValueError as e:
        logger.error(f"Invalid request: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding heritage recipe: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/heritage-recipes/{user_id}", response_model=List[HeritageRecipeResponse])
async def get_family_recipes(
    user_id: int,
    region: Optional[str] = None,
    db: Session = Depends(get_db),
    service: BuddySystemService = Depends(get_buddy_system_service)
):
    """
    Get all heritage recipes accessible to a user (family knowledge base)
    
    For users with buddy links, this includes recipes from all linked family members.
    """
    try:
        recipes = service.get_family_recipes(
            db=db,
            user_id=user_id,
            region=region
        )
        
        return recipes
    
    except Exception as e:
        logger.error(f"Error getting family recipes: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/family-members/{user_id}")
async def get_linked_family_members(
    user_id: int,
    db: Session = Depends(get_db),
    service: BuddySystemService = Depends(get_buddy_system_service)
):
    """
    Get all user IDs linked to this user (family members)
    
    Returns list of linked user IDs.
    """
    try:
        linked_ids = service.get_linked_family_members(
            db=db,
            user_id=user_id
        )
        
        return {
            "user_id": user_id,
            "linked_family_members": linked_ids,
            "count": len(linked_ids)
        }
    
    except Exception as e:
        logger.error(f"Error getting linked family members: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
