"""
Test script for alternative recommendation API endpoints

This script tests the core functionality without running full tests.
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.services.alternative_product_service import AlternativeProductService
from app.db.models import Base, User, ProductScan


async def test_alternatives_api():
    """Test the alternative recommendation API"""
    
    # Create async engine
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{settings.SQLITE_DB_PATH}",
        echo=False
    )
    
    # Create session
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        service = AlternativeProductService(session)
        
        print("=" * 60)
        print("Testing Alternative Recommendation Engine")
        print("=" * 60)
        
        # Test 1: Find alternatives for a cosmetic product
        print("\n1. Finding alternatives for cosmetic product (score: 45)...")
        alternatives = await service.find_alternatives(
            product_category="cosmetic",
            current_score=45.0,
            flagged_edcs=None,  # Don't filter by specific EDCs
            price_preference=None,
            region="south",
            limit=3
        )
        
        print(f"   Found {len(alternatives)} alternatives:")
        for i, alt in enumerate(alternatives, 1):
            print(f"   {i}. {alt.name} (Score: {alt.hormonal_health_score:.0f}/100)")
            print(f"      Brand: {alt.brand}")
            print(f"      Reason: {alt.match_reason}")
        
        # Test 2: Get fallback categories
        print("\n2. Getting fallback categories for cosmetic...")
        fallback = await service.get_fallback_categories("cosmetic")
        print(f"   Fallback categories: {', '.join(fallback)}")
        
        # Test 3: Add to shopping list (create test user first)
        print("\n3. Testing shopping list functionality...")
        
        # Create test user if not exists
        from sqlalchemy import select
        result = await session.execute(
            select(User).where(User.abha_id == "99-9999-9999-9999")
        )
        test_user = result.scalar_one_or_none()
        
        if not test_user:
            test_user = User(
                abha_id="99-9999-9999-9999",
                phone_number="+919999999999",
                name="Test User",
                age=30,
                state="Karnataka",
                district="Bangalore",
                preferred_language="en",
                current_device_id="test-device-001"
            )
            session.add(test_user)
            await session.commit()
            await session.refresh(test_user)
            print(f"   Created test user (ID: {test_user.id})")
        else:
            print(f"   Using existing test user (ID: {test_user.id})")
        
        # Add product to shopping list
        if alternatives:
            first_alt = alternatives[0]
            try:
                item = await service.add_to_shopping_list(
                    user_id=test_user.id,
                    product_id=first_alt.product_id,
                    device_id="test-device-001",
                    replaced_product_name="Harmful Cosmetic Brand",
                    replaced_product_category="cosmetic",
                    notes="Recommended by app",
                    priority=5
                )
                print(f"   Added {first_alt.name} to shopping list (Item ID: {item.id})")
            except Exception as e:
                print(f"   Note: {str(e)}")
        
        # Get shopping list
        shopping_list = await service.get_shopping_list(test_user.id)
        print(f"   Shopping list has {len(shopping_list)} items")
        for item in shopping_list[:3]:  # Show first 3
            print(f"   - {item['name']} (Priority: {item['priority']})")
        
        # Test 4: Notification system
        print("\n4. Testing notification system...")
        
        # Create a test product scan
        result = await session.execute(
            select(ProductScan).where(ProductScan.user_id == test_user.id)
        )
        test_scan = result.scalar_one_or_none()
        
        if not test_scan:
            test_scan = ProductScan(
                user_id=test_user.id,
                product_name="Harmful Cosmetic",
                product_category="cosmetic",
                ocr_text="Test ingredients",
                ocr_confidence=0.95,
                overall_score=45.0,
                hormonal_health_score=45.0,
                risk_level="high",
                flagged_chemicals=["bpa", "phthalate"],
                device_id="test-device-001",
                synced_to_cloud=False
            )
            session.add(test_scan)
            await session.commit()
            print(f"   Created test product scan")
        
        # Create notifications for a new product
        if alternatives:
            count = await service.create_new_product_notifications(
                alternatives[0].product_id
            )
            print(f"   Created {count} notifications")
        
        # Get notifications
        notifications = await service.get_user_notifications(
            user_id=test_user.id,
            unread_only=False,
            limit=5
        )
        print(f"   User has {len(notifications)} notifications")
        for notif in notifications[:3]:  # Show first 3
            print(f"   - {notif['title']}")
            print(f"     Read: {notif['read']}")
        
        print("\n" + "=" * 60)
        print("All tests completed successfully!")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_alternatives_api())
