"""OCR Service with PaddleOCR integration"""
import hashlib
import json
import time
from typing import Optional, List, Dict, Any
from pathlib import Path

import cv2
import numpy as np
from paddleocr import PaddleOCR
from PIL import Image, ImageEnhance
import redis.asyncio as redis

from app.core.config import settings
from app.core.logging import logger


class BoundingBox:
    """Represents a text bounding box from OCR"""
    
    def __init__(self, text: str, coordinates: List[List[int]], confidence: float):
        self.text = text
        self.coordinates = coordinates
        self.confidence = confidence
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        # Calculate bounding box dimensions
        x_coords = [point[0] for point in self.coordinates]
        y_coords = [point[1] for point in self.coordinates]
        
        return {
            "text": self.text,
            "coordinates": {
                "x": min(x_coords),
                "y": min(y_coords),
                "width": max(x_coords) - min(x_coords),
                "height": max(y_coords) - min(y_coords)
            },
            "confidence": self.confidence
        }


class OCRResult:
    """OCR extraction result"""
    
    def __init__(
        self,
        raw_text: str,
        confidence: float,
        detected_language: str,
        bounding_boxes: List[BoundingBox],
        processing_time_ms: int,
        low_confidence_warning: bool = False
    ):
        self.raw_text = raw_text
        self.confidence = confidence
        self.detected_language = detected_language
        self.bounding_boxes = bounding_boxes
        self.processing_time_ms = processing_time_ms
        self.low_confidence_warning = low_confidence_warning
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "raw_text": self.raw_text,
            "confidence": self.confidence,
            "detected_language": self.detected_language,
            "bounding_boxes": [bbox.to_dict() for bbox in self.bounding_boxes],
            "processing_time_ms": self.processing_time_ms,
            "low_confidence_warning": self.low_confidence_warning
        }


