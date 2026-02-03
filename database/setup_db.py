import logging
import sys
from pathlib import Path

"""
Database initialization and setup script.

Run using pixi run python database/setup_db.py
"""

# Add parent directory to path to import database module
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_manager import DatabaseManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def initialize_database():
    """Initialize the database with schema from init.sql."""
    db = DatabaseManager()

    # Read SQL file
    sql_file = Path(__file__).parent / "init.sql"
    with open(sql_file, "r") as f:
        sql_script = f.read()

    logger.info("Initializing database schema...")

    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                # Execute the entire SQL script
                cur.execute(sql_script)
        logger.info("Database schema initialized successfully!")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False


def verify_setup():
    """Verify the database setup is correct."""
    db = DatabaseManager()

    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                # Check PostGIS extension
                cur.execute(
                    "SELECT PostGIS_Version();"
                )
                postgis_version = cur.fetchone()[0]
                logger.info(f"PostGIS version: {postgis_version}")

                # Check tables
                cur.execute(
                    """
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_type = 'BASE TABLE'
                    ORDER BY table_name;
                    """
                )
                tables = [row[0] for row in cur.fetchall()]
                logger.info(f"Tables created: {', '.join(tables)}")

                # Check views
                cur.execute(
                    """
                    SELECT table_name 
                    FROM information_schema.views 
                    WHERE table_schema = 'public'
                    ORDER BY table_name;
                    """
                )
                views = [row[0] for row in cur.fetchall()]
                logger.info(f"Views created: {', '.join(views)}")

                # Check regions
                cur.execute("SELECT COUNT(*) FROM regions;")
                region_count = cur.fetchone()[0]
                logger.info(f"Regions loaded: {region_count}")

        logger.info("Database setup verification complete!")
        return True
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Backcountry Safety Database Setup")
    print("=" * 60)
    print()

    if initialize_database():
        print()
        verify_setup()
    else:
        sys.exit(1)
