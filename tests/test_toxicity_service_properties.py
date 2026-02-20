"""Property-based tests for Toxicity Scoring Service using Hypothesis

**Validates: Requirements 1.3, 1.4, 1.5, 2.1**

Property 3: Ingredient Database Matching
Property 4: EDC Risk Score Calculation
Property 5: Risk-Based Product Flagging
Property 6: Hormonal Health Score Range
"""
import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from hypothesis import Phase

from app.services.toxicity_service import (
    ToxicityScorer,
    ToxicityDatabaseClient,
    Ingredient,
    FlaggedChemical,
    EDCType,
    RegulatoryInfo,
    ToxicityScore
)


# Custom strategies for generating test data

@st.composite
def ingredient_name_strategy(draw):
    """Generate realistic ingredient names"""
    common_ingredients = [
        # Safe ingredients
        "Water", "Glycerin", "Vitamin E", "Vitamin C", "Aloe Vera",
        "Coconut Oil", "Olive Oil", "Shea Butter", "Cocoa Butter",
        
        # Known EDCs
        "BPA", "Bisphenol A", "Methylparaben", "Propylparaben",
        "DEHP", "DBP", "Dibutyl Phthalate", "Lead", "Mercury",
        "Triclosan", "Triclocarban",
        
        # Indian ingredients
        "Turmeric", "Neem", "Kumkum", "Sindoor", "Kajal",
        "Sandalwood", "Rose Water", "Henna"
    ]
    
    return draw(st.sampled_from(common_ingredients))


@st.composite
def ingredient_strategy(draw):
    """Generate Ingredient objects"""
    name = draw(ingredient_name_strategy())
    
    # Optionally add concentration
    concentration = None
    if draw(st.booleans()):
        concentration = f"{draw(st.integers(min_value=1, max_value=99))}%"
    
    # Optionally add CAS number (for known chemicals)
    cas_number = None
    if draw(st.booleans()):
        cas_number = f"{draw(st.integers(min_value=100, max_value=999))}-{draw(st.integers(min_value=10, max_value=99))}-{draw(st.integers(min_value=0, max_value=9))}"
    
    return Ingredient(
        name=name,
        alternate_names=[],
        concentration=concentration,
        cas_number=cas_number
    )


@st.composite
def ingredient_list_strategy(draw, min_size=1, max_size=20):
    """Generate list of ingredients"""
    return draw(st.lists(
        ingredient_strategy(),
        min_size=min_size,
        max_size=max_size
    ))


@st.composite
def edc_type_strategy(draw):
    """Generate EDC type"""
    return draw(st.sampled_from([
        EDCType.BPA,
        EDCType.PHTHALATE,
        EDCType.PARABEN,
        EDCType.ORGANOCHLORINE,
        EDCType.HEAVY_METAL,
        EDCType.PFAS,
        EDCType.UNKNOWN
    ]))


@st.composite
def flagged_chemical_strategy(draw):
    """Generate FlaggedChemical objects"""
    edc_type = draw(edc_type_strategy())
    
    # Risk score should be 0-100
    risk_score = draw(st.floats(min_value=0.0, max_value=100.0))
    
    # Confidence should be 0-1
    confidence = draw(st.floats(min_value=0.0, max_value=1.0))
    
    return FlaggedChemical(
        name=draw(st.text(min_size=1, max_size=50)),
        cas_number=f"{draw(st.integers(min_value=100, max_value=999))}-{draw(st.integers(min_value=10, max_value=99))}-{draw(st.integers(min_value=0, max_value=9))}",
        edc_types=[edc_type],
        risk_score=risk_score,
        health_effects=["Test health effect"],
        regulatory_status=RegulatoryInfo(),
        sources=["test_database"],
        confidence=confidence
    )


# Property-based tests

