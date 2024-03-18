import time as t
import datetime as dt

now_basic_unix = t.time()

def now_basic_bare():
    return dt.datetime.now()

def now_formatted():
    return dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

now_basic_bare_utc = dt.datetime.utcnow()
now_basic_utc = dt.datetime.now(dt.timezone.utc)

# HOURLY TIME REFERENCES
# LAST SECOND OF PREVIOUS DAY: now_previous_hour_last = dt.datetime.now(dt.timezone.utc).replace(minute=0, second=0, microsecond=0) - dt.timedelta(seconds=1)
now_previous_hour = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
three_hours_ago = now_previous_hour - dt.timedelta(hours=3)
twelve_hours_ago = now_previous_hour - dt.timedelta(hours=12)
twenty_four_hours_ago = now_previous_hour - dt.timedelta(hours=24)
fifty_hours_ago = now_previous_hour - dt.timedelta(hours=50)
one_hundred_thirty_hours_ago = now_previous_hour - dt.timedelta(hours=130)

# DAILY TIME REFERENCES
# LAST SECOND OF PREVIOUS HOUR: now_previous_day = dt.datetime.now(dt.timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) - dt.timedelta(seconds=1)
now_previous_day = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
three_days_ago = now_previous_day - dt.timedelta(days=3)
ninety_days_ago = now_previous_day - dt.timedelta(days=90)
one_hundred_eighty_days_ago = now_previous_day - dt.timedelta(days=180)

now2 = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)
now3 = dt.datetime.now(dt.timezone.utc).replace(minute=0, second=0, microsecond=0) - dt.timedelta(seconds=1)

def timestamp_utc(timestamp):
    return dt.datetime.fromtimestamp(timestamp, tz=dt.timezone.utc)

def timestamp_local(timestamp):
    return dt.datetime.fromtimestamp(timestamp)

# timestamp_utc = dt.datetime.fromtimestamp(hourly_data[0], tz=dt.timezone.utc)
# timestamp_local = dt.datetime.fromtimestamp(hourly_data[0])