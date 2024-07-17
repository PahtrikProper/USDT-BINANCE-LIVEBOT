import os
import ccxt
import time
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configurable Parameters
SYMBOL = '1000SATS/USDT'
ORDER_BOOK_DEPTH = 90
TRADE_AMOUNT = 200
TRADE_INTERVAL_SECONDS = 2
MIN_PROFIT_PERCENTAGE = 0.0028  # Minimum profit percentage
MAX_SYMBOL_BALANCE_USDT_EQUIV = 50

# Order Book Analysis Parameters
VOLUME_IMBALANCE_THRESHOLD = 1.5  # Adjusted for higher sensitivity
SIGNIFICANT_VOLUME_MULTIPLIER = 5  # Multiplier to identify significant volume

# Rate Limiting Parameters
MAX_REQUESTS_PER_MINUTE = 1200
RATE_LIMIT_SAFETY_FACTOR = 0.75

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Binance API with rate limiting
exchange = ccxt.binance({
    'apiKey': os.getenv('BINANCE_API_KEY'),
    'secret': os.getenv('BINANCE_API_SECRET'),
    'enableRateLimit': True,
    'rateLimit': int((60 / MAX_REQUESTS_PER_MINUTE) * 1000 / RATE_LIMIT_SAFETY_FACTOR)
})

# Load markets data
def load_markets_data():
    try:
        exchange.load_markets()
        return exchange.markets
    except ccxt.NetworkError as e:
        logger.error(f"Network error: {e}")
    except ccxt.ExchangeError as e:
        logger.error(f"Exchange error: {e}")
    except ccxt.RateLimitExceeded as e:
        logger.error(f"Rate limit exceeded: {e}")
        time.sleep(60)
    return None

market_data = load_markets_data()

def fetch_order_book(symbol, limit=ORDER_BOOK_DEPTH):
    try:
        return exchange.fetch_order_book(symbol, limit=limit)
    except ccxt.NetworkError as e:
        logger.error(f"Network error: {e}")
    except ccxt.ExchangeError as e:
        logger.error(f"Exchange error: {e}")
    except ccxt.RateLimitExceeded as e:
        logger.error(f"Rate limit exceeded: {e}")
        time.sleep(60)
    return None

def fetch_recent_trades(symbol, limit=100):
    try:
        return exchange.fetch_trades(symbol, limit=limit)
    except ccxt.NetworkError as e:
        logger.error(f"Network error: {e}")
    except ccxt.ExchangeError as e:
        logger.error(f"Exchange error: {e}")
    except ccxt.RateLimitExceeded as e:
        logger.error(f"Rate limit exceeded: {e}")
        time.sleep(60)
    return None

def analyze_order_book(order_book):
    asks = order_book['asks']
    bids = order_book['bids']
    
    if not asks or not bids:
        logger.warning("Not enough asks or bids in the order book for analysis.")
        return None
    
    best_ask_price, best_ask_volume = asks[0]
    best_bid_price, best_bid_volume = bids[0]
    
    total_bid_volume = sum(volume for price, volume in bids)
    total_ask_volume = sum(volume for price, volume in asks)
    volume_imbalance = total_bid_volume / total_ask_volume

    min_exit_price = best_ask_price * (1 + MIN_PROFIT_PERCENTAGE)

    market_condition = 'neutral'
    if volume_imbalance > VOLUME_IMBALANCE_THRESHOLD:
        market_condition = 'bullish'
    elif volume_imbalance < 1 / VOLUME_IMBALANCE_THRESHOLD:
        market_condition = 'bearish'

    # Identify significant sell walls and support levels
    significant_sell_walls = [ask for ask in asks if ask[1] > SIGNIFICANT_VOLUME_MULTIPLIER * best_ask_volume]
    significant_support_levels = [bid for bid in bids if bid[1] > SIGNIFICANT_VOLUME_MULTIPLIER * best_bid_volume]

    # Calculate potential profit percentage based on order book
    potential_sell_price = None
    for ask_price, ask_volume in asks:
        if ask_volume < total_bid_volume * 0.1:  # Example threshold, adjust as needed
            potential_sell_price = ask_price
            break

    return {
        'best_ask_price': best_ask_price,
        'best_bid_price': best_bid_price,
        'min_exit_price': min_exit_price,
        'market_condition': market_condition,
        'significant_sell_walls': significant_sell_walls,
        'significant_support_levels': significant_support_levels,
        'potential_sell_price': potential_sell_price
    }

def analyze_recent_trades(recent_trades):
    if not recent_trades:
        logger.warning("No recent trades to analyze.")
        return None
    
    prices = [trade['price'] for trade in recent_trades]
    average_price = sum(prices) / len(prices)
    lowest_price = min(prices)
    
    return {
        'average_price': average_price,
        'lowest_price': lowest_price,
        'recent_prices': prices
    }