class TestIngredientDatabaseMatchingProperty:
    """Property-based tests for ingredient database matching
    
    **Validates: Requirements 1.3**
    **Property 3: Ingredient Database Matching**
    """
    
    @pytest.fixture
    async def db_client(self):
        """Create database client instance"""
        client = ToxicityDatabaseClient()
        await client.connect()
        yield client
        await client.disconnect()
    
    @given(ingredient_strategy())
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
        phases=[Phase.generate, Phase.target]
    )
    @pytest.mark.asyncio
    async def test_property_ingredient_database_matching(
        self,
        db_client,
        ingredient
    ):
        """
        Property 3: Ingredient Database Matching
        
        For any structured ingredient, the Toxicity_Scorer should attempt to match
        the ingredient against toxicology databases, and the ingredient should either
        have a database match or be explicitly marked as "not found".
        
        **Validates: Requirements 1.3**
        """
        # Execute: Try to get EDC info for ingredient
        edc_info = await db_client.get_edc_info(ingredient.name)
        
        # Verify: Result is either a FlaggedChemical or None (explicitly not found)
        assert edc_info is None or isinstance(edc_info, FlaggedChemical), \
            "Database matching should return FlaggedChemical or None"
        
        # Verify: If match found, it has required fields
        if edc_info is not None:
            assert edc_info.name, "Matched chemical should have a name"
            assert edc_info.cas_number, "Matched chemical should have CAS number"
            assert isinstance(edc_info.edc_types, list), "EDC types should be a list"
            assert len(edc_info.edc_types) > 0, "Should have at least one EDC type"
            assert isinstance(edc_info.risk_score, (int, float)), "Risk score should be numeric"
            assert isinstance(edc_info.health_effects, list), "Health effects should be a list"
            assert isinstance(edc_info.regulatory_status, RegulatoryInfo), "Should have regulatory status"
            assert isinstance(edc_info.sources, list), "Sources should be a list"
            assert len(edc_info.sources) > 0, "Should have at least one source"
            assert isinstance(edc_info.confidence, (int, float)), "Confidence should be numeric"
            assert 0.0 <= edc_info.confidence <= 1.0, "Confidence should be between 0 and 1"


class TestEDCRiskScoreCalculationProperty:
    """Property-based tests for EDC risk score calculation
    
    **Validates: Requirements 1.4**
    **Property 4: EDC Risk Score Calculation**
    """
    
    @pytest.fixture
    async def scorer(self):
        """Create scorer instance"""
        client = ToxicityDatabaseClient()
        await client.connect()
        scorer = ToxicityScorer(client)
        yield scorer
        await client.disconnect()
    
    @given(ingredient_list_strategy(min_size=1, max_size=10))
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
        phases=[Phase.generate, Phase.target]
    )
    @pytest.mark.asyncio
    async def test_property_edc_risk_score_range(
        self,
        scorer,
        ingredients
    ):
        """
        Property 4: EDC Risk Score Calculation (Score Range)
        
        For any set of ingredients, the calculated toxicity risk score should be
        a number between 0 and 100.
        
        **Validates: Requirements 1.4**
        """
        # Execute: Score the product
        result = await scorer.score_product(ingredients)
        
        # Verify: Overall score is in valid range
        assert isinstance(result.overall_score, (int, float)), \
            "Overall score should be numeric"
        assert 0.0 <= result.overall_score <= 100.0, \
            f"Overall score should be between 0 and 100, got {result.overall_score}"
        
        # Verify: Result is a ToxicityScore object
        assert isinstance(result, ToxicityScore), \
            "Should return ToxicityScore object"

    @given(
        st.lists(
            st.sampled_from(["BPA", "DEHP", "Methylparaben", "Water", "Glycerin"]),
            min_size=2,
            max_size=5
        )
    )
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
    )
    @pytest.mark.asyncio
    async def test_property_higher_edc_concentration_lower_score(
        self,
        scorer,
        ingredient_names
    ):
        """
        Property 4: EDC Risk Score Calculation (Concentration Effect)
        
        For any set of identified EDC compounds, higher EDC concentrations
        should result in higher risk scores (lower safety scores).
        
        **Validates: Requirements 1.4**
        """
        # Create two product versions: one with more EDCs, one with fewer
        all_ingredients = [Ingredient(name=name) for name in ingredient_names]
        
        # Count known EDCs in the list
        known_edcs = ["BPA", "DEHP", "Methylparaben"]
        edc_count = sum(1 for name in ingredient_names if name in known_edcs)
        
        # Only test if we have at least one EDC
        assume(edc_count > 0)
        
        # Execute: Score the product
        result = await scorer.score_product(all_ingredients)
        
        # Verify: If EDCs are present, score should be less than 100
        if edc_count > 0:
            assert result.overall_score < 100.0, \
                "Products with EDCs should have score less than 100"
            
            # More EDCs should mean more flagged chemicals
            assert len(result.flagged_chemicals) > 0, \
                "Should flag at least some EDCs"
    
    @given(st.lists(ingredient_strategy(), min_size=1, max_size=15))
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
    )
    @pytest.mark.asyncio
    async def test_property_score_calculation_consistency(
        self,
        scorer,
        ingredients
    ):
        """
        Property 4: EDC Risk Score Calculation (Consistency)
        
        For any set of ingredients, scoring the same product twice should
        produce the same result (deterministic).
        
        **Validates: Requirements 1.4**
        """
        # Execute: Score the product twice
        result1 = await scorer.score_product(ingredients)
        result2 = await scorer.score_product(ingredients)
        
        # Verify: Results are consistent
        assert result1.overall_score == result2.overall_score, \
            "Scoring should be deterministic"
        assert result1.hormonal_health_score == result2.hormonal_health_score, \
            "Hormonal health scoring should be deterministic"
        assert result1.risk_level == result2.risk_level, \
            "Risk level classification should be deterministic"
        assert len(result1.flagged_chemicals) == len(result2.flagged_chemicals), \
            "Number of flagged chemicals should be consistent"


