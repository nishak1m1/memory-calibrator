CREATE TABLE IF NOT EXISTS memory_usage (
    id SERIAL PRIMARY KEY,
    hostname VARCHAR(255),
    cgroup VARCHAR(255),
    max_usage BIGINT,
    timestamp TIMESTAMP
);
CREATE TABLE IF NOT EXISTS constant_memory_usage (
    id SERIAL PRIMARY KEY,
    hostname VARCHAR(255),
    cgroup VARCHAR(255),
    max_usage BIGINT,
    timestamp TIMESTAMP
);
