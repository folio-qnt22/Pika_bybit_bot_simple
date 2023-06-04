
import numpy as np
import os
import pandas as pd

import requests
import time

from datetime import datetime, timedelta
from dateutil import parser

from urllib.request import urlopen
from pybit.unified_trading import HTTP

import schedule
from Bot import run as run

def round_to_five_minutes():
    current_time = time.localtime()
    rounded_minutes = ((current_time.tm_min + 4) // 5) * 5
    rounded_time = time.struct_time((current_time.tm_year, current_time.tm_mon, current_time.tm_mday,
                                     current_time.tm_hour, rounded_minutes, 0, current_time.tm_wday,
                                     current_time.tm_yday, current_time.tm_isdst))
    return time.mktime(rounded_time)

while True:
    current_time = time.localtime()
    if current_time.tm_min % 5 == 0 and current_time.tm_sec < 40:
        run()
        time.sleep(30)  # Wait for 5 minutes
    else:
        next_run_time = round_to_five_minutes()
        wait_time = max(next_run_time - time.time(), 0)
        time.sleep(wait_time)
