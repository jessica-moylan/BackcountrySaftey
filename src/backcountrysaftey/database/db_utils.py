import os
import psycopg

DATABASE = {
    'dbname': 'gis',
    'user': os.getenv("POSTGRES_USER"),
    'password': os.getenv("POSTGRES_PASSWORD"),
    'host': 'localhost',
    'port': 5432,
}

def get_all_in_region(region_id: int = 4):
    """Fetch all records from the specified region."""
    try:
        with psycopg.connect(**DATABASE) as conn:
            with conn.cursor() as cur:
                query = "SELECT * FROM reports WHERE region_id = %s;"
                cur.execute(query, (region_id,))
                results = cur.fetchall()
                return results
    except Exception as e:
        print(f"Database error: {e}")
        return []