CREATE TABLE IF NOT EXISTS telemetry (
    ts TIMESTAMPTZ NOT NULL,
    car_id TEXT NOT NULL,
    online BOOLEAN,
    online_state TEXT,
    battery_pct DOUBLE PRECISION,
    range_km DOUBLE PRECISION,
    charging_gun BOOLEAN,
    battery_temp DOUBLE PRECISION,
    voltage_12v DOUBLE PRECISION,
    climate_target DOUBLE PRECISION,
    climate_fan DOUBLE PRECISION,
    temp_inside DOUBLE PRECISION,
    temp_outside DOUBLE PRECISION,
    coolant_temp DOUBLE PRECISION,
    locked BOOLEAN,
    ignition BOOLEAN,
    parked BOOLEAN,
    odometer DOUBLE PRECISION,
    signal_level DOUBLE PRECISION,
    raw JSONB
);

CREATE INDEX IF NOT EXISTS telemetry_ts_idx ON telemetry (ts DESC);
CREATE INDEX IF NOT EXISTS telemetry_car_ts_idx ON telemetry (car_id, ts DESC);

CREATE TABLE IF NOT EXISTS trips (
    car_id TEXT NOT NULL,
    travel_id INT NOT NULL,
    segment_start_time BIGINT NOT NULL,
    segment_end_time BIGINT,
    start_date BIGINT,
    end_date BIGINT,
    duration TEXT,
    distance INT,
    battery_consumption INT,
    odo_first INT,
    odo_last INT,
    battery_first INT,
    battery_last INT,
    title TEXT,
    PRIMARY KEY (car_id, travel_id, segment_start_time)
);

CREATE TABLE IF NOT EXISTS collector_heartbeats (
    ts TIMESTAMPTZ PRIMARY KEY,
    ok BOOLEAN NOT NULL,
    error TEXT,
    duration_ms INT
);
