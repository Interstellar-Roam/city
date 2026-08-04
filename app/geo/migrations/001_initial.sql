CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS places (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    address TEXT,
    categories TEXT[] NOT NULL DEFAULT '{}',
    tags TEXT[] NOT NULL DEFAULT '{}',
    location geography(Point, 4326) NOT NULL,
    city TEXT,
    district TEXT,
    images JSONB NOT NULL DEFAULT '[]'::jsonb,
    source_type TEXT NOT NULL CHECK (source_type IN ('platform', 'user', 'amap', 'import')),
    external_refs JSONB NOT NULL DEFAULT '{}'::jsonb,
    moderation_status TEXT NOT NULL DEFAULT 'published'
        CHECK (moderation_status IN ('pending', 'published', 'rejected', 'archived')),
    quality_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_places_location ON places USING GIST (location);
CREATE INDEX IF NOT EXISTS idx_places_categories ON places USING GIN (categories);
CREATE INDEX IF NOT EXISTS idx_places_tags ON places USING GIN (tags);
CREATE INDEX IF NOT EXISTS idx_places_city_status ON places (city, moderation_status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_places_amap_external_id
    ON places ((external_refs->>'amap'))
    WHERE external_refs ? 'amap';
