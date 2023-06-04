# Pika Bybit Simple bot



How to use:

- The code bot is in Bot.py
- You need to write your own signal in this block


   
    # calculate signals for long and short
    df = get_data(no_days=29)  # download the data

    long_signals = "this is where you will store the signals"
    short_signals = "this is where you will store the signals"

    df["long_signals"] = long_signals
    df["short_signals"] = short_signals

    df_signals = df[["close", "long_signals", "short_signals", "time"]].iloc[-2]

    print("Finished calculating signals 🚀")



- After the signal is setup, run Scheduler.py. It is set to run every 5 mins after a candle is closed






Buy me a coffee

ETH : 0x5477011d5229494b070ae39b7c671fdbfb66919d

Bybit Ref: https://www.bybit.com/invite?ref=1QKXXQ
