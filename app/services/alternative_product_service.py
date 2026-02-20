"""Alternative Product Recommendation Service"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import select, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AlternativeProduct,
    ShoppingListItem,
    ProductNotification,
    ProductScan,
    User
)
from app.core.logging import logger


@dataclass
class Alternative:
    """Alternative product recommendation"""
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
    match_reason: str  # Why this alternative was suggested
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "product_id": self.product_id,
            "name": self.name,
            "brand": self.brand,
            "category": self.category,
            "hormonal_health_score": self.hormonal_health_score,
            "overall_score": self.overall_score,
            "description": self.description,
            "key_ingredients": self.key_ingredients,
            "free_from": self.free_from,
            "price_range": self.price_range,
            "availability": self.availability,
            "online_available": self.online_available,
            "purchase_links": self.purchase_links,
            "certifications": self.certifications,
            "match_reason": self.match_reason
        }


class AlternativeProductService:
    """
    Service for recommending toxin-free product alternatives
    
    Implements:
    - Category-based product matching
    - Ranking by Hormonal Health Score, price, and availability
    - Filtering by EDC-free criteria
    """
    
    # Minimum score threshold for recommendations
    MIN_SCORE_THRESHOLD = 60.0
    
    # Category mappings for broader matching
    CATEGORY_GROUPS = {
        "cosmetic": ["cosmetic", "personal_care"],
        "personal_care": ["cosmetic", "personal_care"],
        "food": ["food"],
        "household": ["household"]
    }
    
    def __init__(self, db_session: AsyncSession):
        """
        Initialize alternative product service
        
        Args:
            db_session: Database session for querying products
        """
        self.db_session = db_session
    
    async def find_alternatives(
        self,
        product_category: str,
        current_score: float,
        flagged_edcs: Optional[List[str]] = None,
        price_preference: Optional[str] = None,
        region: Optional[str] = None,
        limit: int = 5
    ) -> List[Alternative]:
        """
        Find toxin-free alternatives for a product
        
        Args:
            product_category: Category of the product to replace
            current_score: Current product's hormonal health score
            flagged_edcs: List of EDC types found in current product
            price_preference: User's price preference (budget, mid-range, premium)
            region: User's region for availability filtering
            limit: Maximum number of alternatives to return
        
        Returns:
            List of Alternative products ranked by score, price, and availability
        """
        logger.info(
            f"Finding alternatives for category: {product_category}, "
            f"current score: {current_score:.1f}"
        )
        
        # Get related categories for broader matching
        related_categories = self.CATEGORY_GROUPS.get(
            product_category.lower(),
            [product_category.lower()]
        )
        
        # Build query
        query = select(AlternativeProduct).where(
            and_(
                AlternativeProduct.category.in_(related_categories),
                AlternativeProduct.hormonal_health_score > current_score,
                AlternativeProduct.hormonal_health_score >= self.MIN_SCORE_THRESHOLD
            )
        )
        
        # Filter by EDC-free criteria if specified
        if flagged_edcs:
            # Products should be free from the flagged EDCs
            for edc in flagged_edcs:
                query = query.where(
                    AlternativeProduct.free_from.contains([edc])
                )
        
        # Filter by price preference if specified
        if price_preference:
            query = query.where(
                AlternativeProduct.price_range == price_preference
            )
        
        # Execute query
        result = await self.db_session.execute(query)
        products = result.scalars().all()
        
        logger.info(f"Found {len(products)} potential alternatives")
        
        # Convert to Alternative objects and rank
        alternatives = []
        for product in products:
            # Check regional availability
            availability_match = True
            if region and product.availability:
                availability_match = (
                    region.lower() in [a.lower() for a in product.availability] or
                    "all_india" in [a.lower() for a in product.availability]
                )
            
            # Generate match reason
            match_reason = self._generate_match_reason(
                product,
                current_score,
                flagged_edcs,
                availability_match
            )
            
            alternative = Alternative(
                product_id=product.product_id,
                name=product.name,
                brand=product.brand,
                category=product.category,
                hormonal_health_score=product.hormonal_health_score,
                overall_score=product.overall_score,
                description=product.description,
                key_ingredients=product.key_ingredients or [],
                free_from=product.free_from or [],
                price_range=product.price_range,
                availability=product.availability or [],
                online_available=product.online_available,
                purchase_links=product.purchase_links or [],
                certifications=product.certifications or [],
                match_reason=match_reason
            )
            
            alternatives.append(alternative)
        
        # Rank alternatives
        ranked_alternatives = self._rank_alternatives(
            alternatives,
            region,
            price_preference
        )
        
        # Return top N alternatives
        return ranked_alternatives[:limit]
    
    def _generate_match_reason(
        self,
        product: AlternativeProduct,
        current_score: float,
        flagged_edcs: Optional[List[str]],
        availability_match: bool
    ) -> str:
        """Generate explanation for why this alternative was suggested"""
        reasons = []
        
        # Score improvement
        score_improvement = product.hormonal_health_score - current_score
        reasons.append(
            f"{score_improvement:.0f} points safer "
            f"(score: {product.hormonal_health_score:.0f}/100)"
        )
        
        # EDC-free
        if flagged_edcs and product.free_from:
            matching_free = [edc for edc in flagged_edcs if edc in product.free_from]
            if matching_free:
                reasons.append(f"Free from {', '.join(matching_free)}")
        
        # Certifications
        if product.certifications:
            cert_str = ", ".join(product.certifications[:2])
            reasons.append(f"Certified: {cert_str}")
        
        # Availability
        if availability_match:
            reasons.append("Available in your region")
        
        return " • ".join(reasons)
    
    def _rank_alternatives(
        self,
        alternatives: List[Alternative],
        region: Optional[str],
        price_preference: Optional[str]
    ) -> List[Alternative]:
        """
        Rank alternatives by multiple criteria
        
        Ranking priority:
        1. Hormonal Health Score (primary)
        2. Regional availability (if region specified)
        3. Price preference match (if specified)
        4. Overall score (tiebreaker)
        """
        def ranking_key(alt: Alternative) -> tuple:
            # Primary: Hormonal Health Score (descending)
            score_rank = -alt.hormonal_health_score
            
            # Secondary: Regional availability (ascending, 0 = available)
            if region:
                region_available = (
                    region.lower() in [a.lower() for a in alt.availability] or
                    "all_india" in [a.lower() for a in alt.availability]
                )
                availability_rank = 0 if region_available else 1
            else:
                availability_rank = 0
            
            # Tertiary: Price preference match (ascending, 0 = match)
            if price_preference:
                price_match = 0 if alt.price_range == price_preference else 1
            else:
                price_match = 0
            
            # Quaternary: Overall score (descending)
            overall_rank = -alt.overall_score
            
            return (score_rank, availability_rank, price_match, overall_rank)
        
        return sorted(alternatives, key=ranking_key)
    
    async def get_fallback_categories(
        self,
        product_category: str
    ) -> List[str]:
        """
        Get fallback product categories with lower EDC risk
        
        Args:
            product_category: Original product category
        
        Returns:
            List of safer alternative categories
        """
        # Category-specific fallback recommendations
        fallback_map = {
            "cosmetic": [
                "natural cosmetics",
                "organic personal care",
                "ayurvedic beauty products"
            ],
            "personal_care": [
                "natural personal care",
                "organic hygiene products",
                "traditional herbal products"
            ],
            "food": [
                "organic food",
                "fresh produce",
                "traditional whole foods"
            ],
            "household": [
                "natural cleaning products",
                "eco-friendly household items",
                "traditional cleaning methods"
            ]
        }
        
        return fallback_map.get(product_category.lower(), [])
    
    async def add_product(
        self,
        product_id: str,
        name: str,
        category: str,
        hormonal_health_score: float,
        overall_score: float,
        brand: Optional[str] = None,
        description: Optional[str] = None,
        key_ingredients: Optional[List[str]] = None,
        free_from: Optional[List[str]] = None,
        price_range: Optional[str] = None,
        availability: Optional[List[str]] = None,
        online_available: bool = True,
        purchase_links: Optional[List[str]] = None,
        certifications: Optional[List[str]] = None,
        tags: Optional[List[str]] = None
    ) -> AlternativeProduct:
        """
        Add a new alternative product to the database
        
        Args:
            product_id: Unique product identifier
            name: Product name
            category: Product category
            hormonal_health_score: Hormonal health score (0-100)
            overall_score: Overall safety score (0-100)
            brand: Brand name
            description: Product description
            key_ingredients: List of safe key ingredients
            free_from: List of EDCs this product is free from
            price_range: Price range (budget, mid-range, premium)
            availability: List of regions where available
            online_available: Whether available online
            purchase_links: List of purchase URLs
            certifications: List of certifications
            tags: List of tags for matching
        
        Returns:
            Created AlternativeProduct instance
        """
        product = AlternativeProduct(
            product_id=product_id,
            name=name,
            brand=brand,
            category=category,
            hormonal_health_score=hormonal_health_score,
            overall_score=overall_score,
            description=description,
            key_ingredients=key_ingredients,
            free_from=free_from,
            price_range=price_range,
            availability=availability,
            online_available=online_available,
            purchase_links=purchase_links,
            certifications=certifications,
            tags=tags
        )
        
        self.db_session.add(product)
        await self.db_session.commit()
        await self.db_session.refresh(product)
        
        logger.info(f"Added alternative product: {name} (ID: {product_id})")
        
        return product
    
    async def add_to_shopping_list(
        self,
        user_id: int,
        product_id: str,
        device_id: str,
        replaced_product_name: Optional[str] = None,
        replaced_product_category: Optional[str] = None,
        notes: Optional[str] = None,
        priority: int = 0
    ) -> ShoppingListItem:
        """
        Add a product to user's shopping list
        
        Args:
            user_id: User ID
            product_id: Alternative product ID to add
            device_id: Device ID for sync tracking
            replaced_product_name: Name of product being replaced
            replaced_product_category: Category of product being replaced
            notes: User notes
            priority: User-defined priority (higher = more important)
        
        Returns:
            Created ShoppingListItem instance
        """
        # Check if product exists
        query = select(AlternativeProduct).where(
            AlternativeProduct.product_id == product_id
        )
        result = await self.db_session.execute(query)
        product = result.scalar_one_or_none()
        
        if not product:
            raise ValueError(f"Product {product_id} not found")
        
        # Check if already in shopping list
        existing_query = select(ShoppingListItem).where(
            and_(
                ShoppingListItem.user_id == user_id,
                ShoppingListItem.product_id == product_id
            )
        )
        existing_result = await self.db_session.execute(existing_query)
        existing_item = existing_result.scalar_one_or_none()
        
        if existing_item:
            logger.info(f"Product {product_id} already in shopping list for user {user_id}")
            return existing_item
        
        # Create shopping list item
        item = ShoppingListItem(
            user_id=user_id,
            product_id=product_id,
            replaced_product_name=replaced_product_name,
            replaced_product_category=replaced_product_category,
            notes=notes,
            priority=priority,
            device_id=device_id,
            synced_to_cloud=False
        )
        
        self.db_session.add(item)
        await self.db_session.commit()
        await self.db_session.refresh(item)
        
        logger.info(f"Added product {product_id} to shopping list for user {user_id}")
        
        return item
    
    async def get_shopping_list(
        self,
        user_id: int,
        sort_by_priority: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get user's shopping list
        
        Args:
            user_id: User ID
            sort_by_priority: Whether to sort by priority (descending)
        
        Returns:
            List of shopping list items with product details
        """
        query = (
            select(ShoppingListItem, AlternativeProduct)
            .join(AlternativeProduct, ShoppingListItem.product_id == AlternativeProduct.product_id)
            .where(ShoppingListItem.user_id == user_id)
        )
        
        if sort_by_priority:
            query = query.order_by(desc(ShoppingListItem.priority), desc(ShoppingListItem.added_at))
        else:
            query = query.order_by(desc(ShoppingListItem.added_at))
        
        result = await self.db_session.execute(query)
        items = result.all()
        
        shopping_list = []
        for item, product in items:
            shopping_list.append({
                "id": item.id,
                "product_id": product.product_id,
                "name": product.name,
                "brand": product.brand,
                "category": product.category,
                "hormonal_health_score": product.hormonal_health_score,
                "overall_score": product.overall_score,
                "description": product.description,
                "price_range": product.price_range,
                "availability": product.availability,
                "online_available": product.online_available,
                "purchase_links": product.purchase_links,
                "replaced_product_name": item.replaced_product_name,
                "replaced_product_category": item.replaced_product_category,
                "notes": item.notes,
                "priority": item.priority,
                "added_at": item.added_at.isoformat()
            })
        
        logger.info(f"Retrieved {len(shopping_list)} items from shopping list for user {user_id}")
        
        return shopping_list
    
    async def remove_from_shopping_list(
        self,
        user_id: int,
        item_id: int
    ) -> bool:
        """
        Remove an item from shopping list
        
        Args:
            user_id: User ID
            item_id: Shopping list item ID
        
        Returns:
            True if removed, False if not found
        """
        query = select(ShoppingListItem).where(
            and_(
                ShoppingListItem.id == item_id,
                ShoppingListItem.user_id == user_id
            )
        )
        result = await self.db_session.execute(query)
        item = result.scalar_one_or_none()
        
        if not item:
            logger.warning(f"Shopping list item {item_id} not found for user {user_id}")
            return False
        
        await self.db_session.delete(item)
        await self.db_session.commit()
        
        logger.info(f"Removed item {item_id} from shopping list for user {user_id}")
        
        return True
    
    async def create_new_product_notifications(
        self,
        product_id: str
    ) -> int:
        """
        Create notifications for users who scanned high-risk products in the same category
        
        This is called when a new safer product is added to the database.
        
        Args:
            product_id: ID of the newly added product
        
        Returns:
            Number of notifications created
        """
        # Get the new product
        query = select(AlternativeProduct).where(
            AlternativeProduct.product_id == product_id
        )
        result = await self.db_session.execute(query)
        product = result.scalar_one_or_none()
        
        if not product:
            logger.warning(f"Product {product_id} not found")
            return 0
        
        # Find users who scanned high-risk products in this category
        # High-risk = hormonal_health_score < 60
        scans_query = (
            select(ProductScan.user_id, ProductScan.id, ProductScan.product_name)
            .where(
                and_(
                    ProductScan.product_category == product.category,
                    ProductScan.hormonal_health_score < 60.0
                )
            )
            .distinct(ProductScan.user_id)
        )
        
        scans_result = await self.db_session.execute(scans_query)
        scans = scans_result.all()
        
        notifications_created = 0
        
        for user_id, scan_id, scanned_product_name in scans:
            # Check if notification already exists
            existing_query = select(ProductNotification).where(
                and_(
                    ProductNotification.user_id == user_id,
                    ProductNotification.product_id == product_id
                )
            )
            existing_result = await self.db_session.execute(existing_query)
            existing_notification = existing_result.scalar_one_or_none()
            
            if existing_notification:
                continue
            
            # Create notification
            notification = ProductNotification(
                user_id=user_id,
                product_id=product_id,
                notification_type="new_alternative",
                title=f"New Safer Alternative Available: {product.name}",
                message=(
                    f"We found a safer alternative to {scanned_product_name or 'your previous scan'}. "
                    f"{product.name} has a hormonal health score of {product.hormonal_health_score:.0f}/100 "
                    f"and is free from harmful EDCs."
                ),
                related_scan_id=scan_id,
                related_category=product.category,
                sent=False,
                read=False
            )
            
            self.db_session.add(notification)
            notifications_created += 1
        
        await self.db_session.commit()
        
        logger.info(
            f"Created {notifications_created} notifications for new product {product.name}"
        )
        
        return notifications_created
    
    async def get_user_notifications(
        self,
        user_id: int,
        unread_only: bool = False,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get notifications for a user
        
        Args:
            user_id: User ID
            unread_only: Whether to return only unread notifications
            limit: Maximum number of notifications to return
        
        Returns:
            List of notifications with product details
        """
        query = (
            select(ProductNotification, AlternativeProduct)
            .join(AlternativeProduct, ProductNotification.product_id == AlternativeProduct.product_id)
            .where(ProductNotification.user_id == user_id)
        )
        
        if unread_only:
            query = query.where(ProductNotification.read == False)
        
        query = query.order_by(desc(ProductNotification.created_at)).limit(limit)
        
        result = await self.db_session.execute(query)
        items = result.all()
        
        notifications = []
        for notification, product in items:
            notifications.append({
                "id": notification.id,
                "notification_type": notification.notification_type,
                "title": notification.title,
                "message": notification.message,
                "product": {
                    "product_id": product.product_id,
                    "name": product.name,
                    "brand": product.brand,
                    "category": product.category,
                    "hormonal_health_score": product.hormonal_health_score,
                    "overall_score": product.overall_score,
                    "price_range": product.price_range,
                    "availability": product.availability,
                    "purchase_links": product.purchase_links
                },
                "related_category": notification.related_category,
                "sent": notification.sent,
                "read": notification.read,
                "created_at": notification.created_at.isoformat(),
                "sent_at": notification.sent_at.isoformat() if notification.sent_at else None,
                "read_at": notification.read_at.isoformat() if notification.read_at else None
            })
        
        logger.info(f"Retrieved {len(notifications)} notifications for user {user_id}")
        
        return notifications
    
    async def mark_notification_as_read(
        self,
        user_id: int,
        notification_id: int
    ) -> bool:
        """
        Mark a notification as read
        
        Args:
            user_id: User ID
            notification_id: Notification ID
        
        Returns:
            True if marked, False if not found
        """
        query = select(ProductNotification).where(
            and_(
                ProductNotification.id == notification_id,
                ProductNotification.user_id == user_id
            )
        )
        result = await self.db_session.execute(query)
        notification = result.scalar_one_or_none()
        
        if not notification:
            logger.warning(f"Notification {notification_id} not found for user {user_id}")
            return False
        
        notification.read = True
        notification.read_at = datetime.utcnow()
        
        await self.db_session.commit()
        
        logger.info(f"Marked notification {notification_id} as read for user {user_id}")
        
        return True
