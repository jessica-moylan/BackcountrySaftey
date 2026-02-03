-- Initialize PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- Create regions lookup table
CREATE TABLE regions (
    id SERIAL PRIMARY KEY,
    region_name VARCHAR(100) UNIQUE NOT NULL,
    state_name VARCHAR(100) NOT NULL,
    state_id INTEGER
);

-- Insert Utah regions
INSERT INTO regions (id, region_name, state_name, state_id) VALUES
    (1, 'Logan', 'Utah', 45),
    (2, 'Ogden', 'Utah', 45),
    (3, 'Uintas', 'Utah', 45),
    (4, 'Salt Lake', 'Utah', 45),
    (5, 'Provo', 'Utah', 45),
    (6, 'Skyline', 'Utah', 45),
    (7, 'Moab', 'Utah', 45),
    (8, 'Abajos', 'Utah', 45),
    (9, 'Southwest', 'Utah', 45);

-- Create base reports table with PostGIS geometry
CREATE TABLE reports (
    id SERIAL PRIMARY KEY,
    report_id VARCHAR(100) UNIQUE NOT NULL,
    report_url TEXT NOT NULL,
    report_type VARCHAR(50) NOT NULL, -- 'observation' or 'avalanche'
    observation_date DATE NOT NULL,
    location_name TEXT,
    region_id INTEGER REFERENCES regions(id),
    sub_region_name VARCHAR(255),
    geom GEOMETRY(Point, 4326), -- PostGIS spatial column (WGS84 - standard GPS coordinates)
    elevation_ft INTEGER,
    aspect VARCHAR(100),
    slope_angle INTEGER, -- degrees
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create spatial index for efficient geographic queries
CREATE INDEX idx_reports_geom ON reports USING GIST (geom);
CREATE INDEX idx_reports_date ON reports(observation_date);
CREATE INDEX idx_reports_region ON reports(region_id);

-- Create observation-specific data table
CREATE TABLE observations (
    id SERIAL PRIMARY KEY,
    report_id VARCHAR(100) UNIQUE NOT NULL REFERENCES reports(report_id) ON DELETE CASCADE,
    red_flags TEXT[], -- Array of red flag warnings
    new_snow_depth VARCHAR(50),
    new_snow_density VARCHAR(50),
    snow_surface_conditions TEXT,
    avy_problem_1 VARCHAR(255),
    avy_problem_1_trend VARCHAR(50),
    avy_problem_2 VARCHAR(255),
    avy_problem_2_trend VARCHAR(50),
    today_rating VARCHAR(50),
    tomorrow_rating VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create avalanche-specific data table
CREATE TABLE avalanches (
    id SERIAL PRIMARY KEY,
    report_id VARCHAR(100) UNIQUE NOT NULL REFERENCES reports(report_id) ON DELETE CASCADE,
    avalanche_date DATE NOT NULL,
    trigger VARCHAR(255),
    trigger_additional TEXT,
    avalanche_type VARCHAR(100),
    problem VARCHAR(255),
    weak_layer VARCHAR(255),
    depth INTEGER,
    width_feet INTEGER,
    vertical_feet INTEGER,
    caught INTEGER,
    carried INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_avalanches_date ON avalanches(avalanche_date);
CREATE INDEX idx_avalanches_trigger ON avalanches(trigger);

-- Create view for complete observation data
CREATE VIEW observation_details AS
SELECT 
    r.report_id,
    r.report_url,
    r.observation_date,
    r.location_name,
    reg.region_name,
    r.sub_region_name,
    ST_Y(r.geom) as latitude,
    ST_X(r.geom) as longitude,
    r.elevation_ft,
    r.aspect,
    r.slope_angle,
    o.red_flags,
    o.new_snow_depth,
    o.new_snow_density,
    o.snow_surface_conditions,
    o.avy_problem_1,
    o.avy_problem_1_trend,
    o.avy_problem_2,
    o.avy_problem_2_trend,
    o.today_rating,
    o.tomorrow_rating
FROM reports r
JOIN observations o ON r.report_id = o.report_id
LEFT JOIN regions reg ON r.region_id = reg.id
WHERE r.report_type = 'observation';

-- Create view for complete avalanche data
CREATE VIEW avalanche_details AS
SELECT 
    r.report_id,
    r.report_url,
    r.observation_date,
    r.location_name,
    reg.region_name,
    r.sub_region_name,
    ST_Y(r.geom) as latitude,
    ST_X(r.geom) as longitude,
    r.elevation_ft,
    r.aspect,
    r.slope_angle,
    a.avalanche_date,
    a.trigger,
    a.trigger_additional,
    a.avalanche_type,
    a.problem,
    a.weak_layer,
    a.depth,
    a.width_feet,
    a.vertical_feet,
    a.caught,
    a.carried
FROM reports r
JOIN avalanches a ON r.report_id = a.report_id
LEFT JOIN regions reg ON r.region_id = reg.id
WHERE r.report_type = 'avalanche';

-- Example spatial queries you can run:

-- Find all reports within 10km of a point (Salt Lake City example)
-- SELECT * FROM reports 
-- WHERE ST_DWithin(
--     geom::geography,
--     ST_SetSRID(ST_MakePoint(-111.8910, 40.7608), 4326)::geography,
--     10000
-- );

-- Find all reports in a bounding box
-- SELECT * FROM reports 
-- WHERE ST_Contains(
--     ST_MakeEnvelope(-112.0, 40.5, -111.5, 41.0, 4326),
--     geom
-- );

-- Calculate distance between two points
-- SELECT 
--     r1.location_name,
--     r2.location_name,
--     ST_Distance(r1.geom::geography, r2.geom::geography) / 1000 as distance_km
-- FROM reports r1, reports r2
-- WHERE r1.id < r2.id;
