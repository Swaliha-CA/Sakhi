"""
Database migration: Add Buddy System tables

Adds support for intergenerational Buddy System feature:
- buddy_link_requests: Pending link requests requiring consent from both parties
- buddy_links: Active profile links with roles and permissions

Run with: python -m app.db.migrations.add_buddy_system
"""
from sqlalchemy import create_engine, text
from app.core.config import settings
from app.core.logging import logger


def upgrade():
    """Create buddy system tables"""
    database_url = f"sqlite:///{settings.SQLITE_DB_PATH}"
    engine = create_engine(database_url)
    
    with engine.connect() as conn:
        # Create buddy_link_requests table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS buddy_link_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                requester_id INTEGER NOT NULL,
                recipient_id INTEGER NOT NULL,
                requester_role VARCHAR(20) NOT NULL,
                recipient_role VARCHAR(20) NOT NULL,
                proposed_permissions TEXT NOT NULL,
                message TEXT,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                requested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                responded_at TIMESTAMP,
                response_message TEXT,
                FOREIGN KEY (requester_id) REFERENCES users(id),
                FOREIGN KEY (recipient_id) REFERENCES users(id)
            )
        """))
        
        # Create indexes for buddy_link_requests
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_buddy_link_requests_requester_id 
            ON buddy_link_requests(requester_id)
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_buddy_link_requests_recipient_id 
            ON buddy_link_requests(recipient_id)
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_buddy_link_requests_status 
            ON buddy_link_requests(status)
        """))
        
        # Create buddy_links table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS buddy_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                elder_id INTEGER NOT NULL,
                helper_id INTEGER NOT NULL,
                permissions TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                revoked_at TIMESTAMP,
                revoked_by INTEGER,
                revocation_reason TEXT,
                FOREIGN KEY (elder_id) REFERENCES users(id),
                FOREIGN KEY (helper_id) REFERENCES users(id),
                FOREIGN KEY (revoked_by) REFERENCES users(id)
            )
        """))
        
        # Create indexes for buddy_links
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_buddy_links_elder_id 
            ON buddy_links(elder_id)
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_buddy_links_helper_id 
            ON buddy_links(helper_id)
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_buddy_links_is_active 
            ON buddy_links(is_active)
        """))
        
        conn.commit()
        logger.info("Successfully created buddy system tables")


def downgrade():
    """Drop buddy system tables"""
    database_url = f"sqlite:///{settings.SQLITE_DB_PATH}"
    engine = create_engine(database_url)
    
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS buddy_links"))
        conn.execute(text("DROP TABLE IF EXISTS buddy_link_requests"))
        conn.commit()
        logger.info("Successfully dropped buddy system tables")


if __name__ == "__main__":
    logger.info("Running buddy system migration...")
    upgrade()
    logger.info("Migration complete!")
