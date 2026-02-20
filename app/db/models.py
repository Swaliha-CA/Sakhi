"""Database models for offline-first architecture"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    """User profile with ABHA ID integration"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    abha_id = Column(String(14), unique=True, index=True, nullable=False)  # ABHA ID format: XX-XXXX-XXXX-XXXX
    phone_number = Column(String(15), unique=True, index=True)
    name = Column(String(255))
    age = Column(Integer)
    state = Column(String(100))
    district = Column(String(100))
    preferred_language = Column(String(10), default="en")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_synced_at = Column(DateTime, nullable=True)
    
    # Device tracking for migration
    current_device_id = Column(String(255), nullable=True)
    
    # Relationships
    health_records = relationship("HealthRecord", back_populates="user", cascade="all, delete-orphan")
    screenings = relationship("Screening", back_populates="user", cascade="all, delete-orphan")
    product_scans = relationship("ProductScan", back_populates="user", cascade="all, delete-orphan")


class HealthRecord(Base):
    """Immutable append-only health event log"""
    __tablename__ = "health_records"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)  # lab_result, symptom, medication, etc.
    event_data = Column(JSON, nullable=False)  # Flexible JSON storage
    
    # Immutable timestamps
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    device_id = Column(String(255), nullable=False)
    
    # Sync metadata
    synced_to_cloud = Column(Boolean, default=False)
    sync_version = Column(Integer, default=1)
    
    # Relationships
    user = relationship("User", back_populates="health_records")


class Screening(Base):
    """Mental health screening responses (EPDS, PHQ-9)"""
    __tablename__ = "screenings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    screening_type = Column(String(20), nullable=False)  # EPDS, PHQ-9
    responses = Column(JSON, nullable=False)  # Question-answer pairs
    total_score = Column(Integer, nullable=False)
    risk_level = Column(String(20))  # low, moderate, high, critical
    
    # Timestamps
    conducted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    device_id = Column(String(255), nullable=False)
    
    # Sync metadata
    synced_to_cloud = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", back_populates="screenings")


class ProductScan(Base):
    """Product toxicity scan results"""
    __tablename__ = "product_scans"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    product_name = Column(String(255))
    product_category = Column(String(50))
    
    # OCR results
    ocr_text = Column(Text)
    ocr_confidence = Column(Float)
    
    # Toxicity scores
    overall_score = Column(Float)
    hormonal_health_score = Column(Float)
    risk_level = Column(String(20))
    flagged_chemicals = Column(JSON)
    
    # Timestamps
    scanned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    device_id = Column(String(255), nullable=False)
    
    # Sync metadata
    synced_to_cloud = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", back_populates="product_scans")


class SyncLog(Base):
    """Track synchronization events"""
    __tablename__ = "sync_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(255), nullable=False, index=True)
    sync_type = Column(String(20), nullable=False)  # upload, download
    status = Column(String(20), nullable=False)  # success, failed, partial
    records_synced = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class SutikaCheckIn(Base):
    """Daily postpartum check-in records"""
    __tablename__ = "sutika_checkins"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    day_number = Column(Integer, nullable=False)  # 1-45
    recovery_phase = Column(String(20), nullable=False)  # phase_1, phase_2, phase_3
    
    # Health metrics
    energy_level = Column(Integer, nullable=False)  # 1-10
    pain_level = Column(Integer, nullable=False)  # 1-10
    mood_score = Column(Integer, nullable=False)  # 1-10
    breastfeeding_issues = Column(Boolean, default=False)
    bleeding_status = Column(String(20), nullable=False)  # normal, heavy, minimal
    notes = Column(Text, nullable=True)
    
    # Timestamps
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    device_id = Column(String(255), nullable=False)
    
    # Sync metadata
    synced_to_cloud = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User")


class HeritageRecipeDB(Base):
    """Heritage recipes with voice recordings"""
    __tablename__ = "heritage_recipes"
    
    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    region = Column(String(20), nullable=False)  # north, south, east, west, central
    
    # Recipe details
    ingredients = Column(JSON, nullable=False)  # List of ingredients
    preparation = Column(Text, nullable=False)
    nutritional_benefits = Column(JSON, nullable=False)  # List of benefits
    micronutrients = Column(JSON, nullable=False)  # Dict of nutrient levels
    
    # Voice recording
    voice_recording_url = Column(String(500), nullable=True)
    contributed_by = Column(String(255), nullable=True)
    
    # Metadata
    season = Column(String(20), nullable=True)  # summer, monsoon, winter, spring
    tags = Column(JSON, nullable=True)  # List of tags
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Sync metadata
    synced_to_cloud = Column(Boolean, default=False)


class AlternativeProduct(Base):
    """Toxin-free product alternatives database"""
    __tablename__ = "alternative_products"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    brand = Column(String(255), nullable=True)
    category = Column(String(50), nullable=False, index=True)  # cosmetic, food, household, personal_care
    
    # Scoring
    hormonal_health_score = Column(Float, nullable=False, index=True)  # 0-100, higher is safer
    overall_score = Column(Float, nullable=False)  # 0-100, higher is safer
    
    # Product details
    description = Column(Text, nullable=True)
    key_ingredients = Column(JSON, nullable=True)  # List of safe key ingredients
    free_from = Column(JSON, nullable=True)  # List of EDCs this product is free from
    
    # Availability
    price_range = Column(String(20), nullable=True)  # budget, mid-range, premium
    availability = Column(JSON, nullable=True)  # List of regions/stores where available
    online_available = Column(Boolean, default=True)
    purchase_links = Column(JSON, nullable=True)  # List of purchase URLs
    
    # Metadata
    certifications = Column(JSON, nullable=True)  # List of certifications (organic, cruelty-free, etc.)
    tags = Column(JSON, nullable=True)  # List of tags for matching
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Sync metadata
    synced_to_cloud = Column(Boolean, default=False)


