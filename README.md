# Pika Bybit Simple Bot

This is a simple template for a Bybit trading bot. The bot runs every 5 minutes and can be customized with your own trading signals.

## How to Use

1. The main code for the bot is located in `Bot.py`.
2. Write your own trading signals in the following block:

```python
"""
- Calculate signals for long and short positions
df = get_data(no_days=29)  # Download the data

long_signals = "This is where you will store the long signals"
short_signals = "This is where you will store the short signals"

df["long_signals"] = long_signals
df["short_signals"] = short_signals

df_signals = df[["close", "long_signals", "short_signals", "time"]].iloc[-2]

print("Finished calculating signals 🚀")
"""

Replace the placeholder strings "This is where you will store the long signals" and "This is where you will store the short signals" with your actual trading signals.

After setting up the signals, run Scheduler.py. It is configured to run every 5 minutes after a candle is closed.


*Buy me a coffee*

ETH : 0x5477011d5229494b070ae39b7c671fdbfb66919d

Bybit Ref: https://www.bybit.com/invite?ref=1QKXXQ