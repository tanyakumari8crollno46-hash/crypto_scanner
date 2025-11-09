import os
import time
import requests
from binance.client import Client
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Load API keys
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Initialize Binance client
client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)

# Telegram sender
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Telegram error: {e}")

# Analyze RSI
def analyze_symbol(symbol):
    try:
        klines = client.get_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_15MINUTE, limit=100)
        closes = [float(k[4]) for k in klines]

        # RSI Calculation
        deltas = [closes[i+1] - closes[i] for i in range(len(closes)-1)]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        avg_gain = sum(gains[-14:]) / 14
        avg_loss = sum(losses[-14:]) / 14 if sum(losses[-14:]) != 0 else 0.0001
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        # Signal logic
        if rsi < 30:
            signal = "STRONG BUY"
        elif rsi > 70:
            signal = "STRONG SELL"
        else:
            signal = "HOLD"

        return {"symbol": symbol, "RSI": rsi, "signal": signal, "price": closes[-1]}

    except Exception as e:
        print(f"Error analyzing {symbol}: {e}")
        return None


SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]
sent_signals = {}  # To prevent duplicates
last_update_time = 0

print("🚀 Crypto scanner started... (press CTRL + C to stop)")

while True:
    strong_signals = []
    for s in SYMBOLS:
        data = analyze_symbol(s)
        if not data:
            continue

        rsi = data["RSI"]
        price = data["price"]
        signal = data["signal"]

        # Print locally
        print(f"{s}: {signal} | RSI: {rsi:.2f} | Price: {price:.2f}")

        # Only send new strong signals
        if signal in ["STRONG BUY", "STRONG SELL"]:
            if sent_signals.get(s) != signal:
                msg = f"{signal} for {s}! 💥 Price: {price:.2f} | RSI: {rsi:.2f}"
                send_telegram_message(msg)
                sent_signals[s] = signal
                strong_signals.append(s)

        time.sleep(1)  # Prevent hitting Binance too fast

    # Send “no strong signals” only once per hour
    current_time = time.time()
    if not strong_signals and (current_time - last_update_time > 3600):
        send_telegram_message("⏳ No strong signals right now. Market is calm.")
        last_update_time = current_time

    print("-" * 50)
    time.sleep(60 * 5)  # Re-check every 5 minutes
