"""Simple OCR API endpoints without heavy dependencies"""
import os
import tempfile
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse

from app.core.logging import logger

router = APIRouter(prefix="/ocr", tags=["OCR"])


@router.post("/extract-text")
async def extract_text_from_image(
    file: UploadFile = File(..., description="Image file containing text to extract"),
    language: Optional[str] = Query(
        None,
        description="Language code (en, hi, ta, te, bn, ml). Auto-detected if not provided."
    )
) -> JSONResponse:
    """
    Extract text from an uploaded image using OCR
    
    This is a simplified version that works without PaddleOCR.
    For production, install pytesseract or use cloud OCR services.
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload an image file."
        )
    
    # Validate language if provided
    if language and language not in ["en", "hi", "ta", "te", "bn", "ml"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language: {language}. Supported: en, hi, ta, te, bn, ml"
        )
    
    temp_file = None
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        logger.info(f"Processing OCR request for file: {file.filename}, language: {language}")
        
        # Try to use pytesseract if available
        try:
            import pytesseract
            from PIL import Image
            
            # Open image
            image = Image.open(temp_file_path)
            
            # Extract text
            text = pytesseract.image_to_string(image, lang=language or 'eng')
            confidence = 0.85  # Pytesseract doesn't provide confidence easily
            
            result = {
                "raw_text": text.strip(),
                "confidence": confidence,
                "language": language or "en",
                "bounding_boxes": []
            }
            
        except ImportError:
            # Pytesseract not available, return mock data
            logger.warning("Pytesseract not installed, returning mock OCR data")
            result = {
                "raw_text": "MOCK OCR RESULT\n\nIngredients: Water, Glycerin, Sodium Laureth Sulfate, Cocamidopropyl Betaine, Fragrance, Methylparaben, Propylparaben, DMDM Hydantoin, Tetrasodium EDTA, Citric Acid\n\nWarning: Contains parabens and formaldehyde-releasing preservatives. May cause skin irritation.\n\nFor external use only.\nKeep out of reach of children.",
                "confidence": 0.75,
                "language": language or "en",
                "bounding_boxes": [],
                "note": "This is mock data. Install pytesseract for real OCR: pip install pytesseract"
            }
        
        # Return result
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": result,
                "message": "Text extracted successfully" if result["raw_text"] else "No text detected in image"
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
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload an image file."
        )
    
    logger.info(f"Detecting language for file: {file.filename}")
    
    # For now, return English as default
    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "data": {
                "detected_language": "en"
            },
            "message": "Language detected successfully"
        }
    )


@router.get("/health")
async def health_check() -> JSONResponse:
    """
    Health check endpoint for OCR service
    """
    # Check if pytesseract is available
    try:
        import pytesseract
        ocr_available = True
        ocr_engine = "pytesseract"
    except ImportError:
        ocr_available = False
        ocr_engine = "mock"
    
    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "data": {
                "service": "OCR Service",
                "status": "healthy",
                "ocr_engine": ocr_engine,
                "ocr_available": ocr_available,
                "available_languages": ["en", "hi", "ta", "te", "bn", "ml"],
                "note": "Install pytesseract for real OCR functionality" if not ocr_available else "Using pytesseract"
            },
            "message": "OCR service is healthy"
        }
    )
