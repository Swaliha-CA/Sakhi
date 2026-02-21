"""Unit tests for ASHA Dashboard Service"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.models import Base, User, HealthRecord, Screening, ProductScan
from app.services.asha_service import (
    get_asha_service,
    ASHAService,
    Intervention,
    InterventionType,
    AlertType,
    AlertPriority
)


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    yield session
    
    session.close()


@pytest.fixture
def sample_users(db_session):
    """Create sample users for testing"""
    users = [
        User(
            id=1,
            abha_id="12-3456-7890-1234",
            phone_number="+919876543210",
            name="Test User 1",
            age=28,
            state="Karnataka",
            district="Bengaluru",
            preferred_language="en"
        ),
        User(
            id=2,
            abha_id="12-3456-7890-5678",
            phone_number="+919876543211",
            name="Test User 2",
            age=32,
            state="Karnataka",
            district="Bengaluru",
            preferred_language="kn"
        ),
        User(
            id=3,
            abha_id="12-3456-7890-9012",
            phone_number="+919876543212",
            name="Test User 3",
            age=25,
            state="Karnataka",
            district="Mysuru",
            preferred_language="kn"
        )
    ]
    
    for user in users:
        db_session.add(user)
    
    db_session.commit()
    
    return users


@pytest.fixture
def sample_screenings(db_session, sample_users):
    """Create sample screening data"""
    screenings = [
        # High-risk user
        Screening(
            user_id=1,
            screening_type="epds",
            responses={"q1": 3, "q2": 3, "q3": 2},
            total_score=18,
            risk_level="high",
            conducted_at=datetime.utcnow() - timedelta(days=2),
            device_id="device_1"
        ),
        # Moderate-risk user
        Screening(
            user_id=2,
            screening_type="phq9",
            responses={"q1": 2, "q2": 2, "q3": 1},
            total_score=12,
            risk_level="moderate",
            conducted_at=datetime.utcnow() - timedelta(days=5),
            device_id="device_2"
        ),
        # Low-risk user
        Screening(
            user_id=3,
            screening_type="epds",
            responses={"q1": 0, "q2": 1, "q3": 0},
            total_score=5,
            risk_level="low",
            conducted_at=datetime.utcnow() - timedelta(days=1),
    