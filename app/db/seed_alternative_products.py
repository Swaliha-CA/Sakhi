"""Seed script for alternative products database"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, AlternativeProduct
from app.core.config import settings
from app.core.logging import logger


# Sample alternative products data
ALTERNATIVE_PRODUCTS = [
    # Cosmetics - Face Care
    {
        "product_id": "ALT-COSM-001",
        "name": "Himalaya Herbals Nourishing Skin Cream",
        "brand": "Himalaya",
        "category": "cosmetic",
        "hormonal_health_score": 85.0,
        "overall_score": 82.0,
        "description": "Natural face cream with aloe vera and winter cherry, free from parabens and phthalates",
        "key_ingredients": ["Aloe Vera", "Winter Cherry", "Indian Kino Tree"],
        "free_from": ["paraben", "phthalate", "bpa"],
        "price_range": "budget",
        "availability": ["all_india"],
        "online_available": True,
        "purchase_links": ["https://www.amazon.in", "https://www.nykaa.com"],
        "certifications": ["Dermatologically Tested", "Cruelty Free"],
        "tags": ["natural", "ayurvedic", "face_care"]
    },
    {
        "product_id": "ALT-COSM-002",
        "name": "Forest Essentials Facial Cleanser",
        "brand": "Forest Essentials",
        "category": "cosmetic",
        "hormonal_health_score": 92.0,
        "overall_score": 90.0,
        "description": "Luxury ayurvedic facial cleanser with pure essential oils, completely toxin-free",
        "key_ingredients": ["Sandalwood", "Rose Water", "Turmeric"],
        "free_from": ["paraben", "phthalate", "bpa", "pfas", "organochlorine"],
        "price_range": "premium",
        "availability": ["all_india"],
        "online_available": True,
        "purchase_links": ["https://www.forestessentialsindia.com", "https://www.nykaa.com"],
        "certifications": ["Organic", "Cruelty Free", "Vegan"],
        "tags": ["luxury", "ayurvedic", "face_care", "cleanser"]
    },
    {
        "product_id": "ALT-COSM-003",
        "name": "Biotique Bio Almond Oil Nourishing Body Lotion",
        "brand": "Biotique",
        "category": "cosmetic",
        "hormonal_health_score": 78.0,
        "overall_score": 76.0,
        "description": "Natural body lotion with almond oil and pure herbs",
        "key_ingredients": ["Almond Oil", "Margosa", "Coconut Oil"],
        "free_from": ["paraben", "phthalate"],
        "price_range": "mid-range",
        "availability": ["all_india"],
        "online_available": True,
        "purchase_links": ["https://www.amazon.in", "https://www.flipkart.com"],
        "certifications": ["Dermatologically Tested"],
        "tags": ["natural", "body_care", "moisturizer"]
    },
    
    # Personal Care - Hair Care
    {
        "product_id": "ALT-PERS-001",
        "name": "Khadi Natural Herbal Shampoo",
        "brand": "Khadi Natural",
        "category": "personal_care",
        "hormonal_health_score": 88.0,
        "overall_score": 86.0,
        "description": "Herbal shampoo with amla, reetha, and shikakai, free from sulfates and parabens",
        "key_ingredients": ["Amla", "Reetha", "Shikakai", "Bhringraj"],
        "free_from": ["paraben", "phthalate", "organochlorine"],
        "price_range": "budget",
        "availability": ["all_india"],
        "online_available": True,
        "purchase_links": ["https://www.amazon.in", "https://www.khadinatural.com"],
        "certifications": ["Herbal", "Cruelty Free"],
        "tags": ["natural", "hair_care", "shampoo", "ayurvedic"]
    },
    {
        "product_id": "ALT-PERS-002",
        "name": "Mama Earth Onion Hair Oil",
        "brand": "Mama Earth",
        "category": "personal_care",
        "hormonal_health_score": 90.0,
        "overall_score": 88.0,
        "description": "Toxin-free hair oil with onion and plant keratin for hair growth",
        "key_ingredients": ["Onion Oil", "Plant Keratin", "Redensyl"],
        "free_from": ["paraben", "phthalate", "bpa", "heavy_metal"],
        "price_range": "mid-range",
        "availability": ["all_india"],
        "online_available": True,
        "purchase_links": ["https://www.mamaearth.in", "https://www.amazon.in"],
        "certifications": ["Dermatologically Tested", "Made Safe Certified"],
        "tags": ["toxin_free", "hair_care", "hair_oil"]
    },
    
    # Personal Care - Hygiene
    {
        "product_id": "ALT-PERS-003",
        "name": "Sirona Natural Intimate Wash",
        "brand": "Sirona",
        "category": "personal_care",
        "hormonal_health_score": 87.0,
        "overall_score": 85.0,
        "description": "pH-balanced intimate wash with natural ingredients, gynecologist approved",
        "key_ingredients": ["Tea Tree Oil", "Lactic Acid", "Sea Buckthorn"],
        "free_from": ["paraben", "phthalate", "organochlorine"],
        "price_range": "mid-range",
        "availability": ["all_india"],
        "online_available": True,
        "purchase_links": ["https://www.sironaindia.com", "https://www.amazon.in"],
        "certifications": ["Gynecologist Approved", "Dermatologically Tested"],
        "tags": ["intimate_care", "hygiene", "natural"]
    },
    {
        "product_id": "ALT-PERS-004",
        "name": "Plum BodyLovin' Vanilla Vibes Body Wash",
        "brand": "Plum",
        "category": "personal_care",
        "hormonal_health_score": 84.0,
        "overall_score": 82.0,
        "description": "100% vegan body wash with vanilla and coconut, free from harmful chemicals",
        "key_ingredients": ["Vanilla Extract", "Coconut Oil", "Glycerin"],
        "free_from": ["paraben", "phthalate", "bpa"],
        "price_range": "mid-range",
        "availability": ["all_india"],
        "online_available": True,
        "purchase_links": ["https://www.plumgoodness.com", "https://www.nykaa.com"],
        "certifications": ["Vegan", "Cruelty Free", "PETA Certified"],
        "tags": ["vegan", "body_care", "body_wash"]
    },
    
    # Food - Cooking Oil
    {
        "product_id": "ALT-FOOD-001",
        "name": "24 Mantra Organic Cold Pressed Coconut Oil",
        "brand": "24 Mantra",
        "category": "food",
        "hormonal_health_score": 95.0,
        "overall_score": 94.0,
        "description": "Certified organic cold-pressed coconut oil, free from chemicals and preservatives",
        "key_ingredients": ["100% Organic Coconut"],
        "free_from": ["paraben", "phthalate", "bpa", "heavy_metal", "organochlorine"],
        "price_range": "mid-range",
        "availability": ["all_india"],
        "online_available": True,
        "purchase_links": ["https://www.amazon.in", "https://www.bigbasket.com"],
        "certifications": ["USDA Organic", "India Organic", "Non-GMO"],
        "tags": ["organic", "cooking_oil", "coconut_oil"]
    },
    {
        "product_id": "ALT-FOOD-002",
        "name": "Conscious Food Organic Mustard Oil",
        "brand": "Conscious Food",
        "category": "food",
        "hormonal_health_score": 93.0,
        "overall_score": 92.0,
        "description": "Cold-pressed organic mustard oil, traditionally extracted",
        "key_ingredients": ["100% Organic Mustard Seeds"],
        "free_from": ["paraben", "phthalate", "bpa", "heavy_metal"],
        "price_range": "mid-range",
        "availability": ["north", "east", "central"],
        "online_available": True,
        "purchase_links": ["https://www.amazon.in", "https://www.consciousfood.com"],
        "certifications": ["India Organic", "Non-GMO"],
        "tags": ["organic", "cooking_oil", "mustard_oil", "traditional"]
    },
    
    # Food - Packaged Foods
    {
        "product_id": "ALT-FOOD-003",
        "name": "Organic India Tulsi Green Tea",
        "brand": "Organic India",
        "category": "food",
        "hormonal_health_score": 96.0,
        "overall_score": 95.0,
        "description": "Certified organic tulsi green tea with no additives or preservatives",
        "key_ingredients": ["Organic Tulsi", "Organic Green Tea"],
        "free_from": ["paraben", "phthalate", "bpa", "heavy_metal", "organochlorine"],
        "price_range": "mid-range",
        "availability": ["all_india"],
        "online_available": True,
        "purchase_links": ["https://www.organicindia.com", "https://www.amazon.in"],
        "certifications": ["USDA Organic", "India Organic", "Fair Trade"],
        "tags": ["organic", "tea", "herbal", "tulsi"]
    },
    {
        "product_id": "ALT-FOOD-004",
        "name": "Slurrp Farm Millet Pancake Mix",
        "brand": "Slurrp Farm",
        "category": "food",
        "hormonal_health_score": 89.0,
        "overall_score": 87.0,
        "description": "Healthy millet-based pancake mix with no preservatives or artificial colors",
        "key_ingredients": ["Ragi", "Jowar", "Banana Powder"],
        "free_from": ["paraben", "phthalate", "bpa"],
        "price_range": "mid-range",
        "availability": ["all_india"],
        "online_available": True,
        "purchase_links": ["https://www.slurrpfarm.com", "https://www.amazon.in"],
        "certifications": ["No Preservatives", "No Artificial Colors"],
        "tags": ["healthy", "millet", "breakfast", "kids_food"]
    },
    
    # Household - Cleaning Products
    {
        "product_id": "ALT-HOUSE-001",
        "name": "Eco365 Natural Floor Cleaner",
        "brand": "Eco365",
        "category": "household",
        "hormonal_health_score": 91.0,
        "overall_score": 89.0,
        "description": "Plant-based floor cleaner with essential oils, biodegradable formula",
        "key_ingredients": ["Plant-Based Surfactants", "Lemon Essential Oil", "Neem Extract"],
        "free_from": ["paraben", "phthalate", "organochlorine", "pfas"],
        "price_range": "mid-range",
        "availability": ["all_india"],
        "online_available": True,
        "purchase_links": ["https://www.amazon.in"],
        "certifications": ["Biodegradable", "Eco-Friendly"],
        "tags": ["natural", "cleaning", "floor_cleaner", "eco_friendly"]
    },
    {
        "product_id": "ALT-HOUSE-002",
        "name": "The Better Home Natural Dish Wash Gel",
        "brand": "The Better Home",
        "category": "household",
        "hormonal_health_score": 88.0,
        "overall_score": 86.0,
        "description": "Plant-powered dish wash gel with no harsh chemicals",
        "key_ingredients": ["Plant-Based Cleaners", "Lime Essential Oil"],
        "free_from": ["paraben", "phthalate", "organochlorine"],
        "price_range": "budget",
        "availability": ["all_india"],
        "online_available": True,
        "purchase_links": ["https://www.thebetterhome.in", "https://www.amazon.in"],
        "certifications": ["Plant-Based", "Biodegradable"],
        "tags": ["natural", "cleaning", "dish_wash", "plant_based"]
    },
    {
        "product_id": "ALT-HOUSE-003",
        "name": "Puracy Natural Laundry Detergent",
        "brand": "Puracy",
        "category": "household",
        "hormonal_health_score": 90.0,
        "overall_score": 88.0,
        "description": "Hypoallergenic laundry detergent with plant-based enzymes",
        "key_ingredients": ["Plant-Based Enzymes", "Coconut-Based Cleaners"],
        "free_from": ["paraben", "phthalate", "organochlorine", "pfas"],
        "price_range": "premium",
        "availability": ["all_india"],
        "online_available": True,
        "purchase_links": ["https://www.amazon.in"],
        "certifications": ["Hypoallergenic", "Biodegradable", "EPA Safer Choice"],
        "tags": ["natural", "laundry", "hypoallergenic", "plant_based"]
    },
]


async def seed_alternative_products():
    """Seed the alternative products database"""
    # Create async engine using SQLite
    database_url = f"sqlite+aiosqlite:///{settings.SQLITE_DB_PATH}"
    
    engine = create_async_engine(
        database_url,
        echo=True
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        # Check if products already exist
        from sqlalchemy import select
        result = await session.execute(select(AlternativeProduct))
        existing = result.scalars().all()
        
        if existing:
            logger.info(f"Database already contains {len(existing)} products. Skipping seed.")
            return
        
        # Add products
        logger.info(f"Seeding {len(ALTERNATIVE_PRODUCTS)} alternative products...")
        
        for product_data in ALTERNATIVE_PRODUCTS:
            product = AlternativeProduct(**product_data)
            session.add(product)
        
        await session.commit()
        logger.info("Successfully seeded alternative products database")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_alternative_products())
