"""
Vercel serverless function entry point for SAKHI backend API
Simplified version without lifespan events for serverless compatibility
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Create a simple FastAPI app without lifespan
app = FastAPI(
    title="SAKHI - Women's Health Platform",
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
    """Root endpoint"""
    return {
        "service": "SAKHI - Women's Health Platform",
        "version": "1.0.0",
        "status": "running",
        "features": [
            "OCR Scanner",
            "Voice AI", 
            "PPD Prediction",
            "Safer Alternatives",
            "Exposure Tracking",
            "Notifications"
        ],
        "deployment": "Vercel Serverless"
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "SAKHI",
        "version": "1.0.0",
        "platform": "Vercel"
    }

@app.get("/api/v1/ocr/health")
async def ocr_health():
    """OCR health check"""
    return {
        "status": "healthy",
        "service": "OCR Scanner",
        "supported_languages": ["en", "hi", "ta", "te", "bn", "ml"]
    }

@app.post("/api/v1/ocr/extract-text")
async def ocr_extract():
    """OCR text extraction (mock for demo)"""
    return {
        "success": True,
        "text": "Sample product label text",
        "language": "en",
        "toxicity_score": 45,
        "chemicals_detected": ["Parabens", "Phthalates"],
        "message": "This is a demo response. Full OCR requires additional setup."
    }

@app.get("/api/v1/alternatives/find")
async def find_alternatives():
    """Find safer product alternatives"""
    return {
        "success": True,
        "alternatives": [
            {
                "id": 1,
                "name": "Organic Shampoo",
                "brand": "Natural Care",
                "toxicity_score": 15,
                "price": 299,
                "available": True
            },
            {
                "id": 2,
                "name": "Herbal Soap",
                "brand": "Ayur Plus",
                "toxicity_score": 10,
                "price": 150,
                "available": True
            }
        ],
        "count": 2
    }

@app.get("/api/v1/voice/languages")
async def voice_languages():
    """Get supported voice languages"""
    return {
        "languages": [
            {"code": "en", "name": "English"},
            {"code": "hi", "name": "Hindi"},
            {"code": "ta", "name": "Tamil"},
            {"code": "te", "name": "Telugu"},
            {"code": "bn", "name": "Bengali"},
            {"code": "ml", "name": "Malayalam"},
            {"code": "mr", "name": "Marathi"},
            {"code": "gu", "name": "Gujarati"},
            {"code": "kn", "name": "Kannada"},
            {"code": "pa", "name": "Punjabi"},
            {"code": "or", "name": "Odia"},
            {"code": "as", "name": "Assamese"}
        ],
        "total": 12
    }

@app.get("/api/v1/notifications")
async def get_notifications():
    """Get user notifications"""
    return {
        "notifications": [
            {
                "id": 1,
                "type": "health_alert",
                "title": "High Risk Product Detected",
                "message": "The scanned product contains harmful chemicals",
                "timestamp": "2026-02-21T10:30:00Z",
                "read": False
            },
            {
                "id": 2,
                "type": "alternative_available",
                "title": "Safer Alternative Found",
                "message": "We found 5 safer alternatives for your product",
                "timestamp": "2026-02-21T09:15:00Z",
                "read": False
            }
        ],
        "count": 2,
        "unread": 2
    }

# Export for Vercel
handler = app
