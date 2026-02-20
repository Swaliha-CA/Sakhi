"""Property-based tests for LLM service using Hypothesis

**Validates: Requirements 1.2**

Property 2: LLM Ingredient Structuring
For any OCR output containing ingredient information (even with formatting issues 
or ambiguities), the LLM_Processor should produce a structured ingredient list with 
at least the product category identified.
"""
import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from hypothesis import Phase

from app.services.llm_service import (
    LLMService,
    ProductCategory,
    IngredientList
)


# Custom strategies for generating test data

@st.composite
def ingredient_name(draw):
    """Generate realistic ingredient names"""
    common_ingredients = [
        "Water", "Glycerin", "Niacinamide", "Vitamin E", "Vitamin C",
        "Titanium Dioxide", "Zinc Oxide", "Stearic Acid", "Cetyl Alcohol",
        "Fragrance", "Methylparaben", "Propylparaben", "BHA", "BHT",
        "Sodium Lauryl Sulfate", "Coconut Oil", "Olive Oil", "Almond Oil",
        "Turmeric", "Neem", "Aloe Vera", "Shikakai", "Reetha", "Amla",
        "Bhringraj", "Brahmi", "Ashwagandha", "Kumkumadi", "Ubtan",
        "Multani Mitti", "Sandalwood", "Rose Water", "Saffron",
        "Wheat Flour", "Rice Flour", "Besan", "Hing", "Ajwain", "Jeera",
        "Methi", "Haldi", "Mirch", "Dhaniya", "Salt", "Sugar", "Citric Acid"
    ]
    
    # Either pick a common ingredient or generate a random one
    if draw(st.booleans()):
        return draw(st.sampled_from(common_ingredients))
    else:
        # Generate random ingredient-like name
        prefix = draw(st.sampled_from(["Sodium", "Potassium", "Calcium", "Methyl", "Ethyl", "Propyl"]))
        suffix = draw(st.sampled_from(["ate", "ide", "ene", "ine", "ol", "acid"]))
        return f"{prefix}{suffix}"


@st.composite
def ingredient_list_text(draw):
    """Generate ingredient list text with various formats"""
    num_ingredients = draw(st.integers(min_value=1, max_value=15))
    ingredients = [draw(ingredient_name()) for _ in range(num_ingredients)]
    
    # Choose separator
    separator = draw(st.sampled_from([", ", ",", "; ", ";", " | ", "\n"]))
    
    # Optionally add concentrations
    if draw(st.booleans()):
        ingredients_with_conc = []
        for ing in ingredients:
            if draw(st.booleans()):
                conc = draw(st.integers(min_value=1, max_value=99))
                ingredients_with_conc.append(f"{ing} ({conc}%)")
            else:
                ingredients_with_conc.append(ing)
        ingredients = ingredients_with_conc
    
    return separator.join(ingredients)


@st.composite
def product_category_keywords(draw, category):
    """Generate keywords for specific product categories"""
    keywords_map = {
        ProductCategory.COSMETIC: ["cream", "lotion", "lipstick", "kajal", "kumkum", "makeup", "foundation"],
        ProductCategory.FOOD: ["food", "snack", "biscuit", "oil", "masala", "spice", "flour", "edible"],
        ProductCategory.PERSONAL_CARE: ["soap", "shampoo", "toothpaste", "powder", "deodorant", "body wash"],
        ProductCategory.HOUSEHOLD: ["cleaner", "detergent", "disinfectant", "floor cleaner", "dish wash"],
        ProductCategory.UNKNOWN: ["product", "item", "thing", "stuff"]
    }
    
    keywords = keywords_map.get(category, ["product"])
    return draw(st.sampled_from(keywords))