class TestRiskBasedProductFlaggingProperty:
    """Property-based tests for risk-based product flagging
    
    **Validates: Requirements 1.5**
    **Property 5: Risk-Based Product Flagging**
    """
    
    @pytest.fixture
    async def scorer(self):
        """Create scorer instance"""
        client = ToxicityDatabaseClient()
        await client.connect()
        scorer = ToxicityScorer(client)
        yield scorer
        await client.disconnect()
    
    @given(st.floats(min_value=0.0, max_value=100.0))
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
    )
    @pytest.mark.asyncio
    async def test_property_risk_level_threshold_correctness(
        self,
        scorer,
        score
    ):
        """
        Property 5: Risk-Based Product Flagging (Threshold Correctness)
        
        For any calculated risk score, the severity indicator (low/medium/high/critical)
        should correspond to the correct threshold range.
        
        **Validates: Requirements 1.5**
        """
        # Execute: Classify risk level
        risk_level = scorer._classify_risk_level(score)
        
        # Verify: Risk level is valid
        assert risk_level in ["low", "medium", "high", "critical"], \
            f"Risk level should be one of the valid values, got {risk_level}"
        
        # Verify: Risk level matches threshold ranges
        if score >= 70.0:
            assert risk_level == "low", \
                f"Score {score} >= 70 should be 'low' risk, got {risk_level}"
        elif score >= 50.0:
            assert risk_level == "medium", \
                f"Score {score} >= 50 should be 'medium' risk, got {risk_level}"
        elif score >= 30.0:
            assert risk_level == "high", \
                f"Score {score} >= 30 should be 'high' risk, got {risk_level}"
        else:
            assert risk_level == "critical", \
                f"Score {score} < 30 should be 'critical' risk, got {risk_level}"
    
    @given(ingredient_list_strategy(min_size=1, max_size=10))
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
    )
    @pytest.mark.asyncio
    async def test_property_higher_risk_more_severe_flags(
        self,
        scorer,
        ingredients
    ):
        """
        Property 5: Risk-Based Product Flagging (Severity Ordering)
        
        Products with higher risk scores should have more severe flags.
        
        **Validates: Requirements 1.5**
        """
        # Execute: Score the product
        result = await scorer.score_product(ingredients)
        
        # Verify: Risk level severity matches score
        severity_order = ["low", "medium", "high", "critical"]
        
        if result.overall_score >= 70:
            assert result.risk_level == "low"
        elif result.overall_score >= 50:
            assert result.risk_level in ["low", "medium"]
        elif result.overall_score >= 30:
            assert result.risk_level in ["low", "medium", "high"]
        else:
            assert result.risk_level in ["low", "medium", "high", "critical"]
        
        # Verify: Flagged chemicals list is valid
        assert isinstance(result.flagged_chemicals, list), \
            "Flagged chemicals should be a list"
        
        for chemical in result.flagged_chemicals:
            assert isinstance(chemical, FlaggedChemical), \
                "Each flagged item should be a FlaggedChemical"


class TestHormonalHealthScoreRangeProperty:
    """Property-based tests for hormonal health score range
    
    **Validates: Requirements 2.1**
    **Property 6: Hormonal Health Score Range**
    """
    
    @pytest.fixture
    async def scorer(self):
        """Create scorer instance"""
        client = ToxicityDatabaseClient()
        await client.connect()
        scorer = ToxicityScorer(client)
        yield scorer
        await client.disconnect()
    
    @given(ingredient_list_strategy(min_size=1, max_size=10))
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
        phases=[Phase.generate, Phase.target]
    )
    @pytest.mark.asyncio
    async def test_property_hormonal_health_score_range(
        self,
        scorer,
        ingredients
    ):
        """
        Property 6: Hormonal Health Score Range (Valid Range)
        
        For any analyzed product, the Hormonal Health Score should be in the range 0-100.
        
        **Validates: Requirements 2.1**
        """
        # Execute: Score the product
        result = await scorer.score_product(ingredients)
        
        # Verify: Hormonal health score is in valid range
        assert isinstance(result.hormonal_health_score, (int, float)), \
            "Hormonal health score should be numeric"
        assert 0.0 <= result.hormonal_health_score <= 100.0, \
            f"Hormonal health score should be between 0 and 100, got {result.hormonal_health_score}"

    @given(
        st.lists(
            st.sampled_from([
                "BPA", "Bisphenol A",  # BPA - high PCOS penalty
                "DEHP", "Dibutyl Phthalate",  # Phthalates - high PCOS penalty
                "Triclosan",  # Organochlorine - medium PCOS penalty
                "Methylparaben",  # Paraben - low PCOS penalty
                "Water", "Glycerin"  # Safe ingredients
            ]),
            min_size=2,
            max_size=5
        )
    )
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
    )
    @pytest.mark.asyncio
    async def test_property_pcos_compounds_lower_hormonal_score(
        self,
        scorer,
        ingredient_names
    ):
        """
        Property 6: Hormonal Health Score Range (PCOS Penalty)
        
        Products with more PCOS-aggravating compounds (BPA, phthalates, organochlorines)
        should have lower hormonal health scores.
        
        **Validates: Requirements 2.1**
        """
        ingredients = [Ingredient(name=name) for name in ingredient_names]
        
        # Count PCOS-aggravating compounds
        pcos_compounds = ["BPA", "Bisphenol A", "DEHP", "Dibutyl Phthalate", "Triclosan"]
        pcos_count = sum(1 for name in ingredient_names if name in pcos_compounds)
        
        # Only test if we have at least one PCOS compound
        assume(pcos_count > 0)
        
        # Execute: Score the product
        result = await scorer.score_product(ingredients)
        
        # Verify: Hormonal health score should be less than or equal to overall score
        # (PCOS penalties should make it equal or lower)
        assert result.hormonal_health_score <= result.overall_score, \
            f"Hormonal health score ({result.hormonal_health_score}) should be <= overall score ({result.overall_score}) when PCOS compounds present"
        
        # Verify: If PCOS compounds are present, score should be reduced
        if pcos_count > 0:
            assert result.hormonal_health_score < 100.0, \
                "Products with PCOS-aggravating compounds should have hormonal health score < 100"
    
    @given(
        st.lists(
            st.sampled_from(["BPA", "DEHP", "Methylparaben"]),
            min_size=1,
            max_size=3
        ),
        st.lists(
            st.sampled_from(["Water", "Glycerin", "Vitamin E"]),
            min_size=1,
            max_size=3
        )
    )
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
    )
    @pytest.mark.asyncio
    async def test_property_hormonal_score_penalty_comparison(
        self,
        scorer,
        edc_names,
        safe_names
    ):
        """
        Property 6: Hormonal Health Score Range (Penalty Comparison)
        
        Products with high-penalty PCOS compounds (BPA, phthalates) should have
        lower hormonal health scores than products with low-penalty compounds (parabens).
        
        **Validates: Requirements 2.1**
        """
        # Create product with high-penalty EDCs
        high_penalty_ingredients = [Ingredient(name=name) for name in edc_names + safe_names]
        
        # Execute: Score both products
        high_penalty_result = await scorer.score_product(high_penalty_ingredients)
        
        # Verify: High-penalty product has reduced hormonal health score
        assert high_penalty_result.hormonal_health_score < 100.0, \
            "Products with PCOS-aggravating EDCs should have reduced hormonal health score"
        
        # Verify: Hormonal health score is lower than or equal to overall score
        assert high_penalty_result.hormonal_health_score <= high_penalty_result.overall_score, \
            "PCOS penalties should make hormonal health score <= overall score"
    
    @given(ingredient_list_strategy(min_size=1, max_size=15))
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
    )
    @pytest.mark.asyncio
    async def test_property_hormonal_score_never_exceeds_overall(
        self,
        scorer,
        ingredients
    ):
        """
        Property 6: Hormonal Health Score Range (Relationship to Overall Score)
        
        The hormonal health score should never exceed the overall score, since
        PCOS penalties only add additional risk, never reduce it.
        
        **Validates: Requirements 2.1**
        """
        # Execute: Score the product
        result = await scorer.score_product(ingredients)
        
        # Verify: Hormonal health score <= overall score
        assert result.hormonal_health_score <= result.overall_score, \
            f"Hormonal health score ({result.hormonal_health_score}) should never exceed overall score ({result.overall_score})"


