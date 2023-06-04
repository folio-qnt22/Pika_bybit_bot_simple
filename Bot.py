import numpy as np
import os
import pandas as pd
import json
from pathlib import Path
import requests
import time

from datetime import datetime, timedelta
from dateutil import parser

from urllib.request import urlopen
from pybit.unified_trading import HTTP

# logging into bybit
def get_credentials(name):
    root = Path(".")
    file_path = f"{root}/keys/acc_{name}.json"
    # file_path = f"keys/acc_{name+1}.json"
    with open(file_path) as file:

        file = file.read()
        credentials = json.loads(file)

        api_key = credentials["bybit_api_key"]
        api_secret = credentials["bybit_secret_key"]

    return api_key, api_secret


def login(name):
    session = HTTP(
        testnet=False,
        api_key=get_credentials(name=name)[0],
        api_secret=get_credentials(name=name)[1],
    )
    return session


def telegram_log(text):
    """
    Sends a message to a Telegram channel using the Telegram Bot API.

    Parameters:
        text (str): The text message to be sent.

    Returns:
        None
    """
    channel_id = "XXXXXX"
    url = "https://api.telegram.org/bot"
    requests.get(url + "sendMessage", params=dict(chat_id=channel_id, text=text))


def run():
    # getting kline from binance

    def get_kline(startTime, symbol="BTCUSDT", limit=1, interval="5m"):
        data = requests.get(
            "https://fapi.binance.com/fapi/v1/klines",
            params={
                "symbol": symbol,
                "interval": interval,
                "startTime": startTime,
                "endTime": startTime + (500 * 5 * 60 * 1000),
                "limit": limit,
            },
        ).json()

        data = pd.DataFrame(
            data,
            columns=[
                "timestamp",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "close_time",
                "quote_vol",
                "no_of_trades",
                "tb_base_vol",
                "tb_quote_vol",
                "ignore",
            ],
        )
        data.iloc[:, 1:] = data.iloc[:, 1:].astype(float)
        data["time"] = pd.to_datetime(data["timestamp"], unit="ms")
        return data

        data = requests.get(
            "https://fapi.binance.com/futures/data/openInterestHist",
            params={
                "symbol": symbol,
                "period": "5m",
                "startTime": startTime,
                "endTime": startTime + (500 * 5 * 60 * 1000),
                "limit": 500,
            },
        ).json()
        data = pd.DataFrame(data)
        data["time"] = pd.to_datetime(data["timestamp"], unit="ms")
        return data

    def get_data(no_days=30):
        ############################################################
        # This module gets the data from binance and merges it
        # into a single dataframe and returns it
        # no_days: number of days of data to be fetched
        # returns: dataframe with kline and OI data
        ############################################################

        # Get the current time
        now = datetime.now()
        # Subtract 29 days from the current time
        thirty_days_ago = now - timedelta(days=no_days)
        # Convert the datetime object to a Unix timestamp in milliseconds
        timestamp_ms = int(thirty_days_ago.timestamp() * 1000)
        # Convert timestamp in milliseconds to a UTC datetime object
        timestamp_seconds = timestamp_ms / 1000  # convert milliseconds to seconds
        dt_object_utc = datetime.utcfromtimestamp(timestamp_seconds)
        print("Fetching data from Binance 🛜")
        print(f"{no_days} days lookback:", dt_object_utc)

        # Calcualte the number of loops required to get 30 days of data with 5 min candles
        mins = no_days * 24 * 60
        n_loops = int(mins / (5 * 500))

        kline = get_kline(startTime=timestamp_ms, limit=500, symbol="BTCUSDT")
        for i in range(n_loops):
            kline_temp = get_kline(
                startTime=kline["timestamp"].values[-1], limit=500, symbol="BTCUSDT"
            )
            kline = (
                pd.concat([kline, kline_temp]).drop_duplicates().reset_index(drop=True)
            )

        return kline

    def calculate_rsi(prices, period):
        # Calculate price changes
        delta = prices.diff()

        # Calculate gains and losses
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        # Calculate average gains and losses
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()

        # Calculate relative strength
        rs = avg_gain / avg_loss

        # Calculate RSI
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_ema(prices, period):
        # Calculate exponential moving average
        ema = prices.ewm(span=period, adjust=False).mean()

        return ema

    def calculate_position_size(price, loss_amount_in_usd, percentage_loss):
        # percentage_loss = 0.015  # 3% loss
        btc_size = loss_amount_in_usd / (price * percentage_loss)
        return btc_size

    def long_order(
        signal_price,
        position_size,
        SL,
        RR,
        entry_offset,
        ticker="BTCUSDT",
        max_retries=5,
    ):
        retries = 0

        while retries < max_retries:

            try:
                # get the recent price
                entry_price = np.round(signal_price * (1 - entry_offset), 2)
                stop_loss = np.round(entry_price * (1 - SL), 2)
                take_profit = np.round(entry_price * (1 + RR * SL), 2)

                # place the order
                order = session.place_order(
                    category="linear",
                    symbol=ticker,
                    side="Buy",
                    orderType="Limit",
                    qty=str(position_size),
                    price=str(entry_price),
                    # orderFilter="tpslOrder",
                    timeInForce="PostOnly",
                    positionIdx=1,  # hedge mode Buy side
                    takeProfit=str(take_profit),
                    stopLoss=str(stop_loss),
                    tpslMode="Partial",
                    tpOrderType="Market",
                    slOrderType="Market",
                )

                # If the order placement is successful, exit the loop
                break

            except Exception as error:
                # print("Error placing the order:", error)

                retries += 1

                if "ErrCode: 110061" in str(error):
                    print("🤖 Switching the Account...")

                elif "110007" in str(error):
                    print("\n💰 Insufficient balance")

                else:
                    print("\n🤖 Probably the price moved too fast, retrying...")

                if retries >= max_retries:
                    print("Max retries exceeded. Exiting...")

                    return

                # print("Retrying...")
                # Add a delay between retries if needed
                time.sleep(1)
                # send a telegram message (later)

        # Continue with the rest of the code if the order is placed successfully
        print("🤖 Order placed successfully!")

    def short_order(
        signal_price,
        position_size,
        SL,
        RR,
        entry_offset,
        ticker="BTCUSDT",
        max_retries=5,
    ):
        retries = 0

        while retries < max_retries:

            session = login(name=retries)

            try:
                # get the recent price
                entry_price = np.round(signal_price * (1 + entry_offset), 2)
                stop_loss = np.round(entry_price * (1 + SL), 2)
                take_profit = np.round(entry_price * (1 - RR * SL), 2)

                # place the order
                order = session.place_order(
                    category="linear",
                    symbol=ticker,
                    side="Sell",
                    orderType="Limit",
                    qty=str(position_size),
                    price=str(entry_price),
                    # orderFilter="tpslOrder",
                    timeInForce="PostOnly",
                    positionIdx=2,  # hedge mode Sell side
                    takeProfit=str(take_profit),
                    stopLoss=str(stop_loss),
                    tpslMode="Partial",
                    tpOrderType="Market",
                    slOrderType="Market",
                )

                # If the order placement is successful, exit the loop
                break

            except Exception as error:
              
                retries += 1

                if "ErrCode: 110061" in str(error):
                    print("🤖 Switching the Account...")
                    #you have to implement the login function yourself if you want to use this

                elif "110007" in str(error):
                    print("\n💰 Insufficient balance")
                    
                else:
                    print("\n🤖 Probably the price moved too fast, retrying...")
                    

                if retries >= max_retries:
                    print("Max retries exceeded. Exiting...")
                    
                    return

                time.sleep(1)
                

        # Continue with the rest of the code if the order is placed successfully
        print("🤖 Order placed successfully!")


    ######################################################
    # calculate signals for long and short
    df = get_data(no_days=29)  # download the data

    long_signals = "this is where you will store the signals"
    short_signals = "this is where you will store the signals"

    df["long_signals"] = long_signals
    df["short_signals"] = short_signals

    df_signals = df[["close", "long_signals", "short_signals", "time"]].iloc[-2]

    print("Finished calculating signals 🚀")
    ######################################################

    # -----------------------
    # Place the order section
    # -----------------------
    entry_offset = 0.001  # 0.0% entry offset of a signal price
    risk = 0.015  # 1.5%
    RR = 2  # 2:1

    BTC_price = df["close"].values[-1]
    # Example usage
    price = BTC_price  # Current price of BTC

    position_size = calculate_position_size(
        price, loss_amount_in_usd=2.5, percentage_loss=risk
    )
    position_size = np.round(position_size, 3)
    print("🧮 BTC Position Size:", position_size)

    if df_signals["long_signals"] == True:
        long_order_text = "🟢 Found new long!"
        print(long_order_text)
        

        long_order(
            signal_price=df_signals["close"],
            position_size=position_size,
            SL=risk,
            RR=RR,
            entry_offset=entry_offset,
            ticker="BTCUSDT",
        )
    else:
        long_order_text = "📣 No new long"
        print(long_order_text)
        

    if df_signals["short_signals"] == True:
        short_order_text = "🔴 Found new short!"
        print(short_order_text)
        

        short_order(
            signal_price=df_signals["close"],
            position_size=position_size,
            SL=risk,
            RR=RR,
            entry_offset=entry_offset,
            ticker="BTCUSDT",
        )
    else:
        short_order_text = "📣 No new short"
        print(short_order_text)
        

    print("--------------------------------------------------\n")
    # wallet_balance()
