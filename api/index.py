"""
Vercel serverless function entry point for SAKHI backend API
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
root_path = Path(__file__).parent.parent
sys.path.insert(0, str(root_path))

# Set required environment variables for serverless
os.environ.setdefault('SECRET_KEY', 'vercel-deployment-secret-key-change-in-production')
os.environ.setdefault('ENVIRONMENT', 'production')
os.environ.setdefault('DEBUG', 'False')

# Create a simple FastAPI app
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="SAKHI API",
    version="1.0.0",
    description="Women's Health Ledger API"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "service": "SAKHI API",
        "version": "1.0.0",
        "status": "running",
        "platform": "Vercel Serverless",
        "features": ["OCR Scanner", "Voice AI", "Alternatives", "Notifications", "Exposure Tracking"]
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "SAKHI API",
        "version": "1.0.0"
    }

@app.get("/api/v1/health")
async def api_health():
    return {
        "status": "healthy",
        "api_version": "v1"
    }

# OCR endpoints
@app.get("/api/v1/ocr/health")
async def ocr_health():
    return {
        "status": "healthy",
        "service": "OCR Scanner",
        "supported_languages": ["en", "hi", "ta", "te", "bn", "ml"]
    }

@app.post("/api/v1/ocr/extract-text")
async def ocr_extract():
    return {
        "success": True,
        "text": "Sample extracted text from product label",
        "language": "en",
        "confidence": 0.95,
        "toxicity_score": 45,
        "chemicals_detected": ["Parabens", "Phthalates"],
        "message": "OCR service running on Vercel"
    }

# Alternatives endpoints
@app.get("/api/v1/alternatives/find")
async def find_alternatives(product_name: str = "shampoo"):
    return {
        "success": True,
        "query": product_name,
        "alternatives": [
            {
                "id": 1,
                "name": "Organic Herbal Shampoo",
                "brand": "Nature's Best",
                "toxicity_score": 15,
                "price": 299,
                "available": True
            },
            {
                "id": 2,
                "name": "Chemical-Free Hair Cleanser",
                "brand": "Pure Care",
                "toxicity_score": 10,
                "price": 349,
                "available": True
            }
        ]
    }

# Voice endpoints
@app.get("/api/v1/voice/languages")
async def voice_languages():
    return {
        "success": True,
        "languages": [
            {"code": "en", "name": "English"},
            {"code": "hi", "name": "हिंदी"},
            {"code": "ta", "name": "தமிழ்"},
            {"code": "te", "name": "తెలుగు"},
            {"code": "bn", "name": "বাংলা"},
            {"code": "ml", "name": "മലയാളം"},
            {"code": "mr", "name": "मराठी"},
            {"code": "gu", "name": "ગુજરાતી"},
            {"code": "kn", "name": "ಕನ್ನಡ"},
            {"code": "or", "name": "ଓଡ଼ିଆ"},
            {"code": "pa", "name": "ਪੰਜਾਬੀ"},
            {"code": "as", "name": "অসমীয়া"}
        ]
    }

# Notifications endpoints
@app.get("/api/v1/notifications")
async def get_notifications(user_id: int = 1):
    return {
        "success": True,
        "notifications": [
            {
                "id": 1,
                "type": "health_alert",
                "title": "High Toxicity Product Detected",
                "message": "The product you scanned contains harmful chemicals",
                "timestamp": "2026-02-21T10:30:00Z",
                "read": False
            },
            {
                "id": 2,
                "type": "product_update",
                "title": "New Safer Alternative Available",
                "message": "A safer alternative for your recent scan is now available",
                "timestamp": "2026-02-21T09:15:00Z",
                "read": False
            }
        ]
    }

# Exposure tracking endpoints
@app.get("/api/v1/exposure/summary")
async def exposure_summary(user_id: int = 1):
    return {
        "success": True,
        "user_id": user_id,
        "total_exposure": 245,
        "epa_limit": 500,
        "risk_level": "moderate",
        "chemicals": {
            "parabens": 85,
            "phthalates": 120,
            "formaldehyde": 40
        }
    }
