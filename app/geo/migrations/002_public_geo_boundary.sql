-- PostGIS contains public geographic facts only. User attribution, current
-- location, recommendation queries and personal route history live in MongoDB.
DROP TABLE IF EXISTS route_plan_legs;
DROP TABLE IF EXISTS route_plan_stops;
DROP TABLE IF EXISTS route_plans;
DROP TABLE IF EXISTS place_contributions;

ALTER TABLE places DROP COLUMN IF EXISTS created_by;
