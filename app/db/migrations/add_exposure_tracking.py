"""
Database migration: Add EDC exposure tracking tables

Adds:
- edc_exposure_logs: Cumulative exposure tracking by time period
- exposure_alerts: Alerts for threshold violations

Run with: python -m app.db.migrations.add_exposure_tracking
"""
from sqlalchemy import create_engine, text
from app.core.config import settings
from app.core.logging import logger


def upgrade():
    """Create exposure tracking tables"""
    database_url = f"sqlite:///{settings.SQLITE_DB_PATH}"
    engine = create_engine(database_url)
    
    with engine.connect() as conn:
        # Create edc_exposure_logs table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS edc_exposure_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                period_start TIMESTAMP NOT NULL,
                period_end TIMESTAMP NOT NULL,
                period_type VARCHAR(20) NOT NULL,
                total_exposure_score REAL NOT NULL,
                exposure_by_type TEXT NOT NULL,
                exposure_by_category TEXT NOT NULL,
                epa_limit REAL NOT NULL,
                percent_of_limit REAL NOT NULL,
                status VARCHAR(20) NOT NULL,
                top_sources TEXT NOT NULL,
                scan_count INTEGER NOT NULL,
                generated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                synced_to_cloud BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """))
        
        # Create indexes for edc_exposure_logs
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_edc_exposure_logs_user_id 
            ON edc_exposure_logs(user_id)
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_edc_exposure_logs_period_start 
            ON edc_exposure_logs(period_start)
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_edc_exposure_logs_period_end 
            ON edc_exposure_logs(period_end)
        """))
        
        # Create exposure_alerts table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS exposure_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                exposure_log_id INTEGER NOT NULL,
                alert_type VARCHAR(50) NOT NULL,
                severity VARCHAR(20) NOT NULL,
                title VARCHAR(255) NOT NULL,
                message TEXT NOT NULL,
                reduction_strategies TEXT NOT NULL,
                primary_edc_sources TEXT NOT NULL,
                sent BOOLEAN DEFAULT 0,
                acknowledged BOOLEAN DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                sent_at TIMESTAMP,
                acknowledged_at TIMESTAMP,
                synced_to_cloud BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (exposure_log_id) REFERENCES edc_exposure_logs(id)
            )
        """))
        
        # Create indexes for exposure_alerts
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_exposure_alerts_user_id 
            ON exposure_alerts(user_id)
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_exposure_alerts_exposure_log_id 
            ON exposure_alerts(exposure_log_id)
        """))
        
        conn.commit()
        logger.info("Successfully created exposure tracking tables")


def downgrade():
    """Drop exposure tracking tables"""
    database_url = f"sqlite:///{settings.SQLITE_DB_PATH}"
    engine = create_engine(database_url)
    
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS exposure_alerts"))
        conn.execute(text("DROP TABLE IF EXISTS edc_exposure_logs"))
        conn.commit()
        logger.info("Successfully dropped exposure tracking tables")


if __name__ == "__main__":
    logger.info("Running exposure tracking migration...")
    upgrade()
    logger.info("Migration complete!")