class ShoppingListItem(Base):
    """User's shopping list of preferred alternatives"""
    __tablename__ = "shopping_list_items"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    product_id = Column(String(100), ForeignKey("alternative_products.product_id"), nullable=False)
    
    # Original product that was replaced
    replaced_product_name = Column(String(255), nullable=True)
    replaced_product_category = Column(String(50), nullable=True)
    
    # User notes
    notes = Column(Text, nullable=True)
    priority = Column(Integer, default=0)  # User-defined priority
    
    # Timestamps
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    device_id = Column(String(255), nullable=False)
    
    # Sync metadata
    synced_to_cloud = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User")
    product = relationship("AlternativeProduct")


class ProductNotification(Base):
    """Notifications for new safer products"""
    __tablename__ = "product_notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    product_id = Column(String(100), ForeignKey("alternative_products.product_id"), nullable=False)
    
    # Notification details
    notification_type = Column(String(50), nullable=False)  # new_alternative, price_drop, back_in_stock
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    
    # Related to previous scan
    related_scan_id = Column(Integer, ForeignKey("product_scans.id"), nullable=True)
    related_category = Column(String(50), nullable=False)
    
    # Status
    sent = Column(Boolean, default=False)
    read = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    sent_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User")
    product = relationship("AlternativeProduct")
    related_scan = relationship("ProductScan")


class EDCExposureLog(Base):
    """Cumulative EDC exposure tracking"""
    __tablename__ = "edc_exposure_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Time period
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False, index=True)
    period_type = Column(String(20), nullable=False)  # daily, weekly, monthly
    
    # Aggregated exposure data
    total_exposure_score = Column(Float, nullable=False)  # Weighted cumulative score
    exposure_by_type = Column(JSON, nullable=False)  # Dict of EDC type -> exposure score
    exposure_by_category = Column(JSON, nullable=False)  # Dict of product category -> exposure score
    
    # EPA safe limit comparison
    epa_limit = Column(Float, nullable=False)  # Safe limit for the period
    percent_of_limit = Column(Float, nullable=False)  # Percentage of EPA limit
    status = Column(String(20), nullable=False)  # safe, approaching_limit, exceeds_limit
    
    # Top sources
    top_sources = Column(JSON, nullable=False)  # List of product scan IDs contributing most
    
    # Metadata
    scan_count = Column(Integer, nullable=False)  # Number of scans in this period
    generated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Sync metadata
    synced_to_cloud = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User")


class ExposureAlert(Base):
    """Alerts for EDC exposure threshold violations"""
    __tablename__ = "exposure_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    exposure_log_id = Column(Integer, ForeignKey("edc_exposure_logs.id"), nullable=False)
    
    # Alert details
    alert_type = Column(String(50), nullable=False)  # weekly_limit_exceeded, trend_increasing, high_edc_type
    severity = Column(String(20), nullable=False)  # warning, critical
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    
    # Reduction strategies
    reduction_strategies = Column(JSON, nullable=False)  # List of personalized recommendations
    primary_edc_sources = Column(JSON, nullable=False)  # List of main EDC sources to address
    
    # Status
    sent = Column(Boolean, default=False)
    acknowledged = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    sent_at = Column(DateTime, nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    
    # Sync metadata
    synced_to_cloud = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User")
    exposure_log = relationship("EDCExposureLog")



class BuddyLinkRequest(Base):
    """Pending buddy link requests requiring consent from both parties"""
    __tablename__ = "buddy_link_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Requester and recipient
    requester_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Proposed roles
    requester_role = Column(String(20), nullable=False)  # elder or digital_helper
    recipient_role = Column(String(20), nullable=False)  # elder or digital_helper
    
    # Proposed permissions (stored as comma-separated string)
    proposed_permissions = Column(Text, nullable=False)
    
    # Request metadata
    message = Column(Text, nullable=True)
    status = Column(String(20), default="pending", nullable=False)  # pending, active, rejected, revoked
    
    # Timestamps
    requested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    responded_at = Column(DateTime, nullable=True)
    
    # Response
    response_message = Column(Text, nullable=True)
    
    # Relationships
    requester = relationship("User", foreign_keys=[requester_id])
    recipient = relationship("User", foreign_keys=[recipient_id])


class BuddyLink(Base):
    """Active buddy profile links with defined roles and permissions"""
    __tablename__ = "buddy_links"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Linked users
    elder_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    helper_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Permissions (stored as comma-separated string)
    permissions = Column(Text, nullable=False)
    
    # Link metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    revoked_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    revocation_reason = Column(Text, nullable=True)
    
    # Relationships
    elder = relationship("User", foreign_keys=[elder_id])
    helper = relationship("User", foreign_keys=[helper_id])
    revoker = relationship("User", foreign_keys=[revoked_by])
