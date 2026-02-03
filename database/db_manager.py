import logging
from contextlib import contextmanager
from typing import Any
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages PostgreSQL/PostGIS database connections and operations."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "gis",
        user: str = os.getenv("POSTGRES_USER"),
        password: str = os.getenv("POSTGRES_PASSWORD"),
    ):
        """Initialize database connection parameters.

        Args:
            host: Database host address
            port: Database port number
            database: Database name
            user: Database username
            password: Database password
        """
        self.conn_params = {
            "host": host,
            "port": port,
            "database": database,
            "user": user,
            "password": password,
        }
        logger.info(f"Database manager initialized for {host}:{port}/{database}")

    @contextmanager
    def get_connection(self):
        """Context manager for database connections.

        Yields:
            psycopg2.connection: Active database connection

        Example:
            with db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM reports")
        """
        conn = None
        try:
            conn = psycopg2.connect(**self.conn_params)
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def insert_report(
        self,
        base_info: dict[str, Any],
        specific_data: dict[str, Any],
        report_type: str,
    ) -> None:
        """Insert a report (observation or avalanche) into the database.

        Args:
            base_info: Dictionary with base report information
            specific_data: Dictionary with observation or avalanche specific data
            report_type: Either 'observation' or 'avalanche'
        """
        print(f"Inserting {report_type} report: {base_info['report_id']}")

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Insert base report
                cur.execute(
                    """
                    INSERT INTO reports (
                        report_id, report_url, report_type, observation_date,
                        location_name, region_id, sub_region_name, geom,
                        elevation_ft, aspect, slope_angle
                    ) VALUES (
                        %(report_id)s, %(report_url)s, %(report_type)s, %(observation_date)s,
                        %(location_name)s, %(region_id)s, %(sub_region_name)s,
                        ST_SetSRID(ST_MakePoint(%(longitude)s, %(latitude)s), 4326),
                        %(elevation_ft)s, %(aspect)s, %(slope_angle)s
                    )
                    ON CONFLICT (report_id) DO NOTHING
                    """,
                    {
                        **base_info,
                        "report_type": report_type,
                        "sub_region_name": base_info.get("sub-region_name"),
                    },
                )

                # Insert specific data
                if report_type == "observation":
                    cur.execute(
                        """
                        INSERT INTO observations (
                            report_id, red_flags, new_snow_depth, new_snow_density,
                            snow_surface_conditions, avy_problem_1, avy_problem_1_trend,
                            avy_problem_2, avy_problem_2_trend, today_rating, tomorrow_rating
                        ) VALUES (
                            %(report_id)s, %(red_flags)s, %(new_snow_depth)s, %(new_snow_density)s,
                            %(snow_surface_conditions)s, %(avy_problem_1)s, %(avy_problem_1_trend)s,
                            %(avy_problem_2)s, %(avy_problem_2_trend)s, %(today_rating)s, %(tomorrow_rating)s
                        )
                        ON CONFLICT (report_id) DO NOTHING
                        """,
                        specific_data,
                    )
                elif report_type == "avalanche":
                    cur.execute(
                        """
                        INSERT INTO avalanches (
                            report_id, avalanche_date, trigger, trigger_additional,
                            avalanche_type, problem, weak_layer, depth,
                            width_feet, vertical_feet, caught, carried
                        ) VALUES (
                            %(report_id)s, %(avalanche_date)s, %(trigger)s, %(trigger_additional)s,
                            %(avalanche_type)s, %(problem)s, %(weak_layer)s, %(depth)s,
                            %(width_feet)s, %(vertical_feet)s, %(caught)s, %(carried)s
                        )
                        ON CONFLICT (report_id) DO NOTHING
                        """,
                        specific_data,
                    )
                # TODO: only log if insert was successful and not skipped due to conflict or duplicate key
                logger.debug(f"Inserted {report_type} report: {base_info['report_id']}")

    def insert_reports_batch(self, reports: list[tuple[dict, dict]]) -> int:
        """Insert multiple reports in a batch.

        Args:
            reports: List of (base_info, specific_data) tuples from scraper

        Returns:
            int: Number of reports successfully inserted
        """
        inserted = 0
        for base_info, specific_data in reports:
            try:
                # Determine report type from URL
                report_type = (
                    "avalanche"
                    if "/avalanche/" in base_info["report_url"]
                    else "observation"
                )
                self.insert_report(base_info, specific_data, report_type)
                inserted += 1
            except Exception as e:
                logger.error(
                    f"Failed to insert report {base_info.get('report_id')}: {e}"
                )
                continue

        logger.info(f"Successfully inserted {inserted}/{len(reports)} reports")
        return inserted

    def get_reports_by_date(self, start_date: str, end_date: str = None) -> list[dict]:
        """Retrieve reports within a date range.

        Args:
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format (optional, defaults to start_date)

        Returns:
            list[dict]: List of report dictionaries
        """
        if end_date is None:
            end_date = start_date

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT 
                        report_id, report_type, observation_date, location_name,
                        ST_Y(geom) as latitude, ST_X(geom) as longitude,
                        elevation_ft, aspect, slope_angle
                    FROM reports
                    WHERE observation_date BETWEEN %s AND %s
                    ORDER BY observation_date DESC
                    """,
                    (start_date, end_date),
                )

                columns = [desc[0] for desc in cur.description]
                return [dict(zip(columns, row)) for row in cur.fetchall()]

    def get_reports_near_location(
        self, latitude: float, longitude: float, radius_km: float = 10
    ) -> list[dict]:
        """Find reports within a radius of a geographic point.

        Args:
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees
            radius_km: Search radius in kilometers

        Returns:
            list[dict]: List of nearby reports with distance
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT 
                        report_id, report_type, observation_date, location_name,
                        ST_Y(geom) as latitude, ST_X(geom) as longitude,
                        ST_Distance(
                            geom::geography,
                            ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
                        ) / 1000 as distance_km
                    FROM reports
                    WHERE ST_DWithin(
                        geom::geography,
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                        %s
                    )
                    ORDER BY distance_km
                    """,
                    (longitude, latitude, longitude, latitude, radius_km * 1000),
                )

                columns = [desc[0] for desc in cur.description]
                return [dict(zip(columns, row)) for row in cur.fetchall()]

    def get_statistics(self) -> dict[str, Any]:
        """Get database statistics.

        Returns:
            dict: Statistics including counts by type, date range, etc.
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT 
                        COUNT(*) as total_reports,
                        COUNT(*) FILTER (WHERE report_type = 'observation') as observations,
                        COUNT(*) FILTER (WHERE report_type = 'avalanche') as avalanches,
                        MIN(observation_date) as earliest_date,
                        MAX(observation_date) as latest_date
                    FROM reports
                    """
                )
                result = cur.fetchone()
                return {
                    "total_reports": result[0],
                    "observations": result[1],
                    "avalanches": result[2],
                    "earliest_date": result[3],
                    "latest_date": result[4],
                }