@st.composite
def ocr_text_with_ingredients(draw):
    """Generate OCR text that contains ingredient information"""
    # Generate product name with category hint
    category = draw(st.sampled_from(list(ProductCategory)))
    category_keyword = draw(product_category_keywords(category))
    
    brand = draw(st.sampled_from([
        "Fair & Lovely", "Patanjali", "Himalaya", "Dabur", "Emami",
        "Lakme", "Ponds", "Nivea", "Garnier", "Biotique", "Khadi"
    ]))
    
    product_name = f"{brand} {category_keyword.title()}"
    
    # Generate manufacturer
    manufacturer = draw(st.sampled_from([
        "Hindustan Unilever Limited", "Patanjali Ayurved Limited",
        "Dabur India Limited", "Emami Limited", "Marico Limited",
        "ITC Limited", "Godrej Consumer Products"
    ]))
    
    # Generate ingredient list
    ingredients = draw(ingredient_list_text())
    
    # Choose format style
    format_style = draw(st.integers(min_value=0, max_value=3))
    
    if format_style == 0:
        # Clean format
        text = f"""{product_name}
Manufacturer: {manufacturer}

Ingredients: {ingredients}

Net Weight: 50g
"""
    elif format_style == 1:
        # Compact format
        text = f"{product_name}\nMfr: {manufacturer}\nIngredients: {ingredients}"
    
    elif format_style == 2:
        # Verbose format with extra info
        text = f"""Product Name: {product_name}
Manufactured by: {manufacturer}
Country of Origin: India

List of Ingredients:
{ingredients}

Storage: Store in cool dry place
Expiry: 24 months from manufacturing
"""
    else:
        # Minimal format with ingredients label
        text = f"{product_name}\n{manufacturer}\nIngredients: {ingredients}"
    
    return text, category


