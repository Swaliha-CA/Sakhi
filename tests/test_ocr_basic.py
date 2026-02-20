"""Basic unit tests for OCR service (without PaddleOCR dependency)"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import numpy as np
from pathlib import Path

from app.services.ocr_service import OCRService, OCRResult, BoundingBox
from app.core.config import settings


class TestOCRServiceBasic:
    """Basic test suite for OCR service without PaddleOCR"""
    
    @pytest.fixture
    def ocr_service(self):
        """Create OCR service instance"""
        service = OCRService()
        return service
    
    def test_ocr_service_creation(self, ocr_service):
        """Test OCR service can be created"""
        assert ocr_service is not None
        assert ocr_service._engines_initialized is False
        assert isinstance(ocr_service.ocr_engines, dict)
    
    def test_bounding_box_creation(self):
        """Test BoundingBox creation and serialization"""
        bbox = BoundingBox(
            text="Test",
            coordinates=[[10, 20], [100, 20], [100, 50], [10, 50]],
            confidence=0.95
        )
        
        assert bbox.text == "Test"
        assert bbox.confidence == 0.95
        
        bbox_dict = bbox.to_dict()
        assert bbox_dict["text"] == "Test"
        assert bbox_dict["confidence"] == 0.95
        assert "coordinates" in bbox_dict
        assert "x" in bbox_dict["coordinates"]
        assert "y" in bbox_dict["coordinates"]
        assert "width" in bbox_dict["coordinates"]
        assert "height" in bbox_dict["coordinates"]
    
    def test_ocr_result_creation(self):
        """Test OCRResult creation and serialization"""
        bbox = BoundingBox(
            text="Test",
            coordinates=[[10, 20], [100, 20], [100, 50], [10, 50]],
            confidence=0.95
        )
        
        result = OCRResult(
            raw_text="Test text",
            confidence=0.95,
            detected_language="en",
            bounding_boxes=[bbox],
            processing_time_ms=100,
            low_confidence_warning=False
        )
        
        assert result.raw_text == "Test text"
        assert result.confidence == 0.95
        assert result.detected_language == "en"
        assert len(result.bounding_boxes) == 1
        assert result.processing_time_ms == 100
        assert result.low_confidence_warning is False
        
        result_dict = result.to_dict()
        assert result_dict["raw_text"] == "Test text"
        assert result_dict["confidence"] == 0.95
        assert result_dict["detected_language"] == "en"
        assert len(result_dict["bounding_boxes"]) == 1
    
    def test_cache_key_calculation(self, ocr_service, tmp_path):
        """Test cache key calculation"""
        # Create a temporary test file
        test_file = tmp_path / "test.jpg"
        test_file.write_bytes(b"test image content")
        
        key1 = ocr_service._calculate_cache_key(str(test_file), "en")
        key2 = ocr_service._calculate_cache_key(str(test_file), "en")
        
        # Same file and language should produce same key
        assert key1 == key2
        assert key1.startswith("ocr:")
        
        # Different language should produce different key
        key3 = ocr_service._calculate_cache_key(str(test_file), "hi")
        assert key1 != key3
    
    def test_language_detection(self, ocr_service):
        """Test language detection returns valid language"""
        # This is a simple implementation that returns 'en'
        detected = ocr_service._detect_language("dummy_path.jpg")
        assert detected in settings.OCR_SUPPORTED_LANGUAGES
    
    @pytest.mark.asyncio
    async def test_redis_connection_graceful_failure(self, ocr_service):
        """Test that service handles Redis connection failure gracefully"""
        # Service should work even if Redis is not available
        await ocr_service.connect_redis()
        # No assertion needed - just verify it doesn't crash
        assert True
    
    def test_confidence_threshold_configuration(self):
        """Test that confidence threshold is properly configured"""
        assert settings.OCR_CONFIDENCE_THRESHOLD == 0.85
        assert isinstance(settings.OCR_CONFIDENCE_THRESHOLD, float)
        assert 0.0 <= settings.OCR_CONFIDENCE_THRESHOLD <= 1.0
    
    def test_supported_languages_configuration(self):
        """Test that supported languages are properly configured"""
        assert len(settings.OCR_SUPPORTED_LANGUAGES) > 0
        assert "en" in settings.OCR_SUPPORTED_LANGUAGES
        
        # All languages should be valid codes
        for lang in settings.OCR_SUPPORTED_LANGUAGES:
            assert isinstance(lang, str)
            assert len(lang) == 2  # ISO 639-1 language codes
    
    def test_cache_ttl_configuration(self):
        """Test that cache TTL is properly configured"""
        assert settings.OCR_CACHE_TTL == 86400  # 24 hours
        assert isinstance(settings.OCR_CACHE_TTL, int)
        assert settings.OCR_CACHE_TTL > 0
    
    def test_preprocessing_with_valid_image(self, ocr_service, tmp_path):
        """Test image preprocessing with a valid image"""
        # Create a simple test image
        from PIL import Image
        img = Image.new('RGB', (100, 100), color='white')
        test_file = tmp_path / "test.jpg"
        img.save(test_file)
        
        # Test preprocessing
        preprocessed = ocr_service._preprocess_image(str(test_file))
        
        assert isinstance(preprocessed, np.ndarray)
        assert len(preprocessed.shape) == 3  # Height, Width, Channels
    
    def test_preprocessing_with_invalid_image(self, ocr_service):
        """Test preprocessing handles invalid images"""
        # Preprocessing returns None for invalid images (fallback behavior)
        result = ocr_service._preprocess_image("/nonexistent/image.jpg")
        # The function tries to read the image and returns None on failure
        assert result is None
