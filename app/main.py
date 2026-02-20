"""Main FastAPI application"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import logger
from app.api.v1.endpoints import ocr, voice, alternatives, buddy, notifications, population_health
from app.services.ocr_service import ocr_service
from app.services.voice_service import bhashini_service
from app.db.sqlite_manager import sqlite_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    
    # Connect to Redis
    await ocr_service.connect_redis()
    
    # Initialize Bhashini service
    if bhashini_service:
        await bhashini_service.connect()
    
    # Initialize SQLite database
    from app.db.sqlite_manager import get_sqlite_manager
    get_sqlite_manager()
    
    yield
    
    # Shutdown
    logger.info("Shutting down application")
    await ocr_service.disconnect_redis()
    
    if bhashini_service:
        await bhashini_service.disconnect()
    
    if sqlite_manager:
        sqlite_manager.close()


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Women's Health Ledger - OCR Service for Product Label Scanning",
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
app.include_router(ocr.router, prefix=settings.API_PREFIX, tags=["OCR"])
app.include_router(voice.router, prefix=f"{settings.API_PREFIX}/voice", tags=["Voice AI"])
app.include_router(alternatives.router, prefix=settings.API_PREFIX, tags=["Alternatives"])
app.include_router(buddy.router, prefix=settings.API_PREFIX, tags=["Buddy System"])
app.include_router(notifications.router, prefix=settings.API_PREFIX, tags=["Notifications"])
app.include_router(population_health.router, prefix=f"{settings.API_PREFIX}/population-health", tags=["Population Health"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
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
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )
