ATTACH TABLE transactions
(
    `event_time` DateTime,
    `symbol` LowCardinality(String),
    `amount` Float32,
    `price` Float32,
    `action` Enum8('buy' = 1, 'sell' = 0),
    `use` Nullable(UInt8)
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_time)
ORDER BY symbol
SETTINGS index_granularity = 8192

