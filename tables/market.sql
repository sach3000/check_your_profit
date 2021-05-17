ATTACH TABLE market
(
    `get_time` DateTime,
    `symbol` LowCardinality(String),
    `price_usdt` Float32
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(get_time)
ORDER BY get_time
SETTINGS index_granularity = 8192

