import MetaTrader5 as mt5
import time
from datetime import datetime

# Configuration
SYMBOL = "Volatility 150 (1s) Index"
LOT_SIZE = 0.01
MAGIC_NUMBER = 150001
STOP_LOSS = 0.02  # $0.02 stop loss

def initialize_mt5():
    """Initialize MT5 connection"""
    if not mt5.initialize():
        print("Initialize() failed, error code =", mt5.last_error())
        return False
    
    account = 40542280
    password = "Jave781227@"
    server = "Deriv-Demo"
    
    if not mt5.login(account, password=password, server=server):
        print("Login failed, error code =", mt5.last_error())
        mt5.shutdown()
        return False
    
    print(f"Connected to account #{account}")
    return True

def get_candle_data(symbol, timeframe, count):
    """Get candle data with error handling"""
    for _ in range(3):  # Retry up to 3 times
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
        if rates is not None and len(rates) >= count:
            return rates
        time.sleep(0.1)
    return None

def check_entry_conditions(symbol):
    """Check refined entry conditions"""
    candles = get_candle_data(symbol, mt5.TIMEFRAME_M1, 2)
    if candles is None:
        return 0
    
    prev_candle = candles[1]
    current_candle = candles[0]
    
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return 0
    
    current_open = tick.bid  # Using bid price for sell, ask for buy
    
    # Bullish entry condition
    if (prev_candle[4] > prev_candle[1] and  # Previous candle was bullish
        current_open > prev_candle[4]):      # New candle opens above previous close
        return 1
    
    # Bearish entry condition
    elif (prev_candle[4] < prev_candle[1] and  # Previous candle was bearish
          current_open < prev_candle[4]):      # New candle opens below previous close
        return -1
    
    return 0

def execute_trade(symbol, direction):
    """Execute trade with stop loss only"""
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return False

    price = tick.ask if direction == 1 else tick.bid
    sl_price = price - STOP_LOSS if direction == 1 else price + STOP_LOSS

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": LOT_SIZE,
        "type": mt5.ORDER_TYPE_BUY if direction == 1 else mt5.ORDER_TYPE_SELL,
        "price": price,
        "sl": sl_price,
        "deviation": 10,
        "magic": MAGIC_NUMBER,
        "comment": "SL Only Trade",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_FOK,
    }
    
    result = mt5.order_send(request)
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        print(f"{'BUY' if direction == 1 else 'SELL'} executed at {price} with SL at {sl_price}")
        return True
    else:
        print(f"Order failed: {result.comment}")
        return False

def monitor_and_close_profits():
    """Monitor and immediately close profitable trades"""
    positions = mt5.positions_get()
    if not positions:
        return 0
    
    closed = 0
    for position in positions:
        if position.profit > 0:  # Close immediately when profitable
            tick = mt5.symbol_info_tick(position.symbol)
            if not tick:
                continue
                
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": position.volume,
                "type": mt5.ORDER_TYPE_BUY if position.type == mt5.ORDER_TYPE_SELL else mt5.ORDER_TYPE_SELL,
                "position": position.ticket,
                "price": tick.ask if position.type == mt5.ORDER_TYPE_SELL else tick.bid,
                "deviation": 5,
                "magic": MAGIC_NUMBER,
                "comment": "Profit Taken",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            result = mt5.order_send(request)
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                closed += 1
                print(f"Closed {position.symbol} (Profit: ${position.profit:.2f}) at {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
    
    return closed

def main():
    if not initialize_mt5():
        return
    
    if not mt5.symbol_select(SYMBOL, True):
        print(f"Symbol {SYMBOL} not found")
        mt5.shutdown()
        return
    
    print(f"\n=== Trading Bot: {SYMBOL} ===")
    print("Strategy:")
    print("- Buy if previous candle bullish AND new candle opens above previous close")
    print("- Sell if previous candle bearish AND new candle opens below previous close")
    print(f"- ${STOP_LOSS} stop loss on all trades")
    print("- Close trades immediately when profitable\n")
    
    try:
        while True:
            # Check and close profitable trades
            monitor_and_close_profits()
            
            # Check entry conditions (only if no positions exist)
            if not mt5.positions_total():
                direction = check_entry_conditions(SYMBOL)
                if direction != 0:
                    execute_trade(SYMBOL, direction)
            
            time.sleep(0.01)  # Fast monitoring loop
    
    except KeyboardInterrupt:
        print("\nStopping bot...")
    finally:
        mt5.shutdown()

if __name__ == "__main__":
    main()
