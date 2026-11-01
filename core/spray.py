"""Spray window finder. Guideline thresholds (assumptions, adjust to the product label):
wind 3 to 15 km/h, no rain for 4 hours, rain probability at most 30 percent, air temperature at most 35 C,
daytime 6 to 19 hours (early morning and evening are best)."""
from datetime import datetime, timedelta


def _num(x, default=0.0):
    return default if x is None else float(x)


def spray_windows(h, now_iso, hours_ahead=48, min_len=2, top=3,
                  min_wind=3, max_wind=15, max_pop=30, max_temp=35):
    times = h["time"]
    start = next((i for i, x in enumerate(times) if x >= now_iso), len(times))
    end = min(len(times), start + hours_ahead)
    good = []
    for i in range(start, end):
        hr = int(times[i][11:13])
        dry4 = all(_num(v) <= 0.1 for v in h["precipitation"][i:i + 4])
        ok = (6 <= hr <= 19 and dry4 and _num(h["precipitation_probability"][i]) <= max_pop
              and min_wind <= _num(h["wind_speed_10m"][i]) <= max_wind
              and _num(h["temperature_2m"][i]) <= max_temp)
        good.append(ok)
    windows, run = [], None
    for k, ok in enumerate(good):
        i = start + k
        if ok and run is None:
            run = i
        if (not ok or k == len(good) - 1) and run is not None:
            last = i if ok else i - 1
            if last - run + 1 >= min_len:
                e = datetime.fromisoformat(times[last]) + timedelta(hours=1)
                windows.append({"start": times[run], "end": e.strftime("%Y-%m-%dT%H:%M")})
            run = None
    return windows[:top]
