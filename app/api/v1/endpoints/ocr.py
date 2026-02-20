"""OCR API endpoints"""
import os
import tempfile
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse

from app.services.ocr_service import ocr_service
from app.core.logging import logger


router = APIRouter(prefix="/ocr", tags=["OCR"])


@router.post("/extract-text")
async def extract_text_from_image(
    file: UploadFile = File(..., description="Image file containing text to extract"),
    language: Optional[str] = Query(
        None,
        description="Language code (en, hi, ta, te, bn). Auto-detected if not provided."
    )
) -> JSONResponse:
    """
    Extract text from an uploaded image using OCR
    
    Supports multilingual Indian labels (Hindi, Tamil, Telugu, Bengali, English)
    with image preprocessing and confidence scoring.
    
    Returns:
        OCRResult with extracted text, confidence score, and bounding boxes
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload an image file."
        )
    
    # Validate language if provided
    if language and language not in ["en", "hi", "ta", "te", "bn"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language: {language}. Supported: en, hi, ta, te, bn"
        )
    
    # Save uploaded file temporarily
    temp_file = None
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        logger.info(f"Processing OCR request for file: {file.filename}, language: {language}")
        
        # Extract text using OCR service
        result = await ocr_service.extract_text(temp_file_path, language)
        
        # Return result
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": result.to_dict(),
                "message": "Text extracted successfully" if result.raw_text else "No text detected in image"
            }
        )
        
    except Exception as e:
        logger.error(f"OCR extraction failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"OCR extraction failed: {str(e)}"
        )
    
    finally:
        # Clean up temporary file
        if temp_file and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.warning(f"Failed to delete temporary file: {e}")


@router.post("/detect-language")
async def detect_language_from_image(
    file: UploadFile = File(..., description="Image file to detect language from")
) -> JSONResponse:
    """
    Detect language from an uploaded image
    
    Returns:
        Detected language code
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload an image file."
        )
    
    # Save uploaded file temporarily
    temp_file = None
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        logger.info(f"Detecting language for file: {file.filename}")
        
        # Detect language
        detected_language = await ocr_service.detect_language(temp_file_path)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "detected_language": detected_language
                },
                "message": "Language detected successfully"
            }
        )
        
    except Exception as e:
        logger.error(f"Language detection failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Language detection failed: {str(e)}"
        )
    
    finally:
        # Clean up temporary file
        if temp_file and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.warning(f"Failed to delete temporary file: {e}")


@router.get("/health")
async def health_check() -> JSONResponse:
    """
    Health check endpoint for OCR service
    
    Returns:
        Service status and available languages
    """
    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "data": {
                "service": "OCR Service",
                "status": "healthy",
                "available_languages": list(ocr_service.ocr_engines.keys()),
                "redis_connected": ocr_service.redis_client is not None
            },
            "message": "OCR service is healthy"
        }
    )
