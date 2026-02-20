"""Buddy System Service for intergenerational health profile linking

Enables elders to link with digital helpers (family members) who can:
- Assist with data logging
- Receive health alerts on their behalf
- View health data with granular permission controls
- Share heritage recipes and cultural knowledge

Features:
- Buddy link request workflow with consent from both parties
- Granular permission controls (view health data, log data, receive alerts, manage appointments)
- Privacy controls allowing elders to specify what data is shared
- Dual notification for elder alerts
- Data attribution correctness (data logged by helper attributed to elder)
"""
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.db.models import User, BuddyLink, BuddyLinkRequest, HealthRecord
from app.core.logging import logger


def send_health_alert_with_buddy_notification(
    db: Session,
    user_id: int,
    alert_type: str,
    severity: str,
    title: str,
    message: str,
    data_category: Optional[str] = None
) -> Dict[str, Any]:
    """
    Helper function to send health alerts with automatic buddy notifications
    
    This is a convenience function that integrates with the notification service
    to send alerts to both the user and their linked digital helpers.
    
    Args:
        db: Database session
        user_id: User ID to send alert to
        alert_type: Type of alert (high_ppd_risk, micronutrient_deficiency, etc.)
        severity: Alert severity (info, warning, critical)
        title: Alert title
        message: Alert message
        data_category: Data category for privacy filtering
    
    Returns:
        Notification result dictionary
    
    Example:
        >>> send_health_alert_with_buddy_notification(
        ...     db=db,
        ...     user_id=123,
        ...     alert_type="high_ppd_risk",
        ...     severity="critical",
        ...     title="PPD Risk Alert",
        ...     message="Your PPD risk score is high. Please consult your healthcare provider.",
        ...     data_category="ppd_risk"
        ... )
    """
    from app.services.notification_service import get_notification_service, HealthAlert
    
    notification_service = get_notification_service()
    
    alert = HealthAlert(
        user_id=user_id,
        alert_type=alert_type,
        severity=severity,
        title=title,
        message=message,
        data_category=data_category
    )
    
    return notification_service.send_health_alert(db=db, alert=alert)


class BuddyRole(str, Enum):
    """Roles in buddy relationship"""
    ELDER = "elder"
    DIGITAL_HELPER = "digital_helper"


class BuddyPermission(str, Enum):
    """Granular permissions for buddy access"""
    VIEW_HEALTH_DATA = "view_health_data"
    LOG_DATA = "log_data"
    RECEIVE_ALERTS = "receive_alerts"
    MANAGE_APPOINTMENTS = "manage_appointments"
    VIEW_LAB_RESULTS = "view_lab_results"
    VIEW_SCREENINGS = "view_screenings"
    VIEW_PRODUCT_SCANS = "view_product_scans"
    SHARE_RECIPES = "share_recipes"


class LinkStatus(str, Enum):
    """Status of buddy link"""
    PENDING = "pending"
    ACTIVE = "active"
    REJECTED = "rejected"
    REVOKED = "revoked"


@dataclass
class BuddyLinkInfo:
    """Information about a buddy link"""
    link_id: int
    elder_id: int
    elder_name: str
    helper_id: int
    helper_name: str
    permissions: List[str]
    created_at: datetime
    is_active: bool
    revoked_at: Optional[datetime] = None
    revoked_by: Optional[int] = None
    revocation_reason: Optional[str] = None


@dataclass
class LinkRequestInfo:
    """Information about a buddy link request"""
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
    requested_at: datetime
    responded_at: Optional[datetime] = None
    response_message: Optional[str] = None


class BuddySystemService:
    """
    Buddy System Service for profile linking
    
    Features:
    - Create buddy link requests with consent workflow
    - Accept/reject link requests
    - Manage granular permissions
    - Revoke links with reason tracking
    - Check permissions for access control
    - Log data on behalf of elder (with proper attribution)
    - Get linked profiles
    """
    
    def create_link_request(
        self,
        db: Session,
        requester_id: int,
        recipient_id: int,
        requester_role: BuddyRole,
        recipient_role: BuddyRole,
        proposed_permissions: List[BuddyPermission],
        message: Optional[str] = None
    ) -> LinkRequestInfo:
        """
        Create a buddy link request requiring consent from both parties
        
        Args:
            db: Database session
            requester_id: User ID of person initiating the request
            recipient_id: User ID of person receiving the request
            requester_role: Role of requester (elder or digital_helper)
            recipient_role: Role of recipient (elder or digital_helper)
            proposed_permissions: List of permissions being requested
            message: Optional message to recipient
        
        Returns:
            LinkRequestInfo with request details
        
        Raises:
            ValueError: If users don't exist, roles are invalid, or link already exists
        """
        logger.info(
            f"Creating buddy link request: {requester_id} ({requester_role.value}) -> "
            f"{recipient_id} ({recipient_role.value})"
        )
        
        # Validate users exist
        requester = db.query(User).filter(User.id == requester_id).first()
        recipient = db.query(User).filter(User.id == recipient_id).first()
        
        if not requester:
            raise ValueError(f"Requester user {requester_id} not found")
        if not recipient:
            raise ValueError(f"Recipient user {recipient_id} not found")
        
        # Validate roles (one must be elder, one must be helper)
        if requester_role == recipient_role:
            raise ValueError("Requester and recipient must have different roles (one elder, one helper)")
        
        if requester_role not in [BuddyRole.ELDER, BuddyRole.DIGITAL_HELPER]:
            raise ValueError(f"Invalid requester role: {requester_role}")
        if recipient_role not in [BuddyRole.ELDER, BuddyRole.DIGITAL_HELPER]:
            raise ValueError(f"Invalid recipient role: {recipient_role}")
        
        # Check if link already exists
        existing_link = db.query(BuddyLink).filter(
            or_(
                and_(BuddyLink.elder_id == requester_id, BuddyLink.helper_id == recipient_id),
                and_(BuddyLink.elder_id == recipient_id, BuddyLink.helper_id == requester_id)
            ),
            BuddyLink.is_active == True
        ).first()
        
        if existing_link:
            raise ValueError("Active buddy link already exists between these users")
        
        # Check if pending request already exists
        existing_request = db.query(BuddyLinkRequest).filter(
            or_(
                and_(BuddyLinkRequest.requester_id == requester_id, BuddyLinkRequest.recipient_id == recipient_id),
                and_(BuddyLinkRequest.requester_id == recipient_id, BuddyLinkRequest.recipient_id == requester_id)
            ),
            BuddyLinkRequest.status == LinkStatus.PENDING.value
        ).first()
        
        if existing_request:
            raise ValueError("Pending buddy link request already exists between these users")
        
        # Convert permissions to comma-separated string
        permissions_str = ",".join([p.value for p in proposed_permissions])
        
        # Create request
        request = BuddyLinkRequest(
            requester_id=requester_id,
            recipient_id=recipient_id,
            requester_role=requester_role.value,
            recipient_role=recipient_role.value,
            proposed_permissions=permissions_str,
            message=message,
            status=LinkStatus.PENDING.value
        )
        
        db.add(request)
        db.commit()
        db.refresh(request)
        
        logger.info(f"Buddy link request created with ID: {request.id}")
        
        return LinkRequestInfo(
            request_id=request.id,
            requester_id=requester_id,
            requester_name=requester.name or "Unknown",
            requester_role=requester_role.value,
            recipient_id=recipient_id,
            recipient_name=recipient.name or "Unknown",
            recipient_role=recipient_role.value,
            proposed_permissions=[p.value for p in proposed_permissions],
            message=message,
            status=LinkStatus.PENDING.value,
            requested_at=request.requested_at
        )
    
    def accept_link_request(
        self,
        db: Session,
        request_id: int,
        recipient_id: int,
        response_message: Optional[str] = None
    ) -> BuddyLinkInfo:
        """
        Accept a buddy link request and create active link
        
        Args:
            db: Database session
            request_id: ID of the link request
            recipient_id: User ID of recipient accepting the request
            response_message: Optional response message
        
        Returns:
            BuddyLinkInfo for the newly created link
        
        Raises:
            ValueError: If request not found, already responded to, or user not authorized
        """
        logger.info(f"Accepting buddy link request {request_id} by user {recipient_id}")
        
        # Get request
        request = db.query(BuddyLinkRequest).filter(BuddyLinkRequest.id == request_id).first()
        
        if not request:
            raise ValueError(f"Link request {request_id} not found")
        
        if request.recipient_id != recipient_id:
            raise ValueError("Only the recipient can accept this request")
        
        if request.status != LinkStatus.PENDING.value:
            raise ValueError(f"Request already responded to with status: {request.status}")
        
        # Determine elder and helper IDs based on roles
        if request.requester_role == BuddyRole.ELDER.value:
            elder_id = request.requester_id
            helper_id = request.recipient_id
        else:
            elder_id = request.recipient_id
            helper_id = request.requester_id
        
        # Create buddy link
        link = BuddyLink(
            elder_id=elder_id,
            helper_id=helper_id,
            permissions=request.proposed_permissions,
            is_active=True
        )
        
        db.add(link)
        
        # Update request status
        request.status = LinkStatus.ACTIVE.value
        request.responded_at = datetime.utcnow()
        request.response_message = response_message
        
        db.commit()
        db.refresh(link)
        
        logger.info(f"Buddy link created with ID: {link.id} (Elder: {elder_id}, Helper: {helper_id})")
        
        # Get user names
        elder = db.query(User).filter(User.id == elder_id).first()
        helper = db.query(User).filter(User.id == helper_id).first()
        
        return BuddyLinkInfo(
            link_id=link.id,
            elder_id=elder_id,
            elder_name=elder.name if elder else "Unknown",
            helper_id=helper_id,
            helper_name=helper.name if helper else "Unknown",
            permissions=link.permissions.split(","),
            created_at=link.created_at,
            is_active=True
        )
    
    def reject_link_request(
        self,
        db: Session,
        request_id: int,
        recipient_id: int,
        response_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Reject a buddy link request
        
        Args:
            db: Database session
            request_id: ID of the link request
            recipient_id: User ID of recipient rejecting the request
            response_message: Optional reason for rejection
        
        Returns:
            Status dictionary
        
        Raises:
            ValueError: If request not found, already responded to, or user not authorized
        """
        logger.info(f"Rejecting buddy link request {request_id} by user {recipient_id}")
        
        # Get request
        request = db.query(BuddyLinkRequest).filter(BuddyLinkRequest.id == request_id).first()
        
        if not request:
            raise ValueError(f"Link request {request_id} not found")
        
        if request.recipient_id != recipient_id:
            raise ValueError("Only the recipient can reject this request")
        
        if request.status != LinkStatus.PENDING.value:
            raise ValueError(f"Request already responded to with status: {request.status}")
        
        # Update request status
        request.status = LinkStatus.REJECTED.value
        request.responded_at = datetime.utcnow()
        request.response_message = response_message
        
        db.commit()
        
        logger.info(f"Buddy link request {request_id} rejected")
        
        return {
            "status": "rejected",
            "request_id": request_id,
            "message": "Link request rejected"
        }
    
    def revoke_link(
        self,
        db: Session,
        link_id: int,
        user_id: int,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Revoke an active buddy link (can be done by either party)
        
        Args:
            db: Database session
            link_id: ID of the buddy link
            user_id: User ID of person revoking the link
            reason: Optional reason for revocation
        
        Returns:
            Status dictionary
        
        Raises:
            ValueError: If link not found, already revoked, or user not authorized
        """
        logger.info(f"Revoking buddy link {link_id} by user {user_id}")
        
        # Get link
        link = db.query(BuddyLink).filter(BuddyLink.id == link_id).first()
        
        if not link:
            raise ValueError(f"Buddy link {link_id} not found")
        
        if user_id not in [link.elder_id, link.helper_id]:
            raise ValueError("Only linked users can revoke this link")
        
        if not link.is_active:
            raise ValueError("Link is already revoked")
        
        # Revoke link
        link.is_active = False
        link.revoked_at = datetime.utcnow()
        link.revoked_by = user_id
        link.revocation_reason = reason
        
        db.commit()
        
        logger.info(f"Buddy link {link_id} revoked by user {user_id}")
        
        return {
            "status": "revoked",
            "link_id": link_id,
            "revoked_by": user_id,
            "revoked_at": link.revoked_at.isoformat(),
            "message": "Buddy link revoked successfully"
        }
    
    def get_user_links(
        self,
        db: Session,
        user_id: int,
        include_inactive: bool = False
    ) -> List[BuddyLinkInfo]:
        """
        Get all buddy links for a user
        
        Args:
            db: Database session
            user_id: User ID
            include_inactive: Whether to include revoked links
        
        Returns:
            List of BuddyLinkInfo
        """
        logger.info(f"Getting buddy links for user {user_id}")
        
        # Query links where user is either elder or helper
        query = db.query(BuddyLink).filter(
            or_(
                BuddyLink.elder_id == user_id,
                BuddyLink.helper_id == user_id
            )
        )
        
        if not include_inactive:
            query = query.filter(BuddyLink.is_active == True)
        
        links = query.all()
        
        # Convert to BuddyLinkInfo
        result = []
        for link in links:
            elder = db.query(User).filter(User.id == link.elder_id).first()
            helper = db.query(User).filter(User.id == link.helper_id).first()
            
            result.append(BuddyLinkInfo(
                link_id=link.id,
                elder_id=link.elder_id,
                elder_name=elder.name if elder else "Unknown",
                helper_id=link.helper_id,
                helper_name=helper.name if helper else "Unknown",
                permissions=link.permissions.split(","),
                created_at=link.created_at,
                is_active=link.is_active,
                revoked_at=link.revoked_at,
                revoked_by=link.revoked_by,
                revocation_reason=link.revocation_reason
            ))
        
        logger.info(f"Found {len(result)} buddy links for user {user_id}")
        
        return result
    
    def get_pending_requests(
        self,
        db: Session,
        user_id: int
    ) -> List[LinkRequestInfo]:
        """
        Get pending buddy link requests for a user (both sent and received)
        
        Args:
            db: Database session
            user_id: User ID
        
        Returns:
            List of LinkRequestInfo
        """
        logger.info(f"Getting pending requests for user {user_id}")
        
        # Query requests where user is either requester or recipient
        requests = db.query(BuddyLinkRequest).filter(
            or_(
                BuddyLinkRequest.requester_id == user_id,
                BuddyLinkRequest.recipient_id == user_id
            ),
            BuddyLinkRequest.status == LinkStatus.PENDING.value
        ).all()
        
        # Convert to LinkRequestInfo
        result = []
        for request in requests:
            requester = db.query(User).filter(User.id == request.requester_id).first()
            recipient = db.query(User).filter(User.id == request.recipient_id).first()
            
            result.append(LinkRequestInfo(
                request_id=request.id,
                requester_id=request.requester_id,
                requester_name=requester.name if requester else "Unknown",
                requester_role=request.requester_role,
                recipient_id=request.recipient_id,
                recipient_name=recipient.name if recipient else "Unknown",
                recipient_role=request.recipient_role,
                proposed_permissions=request.proposed_permissions.split(","),
                message=request.message,
                status=request.status,
                requested_at=request.requested_at,
                responded_at=request.responded_at,
                response_message=request.response_message
            ))
        
        logger.info(f"Found {len(result)} pending requests for user {user_id}")
        
        return result
    
    def check_permission(
        self,
        db: Session,
        helper_id: int,
        elder_id: int,
        permission: BuddyPermission
    ) -> bool:
        """
        Check if a helper has a specific permission for an elder
        
        Args:
            db: Database session
            helper_id: Digital helper user ID
            elder_id: Elder user ID
            permission: Permission to check
        
        Returns:
            True if permission granted, False otherwise
        """
        # Get active link
        link = db.query(BuddyLink).filter(
            BuddyLink.elder_id == elder_id,
            BuddyLink.helper_id == helper_id,
            BuddyLink.is_active == True
        ).first()
        
        if not link:
            return False
        
        # Check if permission is in the list
        permissions = link.permissions.split(",")
        return permission.value in permissions
    
    def update_permissions(
        self,
        db: Session,
        link_id: int,
        elder_id: int,
        new_permissions: List[BuddyPermission]
    ) -> BuddyLinkInfo:
        """
        Update permissions for a buddy link (only elder can update)
        
        Args:
            db: Database session
            link_id: ID of the buddy link
            elder_id: Elder user ID (must match link's elder)
            new_permissions: New list of permissions
        
        Returns:
            Updated BuddyLinkInfo
        
        Raises:
            ValueError: If link not found, not active, or user not authorized
        """
        logger.info(f"Updating permissions for buddy link {link_id} by elder {elder_id}")
        
        # Get link
        link = db.query(BuddyLink).filter(BuddyLink.id == link_id).first()
        
        if not link:
            raise ValueError(f"Buddy link {link_id} not found")
        
        if link.elder_id != elder_id:
            raise ValueError("Only the elder can update permissions")
        
        if not link.is_active:
            raise ValueError("Cannot update permissions for inactive link")
        
        # Update permissions
        permissions_str = ",".join([p.value for p in new_permissions])
        link.permissions = permissions_str
        link.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(link)
        
        logger.info(f"Permissions updated for buddy link {link_id}")
        
        # Get user names
        elder = db.query(User).filter(User.id == link.elder_id).first()
        helper = db.query(User).filter(User.id == link.helper_id).first()
        
        return BuddyLinkInfo(
            link_id=link.id,
            elder_id=link.elder_id,
            elder_name=elder.name if elder else "Unknown",
            helper_id=link.helper_id,
            helper_name=helper.name if helper else "Unknown",
            permissions=link.permissions.split(","),
            created_at=link.created_at,
            is_active=link.is_active
        )
    
    def log_data_for_elder(
        self,
        db: Session,
        helper_id: int,
        elder_id: int,
        event_type: str,
        event_data: Dict[str, Any],
        device_id: str
    ) -> Dict[str, Any]:
        """
        Log health data on behalf of an elder (with proper attribution)
        
        Args:
            db: Database session
            helper_id: Digital helper user ID
            elder_id: Elder user ID
            event_type: Type of health event
            event_data: Event data
            device_id: Device ID
        
        Returns:
            Created health record info
        
        Raises:
            ValueError: If no active link or permission not granted
        """
        logger.info(f"Helper {helper_id} logging data for elder {elder_id}")
        
        # Check if helper has LOG_DATA permission
        if not self.check_permission(db, helper_id, elder_id, BuddyPermission.LOG_DATA):
            raise ValueError("Helper does not have permission to log data for this elder")
        
        # Create health record attributed to elder
        record = HealthRecord(
            user_id=elder_id,  # Data attributed to elder, not helper
            event_type=event_type,
            event_data={
                **event_data,
                "logged_by_helper": helper_id,  # Track who logged it
                "logged_via_buddy_system": True
            },
            recorded_at=datetime.utcnow(),
            device_id=device_id,
            synced_to_cloud=False
        )
        
        db.add(record)
        db.commit()
        db.refresh(record)
        
        logger.info(
            f"Health record {record.id} created for elder {elder_id} "
            f"by helper {helper_id}"
        )
        
        return {
            "record_id": record.id,
            "user_id": elder_id,
            "event_type": event_type,
            "logged_by": helper_id,
            "recorded_at": record.recorded_at.isoformat(),
            "message": "Data logged successfully for elder"
        }
    
    def get_link_by_users(
        self,
        db: Session,
        user1_id: int,
        user2_id: int
    ) -> Optional[BuddyLinkInfo]:
        """
        Get active buddy link between two users (regardless of role)
        
        Args:
            db: Database session
            user1_id: First user ID
            user2_id: Second user ID
        
        Returns:
            BuddyLinkInfo if link exists, None otherwise
        """
        # Query link where users are either elder or helper
        link = db.query(BuddyLink).filter(
            or_(
                and_(BuddyLink.elder_id == user1_id, BuddyLink.helper_id == user2_id),
                and_(BuddyLink.elder_id == user2_id, BuddyLink.helper_id == user1_id)
            ),
            BuddyLink.is_active == True
        ).first()
        
        if not link:
            return None
        
        # Get user names
        elder = db.query(User).filter(User.id == link.elder_id).first()
        helper = db.query(User).filter(User.id == link.helper_id).first()
        
        return BuddyLinkInfo(
            link_id=link.id,
            elder_id=link.elder_id,
            elder_name=elder.name if elder else "Unknown",
            helper_id=link.helper_id,
            helper_name=helper.name if helper else "Unknown",
            permissions=link.permissions.split(","),
            created_at=link.created_at,
            is_active=link.is_active
        )
    
    def add_heritage_recipe(
        self,
        db: Session,
        user_id: int,
        name: str,
        region: str,
        ingredients: List[str],
        preparation: str,
        nutritional_benefits: List[str],
        micronutrients: Dict[str, float],
        voice_recording_url: Optional[str] = None,
        season: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Add a voice-recorded heritage recipe to the family knowledge base
        
        Args:
            db: Database session
            user_id: User ID (elder or helper)
            name: Recipe name
            region: Region (north, south, east, west, central)
            ingredients: List of ingredients
            preparation: Preparation instructions
            nutritional_benefits: List of nutritional benefits
            micronutrients: Dict of micronutrient levels
            voice_recording_url: Optional URL to voice recording
            season: Optional season (summer, monsoon, winter, spring)
            tags: Optional list of tags
        
        Returns:
            Created recipe info
        """
        from app.db.models import HeritageRecipeDB
        import uuid
        
        logger.info(f"User {user_id} adding heritage recipe: {name}")
        
        # Get user info
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Generate unique recipe ID
        recipe_id = f"recipe_{uuid.uuid4().hex[:12]}"
        
        # Create recipe
        recipe = HeritageRecipeDB(
            recipe_id=recipe_id,
            name=name,
            region=region,
            ingredients=ingredients,
            preparation=preparation,
            nutritional_benefits=nutritional_benefits,
            micronutrients=micronutrients,
            voice_recording_url=voice_recording_url,
            contributed_by=user.name,
            season=season,
            tags=tags or [],
            synced_to_cloud=False
        )
        
        db.add(recipe)
        db.commit()
        db.refresh(recipe)
        
        logger.info(f"Heritage recipe {recipe_id} created by {user.name}")
        
        return {
            "recipe_id": recipe.recipe_id,
            "name": recipe.name,
            "region": recipe.region,
            "contributed_by": recipe.contributed_by,
            "voice_recording_url": recipe.voice_recording_url,
            "created_at": recipe.created_at.isoformat(),
            "message": "Heritage recipe added successfully"
        }
    
    def get_family_recipes(
        self,
        db: Session,
        user_id: int,
        region: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all heritage recipes accessible to a user (family knowledge base)
        
        For users with buddy links, this includes recipes from all linked family members.
        
        Args:
            db: Database session
            user_id: User ID
            region: Optional region filter
        
        Returns:
            List of recipe info
        """
        from app.db.models import HeritageRecipeDB
        
        logger.info(f"Getting family recipes for user {user_id}")
        
        # Get all recipes (family knowledge base is shared across all users)
        # In a real implementation, you might want to filter by family/linked profiles
        query = db.query(HeritageRecipeDB)
        
        if region:
            query = query.filter(HeritageRecipeDB.region == region)
        
        recipes = query.all()
        
        return [
            {
                "recipe_id": recipe.recipe_id,
                "name": recipe.name,
                "region": recipe.region,
                "ingredients": recipe.ingredients,
                "preparation": recipe.preparation,
                "nutritional_benefits": recipe.nutritional_benefits,
                "micronutrients": recipe.micronutrients,
                "voice_recording_url": recipe.voice_recording_url,
                "contributed_by": recipe.contributed_by,
                "season": recipe.season,
                "tags": recipe.tags,
                "created_at": recipe.created_at.isoformat()
            }
            for recipe in recipes
        ]
    
    def get_linked_family_members(
        self,
        db: Session,
        user_id: int
    ) -> List[int]:
        """
        Get all user IDs linked to this user (family members)
        
        Args:
            db: Database session
            user_id: User ID
        
        Returns:
            List of linked user IDs
        """
        # Get all active links where user is either elder or helper
        links = db.query(BuddyLink).filter(
            or_(
                BuddyLink.elder_id == user_id,
                BuddyLink.helper_id == user_id
            ),
            BuddyLink.is_active == True
        ).all()
        
        # Extract linked user IDs
        linked_ids = []
        for link in links:
            if link.elder_id == user_id:
                linked_ids.append(link.helper_id)
            else:
                linked_ids.append(link.elder_id)
        
        return linked_ids


# Global service instance
buddy_system_service: Optional[BuddySystemService] = None


def get_buddy_system_service() -> BuddySystemService:
    """
    Get or create global buddy system service instance
    
    Returns:
        BuddySystemService instance
    """
    global buddy_system_service
    
    if buddy_system_service is None:
        buddy_system_service = BuddySystemService()
        logger.info("Buddy system service initialized")
    
    return buddy_system_service
