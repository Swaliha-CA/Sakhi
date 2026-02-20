"""
Manual test script for buddy system heritage recipes feature

Tests:
1. Adding a heritage recipe
2. Retrieving family recipes
3. Getting linked family members
"""
from app.db.sqlite_manager import get_db
from app.services.buddy_system_service import get_buddy_system_service


def test_heritage_recipes():
    """Test heritage recipe functionality"""
    print("\n=== Testing Heritage Recipe Feature ===\n")
    
    # Get service and database
    service = get_buddy_system_service()
    db = next(get_db())
    
    try:
        # Test 1: Add a heritage recipe
        print("Test 1: Adding a heritage recipe...")
        recipe_data = {
            "user_id": 1,  # Assuming user 1 exists
            "name": "Grandmother's Ragi Kanji",
            "region": "south",
            "ingredients": [
                "1 cup ragi flour",
                "4 cups water",
                "Salt to taste",
                "1 tsp ghee"
            ],
            "preparation": "Mix ragi flour with water. Cook on low heat for 15 minutes, stirring continuously. Add salt and ghee.",
            "nutritional_benefits": [
                "Rich in calcium",
                "High in iron",
                "Good for bone health",
                "Helps with anemia"
            ],
            "micronutrients": {
                "iron_mg": 3.9,
                "calcium_mg": 344,
                "protein_g": 7.3,
                "fiber_g": 11.5
            },
            "voice_recording_url": "https://example.com/recordings/ragi_kanji.mp3",
            "season": "monsoon",
            "tags": ["postpartum", "iron-rich", "traditional", "south-indian"]
        }
        
        result = service.add_heritage_recipe(db=db, **recipe_data)
        print(f"✓ Recipe added successfully: {result['recipe_id']}")
        print(f"  Name: {result['name']}")
        print(f"  Region: {result['region']}")
        print(f"  Contributed by: {result['contributed_by']}")
        
        # Test 2: Retrieve family recipes
        print("\nTest 2: Retrieving family recipes...")
        recipes = service.get_family_recipes(db=db, user_id=1)
        print(f"✓ Found {len(recipes)} recipes in family knowledge base")
        for recipe in recipes[:3]:  # Show first 3
            print(f"  - {recipe['name']} ({recipe['region']})")
            if recipe.get('voice_recording_url'):
                print(f"    Voice recording: {recipe['voice_recording_url']}")
        
        # Test 3: Get linked family members
        print("\nTest 3: Getting linked family members...")
        linked_members = service.get_linked_family_members(db=db, user_id=1)
        print(f"✓ User 1 has {len(linked_members)} linked family members")
        if linked_members:
            print(f"  Linked IDs: {linked_members}")
        else:
            print("  (No linked family members yet)")
        
        print("\n=== All tests passed! ===\n")
        
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()


if __name__ == "__main__":
    test_heritage_recipes()
