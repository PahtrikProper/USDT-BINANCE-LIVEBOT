
# Binance Automated Trading Bot

This project is a simple automated trading bot for the Binance cryptocurrency exchange. The bot is written in Python and uses the `ccxt` library to interact with the Binance API. It fetches the order book and recent trades for a specified symbol, analyzes the data, and places buy and sell orders based on market conditions.

## Features

- **Order Book Analysis**: Fetches and analyzes the order book for the specified symbol to determine market conditions.
- **Recent Trades Analysis**: Fetches and analyzes recent trades to identify average prices and trends.
- **Automated Trading**: Places buy and sell orders based on the analyzed data and configurable parameters.
- **Rate Limiting**: Implements rate limiting to comply with Binance API limits.
- **Logging**: Logs important information and errors for monitoring and debugging.

## Requirements

- Python 3.6+
- `ccxt` library
- `python-dotenv` library

## Installation

1. Install the required libraries:
    ```bash
    pip install ccxt python-dotenv
    ```

2. Create a `.env` file in the root directory of the project and add your Binance API key and secret:
    ```
    BINANCE_API_KEY=your_api_key
    BINANCE_API_SECRET=your_api_secret
    ```

## Configuration

The following parameters can be configured in the script:

- `SYMBOL`: The trading pair symbol (e.g., '1000SATS/USDT').
- `ORDER_BOOK_DEPTH`: The depth of the order book to fetch (default is 90).
- `TRADE_AMOUNT`: The amount of USDT to trade in each buy order (default is 200 USDT).
- `TRADE_INTERVAL_SECONDS`: The interval between each trade attempt (default is 2 seconds).
- `MIN_PROFIT_PERCENTAGE`: The minimum profit percentage to aim for when placing sell orders (default is 0.28%).
- `MAX_SYMBOL_BALANCE_USDT_EQUIV`: The maximum equivalent USDT value of the symbol balance to hold (default is 50 USDT).
- `VOLUME_IMBALANCE_THRESHOLD`: The threshold for volume imbalance to determine market conditions (default is 1.5).
- `SIGNIFICANT_VOLUME_MULTIPLIER`: The multiplier to identify significant volume in the order book (default is 5).
- `MAX_REQUESTS_PER_MINUTE`: The maximum number of API requests per minute (default is 1200).
- `RATE_LIMIT_SAFETY_FACTOR`: A safety factor to apply to the rate limit (default is 0.75).

## Usage

To start the trading bot, simply run the script:

```bash
python main.py
```

## Script Overview

### Initialization

- **Environment Variables**: Loads Binance API key and secret from the `.env` file.
- **Logging**: Sets up logging to log important information and errors.
- **Binance API Initialization**: Initializes the Binance API with rate limiting.

### Market Data Fetching

- **Load Markets Data**: Fetches and stores market data from Binance.
- **Fetch Order Book**: Retrieves the order book for the specified symbol.
- **Fetch Recent Trades**: Retrieves recent trades for the specified symbol.

### Data Analysis

- **Analyze Order Book**: Analyzes the order book to determine the best ask and bid prices, volume imbalance, and market condition.
- **Analyze Recent Trades**: Analyzes recent trades to calculate average and lowest prices.

### Trading Logic

- **Determine Best Entry Price**: Determines the best entry price for placing buy orders based on order book and recent trades analysis.
- **Validate Order**: Validates orders to ensure they meet Binance's minimum and maximum constraints.
- **Place Order**: Places buy or sell orders on Binance.
- **Update Order Status**: Updates the status of open orders to check if they are filled or not.
- **Fetch Balances**: Retrieves the current balance of USDT and the trading symbol.
- **Calculate Fees**: Calculates applicable trading fees.
- **Check Open Orders**: Checks for any unfilled open orders to avoid placing duplicate orders.

### Live Trading Loop

- **Balance Check**: Fetches initial balances and checks for open orders.
- **Order Book and Trades Analysis**: Continuously fetches and analyzes order book and recent trades data.
- **Trading Decision**: Makes trading decisions based on analyzed data and places buy or sell orders accordingly.
- **Order Monitoring**: Monitors the status of placed orders and updates balances.

## Disclaimer

This trading bot is for educational purposes only. Trading cryptocurrencies involves significant risk and can result in substantial financial losses. Use this bot at your own risk.

## License

This project is licensed under the MIT License.
