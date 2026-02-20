"""
Database migration: Add shopping list and notification tables

This migration adds:
- shopping_list_items table for user shopping lists
- product_notifications table for new product alerts
"""
from sqlalchemy import create_engine, text
from app.core.config import settings
from app.core.logging import logger


def upgrade():
    """Add shopping list and notification tables"""
    engine = create_engine(f"sqlite:///{settings.SQLITE_DB_PATH}")
    
    with engine.connect() as conn:
        # Create shopping_list_items table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS shopping_list_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_id VARCHAR(100) NOT NULL,
                replaced_product_name VARCHAR(255),
                replaced_product_category VARCHAR(50),
                notes TEXT,
                priority INTEGER DEFAULT 0,
                added_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                device_id VARCHAR(255) NOT NULL,
                synced_to_cloud BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (product_id) REFERENCES alternative_products(product_id)
            )
        """))
        
        # Create indexes for shopping_list_items
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_shopping_list_user_id 
            ON shopping_list_items(user_id)
        """))
        
        # Create product_notifications table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS product_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_id VARCHAR(100) NOT NULL,
                notification_type VARCHAR(50) NOT NULL,
                title VARCHAR(255) NOT NULL,
                message TEXT NOT NULL,
                related_scan_id INTEGER,
                related_category VARCHAR(50) NOT NULL,
                sent BOOLEAN DEFAULT 0,
                read BOOLEAN DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                sent_at TIMESTAMP,
                read_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (product_id) REFERENCES alternative_products(product_id),
                FOREIGN KEY (related_scan_id) REFERENCES product_scans(id)
            )
        """))
        
        # Create indexes for product_notifications
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_notifications_user_id 
            ON product_notifications(user_id)
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_notifications_read 
            ON product_notifications(user_id, read)
        """))
        
        conn.commit()
        
    logger.info("Migration completed: Added shopping_list_items and product_notifications tables")


def downgrade():
    """Remove shopping list and notification tables"""
    engine = create_engine(f"sqlite:///{settings.SQLITE_DB_PATH}")
    
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS product_notifications"))
        conn.execute(text("DROP TABLE IF EXISTS shopping_list_items"))
        conn.commit()
        
    logger.info("Migration rolled back: Removed shopping_list_items and product_notifications tables")


if __name__ == "__main__":
    upgrade()
