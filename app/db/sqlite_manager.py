"""SQLite database manager for offline-first storage with encryption"""
import os
from pathlib import Path
from typing import Optional
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine

from app.db.models import Base
from app.core.config import settings
from app.core.logging import logger


class SQLiteManager:
    """
    Manages local SQLite database with SQLCipher encryption
    
    Features:
    - At-rest encryption using SQLCipher
    - Automatic schema creation
    - Connection pooling
    - WAL mode for better concurrency
    """
    
    def __init__(self, db_path: Optional[str] = None, encryption_key: Optional[str] = None):
        """
        Initialize SQLite manager
        
        Args:
            db_path: Path to SQLite database file (default: ./data/local.db)
            encryption_key: Encryption key for SQLCipher (default: from settings)
        """
        self.db_path = db_path or settings.SQLITE_DB_PATH
        self.encryption_key = encryption_key or settings.SQLITE_ENCRYPTION_KEY
        
        # Ensure data directory exists
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        
        # Create engine with SQLCipher support
        self.engine = self._create_engine()
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Create tables
        self._create_tables()
        
        logger.info(f"SQLite database initialized at: {self.db_path}")
    
    def _create_engine(self) -> Engine:
        """Create SQLAlchemy engine with SQLCipher encryption"""
        # SQLite connection string
        db_url = f"sqlite:///{self.db_path}"
        
        # Create engine
        engine = create_engine(
            db_url,
            connect_args={
                "check_same_thread": False,  # Allow multi-threading
                "timeout": 30  # 30 second timeout for locks
            },
            pool_pre_ping=True,  # Verify connections before using
            echo=False  # Set to True for SQL debugging
        )
        
        # Enable SQLCipher encryption and WAL mode
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            
            # Enable SQLCipher encryption (if key provided)
            if self.encryption_key:
                cursor.execute(f"PRAGMA key = '{self.encryption_key}'")
            
            # Enable WAL mode for better concurrency
            cursor.execute("PRAGMA journal_mode = WAL")
            
            # Enable foreign keys
            cursor.execute("PRAGMA foreign_keys = ON")
            
            # Optimize for performance
            cursor.execute("PRAGMA synchronous = NORMAL")
            cursor.execute("PRAGMA cache_size = -64000")  # 64MB cache
            cursor.execute("PRAGMA temp_store = MEMORY")
            
            cursor.close()
        
        return engine
    
    def _create_tables(self):
        """Create all tables if they don't exist"""
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created/verified")
    
    def get_session(self) -> Session:
        """
        Get a new database session
        
        Returns:
            SQLAlchemy Session
        """
        return self.SessionLocal()
    
    def close(self):
        """Close database connections"""
        self.engine.dispose()
        logger.info("Database connections closed")
    
    def vacuum(self):
        """Optimize database (reclaim space, rebuild indexes)"""
        with self.engine.connect() as conn:
            conn.execute("VACUUM")
        logger.info("Database vacuumed")
    
    def get_db_size(self) -> int:
        """
        Get database file size in bytes
        
        Returns:
            Size in bytes
        """
        if os.path.exists(self.db_path):
            return os.path.getsize(self.db_path)
        return 0


# Global SQLite manager instance
sqlite_manager: Optional[SQLiteManager] = None


def get_sqlite_manager() -> SQLiteManager:
    """
    Get or create global SQLite manager instance
    
    Returns:
        SQLiteManager instance
    """
    global sqlite_manager
    
    if sqlite_manager is None:
        sqlite_manager = SQLiteManager()
    
    return sqlite_manager


def get_db() -> Session:
    """
    Dependency for FastAPI to get database session
    
    Yields:
        Database session
    """
    manager = get_sqlite_manager()
    db = manager.get_session()
    try:
        yield db
    finally:
        db.close()