class OCRService:
    """OCR Service using PaddleOCR with multilingual support"""
    
    def __init__(self):
        """Initialize OCR service with PaddleOCR engines"""
        self.redis_client: Optional[redis.Redis] = None
        self.ocr_engines: Dict[str, PaddleOCR] = {}
        # Don't initialize engines in __init__ to avoid blocking
        # They will be initialized on first use
        self._engines_initialized = False
    
    def _initialize_ocr_engines(self):
        """Initialize PaddleOCR engines for supported languages"""
        if self._engines_initialized:
            return
        
        logger.info("Initializing PaddleOCR engines...")
        
        # Language mapping for PaddleOCR
        lang_map = {
            "en": "en",
            "hi": "hi",
            "ta": "ta",
            "te": "te"
        }
        
        for lang_code in settings.OCR_SUPPORTED_LANGUAGES:
            try:
                paddle_lang = lang_map.get(lang_code, "en")
                # Initialize with default parameters (CPU-only by default)
                self.ocr_engines[lang_code] = PaddleOCR(lang=paddle_lang)
                logger.info(f"Initialized OCR engine for language: {lang_code}")
            except Exception as e:
                logger.error(f"Failed to initialize OCR engine for {lang_code}: {e}")
        
        self._engines_initialized = True
        logger.info(f"OCR engines initialized for {len(self.ocr_engines)} languages")
    
    async def connect_redis(self):
        """Connect to Redis for caching"""
        try:
            self.redis_client = await redis.from_url(
                f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
                password=settings.REDIS_PASSWORD,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("Connected to Redis for OCR caching")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Caching disabled.")
            self.redis_client = None
    
    async def disconnect_redis(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Disconnected from Redis")
    
    def _preprocess_image(self, image_path: str) -> np.ndarray:
        """
        Preprocess image for better OCR results
        - Enhance contrast and brightness
        - Convert to grayscale if needed
        """
        try:
            # Read image
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError(f"Failed to read image: {image_path}")
            
            # Convert to PIL for enhancement
            pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(pil_img)
            pil_img = enhancer.enhance(1.5)
            
            # Enhance brightness
            enhancer = ImageEnhance.Brightness(pil_img)
            pil_img = enhancer.enhance(1.2)
            
            # Enhance sharpness
            enhancer = ImageEnhance.Sharpness(pil_img)
            pil_img = enhancer.enhance(1.3)
            
            # Convert back to OpenCV format
            enhanced_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            
            logger.debug(f"Preprocessed image: {image_path}")
            return enhanced_img
            
        except Exception as e:
            logger.error(f"Image preprocessing failed: {e}")
            # Return original image if preprocessing fails
            return cv2.imread(image_path)
    
    def _detect_language(self, image_path: str) -> str:
        """
        Detect language from image
        For now, returns 'en' as default. Can be enhanced with language detection.
        """
        # TODO: Implement actual language detection
        # For now, try English first as it's most common
        return "en"
    
    def _calculate_cache_key(self, image_path: str, language: Optional[str]) -> str:
        """Calculate cache key for OCR result"""
        # Use file content hash for cache key
        with open(image_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
        
        lang = language or "auto"
        return f"ocr:{file_hash}:{lang}"
    
    async def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached OCR result from Redis"""
        if not self.redis_client:
            return None
        
        try:
            cached = await self.redis_client.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for key: {cache_key}")
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Failed to get cached result: {e}")
        
        return None
    
    async def _cache_result(self, cache_key: str, result: Dict[str, Any]):
        """Cache OCR result in Redis"""
        if not self.redis_client:
            return
        
        try:
            await self.redis_client.setex(
                cache_key,
                settings.OCR_CACHE_TTL,
                json.dumps(result)
            )
            logger.debug(f"Cached result for key: {cache_key}")
        except Exception as e:
            logger.warning(f"Failed to cache result: {e}")
    
    async def extract_text(
        self,
        image_path: str,
        language: Optional[str] = None
    ) -> OCRResult:
        """
        Extract text from image using PaddleOCR
        
        Args:
            image_path: Path to the image file
            language: Optional language code (en, hi, ta, te)
        
        Returns:
            OCRResult with extracted text and metadata
        """
        # Initialize engines on first use
        if not self._engines_initialized:
            self._initialize_ocr_engines()
        
        start_time = time.time()
        
        # Check cache first
        cache_key = self._calculate_cache_key(image_path, language)
        cached_result = await self._get_cached_result(cache_key)
        
        if cached_result:
            # Reconstruct OCRResult from cached data
            bounding_boxes = [
                BoundingBox(
                    text=bbox["text"],
                    coordinates=[[bbox["coordinates"]["x"], bbox["coordinates"]["y"]]],
                    confidence=bbox["confidence"]
                )
                for bbox in cached_result["bounding_boxes"]
            ]
            
            return OCRResult(
                raw_text=cached_result["raw_text"],
                confidence=cached_result["confidence"],
                detected_language=cached_result["detected_language"],
                bounding_boxes=bounding_boxes,
                processing_time_ms=cached_result["processing_time_ms"],
                low_confidence_warning=cached_result.get("low_confidence_warning", False)
            )
        
        # Detect language if not provided
        if not language:
            language = self._detect_language(image_path)
        
        # Validate language
        if language not in self.ocr_engines:
            logger.warning(f"Unsupported language: {language}, falling back to English")
            language = "en"
        
        # Preprocess image
        preprocessed_img = self._preprocess_image(image_path)
        
        # Perform OCR
        try:
            ocr_engine = self.ocr_engines[language]
            result = ocr_engine.ocr(preprocessed_img, cls=True)
            
            if not result or not result[0]:
                logger.warning(f"No text detected in image: {image_path}")
                return OCRResult(
                    raw_text="",
                    confidence=0.0,
                    detected_language=language,
                    bounding_boxes=[],
                    processing_time_ms=int((time.time() - start_time) * 1000),
                    low_confidence_warning=True
                )
            
            # Parse OCR results
            bounding_boxes = []
            text_lines = []
            confidences = []
            
            for line in result[0]:
                if line:
                    bbox_coords = line[0]
                    text_info = line[1]
                    text = text_info[0]
                    confidence = text_info[1]
                    
                    bounding_boxes.append(
                        BoundingBox(
                            text=text,
                            coordinates=bbox_coords,
                            confidence=confidence
                        )
                    )
                    text_lines.append(text)
                    confidences.append(confidence)
            
            # Calculate average confidence
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            # Check confidence threshold
            low_confidence = avg_confidence < settings.OCR_CONFIDENCE_THRESHOLD
            if low_confidence:
                logger.warning(
                    f"OCR confidence ({avg_confidence:.2f}) below threshold "
                    f"({settings.OCR_CONFIDENCE_THRESHOLD})"
                )
            
            # Combine text lines
            raw_text = "\n".join(text_lines)
            
            processing_time = int((time.time() - start_time) * 1000)
            
            ocr_result = OCRResult(
                raw_text=raw_text,
                confidence=avg_confidence,
                detected_language=language,
                bounding_boxes=bounding_boxes,
                processing_time_ms=processing_time,
                low_confidence_warning=low_confidence
            )
            
            # Cache the result
            await self._cache_result(cache_key, ocr_result.to_dict())
            
            logger.info(
                f"OCR completed: {len(text_lines)} lines, "
                f"confidence={avg_confidence:.2f}, time={processing_time}ms"
            )
            
            return ocr_result
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            raise
    
    async def detect_language(self, image_path: str) -> str:
        """
        Detect language from image
        
        Args:
            image_path: Path to the image file
        
        Returns:
            Detected language code
        """
        # For now, use simple detection
        # Can be enhanced with actual language detection model
        detected = self._detect_language(image_path)
        logger.info(f"Detected language: {detected}")
        return detected


# Global OCR service instance
ocr_service = OCRService()
