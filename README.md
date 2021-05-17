## Check you profit on Binance

This is a simple utility for determining your profit when trading coins on the Binance crypto exchange.

Before starting crowler.py, you need:
1. Create API for reading on Binance site
2. Install Clickhouse-server.
3. Create user in clickhouse server (users.xml)
4. Create database and tables
5. Install pyton3-pip with requirements.txt
6. Fill in the file (.env)

### Database

```
CREATE DATABASE coins
ENGINE = Ordinary
```

### Tables
```
CREATE TABLE transactions
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
```

```
CREATE TABLE market
(
    `get_time` DateTime,
    `symbol` LowCardinality(String),
    `price_usdt` Float32
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(get_time)
ORDER BY get_time
SETTINGS index_granularity = 8192
```

```
CREATE TABLE coins_road
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
```

### users.xml (add user)

```
        <stat>
            <password>stat</password>
            <networks>
                <ip>::/0</ip>
            </networks>
            <profile>default</profile>
            <quota>default</quota>
        </stat>

```
### Support only USD and BTC coins !

### License
MIT
