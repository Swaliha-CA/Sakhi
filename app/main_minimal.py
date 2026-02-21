"""Minimal FastAPI application for testing (without OCR dependencies)"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import logger
from app.api.v1.endpoints import voice, asha
from app.api.v1.endpoints import ocr_simple
from app.services.voice_service import bhashini_service
from app.db.sqlite_manager import sqlite_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    
    # Initialize Bhashini service
    if bhashini_service:
        await bhashini_service.connect()
    
    # Initialize SQLite database
    from app.db.sqlite_manager import get_sqlite_manager
    get_sqlite_manager()
    
    yield
    
    # Shutdown
    logger.info("Shutting down application")
    
    if bhashini_service:
        await bhashini_service.disconnect()
    
    if sqlite_manager:
        sqlite_manager.close()


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Women's Health Ledger - Voice AI & PPD Prediction Service",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ocr_simple.router, prefix=settings.API_PREFIX, tags=["OCR"])
app.include_router(voice.router, prefix=f"{settings.API_PREFIX}/voice", tags=["Voice AI"])
app.include_router(asha.router, prefix=settings.API_PREFIX, tags=["ASHA Dashboard"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "features": ["OCR Scanner", "Voice AI", "PPD Prediction", "Offline Sync"]
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main_minimal:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )
