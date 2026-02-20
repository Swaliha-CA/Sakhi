"""Property-based tests for Sutika Paricharya service using Hypothesis

**Validates: Requirements 5.2, 5.4, 5.5, 14.1, 14.2, 14.3, 14.4, 14.5**

Property 24: Regional Food Recommendation Adaptation
Property 25: Nutritional Equivalence Across Regions
Property 26: Heritage Recipe Storage and Tagging
Property 27: Deficiency-Based Food Suggestions
"""
import pytest
from hypothesis import given, strategies as st, settings, assume
from hypothesis import Phase

from app.services.sutika_service import (
    SutikaParicharya,
    Region,
    Season,
    RecoveryPhase,
    HeritageRecipe,
    DailyCheckIn
)


# Custom strategies for generating test data

@st.composite
def region_strategy(draw):
    """Generate valid regions"""
    return draw(st.sampled_from(list(Region)))


@st.composite
def season_strategy(draw):
    """Generate valid seasons"""
    return draw(st.sampled_from(list(Season)))


@st.composite
def deficiency_list(draw):
    """Generate list of nutrient deficiencies"""
    nutrients = ["iron", "calcium", "protein", "vitamin_a", "b_vitamins", "healthy_fats"]
    num_deficiencies = draw(st.integers(min_value=0, max_value=3))
    if num_deficiencies == 0:
        return []
    return draw(st.lists(
        st.sampled_from(nutrients),
        min_size=num_deficiencies,
        max_size=num_deficiencies,
        unique=True
    ))


@st.composite
def heritage_recipe_strategy(draw):
    """Generate valid heritage recipes"""
    recipe_id = f"test_{draw(st.text(min_size=5, max_size=10, alphabet=st.characters(whitelist_categories=('Ll', 'Nd'))))}"
    name = draw(st.text(min_size=5, max_size=50))
    region = draw(region_strategy())
    
    ingredients = draw(st.lists(
        st.text(min_size=5, max_size=30),
        min_size=2,
        max_size=10
    ))
    
    preparation = draw(st.text(min_size=10, max_size=200))
    
    nutritional_benefits = draw(st.lists(
        st.text(min_size=5, max_size=50),
        min_size=1,
        max_size=5
    ))
    
    # Micronutrients with levels
    nutrient_levels = ["low", "medium", "high", "very_high"]
    micronutrients = {
        "iron": draw(st.sampled_from(nutrient_levels)),
        "calcium": draw(st.sampled_from(nutrient_levels)),
        "protein": draw(st.sampled_from(nutrient_levels))
    }
    
    season = draw(st.one_of(st.none(), season_strategy()))
    tags = draw(st.lists(st.text(min_size=3, max_size=15), min_size=0, max_size=5))
    
    return HeritageRecipe(
        recipe_id=recipe_id,
        name=name,
        region=region,
        ingredients=ingredients,
        preparation=preparation,
        nutritional_benefits=nutritional_benefits,
        micronutrients=micronutrients,
        season=season,
        tags=tags
    )


@st.composite
def daily_checkin_strategy(draw):
    """Generate valid daily check-ins"""
    day_number = draw(st.integers(min_value=1, max_value=45))
    
    # Determine phase based on day number
    if day_number <= 15:
        phase = RecoveryPhase.PHASE_1
    elif day_number <= 30:
        phase = RecoveryPhase.PHASE_2
    else:
        phase = RecoveryPhase.PHASE_3
    
    return DailyCheckIn(
        user_id=draw(st.integers(min_value=1, max_value=1000)),
        day_number=day_number,
        recovery_phase=phase,
        energy_level=draw(st.integers(min_value=1, max_value=10)),
        pain_level=draw(st.integers(min_value=1, max_value=10)),
        mood_score=draw(st.integers(min_value=1, max_value=10)),
        breastfeeding_issues=draw(st.booleans()),
        bleeding_status=draw(st.sampled_from(["normal", "heavy", "minimal"])),
        notes=draw(st.one_of(st.none(), st.text(max_size=200)))
    )


# Property Tests