def determine_best_entry_price(order_book_analysis, recent_trades_analysis):
    significant_bid_price = order_book_analysis['best_bid_price']
    average_price = recent_trades_analysis['average_price']
    lowest_price = recent_trades_analysis['lowest_price']

    # Determine best entry price as the higher of significant bid price and average recent price
    best_entry_price = max(significant_bid_price, average_price)
    
    # Ensure we're not buying at a peak
    if best_entry_price > lowest_price * 1.01:  # Example threshold, adjust as needed
        best_entry_price = lowest_price

    return best_entry_price

def validate_order(symbol, side, price, amount):
    global market_data
    if market_data is None:
        market_data = load_markets_data()
        if market_data is None:
            return False

    market = market_data[symbol]

    if amount < market['limits']['amount']['min']:
        logger.error(f"Order amount {amount} is less than minimum allowed {market['limits']['amount']['min']}.")
        return False

    price_precision = market['precision']['price']
    amount_precision = market['precision']['amount']
    price = round(price, price_precision)
    amount = round(amount, amount_precision)

    lot_size_step = market['limits']['amount'].get('step')
    if lot_size_step and amount % lot_size_step != 0:
        logger.error(f"Order amount {amount} is not a multiple of lot size step {lot_size_step}.")
        return False

    notional = price * amount
    if notional < market['limits']['cost']['min']:
        logger.error(f"Order notional {notional} is less than minimum allowed {market['limits']['cost']['min']}.")
        return False

    return price, amount

def place_order(symbol, side, price, amount):
    logger.info(f"Placing {side} order: {amount:.8f} {symbol} at {price:.8f}")
    validation = validate_order(symbol, side, price, amount)
    if not validation:
        return None
    price, amount = validation
    try:
        if side == 'buy':
            order = exchange.create_limit_buy_order(symbol, amount, price)
        else:
            order = exchange.create_limit_sell_order(symbol, amount, price)
        logger.info(f"Order placed: {order}")
        return order
    except ccxt.InsufficientFunds as e:
        logger.error(f"Insufficient funds: {e}")
    except ccxt.NetworkError as e:
        logger.error(f"Network error: {e}")
    except ccxt.ExchangeError as e:
        logger.error(f"Exchange error: {e}")
    except ccxt.RateLimitExceeded as e:
        logger.error(f"Rate limit exceeded: {e}")
        time.sleep(60)
    return None

def update_order_status(order):
    try:
        order_info = exchange.fetch_order(order['id'], order['symbol'])
        order.update(order_info)
    except ccxt.NetworkError as e:
        logger.error(f"Network error: {e}")
    except ccxt.ExchangeError as e:
        logger.error(f"Exchange error: {e}")
    except ccxt.RateLimitExceeded as e:
        logger.error(f"Rate limit exceeded: {e}")
        time.sleep(60)
    return order

def fetch_balances():
    try:
        balance_info = exchange.fetch_balance()
        usdt_balance = balance_info['total']['USDT']
        symbol_balance = balance_info['total'][SYMBOL.split('/')[0]]
        return usdt_balance, symbol_balance
    except ccxt.NetworkError as e:
        logger.error(f"Network error: {e}")
    except ccxt.ExchangeError as e:
        logger.error(f"Exchange error: {e}")
    except ccxt.RateLimitExceeded as e:
        logger.error(f"Rate limit exceeded: {e}")
        time.sleep(60)
    return None, None

def calculate_fees(symbol, side, amount, price):
    try:
        fee_info = exchange.calculate_fee(symbol, side, 'limit', amount, price, 'maker')
        return fee_info['rate']
    except Exception as e:
        logger.error(f"Failed to calculate fees: {e}")
        return 0

def check_open_orders(symbol):
    try:
        open_orders = exchange.fetch_open_orders(symbol)
        return len(open_orders) > 0
    except ccxt.NetworkError as e:
        logger.error(f"Network error: {e}")
    except ccxt.ExchangeError as e:
        logger.error(f"Exchange error: {e}")
    except ccxt.RateLimitExceeded as e:
        logger.error(f"Rate limit exceeded: {e}")
        time.sleep(60)
    return False

