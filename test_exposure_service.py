"""
Test script for exposure aggregation service

This script demonstrates the exposure aggregation functionality
without requiring full test infrastructure.
"""
import sys
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.logging import logger
from app.db.models import Base, User, ProductScan
from app.services.exposure_aggregation_service import (
    ExposureAggregationService,
    PeriodType
)


def setup_test_data(db_session):
    """Create test user and product scans"""
    
    # Create test user
    test_user = User(
        abha_id="12-3456-7890-1234",
        phone_number="+919876543210",
        name="Test User",
        age=28,
        state="Karnataka",
        district="Bengaluru",
        preferred_language="en"
    )
    db_session.add(test_user)
    db_session.commit()
    db_session.refresh(test_user)
    
    logger.info(f"Created test user with ID: {test_user.id}")
    
    # Create test product scans over the past 30 days
    now = datetime.utcnow()
    
    scans = [
        # High-risk cosmetic with BPA (15 days ago)
        ProductScan(
            user_id=test_user.id,
            product_name="Test Lipstick Brand A",
            product_category="cosmetic",
            ocr_text="Ingredients: Bisphenol A, Parabens, Fragrance",
            ocr_confidence=0.92,
            overall_score=25.0,
            hormonal_health_score=20.0,
            risk_level="critical",
            flagged_chemicals=[
                {
                    "name": "Bisphenol A (BPA)",
                    "cas_number": "80-05-7",
                    "edc_types": ["bpa"],
                    "risk_score": 85.0,
                    "confidence": 0.95
                },
                {
                    "name": "Methylparaben",
                    "cas_number": "99-76-3",
                    "edc_types": ["paraben"],
                    "risk_score": 45.0,
                    "confidence": 0.90
                }
            ],
            scanned_at=now - timedelta(days=15),
            device_id="test-device-1"
        ),
        
        # Medium-risk personal care with phthalates (10 days ago)
        ProductScan(
            user_id=test_user.id,
            product_name="Test Shampoo Brand B",
            product_category="personal_care",
            ocr_text="Ingredients: Dibutyl phthalate, Sodium lauryl sulfate",
            ocr_confidence=0.88,
            overall_score=45.0,
            hormonal_health_score=40.0,
            risk_level="high",
            flagged_chemicals=[
                {
                    "name": "Dibutyl phthalate (DBP)",
                    "cas_number": "84-74-2",
                    "edc_types": ["phthalate"],
                    "risk_score": 80.0,
                    "confidence": 0.92
                }
            ],
            scanned_at=now - timedelta(days=10),
            device_id="test-device-1"
        ),
        
        # Low-risk food product (5 days ago)
        ProductScan(
            user_id=test_user.id,
            product_name="Organic Snack Brand C",
            product_category="food",
            ocr_text="Ingredients: Organic wheat, Salt, Natural flavors",
            ocr_confidence=0.95,
            overall_score=85.0,
            hormonal_health_score=90.0,
            risk_level="low",
            flagged_chemicals=[],
            scanned_at=now - timedelta(days=5),
            device_id="test-device-1"
        ),
        
        # High-risk cosmetic with heavy metals (2 days ago)
        ProductScan(
            user_id=test_user.id,
            product_name="Test Kajal Brand D",
            product_category="cosmetic",
            ocr_text="Ingredients: Lead, Carbon black, Wax",
            ocr_confidence=0.85,
            overall_score=15.0,
            hormonal_health_score=10.0,
            risk_level="critical",
            flagged_chemicals=[
                {
                    "name": "Lead",
                    "cas_number": "7439-92-1",
                    "edc_types": ["heavy_metal"],
                    "risk_score": 95.0,
                    "confidence": 0.98
                }
            ],
            scanned_at=now - timedelta(days=2),
            device_id="test-device-1"
        )
    ]
    
    for scan in scans:
        db_session.add(scan)
    
    db_session.commit()
    logger.info(f"Created {len(scans)} test product scans")
    
    return test_user.id


def test_exposure_aggregation(db_session, user_id):
    """Test exposure aggregation service"""
    
    logger.info("\n" + "="*60)
    logger.info("Testing Exposure Aggregation Service")
    logger.info("="*60)
    
    # Create service
    service = ExposureAggregationService(db_session)
    
    # Test 1: Generate monthly exposure report
    logger.info("\n--- Test 1: Monthly Exposure Report ---")
    monthly_report = service.generate_exposure_report(
        user_id=user_id,
        period_type=PeriodType.MONTHLY
    )
    
    logger.info(f"Period: {monthly_report.period_start} to {monthly_report.period_end}")
    logger.info(f"Total Exposure: {monthly_report.total_exposure:.2f}")
    logger.info(f"EPA Limit: {monthly_report.epa_limit:.2f}")
    logger.info(f"Percent of Limit: {monthly_report.percent_of_limit:.1f}%")
    logger.info(f"Status: {monthly_report.status}")
    logger.info(f"Scan Count: {monthly_report.scan_count}")
    
    logger.info("\nExposure by EDC Type:")
    for edc_type, exposure in monthly_report.exposure_by_type.items():
        logger.info(f"  {edc_type}: {exposure:.2f}")
    
    logger.info("\nExposure by Category:")
    for category, exposure in monthly_report.exposure_by_category.items():
        logger.info(f"  {category}: {exposure:.2f}")
    
    logger.info("\nTop Sources:")
    for i, source in enumerate(monthly_report.top_sources[:3], 1):
        logger.info(
            f"  {i}. {source['product_name']} "
            f"({source['category']}, risk: {source['risk_level']}) - "
            f"Contribution: {source['exposure_contribution']:.2f}"
        )
    
    logger.info("\nRecommendations:")
    for i, rec in enumerate(monthly_report.recommendations[:5], 1):
        logger.info(f"  {i}. {rec}")
    
    # Test 2: Get current exposure (last 7 days)
    logger.info("\n--- Test 2: Weekly Exposure ---")
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    
    weekly_exposure = service.calculate_cumulative_exposure(
        user_id=user_id,
        period_start=week_ago,
        period_end=now
    )
    
    logger.info(f"Weekly Total Exposure: {weekly_exposure.total_exposure:.2f}")
    logger.info(f"Scans in Period: {weekly_exposure.scan_count}")
    
    epa_limit, percent, status = service.compare_to_epa_limits(
        weekly_exposure.total_exposure,
        PeriodType.WEEKLY
    )
    logger.info(f"Weekly EPA Limit: {epa_limit:.2f}")
    logger.info(f"Percent of Limit: {percent:.1f}%")
    logger.info(f"Status: {status.value}")
    
    # Test 3: Trend analysis
    logger.info("\n--- Test 3: Trend Analysis ---")
    logger.info(f"Number of trend periods: {len(monthly_report.trend_data)}")
    
    if monthly_report.trend_data:
        logger.info("\nTrend Data (last 3 periods):")
        for trend in monthly_report.trend_data[-3:]:
            logger.info(
                f"  {trend['period_start'][:10]} to {trend['period_end'][:10]}: "
                f"Exposure={trend['total_exposure']:.2f}, Scans={trend['scan_count']}"
            )
    
    logger.info("\n" + "="*60)
    logger.info("All tests completed successfully!")
    logger.info("="*60 + "\n")


def main():
    """Main test function"""
    try:
        # Setup database
        database_url = f"sqlite:///{settings.SQLITE_DB_PATH}"
        engine = create_engine(database_url)
        SessionLocal = sessionmaker(bind=engine)
        db_session = SessionLocal()
        
        logger.info("Starting exposure aggregation service test...")
        
        # Setup test data
        user_id = setup_test_data(db_session)
        
        # Run tests
        test_exposure_aggregation(db_session, user_id)
        
        # Cleanup
        db_session.close()
        
        logger.info("Test completed successfully!")
        return 0
    
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