# Feature: women-health-ledger, Property 24: Regional Food Recommendation Adaptation
@given(
    region=region_strategy(),
    season=st.one_of(st.none(), season_strategy()),
    deficiencies=deficiency_list()
)
@settings(max_examples=20, deadline=None)
def test_property_24_regional_food_recommendations(region, season, deficiencies):
    """
    Property 24: Regional Food Recommendation Adaptation
    
    For any nutritional recommendation, the suggested foods should match the user's 
    region (North/South/East/West/Central/Northeast India) and be appropriate for 
    the current season.
    
    **Validates: Requirements 5.2, 14.1, 14.3, 14.4**
    """
    service = SutikaParicharya()
    
    # Get recommendations
    recommendations = service.get_regional_recommendations(
        region=region,
        deficiencies=deficiencies,
        season=season
    )
    
    # Property: All recommendations should match region or be universal (CENTRAL)
    for recipe in recommendations:
        assert recipe.region == region or recipe.region == Region.CENTRAL, \
            f"Recipe {recipe.name} has region {recipe.region}, expected {region} or CENTRAL"
    
    # Property: If season specified, recipes should match season or be year-round (None)
    if season:
        for recipe in recommendations:
            assert recipe.season is None or recipe.season == season, \
                f"Recipe {recipe.name} has season {recipe.season}, expected {season} or None"
    
    # Property: Recommendations should be a list (possibly empty)
    assert isinstance(recommendations, list)


# Feature: women-health-ledger, Property 25: Nutritional Equivalence Across Regions
@given(
    deficiency=st.sampled_from(["iron", "calcium", "protein", "vitamin_a"])
)
@settings(max_examples=20, deadline=None)
def test_property_25_nutritional_equivalence_across_regions(deficiency):
    """
    Property 25: Nutritional Equivalence Across Regions
    
    For any nutritional need (e.g., iron deficiency), the system should provide 
    regionally appropriate food suggestions that are nutritionally equivalent across 
    different Indian regions.
    
    **Validates: Requirements 14.2**
    """
    service = SutikaParicharya()
    
    # Get recommendations for different regions with same deficiency
    north_recs = service.get_regional_recommendations(
        region=Region.NORTH,
        deficiencies=[deficiency]
    )
    
    south_recs = service.get_regional_recommendations(
        region=Region.SOUTH,
        deficiencies=[deficiency]
    )
    
    # Property: Both regions should have recommendations addressing the deficiency
    # (either region-specific or universal recipes)
    assert len(north_recs) > 0, f"No recommendations for {deficiency} in North region"
    assert len(south_recs) > 0, f"No recommendations for {deficiency} in South region"
    
    # Property: Recommendations should address the deficiency
    # Check that at least one recipe in each region has high/very_high level of the nutrient
    north_addresses = any(
        recipe.micronutrients.get(deficiency) in ["high", "very_high"]
        for recipe in north_recs
    )
    south_addresses = any(
        recipe.micronutrients.get(deficiency) in ["high", "very_high"]
        for recipe in south_recs
    )
    
    assert north_addresses, f"North recommendations don't address {deficiency} deficiency"
    assert south_addresses, f"South recommendations don't address {deficiency} deficiency"


# Feature: women-health-ledger, Property 26: Heritage Recipe Storage and Tagging
@given(recipe=heritage_recipe_strategy())
@settings(max_examples=20, deadline=None)
def test_property_26_heritage_recipe_storage_and_tagging(recipe):
    """
    Property 26: Heritage Recipe Storage and Tagging
    
    For any voice-recorded heritage recipe, it should be stored in the family's shared 
    knowledge base with tags for region and nutritional profile, and should be 
    retrievable by any linked family member.
    
    **Validates: Requirements 5.4, 10.3, 14.5**
    """
    service = SutikaParicharya()
    
    # Add recipe
    service.add_recipe(recipe)
    
    # Property: Recipe should be stored and retrievable
    assert recipe.recipe_id in service.recipes, \
        f"Recipe {recipe.recipe_id} not found in service"
    
    stored_recipe = service.recipes[recipe.recipe_id]
    
    # Property: Stored recipe should match original
    assert stored_recipe.recipe_id == recipe.recipe_id
    assert stored_recipe.name == recipe.name
    assert stored_recipe.region == recipe.region
    
    # Property: Recipe should have region tag (implicit or explicit)
    assert stored_recipe.region is not None
    
    # Property: Recipe should have micronutrient profile
    assert isinstance(stored_recipe.micronutrients, dict)
    assert len(stored_recipe.micronutrients) > 0
    
    # Property: Recipe should be retrievable through regional recommendations
    regional_recs = service.get_regional_recommendations(region=recipe.region)
    recipe_ids = [r.recipe_id for r in regional_recs]
    assert recipe.recipe_id in recipe_ids, \
        f"Recipe {recipe.recipe_id} not retrievable through regional recommendations"