def live_trading(symbol):
    while True:
        balance, symbol_balance = fetch_balances()
        if balance is None or symbol_balance is None:
            logger.error("Failed to fetch initial balances. Exiting.")
            return

        active_trade = None
        last_api_call_time = time.time()
        previous_market_condition = 'neutral'

        while True:
            time_since_last_call = time.time() - last_api_call_time
            if time_since_last_call < TRADE_INTERVAL_SECONDS:
                time.sleep(TRADE_INTERVAL_SECONDS - time_since_last_call)
            
            if check_open_orders(symbol):
                logger.info("There are unfilled open orders. Skipping this iteration.")
                continue
            
            order_book = fetch_order_book(symbol)
            recent_trades = fetch_recent_trades(symbol)
            last_api_call_time = time.time()
            
            if order_book is None or recent_trades is None:
                logger.warning("Failed to fetch order book or recent trades. Skipping this iteration.")
                continue

            order_book_analysis = analyze_order_book(order_book)
            recent_trades_analysis = analyze_recent_trades(recent_trades)
            
            if order_book_analysis is None or recent_trades_analysis is None:
                logger.warning("Failed to analyze order book or recent trades. Skipping this iteration.")
                continue
            
            best_entry_price = determine_best_entry_price(order_book_analysis, recent_trades_analysis)

            # Avoid buying if there are significant sell walls above the best entry price
            significant_sell_walls = order_book_analysis['significant_sell_walls']
            if any(wall[0] <= best_entry_price for wall in significant_sell_walls):
                logger.info("Significant sell walls detected above the best entry price. Skipping this iteration.")
                continue

            # Avoid buying during strong downtrends by analyzing recent price movements
            if recent_trades_analysis['recent_prices'][-1] < min(recent_trades_analysis['recent_prices']):
                logger.info("Strong downtrend detected. Skipping this iteration.")
                continue

            logger.info(f"Market condition: {order_book_analysis['market_condition']}, Best entry price: {best_entry_price:.8f}")

            symbol_balance_usdt_equiv = symbol_balance * best_entry_price

            if (previous_market_condition in ['neutral', 'bearish'] and 
                order_book_analysis['market_condition'] == 'bullish' and 
                symbol_balance_usdt_equiv < MAX_SYMBOL_BALANCE_USDT_EQUIV):
                if active_trade is None and balance >= TRADE_AMOUNT:
                    amount_to_buy = TRADE_AMOUNT / best_entry_price
                    active_trade = place_order(symbol, 'buy', best_entry_price, amount_to_buy)
                    if active_trade is not None:
                        logger.info(f"Buy order placed at best entry price: {best_entry_price:.8f}")
                        balance, symbol_balance = fetch_balances()  # Refresh balances
                        logger.info(f"Updated balance after placing buy order: {balance:.2f} USDT, {SYMBOL.split('/')[0]} balance: {symbol_balance:.8f}")

            if active_trade and active_trade['side'] == 'buy':
                active_trade = update_order_status(active_trade)
                if active_trade['status'] == 'closed':
                    logger.info(f"Buy order filled at {active_trade['price']:.8f}")
                    balance, symbol_balance = fetch_balances()  # Refresh balances
                    
                    logger.info("Waiting 10 seconds before placing the sell order.")
                    time.sleep(10)
                    
                    min_sell_price = order_book_analysis['min_exit_price']

                    # Fetch applicable fees
                    sell_fee_rate = calculate_fees(symbol, 'sell', symbol_balance, min_sell_price)

                    # Calculate the amount to sell considering the fees
                    amount_to_sell = symbol_balance / (1 + sell_fee_rate)

                    # Calculate the potential profit percentage based on the order book analysis
                    potential_sell_price = order_book_analysis['potential_sell_price']
                    if potential_sell_price and potential_sell_price > min_sell_price:
                        min_sell_price = potential_sell_price

                    # Check if the equivalent value of the sell order is less than 50 USDT
                    if amount_to_sell * min_sell_price < MAX_SYMBOL_BALANCE_USDT_EQUIV:
                        logger.info(f"Equivalent value of the sell order is less than {MAX_SYMBOL_BALANCE_USDT_EQUIV} USDT. Skipping sell order.")
                        active_trade = None
                    else:
                        while True:
                            sell_order = place_order(symbol, 'sell', min_sell_price, amount_to_sell)
                            if sell_order:
                                logger.info(f"Sell order placed at price: {min_sell_price:.8f}")
                                balance, symbol_balance = fetch_balances()  # Refresh balances
                                logger.info(f"Updated {SYMBOL.split('/')[0]} balance after placing sell order: {symbol_balance:.8f}")
                                break
                            else:
                                logger.error(f"Failed to place sell order. Retrying with adjusted amount.")
                                amount_to_sell *= 0.99  # Reduce the amount slightly and retry

            elif active_trade and active_trade['side'] == 'sell':
                active_trade = update_order_status(active_trade)
                if active_trade['status'] == 'closed':
                    logger.info(f"Sell order filled at {active_trade['price']:.8f}")
                    balance, symbol_balance = fetch_balances()  # Refresh balances
                    logger.info(f"Updated balance after sell order filled: {balance:.2f} USDT, {SYMBOL.split('/')[0]} balance: {symbol_balance:.8f}")
                    active_trade = None

            total_value = balance + symbol_balance * best_entry_price
            logger.info(f"Current Balance: {balance:.2f} USDT, {SYMBOL.split('/')[0]} Balance: {symbol_balance:.8f}, Total Value: {total_value:.2f}")
            previous_market_condition = order_book_analysis['market_condition']

def main():
    live_trading(SYMBOL)

if __name__ == "__main__":
    main()