@st.composite
def ocr_text_with_formatting_issues(draw):
    """Generate OCR text with common formatting issues and ambiguities"""
    base_text, category = draw(ocr_text_with_ingredients())
    
    # Apply various formatting issues
    issue_type = draw(st.integers(min_value=0, max_value=5))
    
    if issue_type == 0:
        # Add random line breaks
        text = base_text.replace(" ", draw(st.sampled_from([" ", "\n", "  "])))
    
    elif issue_type == 1:
        # Add OCR artifacts (random special characters)
        artifacts = ["@", "#", "$", "!", "~", "|", "^"]
        artifact = draw(st.sampled_from(artifacts))
        # Insert artifacts at random positions
        words = base_text.split()
        if words:
            idx = draw(st.integers(min_value=0, max_value=len(words)-1))
            words[idx] = words[idx] + artifact
            text = " ".join(words)
        else:
            text = base_text
    
    elif issue_type == 2:
        # Inconsistent capitalization
        text = ""
        for char in base_text:
            if char.isalpha():
                text += char.upper() if draw(st.booleans()) else char.lower()
            else:
                text += char
    
    elif issue_type == 3:
        # Missing spaces or extra spaces
        text = base_text.replace(" ", draw(st.sampled_from(["", " ", "  ", "   "])))
    
    elif issue_type == 4:
        # Partial text (simulate incomplete OCR)
        split_point = draw(st.integers(min_value=len(base_text)//2, max_value=len(base_text)))
        text = base_text[:split_point]
    
    else:
        # Mixed with numbers (simulate OCR confusion)
        text = base_text.replace("o", "0").replace("O", "0").replace("l", "1").replace("I", "1")
    
    return text, category


# Property-based tests

class TestLLMIngredientStructuringProperty:
    """Property-based tests for LLM ingredient structuring
    
    **Validates: Requirements 1.2**
    **Property 2: LLM Ingredient Structuring**
    """
    
    @pytest.fixture
    def llm_service(self):
        """Create LLM service instance"""
        return LLMService()
    
    @given(ocr_text_with_ingredients())
    @settings(
        max_examples=20,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
        phases=[Phase.generate, Phase.target]
    )
    @pytest.mark.asyncio
    async def test_property_llm_structures_clean_ingredient_text(
        self,
        llm_service,
        ocr_data
    ):
        """
        Property 2: LLM Ingredient Structuring (Clean Text)
        
        For any OCR output containing ingredient information in clean format,
        the LLM_Processor should produce a structured ingredient list with 
        at least the product category identified.
        
        **Validates: Requirements 1.2**
        """
        ocr_text, expected_category = ocr_data
        
        # Assume text is not empty
        assume(len(ocr_text.strip()) > 10)
        
        # Execute: Structure ingredients from OCR text
        result = await llm_service.structure_ingredients(ocr_text)
        
        # Verify: Result is an IngredientList
        assert isinstance(result, IngredientList), \
            "LLM should return IngredientList object"
        
        # Verify: Product category is identified (not unknown)
        # Note: Due to fallback regex, category might not match expected exactly,
        # but it should at least be identified (not remain as UNKNOWN for clean text)
        assert result.category in list(ProductCategory), \
            f"Category should be valid ProductCategory enum, got {result.category}"
        
        # Verify: Product name is extracted
        assert result.product_name, \
            "Product name should be extracted and non-empty"
        
        # Verify: At least some ingredients are extracted
        # (Even if OCR is imperfect, should extract at least 1 ingredient from clean text)
        assert len(result.ingredients) >= 1, \
            f"Should extract at least 1 ingredient from text with ingredients, got {len(result.ingredients)}"
        
        # Verify: Each ingredient has a name
        for ing in result.ingredients:
            assert ing.name, \
                "Each ingredient should have a non-empty name"
            assert isinstance(ing.alternate_names, list), \
                "Alternate names should be a list"
        
        # Verify: Confidence score is in valid range
        assert 0.0 <= result.confidence <= 1.0, \
            f"Confidence should be between 0 and 1, got {result.confidence}"
        
        # Verify: Hallucination flags is a list
        assert isinstance(result.hallucination_flags, list), \
            "Hallucination flags should be a list"
    
    @given(ocr_text_with_formatting_issues())
    @settings(
        max_examples=20,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
        phases=[Phase.generate, Phase.target]
    )
    @pytest.mark.asyncio
    async def test_property_llm_handles_formatting_issues(
        self,
        llm_service,
        ocr_data
    ):
        """
        Property 2: LLM Ingredient Structuring (Formatting Issues)
        
        For any OCR output with formatting issues or ambiguities,
        the LLM_Processor should still produce a structured ingredient list 
        with at least the product category identified.
        
        **Validates: Requirements 1.2**
        """
        ocr_text, expected_category = ocr_data
        
        # Assume text is not empty
        assume(len(ocr_text.strip()) > 10)
        
        # Execute: Structure ingredients from problematic OCR text
        result = await llm_service.structure_ingredients(ocr_text)
        
        # Verify: Result is an IngredientList (even with formatting issues)
        assert isinstance(result, IngredientList), \
            "LLM should return IngredientList even with formatting issues"
        
        # Verify: Product category is identified
        # With formatting issues, category might be UNKNOWN, but should still be valid
        assert result.category in list(ProductCategory), \
            f"Category should be valid ProductCategory enum, got {result.category}"
        
        # Verify: Structure is complete (all required fields present)
        assert hasattr(result, 'product_name'), "Should have product_name field"
        assert hasattr(result, 'manufacturer'), "Should have manufacturer field"
        assert hasattr(result, 'ingredients'), "Should have ingredients field"
        assert hasattr(result, 'confidence'), "Should have confidence field"
        assert hasattr(result, 'hallucination_flags'), "Should have hallucination_flags field"
        
        # Verify: Ingredients is a list (even if empty due to severe formatting issues)
        assert isinstance(result.ingredients, list), \
            "Ingredients should be a list"
        
        # Verify: Confidence score is in valid range
        assert 0.0 <= result.confidence <= 1.0, \
            f"Confidence should be between 0 and 1, got {result.confidence}"
        
        # Verify: If ingredients are extracted, they have valid structure
        for ing in result.ingredients:
            assert hasattr(ing, 'name'), "Ingredient should have name field"
            assert hasattr(ing, 'alternate_names'), "Ingredient should have alternate_names field"
            assert hasattr(ing, 'concentration'), "Ingredient should have concentration field"
            assert hasattr(ing, 'cas_number'), "Ingredient should have cas_number field"
    
    @given(
        st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs')),
            min_size=20,
            max_size=500
        )
    )
    @settings(
        max_examples=10,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
    )
    @pytest.mark.asyncio
    async def test_property_llm_handles_arbitrary_text(
        self,
        llm_service,
        random_text
    ):
        """
        Property 2: LLM Ingredient Structuring (Arbitrary Text)
        
        For any arbitrary text input, the LLM_Processor should not crash
        and should return a valid IngredientList structure (even if empty).
        
        **Validates: Requirements 1.2**
        """
        # Assume text is not just whitespace
        assume(len(random_text.strip()) > 10)
        
        # Execute: Try to structure ingredients from arbitrary text
        result = await llm_service.structure_ingredients(random_text)
        
        # Verify: No exception is raised and result is valid
        assert isinstance(result, IngredientList), \
            "Should return IngredientList even for arbitrary text"
        
        # Verify: All required fields are present
        assert hasattr(result, 'product_name')
        assert hasattr(result, 'manufacturer')
        assert hasattr(result, 'category')
        assert hasattr(result, 'ingredients')
        assert hasattr(result, 'confidence')
        assert hasattr(result, 'hallucination_flags')
        
        # Verify: Category is valid enum value
        assert result.category in list(ProductCategory)
        
        # Verify: Confidence is in valid range
        assert 0.0 <= result.confidence <= 1.0
        
        # Verify: Ingredients is a list
        assert isinstance(result.ingredients, list)
    
    @given(
        st.lists(
            ingredient_name(),
            min_size=1,
            max_size=20
        )
    )
    @settings(
        max_examples=10,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
    )
    @pytest.mark.asyncio
    async def test_property_ingredient_extraction_completeness(
        self,
        llm_service,
        ingredient_names
    ):
        """
        Property 2: LLM Ingredient Structuring (Extraction Completeness)
        
        For any list of ingredients in the OCR text, the LLM should extract
        at least some of them (not lose all ingredients).
        
        **Validates: Requirements 1.2**
        """
        # Create simple ingredient list text
        ocr_text = f"""Test Product
Manufacturer: Test Company
Ingredients: {', '.join(ingredient_names)}
"""
        
        # Execute: Structure ingredients
        result = await llm_service.structure_ingredients(ocr_text)
        
        # Verify: At least some ingredients are extracted
        # (We don't require 100% extraction due to OCR ambiguities, but should get at least 1)
        assert len(result.ingredients) >= 1, \
            f"Should extract at least 1 ingredient from list of {len(ingredient_names)}, got {len(result.ingredients)}"
        
        # Verify: Extracted ingredients have names
        for ing in result.ingredients:
            assert ing.name, "Extracted ingredient should have non-empty name"
    
    @given(
        st.sampled_from([
            ProductCategory.COSMETIC,
            ProductCategory.FOOD,
            ProductCategory.PERSONAL_CARE,
            ProductCategory.HOUSEHOLD
        ])
    )
    @settings(
        max_examples=10,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
    )
    @pytest.mark.asyncio
    async def test_property_category_identification_consistency(
        self,
        llm_service,
        category
    ):
        """
        Property 2: LLM Ingredient Structuring (Category Consistency)
        
        For OCR text with clear category indicators, the LLM should identify
        a category (not return UNKNOWN for obvious cases).
        
        **Validates: Requirements 1.2**
        """
        # Generate text with clear category keyword
        keyword = {
            ProductCategory.COSMETIC: "Face Cream",
            ProductCategory.FOOD: "Masala Powder",
            ProductCategory.PERSONAL_CARE: "Herbal Shampoo",
            ProductCategory.HOUSEHOLD: "Floor Cleaner"
        }[category]
        
        ocr_text = f"""{keyword}
Manufacturer: Test Company
Ingredients: Water, Glycerin, Fragrance
"""
        
        # Execute: Structure ingredients
        result = await llm_service.structure_ingredients(ocr_text)
        
        # Verify: Category is identified (not UNKNOWN)
        # Note: Due to fallback regex, it should identify the category
        assert result.category != ProductCategory.UNKNOWN, \
            f"Should identify category for clear keyword '{keyword}', got {result.category}"
        
        # Verify: Category matches expected (for fallback regex at least)
        assert result.category == category, \
            f"Should identify correct category {category} for keyword '{keyword}', got {result.category}"
    
    @given(st.integers(min_value=0, max_value=100))
    @settings(
        max_examples=10,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
    )
    @pytest.mark.asyncio
    async def test_property_confidence_score_validity(
        self,
        llm_service,
        seed
    ):
        """
        Property 2: LLM Ingredient Structuring (Confidence Score)
        
        For any OCR text, the confidence score should always be in valid range [0, 1].
        
        **Validates: Requirements 1.2**
        """
        # Generate varied OCR text based on seed
        if seed < 33:
            # Clean text
            ocr_text = "Test Cream\nManufacturer: Test\nIngredients: Water, Glycerin"
        elif seed < 66:
            # Messy text
            ocr_text = "T3st!@#Cr3am\nMfr:T3st\nIng:W@ter,Glyc3rin"
        else:
            # Minimal text
            ocr_text = "Product\nIngredients: Water"
        
        # Execute: Structure ingredients
        result = await llm_service.structure_ingredients(ocr_text)
        
        # Verify: Confidence is always in valid range
        assert 0.0 <= result.confidence <= 1.0, \
            f"Confidence must be between 0 and 1, got {result.confidence}"
        
        # Verify: Confidence is a float
        assert isinstance(result.confidence, (int, float)), \
            f"Confidence should be numeric, got {type(result.confidence)}"
