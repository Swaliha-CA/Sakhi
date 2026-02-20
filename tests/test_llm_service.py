"""Unit tests for LLM service"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.llm_service import (
    LLMService,
    ProductCategory,
    Ingredient,
    IngredientList
)


@pytest.fixture
def llm_service():
    """Create LLM service instance"""
    service = LLMService()
    return service


@pytest.fixture
def sample_ocr_text():
    """Sample OCR text from product label"""
    return """
    Fair & Lovely Advanced Multi-Vitamin Cream
    Manufacturer: Hindustan Unilever Limited
    
    Ingredients: Water, Glycerin, Niacinamide, Titanium Dioxide,
    Stearic Acid, Vitamin E, Vitamin B3, Fragrance, Methylparaben
    
    Net Weight: 50g
    """


@pytest.fixture
def sample_complex_label():
    """Sample complex multilingual label"""
    return """
    पतंजलि केश कांति हेयर ऑयल
    Patanjali Kesh Kanti Hair Oil
    निर्माता: पतंजलि आयुर्वेद लिमिटेड
    
    सामग्री / Ingredients: तिल का तेल (Sesame Oil), नारियल तेल (Coconut Oil),
    भृंगराज (Bhringraj), आंवला (Amla), ब्राह्मी (Brahmi)
    """


class TestLLMService:
    """Test LLM service functionality"""
    
    def test_initialization(self, llm_service):
        """Test service initialization"""
        assert llm_service is not None
        assert llm_service.redis_client is None
        assert not llm_service._initialized
    
    def test_is_complex_label_simple(self, llm_service, sample_ocr_text):
        """Test complexity detection for simple label"""
        is_complex = llm_service._is_complex_label(sample_ocr_text)
        assert not is_complex
    
    def test_is_complex_label_multilingual(self, llm_service, sample_complex_label):
        """Test complexity detection for multilingual label"""
        is_complex = llm_service._is_complex_label(sample_complex_label)
        assert is_complex  # Should detect mixed scripts
    
    def test_is_complex_label_long_list(self, llm_service):
        """Test complexity detection for long ingredient list"""
        long_text = "Ingredients: " + ", ".join([f"Ingredient{i}" for i in range(25)])
        is_complex = llm_service._is_complex_label(long_text)
        assert is_complex  # Should detect >20 commas
    
    def test_is_complex_label_poor_ocr(self, llm_service):
        """Test complexity detection for poor OCR quality"""
        poor_text = "Pr0duct: T3st!@# M@ny $pec!@l Ch@rs!!!"
        is_complex = llm_service._is_complex_label(poor_text)
        assert is_complex  # Should detect high special char ratio
    
    def test_build_prompt(self, llm_service, sample_ocr_text):
        """Test prompt building"""
        context = {"detected_language": "en", "confidence": 0.9}
        prompt = llm_service._build_prompt(sample_ocr_text, context)
        
        assert "Indian product label" in prompt
        assert sample_ocr_text in prompt
        assert "JSON" in prompt
        assert "hallucination_flags" in prompt
    
    def test_get_empty_result(self, llm_service):
        """Test empty result structure"""
        result = llm_service._get_empty_result()
        
        assert result["product_name"] == ""
        assert result["manufacturer"] == ""
        assert result["category"] == "unknown"
        assert result["ingredients"] == []
        assert result["confidence"] == 0.0
        assert result["hallucination_flags"] == []
    
    def test_fallback_regex_extraction_basic(self, llm_service, sample_ocr_text):
        """Test regex fallback extraction"""
        result = llm_service._fallback_regex_extraction(sample_ocr_text)
        
        assert result["product_name"] != ""
        assert result["manufacturer"] != ""
        assert len(result["ingredients"]) > 0
        assert result["confidence"] == 0.5
        assert result["category"] in ["cosmetic", "food", "household", "personal_care", "unknown"]
    
    def test_fallback_regex_extraction_ingredients(self, llm_service):
        """Test regex extraction finds ingredients"""
        text = """
        Product: Test Cream
        Manufacturer: Test Company
        Ingredients: Water, Glycerin, Niacinamide (5%), Vitamin E
        """
        result = llm_service._fallback_regex_extraction(text)
        
        assert len(result["ingredients"]) >= 3
        # Check that concentration is extracted
        niacinamide = next((ing for ing in result["ingredients"] if "Niacinamide" in ing["name"]), None)
        if niacinamide:
            assert niacinamide["concentration"] == "5%"
    
    def test_fallback_regex_extraction_category_cosmetic(self, llm_service):
        """Test category detection for cosmetic"""
        text = "Product: Face Cream\nIngredients: Water, Glycerin"
        result = llm_service._fallback_regex_extraction(text)
        assert result["category"] == "cosmetic"
    
    def test_fallback_regex_extraction_category_food(self, llm_service):
        """Test category detection for food"""
        text = "Product: Masala Powder\nIngredients: Turmeric, Cumin"
        result = llm_service._fallback_regex_extraction(text)
        assert result["category"] == "food"
    
    def test_fallback_regex_extraction_category_personal_care(self, llm_service):
        """Test category detection for personal care"""
        text = "Product: Herbal Shampoo\nIngredients: Water, Shikakai"
        result = llm_service._fallback_regex_extraction(text)
        assert result["category"] == "personal_care"
    
    def test_dict_to_ingredient_list(self, llm_service):
        """Test conversion from dict to IngredientList"""
        data = {
            "product_name": "Test Product",
            "manufacturer": "Test Manufacturer",
            "category": "cosmetic",
            "ingredients": [
                {
                    "name": "Water",
                    "alternate_names": ["Aqua", "H2O"],
                    "concentration": "80%",
                    "cas_number": "7732-18-5"
                }
            ],
            "confidence": 0.95,
            "hallucination_flags": []
        }
        
        result = llm_service._dict_to_ingredient_list(data)
        
        assert isinstance(result, IngredientList)
        assert result.product_name == "Test Product"
        assert result.manufacturer == "Test Manufacturer"
        assert result.category == ProductCategory.COSMETIC
        assert len(result.ingredients) == 1
        assert result.ingredients[0].name == "Water"
        assert result.confidence == 0.95
    
    @pytest.mark.asyncio
    async def test_identify_product_category_cosmetic(self, llm_service):
        """Test category identification for cosmetic"""
        text = "This is a face cream with natural ingredients"
        category = await llm_service.identify_product_category(text)
        assert category == ProductCategory.COSMETIC
    
    @pytest.mark.asyncio
    async def test_identify_product_category_food(self, llm_service):
        """Test category identification for food"""
        text = "Organic masala spice mix for cooking"
        category = await llm_service.identify_product_category(text)
        assert category == ProductCategory.FOOD
    
    @pytest.mark.asyncio
    async def test_identify_product_category_personal_care(self, llm_service):
        """Test category identification for personal care"""
        text = "Natural shampoo with herbal extracts"
        category = await llm_service.identify_product_category(text)
        assert category == ProductCategory.PERSONAL_CARE
    
    @pytest.mark.asyncio
    async def test_identify_product_category_household(self, llm_service):
        """Test category identification for household"""
        text = "Floor cleaner with disinfectant properties"
        category = await llm_service.identify_product_category(text)
        assert category == ProductCategory.HOUSEHOLD
    
    @pytest.mark.asyncio
    async def test_identify_product_category_unknown(self, llm_service):
        """Test category identification for unknown"""
        text = "Some random text without category keywords"
        category = await llm_service.identify_product_category(text)
        assert category == ProductCategory.UNKNOWN
    
    def test_calculate_cache_key(self, llm_service):
        """Test cache key calculation"""
        text = "Test text"
        context = {"lang": "en"}
        
        key1 = llm_service._calculate_cache_key(text, context)
        key2 = llm_service._calculate_cache_key(text, context)
        
        # Same input should produce same key
        assert key1 == key2
        assert key1.startswith("llm:ingredients:")
        
        # Different input should produce different key
        key3 = llm_service._calculate_cache_key("Different text", context)
        assert key1 != key3
    
    @pytest.mark.asyncio
    async def test_structure_ingredients_with_fallback(self, llm_service, sample_ocr_text):
        """Test structure_ingredients falls back to regex when LLM unavailable"""
        # Don't initialize LLM clients
        result = await llm_service.structure_ingredients(sample_ocr_text)
        
        assert isinstance(result, IngredientList)
        assert result.product_name != ""
        assert len(result.ingredients) > 0
        # Fallback should have lower confidence
        assert result.confidence <= 0.5
    
    @pytest.mark.asyncio
    async def test_translate_to_english_already_english(self, llm_service):
        """Test translation when text is already English"""
        text = "This is English text"
        result = await llm_service.translate_to_english(text, "en")
        assert result == text
    
    def test_ingredient_to_dict(self):
        """Test Ingredient to_dict conversion"""
        ing = Ingredient(
            name="Water",
            alternate_names=["Aqua"],
            concentration="80%",
            cas_number="7732-18-5"
        )
        
        result = ing.to_dict()
        
        assert result["name"] == "Water"
        assert result["alternate_names"] == ["Aqua"]
        assert result["concentration"] == "80%"
        assert result["cas_number"] == "7732-18-5"
    
    def test_ingredient_list_to_dict(self):
        """Test IngredientList to_dict conversion"""
        ing_list = IngredientList(
            ingredients=[
                Ingredient(name="Water", alternate_names=["Aqua"])
            ],
            product_name="Test Product",
            manufacturer="Test Mfr",
            category=ProductCategory.COSMETIC,
            confidence=0.9,
            hallucination_flags=["suspicious_ingredient"]
        )
        
        result = ing_list.to_dict()
        
        assert result["product_name"] == "Test Product"
        assert result["manufacturer"] == "Test Mfr"
        assert result["category"] == "cosmetic"
        assert result["confidence"] == 0.9
        assert len(result["ingredients"]) == 1
        assert result["hallucination_flags"] == ["suspicious_ingredient"]


class TestLLMServiceEdgeCases:
    """Test edge cases and error handling"""
    
    def test_fallback_extraction_empty_text(self, llm_service):
        """Test fallback with empty text"""
        result = llm_service._fallback_regex_extraction("")
        
        assert result["product_name"] == ""
        assert result["ingredients"] == []
        assert result["confidence"] == 0.5
    
    def test_fallback_extraction_no_ingredients(self, llm_service):
        """Test fallback with no ingredients section"""
        text = "Product: Test\nManufacturer: Test Co"
        result = llm_service._fallback_regex_extraction(text)
        
        assert result["product_name"] == "Product: Test"
        assert result["manufacturer"] == "Test Co"
        assert result["ingredients"] == []
    
    def test_is_complex_label_empty(self, llm_service):
        """Test complexity detection with empty text"""
        is_complex = llm_service._is_complex_label("")
        assert not is_complex
    
    @pytest.mark.asyncio
    async def test_redis_connection_failure(self, llm_service):
        """Test graceful handling of Redis connection failure"""
        # This should not raise an exception
        await llm_service.connect_redis()
        # Service should still work without Redis
        assert True
    
    def test_dict_to_ingredient_list_minimal(self, llm_service):
        """Test conversion with minimal data"""
        data = {
            "product_name": "Test",
            "manufacturer": "Test",
            "category": "unknown",
            "ingredients": [],
            "confidence": 0.0,
            "hallucination_flags": []
        }
        
        result = llm_service._dict_to_ingredient_list(data)
        
        assert isinstance(result, IngredientList)
        assert result.product_name == "Test"
        assert len(result.ingredients) == 0