# Feature: women-health-ledger, Property 27: Deficiency-Based Food Suggestions
@given(
    region=region_strategy(),
    deficiencies=deficiency_list()
)
@settings(max_examples=20, deadline=None)
def test_property_27_deficiency_based_food_suggestions(region, deficiencies):
    """
    Property 27: Deficiency-Based Food Suggestions
    
    For any detected nutritional deficiency, the system should suggest region-appropriate 
    foods that are rich in the deficient nutrient.
    
    **Validates: Requirements 5.5**
    """
    service = SutikaParicharya()
    
    # Skip if no deficiencies
    assume(len(deficiencies) > 0)
    
    # Get recommendations
    recommendations = service.get_regional_recommendations(
        region=region,
        deficiencies=deficiencies
    )
    
    # Property: Should return recommendations
    assert len(recommendations) > 0, \
        f"No recommendations for deficiencies {deficiencies} in {region}"
    
    # Property: Recommendations addressing deficiencies should be prioritized (at the front)
    # Check first few recommendations
    if len(recommendations) > 0:
        first_recipe = recommendations[0]
        
        # At least one deficiency should be addressed by the first recipe
        addresses_deficiency = any(
            first_recipe.micronutrients.get(deficiency) in ["high", "very_high"]
            for deficiency in deficiencies
        )
        
        # If there are recipes that address deficiencies, they should be prioritized
        has_addressing_recipes = any(
            any(
                recipe.micronutrients.get(deficiency) in ["high", "very_high"]
                for deficiency in deficiencies
            )
            for recipe in recommendations
        )
        
        if has_addressing_recipes:
            assert addresses_deficiency, \
                "Recipes addressing deficiencies should be prioritized at the front"


# Additional property tests for recovery tracking

# Feature: women-health-ledger, Recovery Phase Determination
@given(day_number=st.integers(min_value=1, max_value=45))
@settings(max_examples=20, deadline=None)
def test_recovery_phase_determination(day_number):
    """
    Property: Recovery phase should be correctly determined based on day number
    
    Days 1-15: Phase 1
    Days 16-30: Phase 2
    Days 31-45: Phase 3
    """
    service = SutikaParicharya()
    
    phase = service.get_recovery_phase(day_number)
    
    # Property: Phase should match day number ranges
    if day_number <= 15:
        assert phase == RecoveryPhase.PHASE_1
    elif day_number <= 30:
        assert phase == RecoveryPhase.PHASE_2
    else:
        assert phase == RecoveryPhase.PHASE_3


# Feature: women-health-ledger, Daily Check-in Recording
@given(checkin=daily_checkin_strategy())
@settings(max_examples=20, deadline=None)
def test_daily_checkin_recording(checkin):
    """
    Property: Daily check-ins should be recorded and retrievable
    """
    service = SutikaParicharya()
    
    # Record check-in
    service.record_daily_checkin(checkin)
    
    # Property: Check-in should be stored
    assert checkin.user_id in service.check_ins
    
    user_checkins = service.check_ins[checkin.user_id]
    
    # Property: Check-in should be in user's list
    assert len(user_checkins) > 0
    
    # Property: Last check-in should match recorded one
    last_checkin = user_checkins[-1]
    assert last_checkin.user_id == checkin.user_id
    assert last_checkin.day_number == checkin.day_number
    assert last_checkin.recovery_phase == checkin.recovery_phase


# Feature: women-health-ledger, Daily Guidance Generation
@given(day_number=st.integers(min_value=1, max_value=45))
@settings(max_examples=20, deadline=None)
def test_daily_guidance_generation(day_number):
    """
    Property: Daily guidance should be generated for any day in the 45-day period
    """
    service = SutikaParicharya()
    
    guidance = service.get_daily_guidance(day_number)
    
    # Property: Guidance should contain required fields
    assert "day_number" in guidance
    assert "phase" in guidance
    assert "milestones" in guidance
    assert "activities" in guidance
    assert "diet_focus" in guidance
    
    # Property: Day number should match
    assert guidance["day_number"] == day_number
    
    # Property: Phase should be correct
    expected_phase = service.get_recovery_phase(day_number)
    assert guidance["phase"] == expected_phase.value
    
    # Property: Milestones should be a list
    assert isinstance(guidance["milestones"], list)
    assert len(guidance["milestones"]) > 0
    
    # Property: Activities should be a list
    assert isinstance(guidance["activities"], list)
    assert len(guidance["activities"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
