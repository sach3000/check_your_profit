ATTACH TABLE coins_road
(
    `calc_time` DateTime,
    `symbol` LowCardinality(String),
    `amount` Float32,
    `start_market` Float32,
    `profit` Float32
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(calc_time)
ORDER BY calc_time
SETTINGS index_granularity = 8192