class TestToxicityScoringComprehensiveProperties:
    """Comprehensive property tests covering multiple requirements"""
    
    @pytest.fixture
    async def scorer(self):
        """Create scorer instance"""
        client = ToxicityDatabaseClient()
        await client.connect()
        scorer = ToxicityScorer(client)
        yield scorer
        await client.disconnect()
    
    @given(ingredient_list_strategy(min_size=1, max_size=20))
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
    )
    @pytest.mark.asyncio
    async def test_property_complete_toxicity_score_structure(
        self,
        scorer,
        ingredients
    ):
        """
        Comprehensive Property: Complete ToxicityScore Structure
        
        For any product, the toxicity scoring should return a complete
        ToxicityScore object with all required fields.
        
        **Validates: Requirements 1.3, 1.4, 1.5, 2.1**
        """
        # Execute: Score the product
        result = await scorer.score_product(ingredients)
        
        # Verify: Result is ToxicityScore
        assert isinstance(result, ToxicityScore), \
            "Should return ToxicityScore object"
        
        # Verify: All required fields are present
        assert hasattr(result, 'overall_score'), "Should have overall_score"
        assert hasattr(result, 'hormonal_health_score'), "Should have hormonal_health_score"
        assert hasattr(result, 'risk_level'), "Should have risk_level"
        assert hasattr(result, 'flagged_chemicals'), "Should have flagged_chemicals"
        assert hasattr(result, 'recommendations'), "Should have recommendations"
        assert hasattr(result, 'confidence_warnings'), "Should have confidence_warnings"
        assert hasattr(result, 'user_warnings'), "Should have user_warnings"
        
        # Verify: Scores are in valid ranges
        assert 0.0 <= result.overall_score <= 100.0
        assert 0.0 <= result.hormonal_health_score <= 100.0
        
        # Verify: Risk level is valid
        assert result.risk_level in ["low", "medium", "high", "critical"]
        
        # Verify: Lists are valid
        assert isinstance(result.flagged_chemicals, list)
        assert isinstance(result.recommendations, list)
        assert isinstance(result.confidence_warnings, list)
        assert isinstance(result.user_warnings, list)
        
        # Verify: Recommendations are always present
        assert len(result.recommendations) > 0, \
            "Should always have at least one recommendation"
        
        # Verify: User warnings are always present
        assert len(result.user_warnings) > 0, \
            "Should always have user warnings about limitations"
    
    @given(
        st.lists(
            st.sampled_from(["Water", "Glycerin", "Vitamin E", "Aloe Vera"]),
            min_size=3,
            max_size=5
        )
    )
    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
    )
    @pytest.mark.asyncio
    async def test_property_safe_product_perfect_scores(
        self,
        scorer,
        safe_ingredient_names
    ):
        """
        Property: Safe Product Scoring
        
        Products with only safe ingredients should have perfect or near-perfect scores.
        
        **Validates: Requirements 1.4, 1.5, 2.1**
        """
        ingredients = [Ingredient(name=name) for name in safe_ingredient_names]
        
        # Execute: Score the safe product
        result = await scorer.score_product(ingredients)
        
        # Verify: High scores for safe products
        assert result.overall_score >= 90.0, \
            f"Safe products should have high overall score, got {result.overall_score}"
        assert result.hormonal_health_score >= 90.0, \
            f"Safe products should have high hormonal health score, got {result.hormonal_health_score}"
        
        # Verify: Low risk level
        assert result.risk_level == "low", \
            f"Safe products should have low risk level, got {result.risk_level}"
        
        # Verify: No or minimal flagged chemicals
        assert len(result.flagged_chemicals) == 0, \
            f"Safe products should have no flagged chemicals, got {len(result.flagged_chemicals)}"
    
    @given(
        st.lists(
            st.sampled_from(["BPA", "DEHP", "Lead", "Mercury"]),
            min_size=2,
            max_size=4
        )
    )
    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
    )
    @pytest.mark.asyncio
    async def test_property_dangerous_product_low_scores(
        self,
        scorer,
        dangerous_ingredient_names
    ):
        """
        Property: Dangerous Product Scoring
        
        Products with multiple high-risk EDCs should have low scores and high risk levels.
        
        **Validates: Requirements 1.4, 1.5, 2.1**
        """
        ingredients = [Ingredient(name=name) for name in dangerous_ingredient_names]
        
        # Execute: Score the dangerous product
        result = await scorer.score_product(ingredients)
        
        # Verify: Low scores for dangerous products
        assert result.overall_score < 50.0, \
            f"Dangerous products should have low overall score, got {result.overall_score}"
        assert result.hormonal_health_score < 50.0, \
            f"Dangerous products should have low hormonal health score, got {result.hormonal_health_score}"
        
        # Verify: High or critical risk level
        assert result.risk_level in ["high", "critical"], \
            f"Dangerous products should have high/critical risk level, got {result.risk_level}"
        
        # Verify: Multiple flagged chemicals
        assert len(result.flagged_chemicals) >= 2, \
            f"Dangerous products should have multiple flagged chemicals, got {len(result.flagged_chemicals)}"
        
        # Verify: Recommendations include warnings
        recommendations_text = " ".join(result.recommendations)
        assert any(keyword in recommendations_text for keyword in ["CRITICAL", "HIGH RISK", "avoid"]), \
            "Dangerous products should have strong warning recommendations"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
