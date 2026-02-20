"""
Database migration: Add Heritage Recipes table

Adds support for voice-recorded heritage recipes feature:
- heritage_recipes: Traditional recipes with voice recordings and nutritional profiles

Run with: python -m app.db.migrations.add_heritage_recipes
"""
from sqlalchemy import create_engine, text
from app.core.config import settings
from app.core.logging import logger


def upgrade():
    """Create heritage_recipes table"""
    database_url = f"sqlite:///{settings.SQLITE_DB_PATH}"
    engine = create_engine(database_url)
    
    with engine.connect() as conn:
        # Create heritage_recipes table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS heritage_recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id VARCHAR(100) UNIQUE NOT NULL,
                name VARCHAR(255) NOT NULL,
                region VARCHAR(20) NOT NULL,
                ingredients TEXT NOT NULL,
                preparation TEXT NOT NULL,
                nutritional_benefits TEXT NOT NULL,
                micronutrients TEXT NOT NULL,
                voice_recording_url VARCHAR(500),
                contributed_by VARCHAR(255),
                season VARCHAR(20),
                tags TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                synced_to_cloud BOOLEAN NOT NULL DEFAULT 0
            )
        """))
        
        # Create indexes for heritage_recipes
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_heritage_recipes_recipe_id 
            ON heritage_recipes(recipe_id)
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_heritage_recipes_region 
            ON heritage_recipes(region)
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_heritage_recipes_contributed_by 
            ON heritage_recipes(contributed_by)
        """))
        
        conn.commit()
        logger.info("Successfully created heritage_recipes table")


def downgrade():
    """Drop heritage_recipes table"""
    database_url = f"sqlite:///{settings.SQLITE_DB_PATH}"
    engine = create_engine(database_url)
    
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS heritage_recipes"))
        conn.commit()
        logger.info("Successfully dropped heritage_recipes table")


if __name__ == "__main__":
    logger.info("Running heritage recipes migration...")
    upgrade()
    logger.info("Migration completed successfully!")
